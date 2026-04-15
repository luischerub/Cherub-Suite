import bpy

class CHERUB_OT_BakeShapeKeysToAttributes(bpy.types.Operator):
    """Bake all shape keys to custom vertex attributes"""
    bl_idname = "cherub.bake_shape_keys_to_attrs"
    bl_label = "Bake Shape Keys to Attributes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH' or not obj.data.shape_keys:
            self.report({'WARNING'}, "Active object must be a mesh with shape keys!")
            return {'CANCELLED'}

        for sk in obj.data.shape_keys.key_blocks:
            if sk.name == "Basis":
                continue
                
            attr_name = sk.name
            if attr_name in obj.data.attributes:
                attr = obj.data.attributes[attr_name]
            else:
                attr = obj.data.attributes.new(name=attr_name, type='FLOAT_VECTOR', domain='POINT')
            
            for i, vertex in enumerate(obj.data.vertices):
                attr.data[i].vector = sk.data[i].co
        
        self.report({'INFO'}, "Baked all shape keys to attributes!")
        return {'FINISHED'}