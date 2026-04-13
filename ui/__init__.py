import bpy

from .pie_specials import CHERUBPIES_MT_Specials
from .pie_delete import CHERUBPIES_MT_Delete
from .pie_modifiers import CHERUBPIES_MT_Modifiers
from .pie_selection import CHERUBPIES_MT_Selection
from .pie_shading import CHERUBPIES_MT_Shading
from .pie_uvs import CHERUBPIES_MT_UVs
from .pie_proportional import (
    CHERUBPIES_MT_ProportionalObjectMode,
    CHERUBPIES_MT_ProportionalEditMode,
    CHERUBPIES_MT_ProportionalMore,
)
from .pie_pivot import CHERUBPIES_MT_PivotOrientation
from .pie_save import CHERUBPIES_MT_SaveOpen, CHERUBPIES_MT_Recover

classes = [
    CHERUBPIES_MT_Specials,
    CHERUBPIES_MT_Delete,
    CHERUBPIES_MT_Modifiers,
    CHERUBPIES_MT_Selection,
    CHERUBPIES_MT_Shading,
    CHERUBPIES_MT_UVs,
    CHERUBPIES_MT_ProportionalObjectMode,
    CHERUBPIES_MT_ProportionalEditMode,
    CHERUBPIES_MT_ProportionalMore,
    CHERUBPIES_MT_PivotOrientation,
    CHERUBPIES_MT_SaveOpen,
    CHERUBPIES_MT_Recover,
]

register_ui, unregister_ui = bpy.utils.register_classes_factory(classes)
