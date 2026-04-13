import bpy
from bpy.types import Menu
from .utils.get_addon_prefs import get_addon_preferences


class CHERUBPIES_MT_UVs(Menu):
    bl_label = "Cherub Pies UVs"

    def draw(self, context):
        layout = self.layout
        tool_settings = context.tool_settings

        pie = layout.menu_pie()
        self.scale_y = get_addon_preferences().scale_y
        #! 4 - LEFT
        pie.scale_y = self.scale_y
        pie.operator(
            "mesh.mark_seam", text="Clear Seam", icon="SHADING_TEXTURE"
        ).clear = True
        #! 6 - RIGHT
        pie.operator("mesh.mark_seam", icon="MATERIAL")
        #! 2 - BOTTOM
        pie.operator("uv.unwrap", icon="GROUP_UVS")
        #! 8 - TOP
        pie_col = pie.column()
        gap = pie_col.column()
        gap.separator()
        gap.scale_x = 5
        gap.scale_y = 5
        main_col = pie_col.split().box()
        # main_col.ui_units_x = 7
        # main_col.ui_units_y = 10
        main_col.scale_y = self.scale_y
        col = main_col.row().column()
        # box = col.box().column()
        col.scale_y = 1.333
        row = col.row()
        row.prop(
            tool_settings, "use_edge_path_live_unwrap", toggle=False, text=""
        )
        sub = row.row()
        sub.alert = (
            True if tool_settings.use_edge_path_live_unwrap == False else False
        )
        sub.label(text="Live Unwrap")

        #! 7 - TOP - LEFT
        pie.separator()
        #! 9 - TOP - RIGHT
        if bpy.context.mode == "EDIT_MESH":
            pie.operator("cherub_pies.call_uv_window", text="UV Editor Window")
        else:
            pie.separator()
        #! 1 - BOTTOM - LEFT
        pie.operator(
            "cherub_pies.unmark_face_boundary", text="Unmark Face Boundary"
        )
        #! 3 - BOTTOM - RIGHT
        pie.operator(
            "cherub_pies.mark_face_boundary", text="Mark Face Boundary"
        )


class CHERUBPIES_MT_UVsEditor(Menu):
    bl_label = "Cherub Pies UVs Editor"

    def draw(self, context):
        layout = self.layout
        tool_settings = context.tool_settings

        pie = layout.menu_pie()
        self.scale_y = get_addon_preferences().scale_y
        #! 4 - LEFT
        pie.separator()
        #! 6 - RIGHT
        pie.separator()
        #! 2 - BOTTOM
        pie.separator()
        #! 8 - TOP
        row = pie.split().box().row()
        row.scale_y = self.scale_y
        row.prop(tool_settings, "uv_select_mode", text="", expand=True)

        #! 7 - TOP - LEFT
        pie.separator()
        #! 9 - TOP - RIGHT
        col = pie.split().box().row().column()
        col.scale_y = self.scale_y
        col.prop(
            tool_settings,
            "use_uv_select_sync",
            text="UV Sync Selection",
            expand=True,
        )
        #! 1 - BOTTOM - LEFT
        pie.operator("uv.uv_snap_to_axis", text="Snap to Axis")
        #! 3 - BOTTOM - RIGHT
        pie.operator("uv.match_islands", text="Match UV Island")
