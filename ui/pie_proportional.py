import bpy
from bpy.types import Menu
from .utils.get_addon_prefs import get_addon_preferences


class CHERUBPIES_MT_ProportionalObjectMode(Menu):
    bl_label = "Cherub Pies Proportional Object Mode"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        self.scale_y = get_addon_preferences().scale_y
        # 4 - LEFT
        pie.operator(
            "cherub_pies.proportional_sphere", text="Sphere", icon="SPHERECURVE"
        )
        # 6 - RIGHT
        pie.operator(
            "cherub_pies.proportional_root", text="Root", icon="ROOTCURVE"
        )
        # 2 - BOTTOM
        pie.operator(
            "cherub_pies.proportional_smooth", text="Smooth", icon="SMOOTHCURVE"
        )
        # 8 - TOP
        pie.prop(
            context.tool_settings,
            "use_proportional_edit_objects",
            text="Proportional On/Off",
        )
        # 7 - TOP - LEFT
        pie.operator(
            "cherub_pies.proportional_linear", text="Linear", icon="LINCURVE"
        )
        # 9 - TOP - RIGHT
        pie.operator(
            "cherub_pies.proportional_sharp", text="Sharp", icon="SHARPCURVE"
        )
        # 1 - BOTTOM - LEFT
        pie.operator(
            "cherub_pies.proportional_constant", text="Constant", icon="NOCURVE"
        )
        # 3 - BOTTOM - RIGHT
        pie.operator(
            "cherub_pies.proportional_random", text="Random", icon="RNDCURVE"
        )


# Pie ProportionalEditEdt - O
class CHERUBPIES_MT_ProportionalEditMode(Menu):
    bl_label = "Cherub Pies Proportional Edit Mode"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        self.scale_y = get_addon_preferences().scale_y
        pie.scale_y = self.scale_y
        # 4 - LEFT
        pie.operator(
            "cherub_pies.proportional_edit_connected",
            text="Connected",
            icon="PROP_CON",
        )
        # 6 - RIGHT
        pie.operator(
            "cherub_pies.proportional_edit_projected",
            text="Projected",
            icon="PROP_ON",
        )
        # 2 - BOTTOM
        pie.operator(
            "cherub_pies.proportional_edit_smooth",
            text="Smooth",
            icon="SMOOTHCURVE",
        )
        # 8 - TOP
        pie.operator(
            "cherub_pies.proportional_edit_toggle",
            text="Proportional On/Off",
            icon="PROP_ON",
        )
        # 7 - TOP - LEFT
        pie.operator(
            "cherub_pies.proportional_edit_sphere",
            text="Sphere",
            icon="SPHERECURVE",
        )
        # 9 - TOP - RIGHT
        pie.operator(
            "cherub_pies.proportional_edit_root", text="Root", icon="ROOTCURVE"
        )
        # 1 - BOTTOM - LEFT
        pie.operator(
            "cherub_pies.proportional_edit_constant",
            text="Constant",
            icon="NOCURVE",
        )
        # 3 - BOTTOM - RIGHT
        pie.menu(
            bl_idname.CHERUBPIES_MT_ProportionalMore,
            text="More",
            icon="LINCURVE",
        )


# Pie ProportionalEditEdt - O
class CHERUBPIES_MT_ProportionalMore(Menu):
    # bl_idname = "cherub_pies.proportional_more"
    bl_label = "Cherub Pies Proportional More"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        self.scale_y = get_addon_preferences().scale_y
        box = pie.split().column()
        box.scale_y = self.scale_y

        box.operator(
            "cherub_pies.proportional_edit_linear",
            text="Linear",
            icon="LINCURVE",
        )
        box.operator(
            "cherub_pies.proportional_edit_sharp",
            text="Sharp",
            icon="SHARPCURVE",
        )
        box.operator(
            "cherub_pies.proportional_edit_random",
            text="Random",
            icon="RNDCURVE",
        )
