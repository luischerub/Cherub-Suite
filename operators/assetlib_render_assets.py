import bpy
import os
from .utils.camera_utils import fit_camera_to_obj

class CHERUB_OT_AssetLibRender(bpy.types.Operator):
    """Render high-quality thumbnails for marked assets"""
    bl_idname = "cherub.assetlib_render_assets"
    bl_label = "Render Thumbnails"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.cherub_settings
        cam = scene.camera

        if not cam:
            self.report({'ERROR'}, "Please add a camera to the scene first!")
            return {'CANCELLED'}

        # 1. Filter: Marked assets in this scene
        if props.only_selected:
            assets = [obj for obj in context.selected_objects 
                      if obj.asset_data and obj.type == 'MESH']
        else:
            assets = [obj for obj in scene.objects 
                      if obj.asset_data and obj.type == 'MESH']

        if not assets:
            self.report({'WARNING'}, "No marked mesh assets found.")
            return {'CANCELLED'}

        # 2. Setup Render Environment
        original_path = scene.render.filepath
        scene.render.resolution_x = props.render_res
        scene.render.resolution_y = props.render_res
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.film_transparent = True
        
        output_folder = bpy.path.abspath(props.output_path)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # 3. Render Loop
        # Hide all meshes to avoid background clutter
        all_meshes = [o for o in scene.objects if o.type == 'MESH']
        for mesh in all_meshes:
            mesh.hide_render = True

        for obj in assets:
            obj.hide_render = False
            
            # Frame the object using our utility
            fit_camera_to_obj(cam, obj, scene, props.padding)
            
            # Set unique filename and render
            scene.render.filepath = os.path.join(output_folder, f"{obj.name}.webp")
            bpy.ops.render.render(write_still=True)
            
            obj.hide_render = True

        # Restore original path
        scene.render.filepath = original_path
        
        self.report({'INFO'}, f"Successfully rendered {len(assets)} assets.")
        return {'FINISHED'}