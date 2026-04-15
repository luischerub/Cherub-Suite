import bpy

from bpy.types import Menu
from .utils.get_addon_prefs import get_addon_preferences


class CHERUBPIES_MT_PivotOrientation(Menu):
    bl_label = "Cherub Pies Pivot and Orientation"

    def draw(self, context):
        layout = self.layout
        # obj = context.object
        pie = layout.menu_pie()
        addon_prefs = get_addon_preferences()
        self.scale_y = addon_prefs.scale_y if addon_prefs else 1.0

        pie.scale_y = self.scale_y

        #! 4 - LEFT
        # col = pie.split().box().row().column()
        # col.scale_y = self.scale_y
        # col.label("Snap Selection")
        pie.operator(
            "view3d.snap_selected_to_cursor",
            text="Selection to Cursor",
            icon="CLIPUV_HLT",
        ).use_offset = False
        # col.operator(
        #     "view3d.snap_selected_to_cursor",
        #     text="Selection to Cursor (Offset)",
        #     icon="CLIPUV_HLT",
        # ).use_offset = True
        # col.operator(
        #     "view3d.snap_selected_to_grid",
        #     text="Selection to Grid",
        #     icon="GRID",
        # )
        # col.operator(
        #     "cherub_pies.selection_cursor_to_center",
        #     text="Selected & Cursor to Center",
        #     icon="CLIPUV_HLT",
        # )
        # Icons that dont exist in 2.8: 'CURSOR'; 'ALIGN'; 'ROTACTIVE'; 'BBOX';

        #! 6 - RIGHT
        # col = pie.split().box().row().column()
        # col.scale_y = self.scale_y
        # col.label("Snap Cursor")
        pie.operator(
            "view3d.snap_cursor_to_center",
            text="Cursor to World Origin",
            icon="WORLD",
        )
        # col.operator(
        #     "view3d.snap_cursor_to_center",
        #     text="Cursor to Center",
        #     icon="CLIPUV_DEHLT",
        # )
        # )
        # col.operator(
        #     "view3d.snap_cursor_to_active",
        #     text="Cursor to Active",
        #     icon="CLIPUV_HLT",
        # )

        #! 2 - BOTTOM
        col = pie.split().box().row().column()
        col.scale_y = self.scale_y
        # col.label("Set Pivot Point")
        col.prop(context.tool_settings, "transform_pivot_point", expand=True)
        # col = pie.split().box().row().column()
        # col = pie.split().row().column()
        # col.scale_y = self.scale_y
        # col.label("Special Operator:")
        # col.operator("cherub_pies.selection_cursor_to_center", icon="QUESTION")

        #! 8 - TOP
        # col.label("Snap Origin")
        if bpy.context.mode == "OBJECT":
            pie.operator(
                "object.origin_set", text="Origin to Geometry", icon="QUESTION"
            ).type = "ORIGIN_GEOMETRY"
        else:
            pie.separator()
        # col.operator(
        #     "object.origin_set",
        #     text="Origin to Center of Mass (Volume)",
        #     icon="QUESTION",
        # ).type = "ORIGIN_CENTER_OF_VOLUME"
        # col.operator(
        #     "object.origin_set",
        #     text="Origin to Center of Mass (Surface)",
        #     icon="QUESTION",
        # ).type = "ORIGIN_CURSOR"
        #! 7 - TOP - LEFT
        pie.separator()

        #! 9 - TOP - RIGHT
        if bpy.context.mode == "OBJECT":
            pie.operator(
                "object.origin_set", text="Origin to 3D Cursor", icon="CURSOR"
            ).type = "ORIGIN_CURSOR"
        else:
            pie.separator()
        #! 1 - BOTTOM - LEFT
        pie.operator(
            "cherub_pies.selection_to_world_origin",
            text="Selection to World Orign",
            icon="WORLD",
        )
        #! 3 - BOTTOM - RIGHT
        pie.operator(
            "view3d.snap_cursor_to_selected",
            text="Cursor to Selected",
            icon="CLIPUV_HLT",
        )
