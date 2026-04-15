import bpy

from bpy.types import Menu
from .utils.get_addon_prefs import get_addon_preferences


class CHERUBPIES_MT_Modifiers(Menu):
    bl_label = "Cherub Pies Modifiers"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        addon_prefs = get_addon_preferences()
        self.scale_y = addon_prefs.scale_y if addon_prefs else 1.0
        pie.scale_y = self.scale_y
        # operator_enum will just spread all available options
        # for the type enum of the operator on the pie
        pie.operator(
            "object.modifier_add", text="Mirror", icon="MOD_MIRROR"
        ).type = "MIRROR"
        pie.operator(
            "object.modifier_add", text="Array", icon="MOD_ARRAY"
        ).type = "ARRAY"
        pie.operator(
            "object.modifier_add", text="Simple Deform", icon="MOD_SIMPLEDEFORM"
        ).type = "SIMPLE_DEFORM"
        pie.operator(
            "object.modifier_add", text="Solidify", icon="MOD_SOLIDIFY"
        ).type = "SOLIDIFY"
        pie.operator(
            "object.modifier_add", text="Subsurf", icon="MOD_SUBSURF"
        ).type = "SUBSURF"
        pie.operator(
            "object.modifier_add", text="Triangulate", icon="MOD_TRIANGULATE"
        ).type = "TRIANGULATE"
        pie.operator(
            "object.modifier_add", text="Wireframe", icon="MOD_WIREFRAME"
        ).type = "WIREFRAME"
        pie.operator(
            "object.modifier_add", text="Remesh", icon="MOD_REMESH"
        ).type = "REMESH"
