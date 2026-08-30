
import os
import bpy
import bpy.utils.previews

preview_collections = {}

from .operators import classes
from .ui import register_ui, unregister_ui
from .asset_settings import register_properties, unregister_properties
from .operators.add_hotkey import add_hotkey, remove_hotkey, draw_keymap_items
from bpy.types import AddonPreferences as Preferences
from bpy.props import (
    FloatProperty,
    EnumProperty,
)

class CHERUBPIES_MT_Prefs(Preferences):
    bl_idname = __package__

    prefs_tabs: EnumProperty(
        items=(
            ("options", "Options", "ADDON OPTIONS"),
            ("keymaps", "Keymaps", "CHANGE KEYMAPS"),
        ),
        default="keymaps",
    )

    scale_y: FloatProperty(name="", default=1, min=1, max=2)
    # reinstall: BoolProperty(
    #     name="Reinstall",
    #     description="Force reinstalling curernt version",
    #     default=False,
    # )

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "prefs_tabs", expand=True)

        if self.prefs_tabs == "options":
            box = layout.box()
            row = box.row(align=True)
            row.label(text="Pie Menus Buttons Scale Y :")
            row.prop(self, "scale_y", expand=True, text=" ")

            userpref = context.preferences
            view = userpref.view
            row = box.row(align=True)
            row.label(text="Pie Menus Radius :")
            row.prop(view, "pie_menu_radius", expand=True, text=" ")

        if self.prefs_tabs == "keymaps":
            wm = bpy.context.window_manager
            draw_keymap_items(wm, layout)


classes.append(CHERUBPIES_MT_Prefs)


def register():
    register_ui()
    register_properties()

    for c in classes:
        bpy.utils.register_class(c)

    if hasattr(bpy.types, "BezierDeformProperties") and not hasattr(bpy.types.Scene, "bezierDeformProperties"):
        bpy.types.Scene.bezierDeformProperties = bpy.props.PointerProperty(type=bpy.types.BezierDeformProperties)

    add_hotkey()

    pcoll = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "docs", "media")
    pcoll.load("cherub_logo", os.path.join(icons_dir, "cherub_logo.png"), 'IMAGE')
    preview_collections["main"] = pcoll

    addon_name = "Cherub Suite"
    print("Registered {}".format(addon_name))


def unregister():
    if hasattr(bpy.types.Scene, "bezierDeformProperties"):
        del bpy.types.Scene.bezierDeformProperties

    unregister_properties()
    unregister_ui()

    for c in classes:
        bpy.utils.unregister_class(c)

    remove_hotkey()

    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    addon_name = "Cherub Suite"
    print("Unregistered {}".format(addon_name))

