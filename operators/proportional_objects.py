import bpy

from bpy.types import Operator
from .utils.set_proportional import set_proportional


class CHERUBPIES_OT_ProportionalSmooth(Operator):
    bl_idname = "cherub_pies.proportional_smooth"
    bl_label = "Proportional Smooth Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit_objects:
            ts.proportional_edit_falloff = "SMOOTH"
        else:
            set_proportional(context)
            ts.proportional_edit_falloff = "SMOOTH"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalSphere(Operator):
    bl_idname = "cherub_pies.proportional_sphere"
    bl_label = "Proportional Sphere Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit_objects:
            ts.proportional_edit_falloff = "SPHERE"
        else:
            set_proportional(context)
            ts.proportional_edit_falloff = "SPHERE"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalRoot(Operator):
    bl_idname = "cherub_pies.proportional_root"
    bl_label = "Proportional Root Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit_objects:
            ts.proportional_edit_falloff = "ROOT"
        else:
            set_proportional(context)
            ts.proportional_edit_falloff = "ROOT"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalSharp(Operator):
    bl_idname = "cherub_pies.proportional_sharp"
    bl_label = "Proportional Sharp Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit_objects:
            ts.proportional_edit_falloff = "SHARP"
        else:
            set_proportional(context)
            ts.proportional_edit_falloff = "SHARP"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalLinear(Operator):
    bl_idname = "cherub_pies.proportional_linear"
    bl_label = "Proportional Linear Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit_objects:
            ts.proportional_edit_falloff = "LINEAR"
        else:
            set_proportional(context)
            ts.proportional_edit_falloff = "LINEAR"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalConstant(Operator):
    bl_idname = "cherub_pies.proportional_constant"
    bl_label = "Proportional Constant Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit_objects:
            ts.proportional_edit_falloff = "CONSTANT"
        else:
            set_proportional(context)
            ts.proportional_edit_falloff = "CONSTANT"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalRandom(Operator):
    bl_idname = "cherub_pies.proportional_random"
    bl_label = "Proportional Random Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit_objects:
            ts.proportional_edit_falloff = "RANDOM"
        else:
            set_proportional(context)
            ts.proportional_edit_falloff = "RANDOM"
        return {"FINISHED"}
