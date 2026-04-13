"""
Copyright (C) 2020 Aditia A. Pratama
aditia.ap@gmail.com

Created by Aditia A. Pratama

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import bpy
from .operators import classes
from .utils import addon_auto_imports
from .ui import register_ui, unregister_ui
from .operators.add_hotkey import add_hotkey, remove_hotkey, draw_keymap_items
from bpy.types import AddonPreferences as Preferences
from bpy.props import (
    StringProperty,
    BoolProperty,
    FloatVectorProperty,
    FloatProperty,
    EnumProperty,
    IntProperty,
)

# load and reload submodules
##################################
modules = addon_auto_imports.setup_addon_modules(
    __path__,
    __name__,
    ignore_packages=[".utils", ".releases"],
    ignore_modules=["addon_updater"],
)

bl_info = {
    "name": "Cherub Pie Menus",
    "description": "Description of this addon",
    "author": "Fernando Lopes, Luís Cherubini & Aditia A. Pratama",
    "version": (0, 0, 96),
    "blender": (2, 80, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Object",
}


def update_panel(self, context):
    message = "Cherub Pie Menus: Updating Panel locations has failed"
    try:
        for panel in panels:
            if "bl_rna" in panel.__dict__:
                bpy.utils.unregister_class(panel)

        for panel in panels:
            panel.bl_category = get_addon_preferences().category
            bpy.utils.register_class(panel)

    except Exception as e:
        print("\n[{}]\n{}\n\nError:\n{}".format(__name__, message, e))
        pass


class CHERUBPIES_MT_Prefs(Preferences):
    bl_idname = __name__

    prefs_tabs: EnumProperty(
        items=(
            ("options", "Options", "ADDON OPTIONS"),
            ("keymaps", "Keymaps", "CHANGE KEYMAPS"),
            ("update", "Update", "UPDATE"),
        ),
        default="keymaps",
    )

    uv_window_x: IntProperty(name="", default=900, min=128, max=1024)
    uv_window_y: IntProperty(name="", default=900, min=128, max=1024)

    scale_y: FloatProperty(name="", default=1, min=1, max=2)

    update_exist: BoolProperty(
        name="Update Exist",
        description="There is new Cherub Pie Menus update",
        default=False,
    )
    update_text: StringProperty(name="Update text", default="")
    category: StringProperty(
        name="Tab Category",
        description="Choose a name for the category of the panel",
        default="Cherub Pies Menu",
        update=update_panel,
    )
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
            row = box.split().row()
            row.label(text="UV Window Resolution:")
            col = row.column_flow(columns=2)
            split = col.split(factor=0.2)
            split.label(text="X :")
            split.prop(self, "uv_window_x", expand=True, text=" ")
            split = col.split(factor=0.2)
            split.label(text="Y :")
            split.prop(self, "uv_window_y", expand=True, text=" ")

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

        if self.prefs_tabs == "update":
            box = layout.box()
            col = box.column()
            sub_row = col.row(align=True)
            sub_row.operator("cherub_pie_menus.check_for_update")
            split_lines_text = self.update_text.splitlines()
            for line in split_lines_text:
                sub_row = col.row(align=True)
                sub_row.label(text=line)
            sub_row.separator()
            sub_row = col.row(align=True)
            if self.update_exist:
                sub_row.operator(
                    "cherub_pie_menus.update_addon",
                    text="Install latest version",
                ).reinstall = False
            else:
                sub_row.operator(
                    "cherub_pie_menus.update_addon",
                    text="Reinstall current version",
                ).reinstall = True
            sub_row.operator("cherub_pie_menus.rollback_addon")


classes.append(CHERUBPIES_MT_Prefs)


def register():
    register_ui()
    # get_addon_preferences().update_text = ""

    for c in classes:
        bpy.utils.register_class(c)

    add_hotkey()

    print("Registered {} with {} modules".format(bl_info["name"], len(modules)))


def unregister():
    unregister_ui()

    for c in classes:
        bpy.utils.unregister_class(c)

    remove_hotkey()

    print("Unregistered {}".format(bl_info["name"]))

