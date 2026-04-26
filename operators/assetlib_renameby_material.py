import bpy


class CHERUB_OT_AssetLibRenameByMaterial(bpy.types.Operator):
    """Rename selected mesh objects to match their active material names"""
    bl_idname = "cherub.assetlib_rename_by_material"
    bl_label = "Rename Objects by Material"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selection = context.selected_objects

        if not selection:
            self.report({'INFO'}, "Select some objects first!")
            return {'CANCELLED'}

        renamed_count = 0
        skipped_count = 0

        for obj in selection:
            if obj.type != 'MESH':
                skipped_count += 1
                continue

            if obj.active_material:
                obj.name = obj.active_material.name
            else:
                obj.name = "MISSING_MAT"
            renamed_count += 1

        self.report({'INFO'}, f"Renamed {renamed_count} objects ({skipped_count} non-mesh skipped).")
        return {'FINISHED'}
