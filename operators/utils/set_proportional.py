import bpy


def set_proportional(context):
    scenes = [s for s in bpy.data.scenes]
    for s in scenes:
        ts = s.tool_settings
        if ts.use_proportional_edit_objects is False:
            ts.use_proportional_edit_objects = True
        else:
            ts.use_proportional_edit_objects = False
    return set_proportional


def set_proportional_edit(context):
    scenes = [s for s in bpy.data.scenes]
    for s in scenes:
        ts = s.tool_settings
        ts.use_proportional_connected = False
        ts.use_proportional_projected = False
        if ts.use_proportional_edit is False:
            ts.use_proportional_edit = True
        else:
            ts.use_proportional_edit = False
    return set_proportional_edit
