import bpy
import bmesh
from bpy.types import Operator


def mark_face_boundary(context):
    meshes = [m.data for m in bpy.context.selected_objects]
    bm = []
    selection_mode = [{"FACE"}, {"EDGE"}, {"VERT"}]

    if bpy.context.mode == "EDIT_MESH":
        for i in range(len(meshes)):
            bm.append(bmesh.from_edit_mesh(meshes[i]))
            break
    for i in range(len(bm)):
        if (
            bm[i].select_mode in selection_mode
            and len(bm[i].select_history) >= 0
        ):
            select_mode = bpy.context.tool_settings.mesh_select_mode
            bpy.ops.mesh.region_to_loop()
            bpy.ops.mesh.mark_seam(clear=False)
            bpy.context.tool_settings.mesh_select_mode = (
                select_mode
            )  # ?(False, False, True)

    return mark_face_boundary


def unmark_face_boundary(context):
    meshes = [m.data for m in bpy.context.selected_objects]
    bm = []
    selection_mode = [{"FACE"}, {"EDGE"}, {"VERT"}]

    if bpy.context.mode == "EDIT_MESH":
        for i in range(len(meshes)):
            bm.append(bmesh.from_edit_mesh(meshes[i]))
            break
    for i in range(len(bm)):
        if (
            bm[i].select_mode in selection_mode
            and len(bm[i].select_history) >= 0
        ):
            select_mode = bpy.context.tool_settings.mesh_select_mode
            bpy.ops.mesh.region_to_loop()
            bpy.ops.mesh.mark_seam(clear=True)
            bpy.context.tool_settings.mesh_select_mode = (
                select_mode
            )  # ?(False, False, True)

    return unmark_face_boundary


class CHERUBPIES_OT_MarkFaceBoundary(Operator):
    bl_idname = "cherub_pies.mark_face_boundary"
    bl_label = "Mark Face Boundary"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        mark_face_boundary(context)

        return {"FINISHED"}


class CHERUBPIES_OT_UnmarkFaceBoundary(Operator):
    bl_idname = "cherub_pies.unmark_face_boundary"
    bl_label = "Unmark Face Boundary"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        unmark_face_boundary(context)

        return {"FINISHED"}

