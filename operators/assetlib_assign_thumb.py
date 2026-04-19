import bpy
import os

class CHERUB_OT_AssetLibAssignThumb(bpy.types.Operator):
    """Assign rendered images as thumbnails for all marked assets"""
    bl_idname = "cherub.assetlib_assign_thumb"
    bl_label = "Apply Thumbnails"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.cherub_settings

        # 1. Collect all marked assets from every datablock collection in the file
        assets = []
        for prop in bpy.types.BlendData.bl_rna.properties:
            if prop.type != 'COLLECTION':
                continue

            collection = getattr(bpy.data, prop.identifier, None)
            if collection is None:
                continue

            for datablock in collection:
                if getattr(datablock, "asset_data", None) is not None:
                    assets.append(datablock)

        if not assets:
            self.report({'WARNING'}, "No marked assets found in this file.")
            return {'CANCELLED'}

        # 2. Path Validation
        output_folder = bpy.path.abspath(props.output_path)
        if not os.path.exists(output_folder):
            self.report({'ERROR'}, f"Folder not found: {output_folder}")
            return {'CANCELLED'}

        available_webps = {
            os.path.splitext(filename)[0]
            for filename in os.listdir(output_folder)
            if filename.lower().endswith('.webp')
        }

        count = 0
        missing = 0
        # 3. Assignment Loop
        for asset in assets:
            if asset.name not in available_webps:
                missing += 1
                print(f"Skipping {asset.name}: No matching .webp found.")
                continue

            img_path = os.path.join(output_folder, f"{asset.name}.webp")

            try:
                # Only exact filename matches are applied; all others stay unchanged.
                with context.temp_override(id=asset):
                    bpy.ops.ed.lib_id_load_custom_preview(filepath=img_path)
                count += 1
            except Exception as e:
                print(f"Failed to assign {asset.name}: {e}")

        self.report({'INFO'}, f"Updated {count} asset thumbnails ({missing} without matching image).")
        return {'FINISHED'}