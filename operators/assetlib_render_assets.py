import bpy
import os

class CHERUB_OT_AssetLibRender(bpy.types.Operator):
    """Render high-quality thumbnails for selected mesh objects"""
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

        # 1. Filter: selected mesh objects only
        assets = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not assets:
            self.report({'WARNING'}, "No selected mesh objects found.")
            return {'CANCELLED'}

        # 2. Setup Render Environment
        original_path = scene.render.filepath
        scene.render.resolution_x = props.render_res
        scene.render.resolution_y = props.render_res
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.film_transparent = True
        
        output_folder = bpy.path.abspath(props.output_path)
        if not output_folder or output_folder.strip("/\\") == "":
            self.report({'WARNING'}, "Please define an output path before rendering.")
            return {'CANCELLED'}
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # 3. Render Loop
        # Hide all meshes and font objects to avoid background clutter
        all_objects = [o for o in scene.objects if o.type in {'MESH', 'FONT'}]
        for obj in all_objects:
            obj.hide_render = True

        # Use the active object as the framing reference — it's the object the artist
        # positioned the camera for.  Fall back to assets[0] if active isn't a mesh.
        reference = context.active_object if (context.active_object and context.active_object.type == 'MESH') else assets[0]
        cam_offset = cam.location.copy() - reference.matrix_world.translation

        for obj in assets:
            obj.hide_render = False

            # Frame the object: apply the same camera offset from its origin
            cam.location = obj.matrix_world.translation + cam_offset
            
            # Set unique filename and render
            scene.render.filepath = os.path.join(output_folder, f"{obj.name}.webp")
            bpy.ops.render.render(write_still=True)
            
            obj.hide_render = True

        # Restore original path
        scene.render.filepath = original_path
        
        self.report({'INFO'}, f"Successfully rendered {len(assets)} assets.")
        return {'FINISHED'}