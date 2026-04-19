import bpy
import os

class CHERUB_OT_AssetLibAssignThumb(bpy.types.Operator):
    """Assign rendered images as thumbnails for selected mesh objects"""
    bl_idname = "cherub.assetlib_assign_thumb"
    bl_label = "Apply Thumbnails"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.cherub_settings

        # 1. Filter: selected mesh objects only
        assets = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not assets:
            self.report({'WARNING'}, "No selected mesh objects found to update.")
            return {'CANCELLED'}

        # 2. Path Validation
        output_folder = bpy.path.abspath(props.output_path)
        if not os.path.exists(output_folder):
            self.report({'ERROR'}, f"Folder not found: {output_folder}")
            return {'CANCELLED'}

        count = 0
        # 3. Assignment Loop
        for obj in assets:
            img_path = os.path.join(output_folder, f"{obj.name}.webp")
            
            if os.path.isfile(img_path):
                try:
                    # The technical 'magic' for Blender 5.0+
                    with bpy.context.temp_override(id=obj):
                        bpy.ops.ed.lib_id_load_custom_preview(filepath=img_path)
                    count += 1
                except Exception as e:
                    print(f"Failed to assign {obj.name}: {e}")
            else:
                print(f"Skipping {obj.name}: No matching .webp found.")

        self.report({'INFO'}, f"Updated {count} asset thumbnails successfully!")
        return {'FINISHED'}