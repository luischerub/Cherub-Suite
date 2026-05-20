import bpy
import math
import os
from mathutils import Vector

class CHERUB_OT_AssetLibRender(bpy.types.Operator):
    """Render high-quality thumbnails for selected mesh objects"""
    bl_idname = "cherub.assetlib_render_assets"
    bl_label = "Render Thumbnails"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.cherub_settings
        cam = scene.camera

        if not cam:
            self.report({'ERROR'}, "Please add a camera to the scene first!")
            return {'CANCELLED'}

        # 1. Filter: selected mesh objects only
        assets = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not assets:
            self.report({'WARNING'}, "No selected mesh objects found.")
            return {'CANCELLED'}

        # 2. Setup Render Environment
        original_path = scene.render.filepath
        scene.render.resolution_x = props.render_res
        scene.render.resolution_y = props.render_res
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.film_transparent = True
        
        output_folder = bpy.path.abspath(props.output_path)
        if not output_folder or output_folder.strip("/\\") == "":
            self.report({'WARNING'}, "Please define an output path before rendering.")
            return {'CANCELLED'}
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # 3. Render Loop
        # Hide all meshes and font objects to avoid background clutter
        all_objects = [o for o in scene.objects if o.type in {'MESH', 'FONT'}]
        for obj in all_objects:
            obj.hide_render = True

        # Use the active object as the framing reference — it's the object the artist
        # positioned the camera for.  Fall back to assets[0] if active isn't a mesh.
        reference = context.active_object if (context.active_object and context.active_object.type == 'MESH') else assets[0]
        cam_offset = cam.location.copy() - reference.matrix_world.translation

        # Pre-compute camera basis once — rotation never changes during the loop.
        if props.fit_per_object:
            cam_mat    = cam.matrix_world.to_3x3()
            cam_right  = cam_mat.col[0].normalized()    # camera local X
            cam_up     = cam_mat.col[1].normalized()    # camera local Y
            cam_look   = (-cam_mat.col[2]).normalized() # camera looks along -Z local
            fov_half   = cam.data.angle / 2             # square render → equal H/V FOV
            tan_fov    = math.tan(fov_half)
            depsgraph  = context.evaluated_depsgraph_get()

        for obj in assets:
            obj.hide_render = False

            if props.fit_per_object:
                # Project every actual mesh vertex (evaluated — modifiers applied) onto
                # the camera image plane, then solve for the minimum distance d at which
                # all vertices fit inside the FOV.
    
                obj_eval  = obj.evaluated_get(depsgraph)
                mesh_eval = obj_eval.to_mesh()
                mat       = obj.matrix_world

                if mesh_eval.vertices:
                    verts = [mat @ v.co for v in mesh_eval.vertices]
                else:
                    # Fallback for meshes with no vertices (shouldn't normally happen).
                    verts = [mat @ Vector(obj.bound_box[i]) for i in range(8)]

                obj_eval.to_mesh_clear()

                # Compute world-space bbox center as the camera's look-at point.
                xs = [v.x for v in verts];  ys = [v.y for v in verts];  zs = [v.z for v in verts]
                bbox_center = Vector(((min(xs) + max(xs)) / 2,
                                      (min(ys) + max(ys)) / 2,
                                      (min(zs) + max(zs)) / 2))

                d = 0.0
                for v in verts:
                    local        = v - bbox_center
                    depth_offset = local.dot(cam_look)
                    d = max(d,
                            abs(local.dot(cam_right)) / tan_fov - depth_offset,
                            abs(local.dot(cam_up))    / tan_fov - depth_offset)

                cam.location = bbox_center - cam_look * (d * props.padding)
            else:
                # Legacy: apply the same camera offset from each object's origin.
                cam.location = obj.matrix_world.translation + cam_offset

            # Set unique filename and render
            scene.render.filepath = os.path.join(output_folder, f"{obj.name}.webp")
            bpy.ops.render.render(write_still=True)

            obj.hide_render = True

        # Restore original path
        scene.render.filepath = original_path
        
        self.report({'INFO'}, f"Successfully rendered {len(assets)} assets.")
        return {'FINISHED'}