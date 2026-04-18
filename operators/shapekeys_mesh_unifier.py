import bpy


class CHERUB_OT_UnifyMeshesToShapeKeys(bpy.types.Operator):
	"""Create a new mesh object and store selected meshes as shape keys"""

	bl_idname = "cherub.unify_meshes_to_shapekeys"
	bl_label = "Unify Meshes to Shape Keys"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		objs = [o for o in context.selected_objects if o.type == "MESH"]
		if len(objs) < 2:
			self.report({"WARNING"}, "Select at least two mesh objects")
			return {"CANCELLED"}

		base = context.view_layer.objects.active
		if not base or base.type != "MESH" or base not in objs:
			self.report({"WARNING"}, "Active object must be one of the selected meshes")
			return {"CANCELLED"}

		base_vert_count = len(base.data.vertices)
		for obj in objs:
			if len(obj.data.vertices) != base_vert_count:
				self.report(
					{"WARNING"},
					f"Vertex count mismatch: '{obj.name}' differs from active mesh",
				)
				return {"CANCELLED"}

		base_copy = base.copy()
		base_copy.data = base.data.copy()
		context.collection.objects.link(base_copy)

		avg_location = objs[0].matrix_world.translation.copy()
		for obj in objs[1:]:
			avg_location += obj.matrix_world.translation
		avg_location /= len(objs)

		base_copy.location = avg_location
		base_copy.rotation_euler = (0.0, 0.0, 0.0)
		base_copy.scale = (1.0, 1.0, 1.0)

		for obj in context.selected_objects:
			obj.select_set(False)
		base_copy.select_set(True)
		context.view_layer.objects.active = base_copy

		if base_copy.data.shape_keys is None:
			base_copy.shape_key_add(name="Basis")

		for obj in objs:
			if obj == base:
				continue
			sk = base_copy.shape_key_add(name=obj.name)
			for i, v in enumerate(obj.data.vertices):
				sk.data[i].co = v.co.copy()

		key_count = len(base_copy.data.shape_keys.key_blocks)
		self.report(
			{"INFO"},
			f"Created '{base_copy.name}' with {key_count} shape keys",
		)
		return {"FINISHED"}
