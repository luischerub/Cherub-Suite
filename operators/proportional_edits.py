import bpy

from bpy.types import Operator
from .utils.set_proportional import set_proportional_edit


class CHERUBPIES_OT_ProportionalEditToggle(Operator):
    bl_idname = "cherub_pies.proportional_edit_toggle"
    bl_label = "Proportional Connected Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        set_proportional_edit(context)
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalEditConnected(Operator):
    bl_idname = "cherub_pies.proportional_edit_connected"
    bl_label = "Proportional Connected Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # ts = context.tool_settings
        ts = context.scene.tool_settings
        ts.use_proportional_connected = False
        ts.use_proportional_projected = False
        if (
            ts.use_proportional_edit is False
            and ts.use_proportional_connected is False
        ):
            ts.use_proportional_edit = True
            ts.use_proportional_connected = True
            ts.use_proportional_projected = False
        elif (
            ts.use_proportional_edit is True
            and ts.use_proportional_projected is False
        ):
            ts.use_proportional_connected = True
            ts.use_proportional_projected = False
        else:
            set_proportional_edit(context)
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalEditProjected(Operator):
    bl_idname = "cherub_pies.proportional_edit_projected"
    bl_label = "Proportional projected Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        ts.use_proportional_connected = False
        ts.use_proportional_projected = False
        if (
            ts.use_proportional_edit is False
            and ts.use_proportional_projected is False
        ):
            ts.use_proportional_edit = True
            ts.use_proportional_projected = True
            ts.use_proportional_connected = False
        elif (
            ts.use_proportional_edit is True
            and ts.use_proportional_projected is False
        ):
            ts.use_proportional_projected = True
            ts.use_proportional_connected = False
        else:
            set_proportional_edit(context)
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalEditSmooth(Operator):
    bl_idname = "cherub_pies.proportional_edit_smooth"
    bl_label = "Proportional Smooth Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit:
            ts.proportional_edit_falloff = "SMOOTH"
        else:
            set_proportional_edit(context)
            ts.proportional_edit_falloff = "SMOOTH"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalEditSphere(Operator):
    bl_idname = "cherub_pies.proportional_edit_sphere"
    bl_label = "Proportional Sphere Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit:
            ts.proportional_edit_falloff = "SPHERE"
        else:
            set_proportional_edit(context)
            ts.proportional_edit_falloff = "SPHERE"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalEditRoot(Operator):
    bl_idname = "cherub_pies.proportional_edit_root"
    bl_label = "Proportional Root Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit:
            ts.proportional_edit_falloff = "ROOT"
        else:
            set_proportional_edit(context)
            ts.proportional_edit_falloff = "ROOT"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalEditSharp(Operator):
    bl_idname = "cherub_pies.proportional_edit_sharp"
    bl_label = "Proportional Sharp Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit:
            ts.proportional_edit_falloff = "SHARP"
        else:
            set_proportional_edit(context)
            ts.proportional_edit_falloff = "SHARP"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalEditLinear(Operator):
    bl_idname = "cherub_pies.proportional_edit_linear"
    bl_label = "Proportional Linear Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit:
            ts.proportional_edit_falloff = "LINEAR"
        else:
            set_proportional_edit(context)
            ts.proportional_edit_falloff = "LINEAR"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalEditConstant(Operator):
    bl_idname = "cherub_pies.proportional_edit_constant"
    bl_label = "Proportional Constant Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit:
            ts.proportional_edit_falloff = "CONSTANT"
        else:
            set_proportional_edit(context)
            ts.proportional_edit_falloff = "CONSTANT"
        return {"FINISHED"}


class CHERUBPIES_OT_ProportionalEditRandom(Operator):
    bl_idname = "cherub_pies.proportional_edit_random"
    bl_label = "Proportional Random Edit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ts = context.scene.tool_settings
        if ts.use_proportional_edit:
            ts.proportional_edit_falloff = "RANDOM"
        else:
            set_proportional_edit(context)
            ts.proportional_edit_falloff = "RANDOM"
        return {"FINISHED"}
