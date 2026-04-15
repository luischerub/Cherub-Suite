import bpy

def draw_shape_keys_button(self, context):
    ob = context.object
    if not ob or ob.type != "MESH":
        return

    layout = self.layout
    row = layout.row(align=True)
    row.operator(
        "cherub.bake_shape_keys_to_attrs",
        text="Bake Keys to Attr",
        icon="GEOMETRY_NODES",
    )
    row.operator(
        "cherub.unify_meshes_to_shapekeys",
        text="Unify Meshes",
        icon="SHAPEKEY_DATA",
    )
    layout.separator()


def register_shape_keys_panel_override():
    bpy.types.DATA_PT_shape_keys.prepend(draw_shape_keys_button)


def unregister_shape_keys_panel_override():
    try:
        bpy.types.DATA_PT_shape_keys.remove(draw_shape_keys_button)
    except ValueError:
        pass
