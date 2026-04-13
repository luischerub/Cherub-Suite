import bpy
import rna_keymap_ui

keymaps_items_dict = {
    "Cherub Pies Specials": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_Specials",
        "Mesh",
        "EMPTY",
        "WINDOW",
        "W",
        "PRESS",
        False,  # ? Ctrl
        True,  # ? Shift
        False,  # ? Alt
        # "3D View Generic",
        # "VIEW_3D",
        # "WINDOW",
        # "W",
        # "PRESS",
        # False,  # Ctrl
        # True,  # Shift
        # False,  # Alt
    ],
    "Cherub Pies Delete": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_Delete",
        "Mesh",
        "EMPTY",
        "WINDOW",
        "X",
        "PRESS",
        False,
        False,
        False,
    ],
    "Cherub Pies Modifiers": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_Modifiers",
        "Mesh",
        "EMPTY",
        "WINDOW",
        "TAB",
        "PRESS",
        True,
        False,
        False,
    ],
    "Cherub Pies Selection": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_Selection",
        "Mesh",
        "EMPTY",
        "WINDOW",
        "RIGHTMOUSE",
        "PRESS",
        False,
        False,
        False,
    ],
    "Cherub Pies Shading": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_Shading",
        "Mesh",
        "EMPTY",
        "WINDOW",
        "W",
        "PRESS",
        False,
        False,
        False,
    ],
    "Cherub Pies UVs": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_UVs",
        "Mesh",
        "EMPTY",
        "WINDOW",
        "Q",
        "PRESS",
        False,
        False,
        False,
    ],
    "Cherub Pies Proportional Object": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_ProportionalObjectMode",
        "Object Mode",
        "EMPTY",
        "WINDOW",
        "O",
        "PRESS",
        False,
        False,
        False,
    ],
    "Cherub Pies Proportional Edit": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_ProportionalEditMode",
        "Mesh",
        "EMPTY",
        "WINDOW",
        "O",
        "PRESS",
        False,
        False,
        False,
    ],
    "Cherub Pies Pivot and Orientation": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_PivotOrientation",
        "3D View Generic",
        "VIEW_3D",
        "WINDOW",
        "S",
        "PRESS",
        False,  # ? Ctrl
        True,
        False,
    ],
    "Cherub Pies Save": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_SaveOpen",
        "Window",
        "EMPTY",
        "WINDOW",
        "ONE",
        "ANY",
        False,  # ? Ctrl
        False,  # ? Shift
        False,  # ? Alt
    ],
    "Cherub Pies QuickFavorites": [
        "wm.call_menu",
        "SCREEN_MT_user_menu",
        "Window",
        "EMPTY",
        "WINDOW",
        "Q",
        "ANY",
        False,  # ? Ctrl
        True,  # ? Shift
        False,  # ? Alt
    ],
    "Cherub Pies UVs Editor": [
        "wm.call_menu_pie",
        "CHERUBPIES_MT_UVsEditor",
        "UV Editor",
        "EMPTY",
        "WINDOW",
        "RIGHTMOUSE",
        "PRESS",
        False,  # ? Ctrl
        False,  # ? Shift
        False,  # ? Alt
    ],
}

addon_keymaps = []


def draw_keymap_items(wm, layout):
    kc = wm.keyconfigs.user

    for name, items in keymaps_items_dict.items():
        kmi_name, kmi_value, km_name = items[:3]
        box = layout.box()
        split = box.split()
        col = split.column()
        col.label(text=name)
        col.separator()
        km = kc.keymaps[km_name]
        get_hotkey_entry_item(kc, km, kmi_name, kmi_value, col)


def get_hotkey_entry_item(kc, km, kmi_name, kmi_value, col):

    # for menus and pie_menu
    if kmi_value:
        for km_item in km.keymap_items:
            if (
                km_item.idname == kmi_name
                and km_item.properties.name == kmi_value
            ):
                col.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi([], kc, km, km_item, col, 0)
                return

        col.label(text=f"No hotkey entry found for {kmi_value}")
        col.operator(CHERUBPIES_OT_AddHotkey.bl_idname, icon="ADD")

    # for operators
    else:
        if km.keymap_items.get(kmi_name):
            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi(
                [], kc, km, km.keymap_items[kmi_name], col, 0
            )
        else:
            col.label(text=f"No hotkey entry found for {kmi_name}")
            col.operator(CHERUBPIES_OT_AddHotkey.bl_idname, icon="ADD")


def add_hotkey():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if not kc:
        return

    # for items in keymaps_items_dict.values():
    items = [i for i in keymaps_items_dict.values()]
    for i in items:
        kmi_name, kmi_value, km_name, space_type, region_type = i[:5]
        eventType, eventValue, ctrl, shift, alt = i[5:]
        km = kc.keymaps.new(
            name=km_name, space_type=space_type, region_type=region_type
        )

        kmi = km.keymap_items.new(
            kmi_name, eventType, eventValue, ctrl=ctrl, shift=shift, alt=alt
        )
        if kmi_value:
            kmi.properties.name = kmi_value

        kmi.active = True

        addon_keymaps.append((km, kmi))


def remove_hotkey():
    """ clears all addon level keymap hotkeys stored in addon_keymaps """
    items = [i for i in keymaps_items_dict.values()]
    # kmi_values = [item[1] for item in keymaps_items_dict.values() if item]
    # kmi_names = [item[0] for item in keymaps_items_dict.values() if item not in [
    #     'wm.call_menu', 'wm.call_menu_pie']]
    kmi_values = [i[1] for i in items if i]
    kmi_names = [
        i[0] for i in items if i not in ["wm.call_menu", "wm.call_menu_pie"]
    ]

    for km, kmi in addon_keymaps:
        # remove addon keymap for menu and pie menu
        if hasattr(kmi.properties, "name"):
            if kmi_values:
                if kmi.properties.name in kmi_values:
                    km.keymap_items.remove(kmi)

        # remove addon_keymap for operators
        else:
            if kmi_names:
                if kmi.name in kmi_names:
                    km.keymap_items.remove(kmi)

    addon_keymaps.clear()


class CHERUBPIES_OT_AddHotkey(bpy.types.Operator):
    """ Add hotkey entry """

    bl_idname = "cherub_pies.add_hotkey"
    bl_label = "Add Hotkeys"
    bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        add_hotkey()

        self.report(
            {"INFO"},
            "Hotkey added in User Preferences -> Input -> Screen -> Screen (Global)",
        )
        return {"FINISHED"}

