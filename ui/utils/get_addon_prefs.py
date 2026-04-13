import bpy
import os


def get_addon_preferences():
    # addon_name = os.path.basename(os.path.dirname(
    #     os.path.abspath(__file__).split("utils")[0]))
    user_preferences = bpy.context.preferences
    addon_prefs = user_preferences.addons["cherub-suite"].preferences

    return addon_prefs
