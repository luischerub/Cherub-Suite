import bmesh
import bpy
import heapq
from time import time
from mathutils.geometry import interpolate_bezier


BEZIER_DEFORM_INSTANCE = None
SAMPLE_STEPS = 48
MAX_CONTROL_SELECTION = 128
MAX_PATH_VERTICES = 5000


class BezierDeformProperties(bpy.types.PropertyGroup):
    falloff: bpy.props.FloatProperty(
        name='Proportional Size',
        description='Deformation radius around the Bezier path',
        min=0.0,
        default=0.7,
        subtype='DISTANCE',
    )


class MESH_OT_bezier_deform(bpy.types.Operator):
    bl_idname = 'mesh.bezier_deform'
    bl_label = 'Bezier Deform'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bool(obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        del event
        global BEZIER_DEFORM_INSTANCE
        BEZIER_DEFORM_INSTANCE = self

        mesh_object = context.active_object
        bm = bmesh.from_edit_mesh(mesh_object.data)
        bm.verts.ensure_lookup_table()

        total_vertices = len(bm.verts)
        selected_count = sum(1 for vertex in bm.verts if vertex.select)
        if selected_count < 2:
            self.report({'WARNING'}, 'Select at least two vertices to run Bezier Deform')
            return {'CANCELLED'}

        if selected_count == total_vertices and total_vertices > 200:
            self.report({'WARNING'}, 'Selection too large (all vertices selected). Select only guide vertices.')
            return {'CANCELLED'}

        if selected_count > MAX_CONTROL_SELECTION:
            self.report(
                {'WARNING'},
                f'Selection too large ({selected_count}). Limit guide vertices to {MAX_CONTROL_SELECTION} or fewer.'
            )
            return {'CANCELLED'}

        control_vertices, path_vertices = self._path_vertices_from_selection(bm)
        if len(path_vertices) < 2:
            self.report({'WARNING'}, 'Select a continuous vertex chain with at least two vertices')
            return {'CANCELLED'}

        if len(path_vertices) > MAX_PATH_VERTICES:
            self.report(
                {'WARNING'},
                f'Computed path is too large ({len(path_vertices)} vertices). Reduce selection complexity.'
            )
            return {'CANCELLED'}

        self.mesh_object = mesh_object
        self.mesh_data = mesh_object.data
        self.vertex_indices = [vertex.index for vertex in path_vertices]
        self.original_positions = {vertex.index: vertex.co.copy() for vertex in bm.verts}
        self.original_active_name = mesh_object.name
        self.original_selection_names = [obj.name for obj in context.selected_objects]
        self.mesh_world_inverse = mesh_object.matrix_world.inverted()

        if not hasattr(context.scene, 'bezierDeformProperties'):
            try:
                if not hasattr(bpy.types, 'BezierDeformProperties'):
                    bpy.utils.register_class(BezierDeformProperties)
                bpy.types.Scene.bezierDeformProperties = bpy.props.PointerProperty(type=BezierDeformProperties)
            except ValueError:
                bpy.types.Scene.bezierDeformProperties = bpy.props.PointerProperty(type=BezierDeformProperties)
            except Exception as ex:
                self.report({'ERROR'}, f'Bezier Deform properties setup failed: {ex}')
                return {'CANCELLED'}

        self.bezierDeformProperties = context.scene.bezierDeformProperties
        self._enable_wireframe_display(context)
        self.curve_object = None
        self.timer = None
        self.last_snapshot = None
        self.last_left_click_time = 0.0
        self.double_click_wait_time = (
            context.preferences.inputs.mouse_double_click_time / 1000.0
            if hasattr(context.preferences, 'inputs') else 0.3
        )

        path_points = [mesh_object.matrix_world @ vertex.co for vertex in path_vertices]
        curve_points = [mesh_object.matrix_world @ vertex.co for vertex in control_vertices]
        self.vertex_fractions = self._curve_fractions(path_points)
        self.path_vertex_indices = [vertex.index for vertex in path_vertices]
        self.path_original_world_points = path_points
        self._prepare_falloff_data()

        bpy.ops.object.mode_set(mode='OBJECT')
        self._create_curve_object(context, curve_points)
        self._apply_curve_deformation()
        self.last_snapshot = self._curve_snapshot()

        self.timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)
        self._set_header(context, self._header_message())
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not self._curve_exists():
            self._restore_mesh()
            self._finish(context, cancelled=True)
            return {'CANCELLED'}

        if event.value == 'PRESS':
            if event.type in {'LEFT_BRACKET', 'MINUS'}:
                self._adjust_falloff(context, -0.05)
                return {'RUNNING_MODAL'}
            if event.type in {'RIGHT_BRACKET', 'EQUAL'}:
                self._adjust_falloff(context, 0.05)
                return {'RUNNING_MODAL'}
            if event.ctrl and event.type == 'WHEELDOWNMOUSE':
                self._adjust_falloff(context, -0.05)
                return {'RUNNING_MODAL'}
            if event.ctrl and event.type == 'WHEELUPMOUSE':
                self._adjust_falloff(context, 0.05)
                return {'RUNNING_MODAL'}

        if event.type == 'TIMER':
            snapshot = self._curve_snapshot()
            if snapshot != self.last_snapshot:
                self.last_snapshot = snapshot
                self._apply_curve_deformation()
            return {'RUNNING_MODAL'}

        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            current_time = time()
            if (current_time - self.last_left_click_time) <= self.double_click_wait_time:
                self._apply_curve_deformation()
                self._finish(context, cancelled=False)
                return {'FINISHED'}
            self.last_left_click_time = current_time

        if event.value == 'PRESS' and event.type == 'ESC':
            self._restore_mesh()
            self._finish(context, cancelled=True)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def _header_message(self):
        return (
            'Bezier Deform | Edit curve points | '
            'Falloff: %.2f ([ / ], Ctrl+Wheel) | Double LMB confirm, Esc cancel'
        ) % self.bezierDeformProperties.falloff

    def _adjust_falloff(self, context, delta):
        self.bezierDeformProperties.falloff = max(0.0, self.bezierDeformProperties.falloff + delta)
        self._apply_curve_deformation()
        self._set_header(context, self._header_message())

    def _path_vertices_from_selection(self, bm):
        controls = self._ordered_selected_controls(bm)
        if len(controls) < 2:
            return [], []

        full_path_indices = []
        for index in range(len(controls) - 1):
            start_index = controls[index].index
            end_index = controls[index + 1].index
            segment = self._shortest_path_indices(bm, start_index, end_index)
            if len(segment) < 2:
                return [], []
            if not full_path_indices:
                full_path_indices.extend(segment)
            else:
                full_path_indices.extend(segment[1:])

        return controls, [bm.verts[index] for index in full_path_indices]

    def _ordered_selected_controls(self, bm):
        selected = [vertex for vertex in bm.verts if vertex.select]
        if len(selected) < 2:
            return []

        # Prefer explicit user intent through selection history when available.
        history_controls = []
        seen = set()
        for element in bm.select_history:
            if isinstance(element, bmesh.types.BMVert) and element.select and element.index not in seen:
                history_controls.append(element)
                seen.add(element.index)

        if len(history_controls) >= 2:
            for vertex in selected:
                if vertex.index not in seen:
                    history_controls.append(vertex)
            return history_controls

        if len(selected) == 2:
            return selected

        selected_by_index = {vertex.index: vertex for vertex in selected}
        active = bm.select_history.active
        if isinstance(active, bmesh.types.BMVert) and active.select:
            start_index = active.index
        else:
            start_index = selected[0].index

        ordered_indices = [start_index]
        remaining = set(selected_by_index.keys())
        remaining.remove(start_index)

        while remaining:
            current_index = ordered_indices[-1]
            best_target = None
            best_path = None
            best_length = float('inf')
            for target_index in remaining:
                path = self._shortest_path_indices(bm, current_index, target_index)
                if len(path) < 2:
                    continue
                length = self._path_length(bm, path)
                if length < best_length:
                    best_length = length
                    best_target = target_index
                    best_path = path

            if best_target is None or best_path is None:
                return []

            ordered_indices.append(best_target)
            remaining.remove(best_target)

        return [selected_by_index[index] for index in ordered_indices]

    def _path_length(self, bm, path_indices):
        total = 0.0
        for index in range(len(path_indices) - 1):
            vertex_a = bm.verts[path_indices[index]]
            target_index = path_indices[index + 1]
            edge = next(
                (edge for edge in vertex_a.link_edges if edge.other_vert(vertex_a).index == target_index),
                None,
            )
            if edge is None:
                return float('inf')
            total += edge.calc_length()
        return total

    def _shortest_path_indices(self, bm, start_index, end_index):
        if start_index == end_index:
            return [start_index]

        distances = {start_index: 0.0}
        previous = {}
        queue = [(0.0, start_index)]

        while queue:
            current_distance, current_index = heapq.heappop(queue)
            if current_index == end_index:
                break

            if current_distance > distances.get(current_index, float('inf')):
                continue

            current_vertex = bm.verts[current_index]
            for edge in current_vertex.link_edges:
                other_index = edge.other_vert(current_vertex).index
                new_distance = current_distance + edge.calc_length()
                if new_distance < distances.get(other_index, float('inf')):
                    distances[other_index] = new_distance
                    previous[other_index] = current_index
                    heapq.heappush(queue, (new_distance, other_index))

        if end_index not in distances:
            return []

        path = [end_index]
        while path[-1] != start_index:
            path.append(previous[path[-1]])
        path.reverse()
        return path

    def _curve_fractions(self, points):
        if len(points) == 2:
            return [0.0, 1.0]

        distances = [0.0]
        total_length = 0.0
        for index in range(1, len(points)):
            total_length += (points[index] - points[index - 1]).length
            distances.append(total_length)

        if total_length == 0.0:
            return [0.0 for _point in points]
        return [distance / total_length for distance in distances]

    def _create_curve_object(self, context, points):
        curve_data = bpy.data.curves.new(name='CherubBezierShaper', type='CURVE')
        curve_data.dimensions = '3D'
        spline = curve_data.splines.new('BEZIER')
        spline.bezier_points.add(len(points) - 1)

        for index, point in enumerate(points):
            bezier_point = spline.bezier_points[index]
            bezier_point.co = point
            bezier_point.handle_left_type = 'AUTO'
            bezier_point.handle_right_type = 'AUTO'

        spline.use_endpoint_u = True

        curve_object = bpy.data.objects.new('CherubBezierShaper', curve_data)
        context.collection.objects.link(curve_object)
        self.curve_object = curve_object

        bpy.ops.object.select_all(action='DESELECT')
        curve_object.select_set(True)
        context.view_layer.objects.active = curve_object
        bpy.ops.object.mode_set(mode='EDIT')

    def _curve_exists(self):
        return bool(self.curve_object and self.curve_object.name in bpy.data.objects)

    def _curve_snapshot(self):
        spline = self.curve_object.data.splines[0]
        return tuple(
            (
                tuple(point.co),
                tuple(point.handle_left),
                tuple(point.handle_right),
            )
            for point in spline.bezier_points
        )

    def _sample_curve(self, fractions):
        spline = self.curve_object.data.splines[0]
        bezier_points = spline.bezier_points
        if len(bezier_points) == 1:
            return [bezier_points[0].co.copy() for _fraction in fractions]

        samples = [bezier_points[0].co.copy()]
        lengths = [0.0]

        for segment_index in range(len(bezier_points) - 1):
            point_a = bezier_points[segment_index]
            point_b = bezier_points[segment_index + 1]
            segment_samples = list(
                interpolate_bezier(
                    point_a.co,
                    point_a.handle_right,
                    point_b.handle_left,
                    point_b.co,
                    SAMPLE_STEPS,
                )
            )
            if segment_index:
                segment_samples = segment_samples[1:]

            for sample in segment_samples:
                lengths.append(lengths[-1] + (sample - samples[-1]).length)
                samples.append(sample.copy())

        total_length = lengths[-1]
        if total_length == 0.0:
            return [samples[0].copy() for _fraction in fractions]

        results = []
        sample_index = 0
        for fraction in fractions:
            target_length = total_length * fraction
            while sample_index + 1 < len(lengths) and lengths[sample_index + 1] < target_length:
                sample_index += 1

            next_index = min(sample_index + 1, len(samples) - 1)
            start_length = lengths[sample_index]
            end_length = lengths[next_index]

            if end_length == start_length:
                results.append(samples[sample_index].copy())
                continue

            factor = (target_length - start_length) / (end_length - start_length)
            results.append(samples[sample_index].lerp(samples[next_index], factor))

        return results

    def _prepare_falloff_data(self):
        path_index_by_vertex = {
            vertex_index: index
            for index, vertex_index in enumerate(self.path_vertex_indices)
        }
        nearest_path_index = {}
        nearest_path_distance = {}

        for vertex_index, original_local in self.original_positions.items():
            if vertex_index in path_index_by_vertex:
                nearest_path_index[vertex_index] = path_index_by_vertex[vertex_index]
                nearest_path_distance[vertex_index] = 0.0
                continue

            world_co = self.mesh_object.matrix_world @ original_local
            best_distance = float('inf')
            best_path_index = 0
            for path_index, path_world in enumerate(self.path_original_world_points):
                distance = (world_co - path_world).length
                if distance < best_distance:
                    best_distance = distance
                    best_path_index = path_index

            nearest_path_index[vertex_index] = best_path_index
            nearest_path_distance[vertex_index] = best_distance

        self.nearest_path_index = nearest_path_index
        self.nearest_path_distance = nearest_path_distance

    def _falloff_weight(self, distance):
        radius = self.bezierDeformProperties.falloff
        if radius <= 0.0:
            return 0.0
        if distance >= radius:
            return 0.0
        return max(0.0, 1.0 - (distance / radius))

    def _apply_curve_deformation(self):
        sampled_points = self._sample_curve(self.vertex_fractions)

        path_deltas = {}
        for path_index, world_position in enumerate(sampled_points):
            path_deltas[path_index] = world_position - self.path_original_world_points[path_index]

        path_set = set(self.path_vertex_indices)
        for vertex_index, original_local in self.original_positions.items():
            source_path_index = self.nearest_path_index[vertex_index]
            delta = path_deltas[source_path_index]

            if vertex_index in path_set:
                influence = 1.0
            else:
                influence = self._falloff_weight(self.nearest_path_distance[vertex_index])

            if influence <= 0.0:
                self.mesh_data.vertices[vertex_index].co = original_local
                continue

            new_world = (self.mesh_object.matrix_world @ original_local) + (delta * influence)
            self.mesh_data.vertices[vertex_index].co = self.mesh_world_inverse @ new_world

        self.mesh_data.update()

    def _restore_mesh(self):
        for vertex_index, position in self.original_positions.items():
            self.mesh_data.vertices[vertex_index].co = position
        self.mesh_data.update()

    def _finish(self, context, cancelled):
        global BEZIER_DEFORM_INSTANCE
        if self.timer is not None:
            context.window_manager.event_timer_remove(self.timer)
            self.timer = None

        self._set_header(context, None)

        if self._curve_exists():
            curve_data = self.curve_object.data
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.objects.remove(self.curve_object, do_unlink=True)
            if curve_data.users == 0:
                bpy.data.curves.remove(curve_data)
            self.curve_object = None

        self._restore_wireframe_display(context)
        self._restore_mesh_object(context)
        if not cancelled:
            bmesh.update_edit_mesh(self.mesh_data)
        BEZIER_DEFORM_INSTANCE = None

    def _enable_wireframe_display(self, context):
        self._old_show_wire = self.mesh_object.show_wire
        self._old_show_all_edges = self.mesh_object.show_all_edges
        self.mesh_object.show_wire = True
        self.mesh_object.show_all_edges = True

        self._old_overlay_wireframes = None
        space_data = context.space_data
        if space_data and hasattr(space_data, 'overlay'):
            self._old_overlay_wireframes = space_data.overlay.show_wireframes
            space_data.overlay.show_wireframes = True

    def _restore_wireframe_display(self, context):
        if hasattr(self, '_old_show_wire'):
            self.mesh_object.show_wire = self._old_show_wire
        if hasattr(self, '_old_show_all_edges'):
            self.mesh_object.show_all_edges = self._old_show_all_edges

        if getattr(self, '_old_overlay_wireframes', None) is not None:
            space_data = context.space_data
            if space_data and hasattr(space_data, 'overlay'):
                space_data.overlay.show_wireframes = self._old_overlay_wireframes

    def _restore_mesh_object(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        for object_name in self.original_selection_names:
            obj = bpy.data.objects.get(object_name)
            if obj is not None:
                obj.select_set(True)

        mesh_object = bpy.data.objects.get(self.original_active_name)
        if mesh_object is not None:
            context.view_layer.objects.active = mesh_object
            bpy.ops.object.mode_set(mode='EDIT')

    def _set_header(self, context, message):
        area = context.area
        if area and area.type == 'VIEW_3D':
            area.header_text_set(message)
