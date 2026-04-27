import bpy
from ... import __package__ as base_package


def get_addon_preferences():
    addon_prefs = bpy.context.preferences.addons.get(base_package)
    if addon_prefs:
        return addon_prefs.preferences
    return None
