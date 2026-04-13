import bpy

from bpy.types import Menu
from .utils.get_addon_prefs import get_addon_preferences
from ..operators.utils.get_tool_settings import get_tool_settings


class CHERUBPIES_MT_Selection(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Cherub Pies Select"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        ts = context.tool_settings
        vert_sel = (True, False, False)
        face_sel = (False, False, True)
        context_sel = [False, False, False]

        for i in range(3):
            context_sel[i] = ts.mesh_select_mode[i]

        # Determine appropriate select type
        if context_sel == list(vert_sel):
            select_type = "VERT_NORMAL"
        elif context_sel == list(face_sel):
            select_type = "FACE_NORMAL"
        else:
            select_type = "FACE_ANGLE"

        # Left
        pie.operator("mesh.select_mode", text="Vertex", icon='VERTEXSEL').type = 'VERT'
        # Right
        pie.operator("mesh.select_mode", text="Edge", icon='EDGESEL').type = 'EDGE'
        # Bottom
        pie.operator("mesh.select_mode", text="Face", icon='FACESEL').type = 'FACE'
        # Top
        pie.operator("mesh.separate", text="Split Selected", icon='UV_SYNC_SELECT')
        # Top Left
        pie.operator("mesh.select_all", text="Invert Selection", icon='ARROW_LEFTRIGHT').action = 'INVERT'

        # Top Right — Select Similar
        pie.operator("mesh.select_similar", text="Select Similar", icon="FACESEL")

        # Bottom Left — X-Ray & Auto Merge toggles in vertical layout
        box = pie.split().box().column(align=True)
        box.label(text="View Options:")
        box.prop(context.space_data.shading, "show_xray", text="X-Ray", toggle=True)
        box.prop(context.tool_settings, "use_mesh_automerge", text="Auto Merge", toggle=True)

        # Bottom Right — only in vertex mode
        if context_sel == list(vert_sel):
            box = pie.split().box().column(align=True)
            box.scale_y = 1.2
            box.label(text="Select Axis:")
            row = box.row(align=True)
            row.operator("mesh.select_axis", text="", icon="EVENT_X").axis = "X"
            row.operator("mesh.select_axis", text="", icon="EVENT_Y").axis = "Y"
            row.operator("mesh.select_axis", text="", icon="EVENT_Z").axis = "Z"



    #OLD CODE
    
    # def draw(self, context):
    #     context_sel = [False, False, False]
    #     face_sel = (False, False, True)
    #     edge_sel = (False, True, False)
    #     vert_sel = (True, False, False)
    #     total_face_sel = bpy.context.object.data.total_vert_sel
    #     total_edge_sel = bpy.context.object.data.total_edge_sel
    #     total_vert_sel = bpy.context.object.data.total_vert_sel
    #     ts = get_tool_settings()

    #     layout = self.layout

    #     pie = layout.menu_pie()
    #     self.scale_y = get_addon_preferences().scale_y
    #     # operator_enum will just spread all available options
    #     # for the type enum of the operator on the pie
    #     pie.scale_y = self.scale_y

    #     #! 4 - LEFT
    #     pie.operator_enum("mesh.select_mode", "type")
    #     # pie.separator()
    #     #! 6 - RIGHT
    #     pie.operator(
    #         "mesh.separate", text="Split Selected", icon="UV_SYNC_SELECT"
    #     ).type = "SELECTED"

    #     #! 2 - BOTTOM
    #     pie.operator(
    #         "mesh.select_all", text="Invert Selection", icon="UV_ISLANDSEL"
    #     ).action = "INVERT"

    #     #8 - TOP
    #     for i in range(len(context_sel)):
    #         context_sel[i] = ts.mesh_select_mode[i]

    #     pie.operator(
    #         "mesh.select_similar", text="Select Normal", icon="FACESEL"
    #     ).type = (
    #         "FACE_NORMAL"
    #         if context_sel == list(vert_sel) or context_sel == list(face_sel)
    #         else "FACE_ANGLE"
    #     )

    #     #! 7 - TOP - LEFT
    #     # col = pie.split().box().row().column()
    #     # col.scale_y = self.scale_y

    #     # col.operator(
    #     #      "wm.context_toggle", text="Limit to Visible"
    #     #  ).data_path = "space_data.shading.show_xray"

    #     # shading = bpy.context.space_data.shading
    #     # tool_settings = bpy.context.tool_settings

    #     # row = col.row()
    #     # row.prop(
    #     #     shading,
    #     #     "show_xray",
    #     #     text=""
    #     #     if bpy.context.space_data.shading.type == "SOLID"
    #     #     else "X-Ray",
    #     #     toggle=False,
    #     # )

    #     # if bpy.context.space_data.shading.type == "SOLID":
    #     #     sub = row.row()
    #     #     sub.active = shading.show_xray
    #     #     sub.prop(shading, "xray_alpha", text="X-Ray", toggle=False)
    #     #     # X-ray mode is off when alpha is 1.0
    #     #     xray_active = shading.show_xray and shading.xray_alpha != 1

    #     # bpy.context.space_data.shading.show_xray = False
    #     # row = col.row(align=True)
    #     # row.prop(
    #     #     tool_settings, "use_mesh_automerge", text="Auto Merge", toggle=False
    #     # )

    #     # col.operator(
    #     #      "wm.context_toggle", text="Auto Merge", icon="AUTOMERGE_ON"
    #     # ).data_path = "scene.tool_settings.use_mesh_automerge"

    #     #! 9 - TOP - RIGHT
    #     box = pie.split().box().row().column(align=True)
    #     box.scale_y = self.scale_y
    #     box.label(text="Select Axis:")
    #     col = box.row().column_flow(columns=3, align=True)
    #     col.label(text="Select Half", icon="MANIPUL")
    #     col.emboss = "PULLDOWN_MENU"
    #     col.ui_units_x = 4
    #     col.ui_units_y = 4
    #     col.alignment = "EXPAND"

    #     col.operator("mesh.select_axis", text="", icon="EVENT_X").axis = "X"
    #     col.operator("mesh.select_axis", text="", icon="EVENT_Y").axis = "Y"
    #     col.operator("mesh.select_axis", text="", icon="EVENT_Z").axis = "Z"

        #! 1 - BOTTOM - LEFT
        # pie.separator()

        #! 3 - BOTTOM - RIGHT
        # pie.separator()
