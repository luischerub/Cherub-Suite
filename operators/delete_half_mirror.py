# Copyright (C) 2019 aditi
#
# This file is part of cherub_pie_menus.
#
# cherub_pie_menus is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cherub_pie_menus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cherub_pie_menus.  If not, see <http://www.gnu.org/licenses/>.

import bpy
import bmesh
from mathutils.geometry import distance_point_to_plane
from mathutils import Vector


def bbox(obj):
    return (Vector(b) for b in obj.bound_box)


def bbox_center(obj):
    return sum(bbox(obj), Vector()) / 8


def bbox_axes(obj):
    bb = list(bbox(obj))
    return tuple(bb[i] - bb[0] for i in (4, 3, 1))


def modifiers_by_name(obj, name):
    """ Find all modifiers with a specific name in obj """
    return [x for x in obj.modifiers if x.name == name]


def modifiers_by_type(obj, typename):
    """ Find all modifiers with a specific type in obj """
    return [x for x in obj.modifiers if x.type == typename]


class CHERUBPIES_OT_DeleteHalfMirror(bpy.types.Operator):

    bl_idname = "cherub_pies.delete_half_mirror"
    bl_label = "Delete Half and Mirror X"
    bl_description = "Only in Edit mode, it will Delete half and apply mirror modifier on X axis"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        sel_objs = bpy.context.selected_objects
        for obj in sel_objs:
            return obj.mode == "EDIT"

    def execute(self, context):
        context = bpy.context
        obj = context.edit_object
        o = bbox_center(obj)
        x, y, z = bbox_axes(obj)

        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        for v in bm.verts:
            v.select = distance_point_to_plane(v.co, o, -x) >= 0.00001
            if v.select >= 1:
                bm.verts.remove(v)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0)
        mod_lists = obj.modifiers.items()
        mod_lists = [m for m in mod_lists if m[1].type == "MIRROR"]
        if not mod_lists:
            obj.modifiers.new("Mirror", type="MIRROR")
            obj.modifiers["Mirror"].use_clip = True
            for mod in reversed(modifiers_by_type(obj, "MIRROR")):
                while obj.modifiers.find(mod.name) != 0:
                    bpy.ops.object.modifier_move_up(modifier=mod.name)

        return {"FINISHED"}
