import bpy
from bpy.types import Operator


class CHERUBPIES_OT_SelectionCursorToCenter(Operator):
    bl_idname = "cherub_pies.selection_cursor_to_center"
    bl_label = "Selected and Cursor to Center"
    bl_description = " "

    def execute(self, context):
        bpy.ops.object.location_clear(clear_delta=False)
        bpy.ops.view3d.snap_cursor_to_center()
        return {"FINISHED"}
