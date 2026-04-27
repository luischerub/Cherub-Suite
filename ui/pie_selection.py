import bpy

from bpy.types import Menu


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


