import bpy


class CHERUBSUITE_PT_MainPanel(bpy.types.Panel):
	bl_idname = "CHERUBSUITE_PT_main_panel"
	bl_label = "Cherub Suite"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Cherub Suite"

	def draw_header(self, context):
		from .. import preview_collections
		pcoll = preview_collections.get("main")
		if pcoll:
			self.layout.label(text="", icon_value=pcoll["cherub_logo"].icon_id)

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		props = getattr(scene, "cherub_settings", None)

		if props is None:
			layout.label(text="Asset settings not registered", icon="ERROR")
			return

		box = layout.box()

		row = box.row(align=True)
		icon = "TRIA_DOWN" if props.asset_tools_expanded else "TRIA_RIGHT"
		row.prop(
			props,
			"asset_tools_expanded",
			text="Asset Library Tools",
			emboss=False,
			icon=icon,
		)

		if not props.asset_tools_expanded:
			return

		col = box.column(align=True)
		col.prop(props, "output_path")
		col.prop(props, "render_res")
		col.prop(props, "padding")

		col.separator()

		col.operator("cherub.assetlib_rename_by_material", icon="MATERIAL")

		col.separator()

		row = col.row(align=True)
		row.operator("cherub.assetlib_render_assets", icon="RENDER_STILL")
		row.prop(props, "fit_per_object", text="", icon="ZOOM_SELECTED")

		col.separator()

		col.operator("cherub.assetlib_assign_thumb", icon="IMAGE_DATA")

		info = col.box()
		info.label(text="Select objects before rendering.", icon="INFO")
