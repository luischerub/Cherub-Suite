"""
This operators will call new UV windows with desired resolution set in User Preferences
"""

import bpy
from bpy.types import Operator
from ..ui.utils.get_addon_prefs import get_addon_preferences


def call_uv_window(context):

    render = bpy.context.scene.render
    preferences = bpy.context.preferences

    #! apply resolution from preferences
    render.resolution_x = get_addon_preferences().uv_window_x
    render.resolution_y = get_addon_preferences().uv_window_y
    render.resolution_percentage = 100
    preferences.view.render_display_type = "WINDOW"

    # Call image editor window
    bpy.ops.render.view_show("INVOKE_DEFAULT")
    bpy.data.images.remove(bpy.data.images["Render Result"])

    # Change area type
    area = bpy.context.window_manager.windows[-1].screen.areas[0]
    area.ui_type = "UV"

    return call_uv_window


class CHERUBPIES_OT_CallUvWindow(Operator):
    bl_idname = "cherub_pies.call_uv_window"
    bl_label = "UV Window Popup"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        render = bpy.context.scene.render
        preferences = bpy.context.preferences

        #! before uv window
        x_res = render.resolution_x
        y_res = render.resolution_y
        display_type = preferences.view.render_display_type

        call_uv_window(context)

        render.resolution_x = x_res
        render.resolution_y = y_res
        preferences.view.render_display_type = display_type

        return {"FINISHED"}
