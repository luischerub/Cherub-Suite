import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, PointerProperty, StringProperty

class CherubAssetSettings(bpy.types.PropertyGroup):
    # The folder where renders are saved/loaded from
    output_path: StringProperty(
        name="Output Path",
        description="Folder for asset thumbnails",
        subtype='DIR_PATH',
        default="//renders/"
    )

    # Render Quality
    render_res: IntProperty(
        name="Resolution",
        description="Resolution of the thumbnail render",
        default=512,
        min=64,
        max=4096
    )

    # Framing
    padding: FloatProperty(
        name="Padding",
        description="Amount of space around the object",
        default=1.1,
        min=1.0
    )

    # Toggle for targeting specific assets
    only_selected: BoolProperty(
        name="Only Selected",
        description="Only process assets that are currently selected",
        default=False
    )

    # N-panel section state
    asset_tools_expanded: BoolProperty(
        name="Asset Library Tools",
        description="Expand or collapse asset library tools",
        default=True,
    )


def register_properties():
    bpy.utils.register_class(CherubAssetSettings)
    bpy.types.Scene.cherub_settings = PointerProperty(type=CherubAssetSettings)


def unregister_properties():
    if hasattr(bpy.types.Scene, "cherub_settings"):
        del bpy.types.Scene.cherub_settings
    bpy.utils.unregister_class(CherubAssetSettings)


# Backward-compatible aliases if any module still imports register/unregister.
def register():
    register_properties()


def unregister():
    unregister_properties()