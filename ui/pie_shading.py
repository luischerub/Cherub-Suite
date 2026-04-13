import bpy
from bpy.types import Menu
from .utils.get_addon_prefs import get_addon_preferences


class CHERUBPIES_MT_Shading(Menu):
    bl_label = "Cherub Pies Shading"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        self.scale_y = get_addon_preferences().scale_y
        pie.scale_y = self.scale_y
        # Find the Smooth by Angle Geometry Nodes modifier
        obj = context.object
        smooth_by_angle_mod = None
        if obj:
            for mod in obj.modifiers:
                if mod.type == 'NODES' and getattr(mod.node_group, 'name', '') == "Smooth by Angle":
                    smooth_by_angle_mod = mod
                    break

        #! 4 - LEFT
        pie.operator(
            "mesh.mark_sharp", text="Clear Sharp", icon="MATCUBE"
        ).clear = True
        #! 6 - RIGHT
        pie.operator("mesh.mark_sharp", icon="MOD_WIREFRAME")
        #! 2 - BOTTOM
        pie.operator("mesh.faces_shade_smooth", icon="SHADING_RENDERED")
        #! 8 - TOP
        pie.operator("mesh.faces_shade_flat", icon="NODE_MATERIAL")
        #! 7 - TOP - LEFT
        pie.operator("mesh.flip_normals", icon="FILE_REFRESH")
        #! 9 - TOP - RIGHT
        pie.operator("mesh.normals_make_consistent", icon="FILE_TICK")
        #! 1 - BOTTOM - LEFT
        if smooth_by_angle_mod:
            col_box = pie.box().column(align=True)
            col_box.prop(
                smooth_by_angle_mod,
                "show_viewport",
                text="Smooth by Angle" if smooth_by_angle_mod.show_viewport else "",
                toggle=False,
            )
            col_box.prop(smooth_by_angle_mod, '["Input_1"]', text="Angle")
        else:
            op = pie.operator(
                "object.modifier_add_node_group",
                text="Add Smooth by Angle",
                icon="ADD"
            )
            op.asset_library_type = 'ESSENTIALS'
            op.relative_asset_identifier = "geometry_nodes\\smooth_by_angle.blend\\NodeTree\\Smooth by Angle"
        #! 3 - BOTTOM - RIGHT
        pie.operator(
            "object.modifier_add",
            text="Add Weighted Normal",
            icon="MOD_NORMALEDIT",
        ).type = "WEIGHTED_NORMAL"
