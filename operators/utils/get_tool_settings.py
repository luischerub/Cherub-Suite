import bpy


def get_tool_settings():
    scenes = [s for s in bpy.data.scenes]
    for s in scenes:
        toolsettings = s.tool_settings

    return toolsettings
