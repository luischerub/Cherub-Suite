import bpy
from bpy.types import Menu, Operator
import os

# Pie Save/Open
class CHERUBPIES_MT_SaveOpen(Menu):
    bl_idname = "CHERUBPIES_MT_SaveOpen"
    bl_label = "Cherub Pies Save/Open"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        #! 4 - LEFT
        pie.menu("TOPBAR_MT_file_import", text="Import")
        # pie.operator("wm.read_homefile", text="New", icon="FILE_NEW")
        #! 6 - RIGHT
        pie.menu("TOPBAR_MT_file_export", text="Export")
        # pie.menu("PIE_MT_link", text="Link Menu", icon="LINK_BLEND")
        #! 2 - BOTTOM
        pie.separator()
        # pie.menu("PIE_MT_fileio", text="Import/Export Menu", icon="IMPORT")
        #! 8 - TOP
        pie.separator()
        # pie.operator("wm.open_mainfile", text="Open File", icon="FILE_FOLDER")
        #! 7 - TOP - LEFT
        pie.operator("wm.save_mainfile", text="Save", icon="FILE_TICK")
        #! 9 - TOP - RIGHT
        pie.operator("wm.save_as_mainfile", text="Save As...", icon="NONE")
        #! 1 - BOTTOM - LEFT
        pie.operator("wm.open_mainfile", text="Open File", icon="FILE_FOLDER")
        # pie.operator(
        #     "file.save_incremental", text="Incremental Save", icon="NONE"
        # )
        #! 3 - BOTTOM - RIGHT
        pie.menu(
            CHERUBPIES_MT_Recover.bl_idname,
            text="Recovery Menu",
            icon="RECOVER_LAST",
        )


class CHERUBPIES_MT_Recover(Menu):
    bl_idname = "CHERUBPIES_MT_Recover"
    bl_label = "Recovery"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        box = pie.split().column()
        box.operator(
            "wm.recover_auto_save", text="Recover Auto Save...", icon="NONE"
        )
        box.operator(
            "wm.recover_last_session",
            text="Recover Last Session",
            icon="RECOVER_LAST",
        )
        box.operator("wm.revert_mainfile", text="Revert", icon="FILE_REFRESH")
        box.separator()
        box.operator("file.report_missing_files", text="Report Missing Files")
        box.operator("file.find_missing_files", text="Find Missing Files")
