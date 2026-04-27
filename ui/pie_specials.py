import bpy
from bpy.types import Menu
from .. import __package__ as base_package


class CHERUBPIES_MT_Specials(Menu):
    bl_label = "Cherub Pies Specials"
    # bl_idname = "mesh.special_menu"

    def draw(self, context):
        ops_mesh = bpy.ops.mesh

        layout = self.layout
        pie = layout.menu_pie()
        addon_prefs = getattr(bpy.context.preferences.addons.get(base_package), 'preferences', None)
        self.scale_y = addon_prefs.scale_y if addon_prefs else 1.0

        pie.scale_y = self.scale_y

        if bpy.context.mode == "EDIT_MESH":
            #! 4 - LEFT
            col = pie.split().box().row().column()
            col.scale_y = self.scale_y

            col.operator(
                "mesh.cherub_edge_flow", text="Edge Flow", icon="IPO_CIRC"
            )
            col.operator(
                "mesh.cherub_edge_linear",
                text="Edge Linear",
                icon="IPO_LINEAR",
            )
            col.operator(
                "mesh.cherub_edge_curve", text="Edge Curve", icon="CURVE_BEZCURVE"
            )
            col.operator(
                "mesh.cherub_vertex_curve", text="Vertex Curve", icon="OUTLINER_DATA_CURVE"
            )
            #! 6 - RIGHT
            pie.operator(
                "transform.shear", text="Shear", icon="OUTLINER_DATA_LATTICE"
            )
            # pie.operator(
            #     "mesh.cherub_edge_flow",
            #     text="Set Edge Flow",
            #     icon="SNAP_FACE",)
            #! 2 - BOTTOM

            pie.operator(
                "mesh.bezier_deform", text="Bezier Deform"
            )

            #! 8 - TOP
            pie.operator(
                "mesh.bridge_edge_loops",
                text="Bridge Edge Loops",
                icon="OUTLINER_OB_LATTICE",
            )
            #! 7 - TOP - LEFT
            pie.operator("mesh.fill_grid", text="Grid Fill", icon="GRID")
            #! 9 - TOP - RIGHT
            pie.operator("mesh.inset", text="Inset", icon="SNAP_FACE")
            #! 1 - BOTTOM - LEFT
            pie.separator()
            # pie.operator(
            #     "cherub_pies.delete_half_mirror",
            #     text="Delete Half and Mirror X",
            # )
            #! 3 - BOTTOM - RIGHT
            pie_col = pie.column()
            gap = pie_col.column()
            gap.separator()
            gap.scale_x = 5
            gap.scale_y = 5
            col = pie_col.split().box().row().column()
            col.scale_y = self.scale_y

            col.operator("mesh.quads_convert_to_tris", text="Triangulate")
            col.operator("mesh.poke", text="Poke Faces")
            col.operator("mesh.face_make_planar", text="Make Planar Faces")
            col.operator("mesh.subdivide", text="Subdivide")

