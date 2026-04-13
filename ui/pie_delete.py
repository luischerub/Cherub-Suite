import bpy

from bpy.types import Menu
from .utils.get_addon_prefs import get_addon_preferences
from ..operators.utils.get_tool_settings import get_tool_settings


class CHERUBPIES_MT_Delete(Menu):
    bl_label = "Cherub Pies Delete"

    def draw(self, context):
        context_sel = [False, False, False]
        face_sel = (False, False, True)
        edge_sel = (False, True, False)
        vert_sel = (True, False, False)
        total_face_sel = bpy.context.object.data.total_vert_sel
        total_edge_sel = bpy.context.object.data.total_edge_sel
        total_vert_sel = bpy.context.object.data.total_vert_sel
        ts = get_tool_settings()

        layout = self.layout
        # toolsettings = context.tool_settings
        ob = context

        if ob.object.type == "MESH":
            pie = layout.menu_pie()
            self.scale_y = get_addon_preferences().scale_y

            pie.scale_y = self.scale_y

            #! 4 - LEFT
            pie.operator(
                "mesh.delete", text="Delete Vertices", icon="VERTEXSEL"
            ).type = "VERT"

            #! 6 - RIGHT
            pie.operator(
                "mesh.delete", text="Delete Edges", icon="EDGESEL"
            ).type = "EDGE"

            #! 2 - BOTTOM
            pie.operator(
                "mesh.delete", text="Delete Faces", icon="FACESEL"
            ).type = "FACE"

            #! 8 - TOP
            pie.operator("mesh.remove_doubles", icon="STICKY_UVS_LOC")

            #! 7 - TOP - LEFT
            pie.operator("mesh.dissolve_edges", icon="SNAP_EDGE")

            #! 9 - TOP - RIGHT
            pie.operator("mesh.edge_collapse", icon="UV_EDGESEL")

            #! 1 - BOTTOM - LEFT
            pie.operator("mesh.dissolve_verts", icon="SNAP_GRID")

            #! 3 - BOTTOM - RIGHT
            for i in range(len(context_sel)):
                context_sel[i] = ts.mesh_select_mode[i]

            pie_col = pie.column()
            box01 = pie_col.column()
            box01.emboss = "RADIAL_MENU"
            box01.ui_units_x = 7
            box01.scale_y = 1.5 * pie.scale_y
            gap = pie_col.column()
            gap.separator()
            gap.scale_y = 7
            box02 = pie_col.box().column(align=True)
            box02.alignment = "CENTER"
            # box = pie.split().box().row().column()
            box02.scale_x = 1.3
            box02.scale_y = 1.333 * self.scale_y
            box02.label(text="Merge", icon="FULLSCREEN_EXIT")
            box03 = box02.split().row(align=True)
            if context_sel == list(vert_sel):
                box03.operator("mesh.merge", text="At First").type = "FIRST"
                box03.operator("mesh.merge", text="At Last").type = "LAST"
            box02.separator()
            box04 = box02.column()
            box04.operator("mesh.merge", text="At Center").type = "CENTER"
            box04.operator("mesh.merge", text="At Cursor").type = "CURSOR"
            box04.operator("mesh.merge", text="Collapse").type = "COLLAPSE"
