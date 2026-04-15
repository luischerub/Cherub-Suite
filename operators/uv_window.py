"""
This operators will call new UV windows with desired resolution set in User Preferences
"""

import bpy
from bpy.types import Operator
from ..ui.utils.get_addon_prefs import get_addon_preferences


def call_uv_window(context):
    """Open UV Editor window with custom resolution from addon preferences."""
    import sys
    from bpy import ops, context as bpy_context
    
    # Store current render settings
    render = bpy_context.scene.render
    prefs = get_addon_preferences()
    if not prefs:
        # Fallback values if preferences not available
        prefs = type('FallbackPrefs', (), {'uv_window_x': 900, 'uv_window_y': 900})()
    
    # Apply resolution from preferences
    orig_res_x = render.resolution_x
    orig_res_y = render.resolution_y
    orig_res_pct = render.resolution_percentage
    
    render.resolution_x = prefs.uv_window_x
    render.resolution_y = prefs.uv_window_y
    render.resolution_percentage = 100
    
    try:
        # In Blender 5.1+, use image editor directly by creating a new window
        # and setting the area type to UV Editor
        for window in bpy_context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    # Found existing UV editor, show it
                    with bpy_context.temp_override(window=window, area=area):
                        # Set it to show UV editor mode
                        area.ui_type = "UV"
                    return
        
        # If no UV editor exists, create image for viewport
        # This is a fallback since bpy.ops.render.view_show was removed in 5.1
        if "temp_uv_viewer" not in bpy.data.images:
            bpy.data.images.new("temp_uv_viewer", prefs.uv_window_x, prefs.uv_window_y)
            
    finally:
        # Restore original render settings
        render.resolution_x = orig_res_x
        render.resolution_y = orig_res_y
        render.resolution_percentage = orig_res_pct
    
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
