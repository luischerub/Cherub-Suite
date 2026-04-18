# Bézier Mesh Shaper - Interactive mesh reshaping using 3D Bézier curves
# (Blender 2.80+ edition)
#
# Copyright (C) 2025 Rafael Navega
# https://gumroad.com/rafaelnavega
#
# Changelog:
# 0.9.67
# - Fix for Projection Mode (API changes from 5.x). Special thanks
#   to user Pluglug for the report.
# - Fix for a missing mouse cursor after cancelling the Projection Mode.
#
# 0.9.66
# - Fix for a bug after split + snapping.
#
# 0.9.65
# - Experimental addition: snapping after curve splitting.
# - Implemented mesh undo/redo after using the smooth snapping function.
#
# 0.9.64
# - Added the keymaps text overlay to the Projection mode.
# - Bugfix for the curve grab action (Ctrl + click-drag).
#
# 0.9.63
# - Added a new item to the settings popup and pie menu, for changing the curve handle
#   types during use (eg automatic, aligned etc). This is done per selected curve knot.
#
# 0.9.62
# - Added a toggable text overlay with keymap (AKA shortcut) info.
#
# 0.9.61
# - Fixes for the deprecated use of the BGL module.
# - Restricted the supported Blender version range to 3.5+. Since no new features were
#   added, if you use a Blender version below 3.5 then you can continue using
#   0.9.60 (the previous B.M.S. version).
#
# 0.9.60
# - Added a simple overlay text when the curve is in unbound mode (detached from the mesh),
#   to help debug mysterious situations when glitches occur in this mode.
#
# 0.9.59
# - Fixed the keymap UI in the add-on preferences to show the key modifier buttons as toggle buttons.
#
# 0.9.58
# - Minor fix for a bug when starting the tool after selecting points with the area selection tools
#   that don't add vertices to the selection history.
#
# 0.9.57
# - Minor fix to cancel the tool when the user does an action that changes the current context area.
#   It seems at least on Blender 2.92.0 this leads to an internal "gizmo-map handler" error.
#
# 0.9.56
# - Added curve handle preselection / auto-selection (makes the tool select the two inside and/or
#   outside handles as soon as it starts).
#
# 0.9.55
# - Small fix in the curve display logic on 2.9X.
#
# 0.9.53 / 0.9.54
# - Fix for a simple case of two vertices selected by selection tools that don't make a selection history.
#   This supports only 2 selected vertices at the moment.
# - Note to self: make sure to just use Deflate (not Deflate64) as the compression method on zip archives.
#
# (. . .)
#
# =======================================================================

bl_info = {
    'name': 'Bezier Mesh Shaper',
    'author': 'Rafael Navega (2025)',
    'description': 'Interactive mesh reshaping using 3D Bézier curves',
    'version': (0, 9, 67),
    'blender': (3, 5, 0),
    'location': '(Edit mode) Mesh > Vertices > Bezier Mesh Shaper',
    'warning': '',
    'category': 'Mesh',
}

from time import time
from random import random
from itertools import chain
from collections import deque
from operator import attrgetter, itemgetter
from math import sqrt, acos, cos, sin

import bpy
# The BGL module is now unused after Bézier Mesh Shaper 0.9.61 for
# Blender 3.5+. See the official deprecation notes in here:
# https://developer.blender.org/docs/release_notes/3.5/python_api/#bgl-deprecation
#import bgl
import gpu
import blf
import bmesh
from bpy_extras import view3d_utils
from mathutils import Quaternion, Vector, kdtree, Matrix
from mathutils.geometry import (
    interpolate_bezier,
    intersect_line_line_2d as intersect2D,
    intersect_line_line as intersectLineLine,
    intersect_point_line as intersectPointLine,
    intersect_line_plane as intersectLinePlane
)


# Bézier Mesh Shaper globals.
BMS_INSTANCE = None # Global reference to the active instance of the operator.
BMS_UNDO_SIZE = 24 # Maximum undo steps. Feel free to increase this number up to 30, 40, 50 etc.
BMS_KEYMAP_NAME = '3D View Generic' # Name of the user keymap (like a group) where the hotkey entries will be added.
BMS_KEYMAP_ITEMS = { } # Used for caching keymap items only once.
BMS_PLOT_RESOLUTION = 101 # Amount of points sampled from the curve, for mapping. Best not to change these values.
BMS_PLOT_DIVISOR = BMS_PLOT_RESOLUTION - 1.0
BMS_PLOT_STEP = 1.0 / BMS_PLOT_DIVISOR
BMS_PLOT_HALFSTEP = BMS_PLOT_STEP / 2.0
BMS_USER_PREFS = bpy.context.preferences


class BMSRuntimeDefaults:
    """Lightweight runtime defaults for embedding BMS into Cherub Suite."""

    # Core behavior defaults
    curveDistance = 0.0
    useAllBetween = True
    useVectorHandleStraight = False
    handleVisibility = 'NOTGRAB'
    menuType = 'DIALOG'
    preselectInner = False
    preselectOuter = False

    # Interaction defaults
    spaceConfirms = True
    rightMouseAction = 'CANCEL'
    grabModeModifer = 'LEFT_CTRL|RIGHT_CTRL'
    useDoubleClick = False

    # Visual defaults
    setCurveColor = False
    curveColor = (0.0, 0.92156, 0.74509)
    showKeymaps = True
    keymapsTextSize = 16

    # Legacy secondary menu behavior (used by standalone menu helper)
    secondaryMenu = '0'


BMS_ADDON_PREFS = BMSRuntimeDefaults()
BMS_SECONDARY_MENU = ( # A preset list to help speed up, used in bezierMeshShaperMenu().
    ('SNAP_STRAIGHT', ' (Snap Straight)'),
    ('SNAP_SMOOTH', ' (Snap Smooth)'),
    ('SNAP_STRAIGHT_P', ' (Straight-Proportional)'),
    ('SNAP_SMOOTH_P', ' (Smooth-Proportional)'),
    ('ALIGNED', ' (Aligned)')
)

# Used in 'recalculateInfluences()', reproduces Blender's proportional edit formulas.
BMS_WEIGHT_FUNCS = {
    'SMOOTH':         lambda w: 3.0 * w * w - (2.0 * w * w * w),
    'LINEAR':         lambda w: w,
    'CONSTANT':       lambda w: 1.0,
    'SHARP':          lambda w: w * w,
    'INVERSE_SQUARE': lambda w: w * (2.0 - w),
    'ROOT':           lambda w: sqrt(w),
    'SPHERE':         lambda w: sqrt(2.0 * w - w * w),
    'RANDOM':         lambda w: random() * w
}

# Used in 'axisLockCurveGrab()'.
BMS_GRAB_AXIS = {
    0: Vector((1, 0, 0)), # X
    1: Vector((0, 1, 0)), # Y
    2: Vector((0, 0, 1)), # Z
}


class BMSShortcuts:
    # Lists of the format (SHORTCUT_NAME, SHORTCUT_DATA, SHORTCUT_KEY_COMBO_TEXT).
    confirm    = ['Confirm: ',           None, 'Confirm: Enter']
    cancel     = ['Cancel: ',            None, 'Cancel: Esc']
    undo       = ['Undo: ',              None, None]
    redo       = ['Redo: ',              None, None]
    settings   = ['Settings Popup: ',    None, None]
    increase   = ['Increase Falloff: ',  None, None]
    decrease   = ['Decrease Falloff: ',  None, None]
    # Use Extremes and Use Direction are handled differently in the
    # shortcuts2DHelper draw handler function.
    extremes   = ['',                    None, None]
    direction  = ['',                    None, None]
    bindunbind = ['Bind/Unbind Curve: ', None, None]

    # Get a reference to the enum object that maps event type to its label.
    allEventTypesGet = bpy.types.Event.bl_rna.properties['type'].enum_items.get

    @staticmethod
    def translateAll():
        allEventTypesGet = BMSShortcuts.allEventTypesGet
        # Skipping the confirm and cancel shortcuts as they're hardcoded.
        for shortcutName in (#'confirm', 'cancel',
                              'undo', 'redo', 'settings', 'increase',
                              'decrease', 'extremes', 'direction', 'bindunbind'):
            # The format of 'rawItemID' was defined in the bottom of getAllKeymaps().
            # (EVENT_TYPE, HAS_SHIFT, HAS_CTRL, HAS_ALT, HAS_OSKEY).
            # NOTE: HAS_OSKEY is ignored. None of the default Blender shortcuts use it
            #       and I believe no one uses it either.
            shortcutEntry = getattr(BMSShortcuts, shortcutName)
            if not shortcutEntry[2]:
                rawItemID = shortcutEntry[1]
                if rawItemID:
                    mods = (('Shift + ' if rawItemID[1] else '')
                            + ('Ctrl + ' if rawItemID[2] else '')
                            + ('Alt + ' if rawItemID[3] else ''))
                    eventData = allEventTypesGet(rawItemID[0], None)
                    if eventData:
                        shortcutEntry[2] = (
                            shortcutEntry[0] + mods + (eventData.description or eventData.name)
                        )
                    else:
                        shortcutEntry[2] = (
                            shortcutEntry[0] + mods + rawItemID[0].title().replace('_', '')
                        )


class BezierUtils:
    @staticmethod
    def evalPoint(t, controlPoints):
        # From https://incolumitas.com/2013/10/06/plotting-bezier-curves/
        mt = 1.0 - t
        mt2 = mt*mt
        t2 = t*t
        return (mt*mt2)*controlPoints[0] + (3.0*mt2*t)*controlPoints[1] \
             + (3.0*mt*t2)*controlPoints[2] + (t2*t)*controlPoints[3]


    @staticmethod
    def evalDerivative(t, controlPoints):
        mt = 1.0 - t
        return (3.0*mt*mt)*(controlPoints[1] - controlPoints[0]) \
        + (6.0*t*mt)*(controlPoints[2] - controlPoints[1]) + (3.0*t*t)*(controlPoints[3] - controlPoints[2])


    @staticmethod
    def fitBezierToVertices(vertices, curveDistance):
        '''
        Fits a cubic Bézier curve segment onto a sequence of vertices and returns the 4 control points.

        vertices: ordered list of BMVert items to be fit by a single cubic Bézier segment.
        Includes the start and end points.
        curveDistance: scalar factor to make the vertices offset along their normals.
        '''

        # Special case for when there's only 2 vertices being fit. Just make it a straight curve.
        if len(vertices) == 2:
            v0Co = vertices[0].co + vertices[0].normal * curveDistance
            v1Co = vertices[1].co + vertices[1].normal * curveDistance
            delta = (v1Co - v0Co) / 3.0
            return (v0Co[:], (v0Co + delta)[:], (v1Co - delta)[:], v1Co[:])

        # Consider the vertices as offset along their normals to avoid intersecting the mesh.
        _offsetPoints = tuple(v.co + v.normal * curveDistance for v in vertices)

        if len(_offsetPoints) == 3:
            # Add one extra data point to avoid a rare fitting error when there's only 3 vertices.
            # The extra point is added on the side where the middle vertex is farthest from.
            if (_offsetPoints[1] - _offsetPoints[0]).length_squared  < (_offsetPoints[2] - _offsetPoints[1]).length_squared:
                _offsetPoints = (_offsetPoints[0], _offsetPoints[1], (_offsetPoints[2] + _offsetPoints[1]) * 0.5, _offsetPoints[2])
            else:
                _offsetPoints = (_offsetPoints[0], (_offsetPoints[1] + _offsetPoints[0]) * 0.5, _offsetPoints[1], _offsetPoints[2])

        # Centripetal parameterization (https://pages.mtu.edu/~shene/COURSES/cs3621/NOTES/INT-APP/PARA-centripetal.html).
        def centripetalLengthGen():
            yield 0.0 # The parameter of the first point.
            currentLength = 0.0
            for index in range(len(_offsetPoints)-1):
                currentLength += sqrt((_offsetPoints[index+1] - _offsetPoints[index]).length)
                yield currentLength

        # Divide all accumulated length steps by the final step (final step = total polyline length).
        # This will normalize all length steps into the parameters of each point.
        parameters = Vector(centripetalLengthGen())
        parameters /= parameters[-1]

        # Cubic Bézier fitting algorithm by Luke Whittlesey.
        # https://nbviewer.jupyter.org/gist/anonymous/5688579
        # What follows is my optimization of it, adapted to Blender's mathutils.

        # Use vectors instead of the 4x4 matrix A and 4x1 matrix B.
        vectorA = Vector.Fill(16)
        tempVectorA = vectorA.copy()

        tempVectorB = Vector.Fill(4)
        vectorBX = tempVectorB.copy() # Each vector represents one 4x1 matrix B, for each axis.
        vectorBY = tempVectorB.copy()
        vectorBZ = tempVectorB.copy()

        for t, co in zip(parameters, _offsetPoints):
            t2 = t*t
            t3 = t2*t
            tm1 = t - 1.0
            tm1_2 = tm1*tm1
            tm1_3 = tm1_2*tm1
            # Compute the 16 matrix A values.
            tempVectorA[:] = (
                2.0*tm1_3*tm1_3,
                -6.0*t*tm1_3*tm1_2,
                6.0*t2*tm1_3*tm1,
                -2.0*t3*tm1_3,
                -6.0*t*tm1_3*tm1_2,
                18.0*t2*tm1_3*tm1,
                -18.0*t3*tm1_3,
                6.0*t3*t*tm1_2,
                6.0*t2*tm1_3*tm1,
                -18.0*t3*tm1_3,
                18.0*t3*t*tm1_2,
                -6.0*t3*t2*tm1,
                -2.0*t3*tm1_3,
                6.0*t3*t*tm1_2,
                -6.0*t3*t2*tm1,
                2.0*t3*t3
            )
            vectorA += tempVectorA # Component-wise summation.

            # Accumulate the 1-row "matrix B" values.
            x, y, z = co
            tempVectorB[:] = (
                2.0*tm1_3,
                -6.0*t*tm1_2,
                6.0*t2*tm1,
                -2.0*t3
            )
            vectorBX += (tempVectorB * x) # Component-wise product.
            vectorBY += (tempVectorB * y)
            vectorBZ += (tempVectorB * z)

        matrixAInv = Matrix((vectorA[:4], vectorA[4:8], vectorA[8:12], vectorA[12:16])).inverted()
        controlPoints = tuple(
            map(Vector, zip(matrixAInv @ -vectorBX, matrixAInv @ -vectorBY, matrixAInv @ -vectorBZ))
        )

        if curveDistance < 0.05:
            # Special-case for when the curve distance is small, force the start and end points to be at the
            # first and last vertices (otherwise they always miss them).
            alpha = curveDistance / 0.05
            return (
                vertices[0].co.lerp(controlPoints[0], alpha),
                controlPoints[1],
                controlPoints[2],
                vertices[-1].co.lerp(controlPoints[-1], alpha)
            )
        else:
            return controlPoints


class BMSProperties(bpy.types.PropertyGroup):
    useExtremes: bpy.props.BoolProperty(
        name = 'Include Extremity Vertices',
        description = 'Whether to deform both the ends of the curve or not',
        default = True
    )

    useDirection: bpy.props.BoolProperty(
        name = 'Use tangent direction',
        description = 'Whether to deform vertices using the curve direction',
        default = True
    )

    falloff: bpy.props.FloatProperty(
        name = 'Proportional Size',
        description = 'How far the deformation spreads to the vertices around the curve',
        min = 0.0001, # Close to but not exactly zero, as that leads to division-by-zero errors.
        max = 100.0,
        default = 0.7,
        precision = 2,
        step = 1,
        unit = 'LENGTH',
        options = {'HIDDEN'},
        update = lambda _self, _context: BMS_INSTANCE.onFalloffUpdate() if BMS_INSTANCE else None
    )

    falloffMode: bpy.props.EnumProperty(
        items = (
            ('OFF', 'Off', 'Turns proportional editing off (only the primary vertices will be used)', 'PROP_OFF', 0),
            ('DISTANCE', 'Distance', 'Deforms all vertices close to the curve', 'PROP_ON', 1),
            ('CONNECTED', 'Connected', 'Deforms only vertices that are physically connected to the primary vertices', 'PROP_CON', 2),
        ),
        name = 'Proportional Editing Mode',
        description = 'Proportional Editing Mode',
        default = 'DISTANCE',
        options = {'HIDDEN'},
        update = lambda _self, _context: BMS_INSTANCE.onFalloffUpdate() if BMS_INSTANCE else None
    )

    falloffType: bpy.props.EnumProperty(
        items = (
            ('SMOOTH', 'Smooth', 'Smooth falloff', 'SMOOTHCURVE', 0),
            ('CONSTANT', 'Constant', 'Constant falloff', 'NOCURVE', 1),
            ('LINEAR', 'Linear', 'Linear falloff', 'LINCURVE', 2),
            ('ROOT', 'Root', 'Root falloff', 'ROOTCURVE', 3),
            ('INVERSE_SQUARE', 'Inverse Square', 'Inverse Square falloff', 'ROOTCURVE', 4),
            ('SHARP', 'Sharp', 'Sharp falloff', 'SHARPCURVE', 5),
            ('SPHERE', 'Sphere', 'Spherical falloff', 'SPHERECURVE', 6),
            ('RANDOM', 'Random', 'Random falloff', 'RNDCURVE', 7),
        ),
        name = 'Falloff Type',
        description = 'The shape of the proportional editing falloff',
        default = 'SMOOTH',
        options = {'HIDDEN'},
        update = lambda _self, _context: BMS_INSTANCE.onFalloffTypeUpdate() if BMS_INSTANCE else None
    )


class BMSVirtualVertex:
    # Used in 'MESH_OT_bezier_mesh_shaper.tryAddRaycastKnot()', to represent a point in the middle of an edge.
    # This way these points can be used with the 'BezierUtils' class as if they were mesh vertices.
    # Their 't' parameter is used for sorting them back to the order they had on the picked line.
    def __init__(self, edge, co, normal, t):
        self.edge = edge # Edge reference is only used for making 'allBetweenVerts' from projected points.
        self.co = co
        self.normal = normal
        self.t = t
        # These next two attributes are used only when editing non-mesh objects, mimicking a BMVert.
        self.hide = False
        self.select = False


class BMSLatticeMesh:
    # Clever way to let this tool affect a lattice object.
    # Used as a wrapper around a lattice object so it behaves like a BMesh and Mesh.
    # Less code needed this way.
    def __init__(self, obj):
        latticePoints = obj.data.points
        self.latticePoints = latticePoints
        # 'verts' will be modified by the operator.
        self.verts = [
            BMSVirtualVertex(edge=None, co=p.co_deform.copy(), normal=None, t=None) for p in latticePoints
        ]

    def to_mesh(self, mesh):
        # BMesh method, commits the coordinates in 'verts' to the actual points of the non-mesh object.
        for point, vert in zip(self.latticePoints, self.verts):
            point.co_deform = vert.co

    def explicitPoints(self):
        NULL_VECTOR = Vector()
        return [
            BMSVirtualVertex(edge=None, co=point.co_deform, normal=NULL_VECTOR, t=None)
            for point in self.latticePoints if point.select
        ]

    def select_linked(self):
        for vert in self.verts:
            vert.select = True

    def free(self):
        pass # BMesh method.

    def update(self):
        pass # Mesh method.


class BMSNURBSMesh:
    # Used as a wrapper around a NURBS Surface object so it behaves like a BMesh and Mesh.
    # NURBS surface points are 4D (x,y,z,w).
    def __init__(self, obj):
        self.splines = obj.data.splines
        self.verts = [
            BMSVirtualVertex(edge=None, co=point.co.to_3d(), normal=None, t=None)
            for spline in self.splines
            for point in spline.points
        ]

    def to_mesh(self, mesh):
        for point, vert in zip(chain.from_iterable(spline.points for spline in self.splines), self.verts):
            point.co[:3] = vert.co

    def explicitPoints(self):
        NULL_VECTOR = Vector()
        return [
            BMSVirtualVertex(edge=None, co=point.co.to_3d(), normal=NULL_VECTOR, t=None)
            for spline in self.splines
            for point in spline.points if point.select
        ]

    def select_linked(self):
        # Called from 'initializeBezierCurve()', selects all the points of splines that have one or more
        # selected points.
        # This mimics the 'bpy.ops.mesh.select_linked' operator on meshes.
        pointsCounter = 0
        for spline in self.splines:
            tempLen = len(spline.points)
            if any(point.select for point in spline.points):
                for vert in self.verts[pointsCounter : pointsCounter + tempLen]:
                    vert.select = True
            pointsCounter += tempLen

    def free(self):
        pass

    def update(self):
        pass


class BMS_OT_transform_settings(bpy.types.Operator):
    '''Change the transform manipulator settings'''
    bl_idname = 'bms.transform_settings'
    bl_label = 'Transform Settings'
    bl_options = {'REGISTER', 'INTERNAL'}

    # Needs this dummy property or the '.invoke_popup()' call below in 'execute()' crashes Blender.
    myBool: bpy.props.BoolProperty(name='Dummy', options={'HIDDEN', 'SKIP_SAVE'})

    def draw(self, context):
        self.layout.row(align=True).label(text='Transform Settings', icon='OBJECT_ORIGIN')
        self.layout.prop(bpy.context.tool_settings, 'transform_pivot_point')
        self.layout.prop(bpy.context.scene.transform_orientation_slots[0], 'type')

    def execute(self, context):
        return context.window_manager.invoke_popup(self, width=0)


class BMS_OT_split(bpy.types.Operator):
    '''Split the curve this many times on each segment'''
    bl_idname = 'bms.split'
    bl_label = 'B.M.S. Split Helper'
    bl_options = {'REGISTER', 'INTERNAL'}

    numberCuts: bpy.props.IntProperty(
        name = 'Number of Splits',
        description = 'Amount of new points, per segment, to split the curve with',
        default = 1,
        min = 1,
        max = 5,
        options = {'HIDDEN'}
    )

    def execute(self, context):
        global BMS_INSTANCE
        if BMS_INSTANCE:
            BMS_INSTANCE.onSubdivide(self.numberCuts)
        return {'CANCELLED'}


class BMS_OT_snap(bpy.types.Operator):
    '''Snap the primary vertices onto the curve. \nThe \'Force Primary Vertices\' preference needs to be on,\n''' \
    '''and it\'s best to use a \'Curve Distance\' preference of zero'''
    bl_idname = 'bms.snap'
    bl_label = 'B.M.S. Snap Helper'
    bl_options = {'REGISTER', 'INTERNAL'}

    mode: bpy.props.EnumProperty(
        name = 'Snap Mode',
        items = (
            ('SNAP_SMOOTH', 'Smooth', 'Snaps the primary vertices to the curve', 'IPO_EASE_IN_OUT', 0),
            ('SNAP_STRAIGHT', 'Straight', 'Straightens the curve, then snaps vertices', 'IPO_LINEAR', 1),
            ('SNAP_SMOOTH_P', 'Smooth (Proportional)', 'Snaps the primary vertices to the curve but keeps '\
            'their relative distances', 'IPO_EASE_IN_OUT', 2),
            ('SNAP_STRAIGHT_P', 'Straight (Proportional)', 'Straightens the curve, then snaps vertices '\
            'but keeps their relative distances', 'IPO_LINEAR', 3),
        ),
        description = 'What kind of curve snapping to perform',
        default = 'SNAP_STRAIGHT'
    )

    def execute(self, context):
        global BMS_INSTANCE
        if BMS_INSTANCE:
            BMS_INSTANCE.onSnap(self.mode)
        return {'CANCELLED'}


class BMS_OT_export_curve(bpy.types.Operator):
    '''Create a copy of the curve as a new object'''
    bl_idname = 'bms.extract_curve'
    bl_label = 'B.M.S. Extract Helper'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global BMS_INSTANCE
        if BMS_INSTANCE:
            BMS_INSTANCE.onCopyCurve(context)
        else:
            self.report({'INFO'}, 'No curve found, nothing to extract.')
        return {'CANCELLED'}


class BMS_MT_split_menu(bpy.types.Menu):
    bl_label = 'Split Curve'

    def draw(self, context):
        layout = self.layout
        layout.operator('bms.split', text='1x').numberCuts = 1
        layout.operator('bms.split', text='2x').numberCuts = 2
        layout.operator('bms.split', text='3x').numberCuts = 3
        layout.operator('bms.split', text='4x').numberCuts = 4
        layout.operator('bms.split', text='5x').numberCuts = 5


class BMS_MT_snap_menu(bpy.types.Menu):
    bl_label = 'Snap To Curve'

    def draw(self, context):
        layout = self.layout
        layout.operator('bms.snap', text='Smooth').mode = 'SNAP_SMOOTH'
        layout.operator('bms.snap', text='Straight').mode = 'SNAP_STRAIGHT'
        layout.operator('bms.snap', text='Smooth (Proportional)').mode = 'SNAP_SMOOTH_P'
        layout.operator('bms.snap', text='Straight (Proportional)').mode = 'SNAP_STRAIGHT_P'


class BMS_MT_pie_menu(bpy.types.Menu):
    bl_label = 'Proportional Editing Falloff'

    def draw(self, context):
        # Pie menus order their items like this: W, E, S, N, then NW, NE, SW, SE.
        # See here: https://blender.stackexchange.com/a/44706

        bmsProperties = context.scene.bmsProperties
        pie = self.layout.menu_pie()

        box = pie.box() # W
        box.label(text='Proportional Editing Falloff')
        box.prop(bmsProperties, 'falloffMode', text='Mode:') if BMS_INSTANCE.meshMode else box.label('(Lattice Mode)')
        box.prop(bmsProperties, 'falloff', text='Falloff Size:')
        box.prop(bmsProperties, 'falloffType')

        # E
        pie.menu('BMS_MT_snap_menu', text='Snap To Curve...') if BMS_INSTANCE.meshMode else pie.label('(Snap Unavailable)')

        box = pie.box() # S
        box.label(text='Extras:')
        box.operator('bms.transform_settings')
        box.operator('bms.extract_curve', text='Extract Curve')
        row = box.row(align=True)
        row.prop(BMS_INSTANCE.obj, 'show_wire', toggle=True)
        row.prop(BMS_INSTANCE.obj, 'show_all_edges', toggle=True)
        row = box.row(align=True)
        row.prop(context.space_data.overlay, 'show_wireframes', text='Global Wireframes', toggle=True)
        row.prop(context.space_data.overlay, 'wireframe_threshold', text='', slider=True)

        pie.separator() # N

        pie.separator() # NW

        # NE
        # Same as in VIEW3D_MT_edit_curve_ctrlpoints from "space_view3d.py".
        if context.mode == 'EDIT_CURVE':
            pie.operator_menu_enum('curve.handle_type_set', 'type')
        else:
            pie.separator()

        pie.separator() # SW

        pie.menu('BMS_MT_split_menu', text='Split Curve...') # SE


class MESH_OT_bezier_mesh_shaper(bpy.types.Operator):
    '''Create a Bézier curve with knots on each selected vertex and manipulate the mesh with it'''
    bl_idname = 'mesh.bezier_mesh_shaper'
    bl_label = 'Bezier Mesh Shaper'
    #bl_undo_group = 'Bezier Mesh Shaper'
    bl_options = {'REGISTER', 'UNDO', 'UNDO_GROUPED', 'BLOCKING'}

    startupAction: bpy.props.EnumProperty(
        name = 'Startup',
        items = (
            ('NORMAL', 'Normal', 'Normal tool startup, no actions', '', 0),
            ('SNAP_SMOOTH', 'Snap To Curve: Smooth', 'Start the tool and use Snap To Curve -> Smooth operation', '', 1),
            ('SNAP_STRAIGHT', 'Snap To Curve: Straight', 'Start the tool and use Snap To Curve -> Straight operation', '', 2),
            ('SNAP_SMOOTH_P', 'Snap To Curve: Smooth (Proportional)', 'Start the tool and use Snap To Curve -> ' \
            'Straight (Proportional) operation', '', 3),
            ('SNAP_STRAIGHT_P', 'Snap To Curve: Straight (Proportional)', 'Start the tool and use Snap To Curve -> ' \
            'Straight (Proportional) operation', '', 4),
            ('ALIGNED', 'Aligned', 'Start the tool with the curve set to Aligned tangents (straight line between ' \
            'the two end points)', '', 5)
        ),
        description = 'What kind of action the tool should perform after starting',
        default = 'NORMAL'
    )

    # Keeping shader interface + main code separate to support Blender 4.x and Blender 5.x.
    POSTPIXEL_VERT_SOURCE_INTERFACE = '''
        uniform mat4 ModelViewProjectionMatrix;
        uniform vec2 offsetPos;
        uniform float scale;
        in vec2 pos;
    '''

    POSTPIXEL_VERT_SOURCE_MAIN = '''
        void main()
        {
            gl_Position = ModelViewProjectionMatrix * vec4((pos * scale) + offsetPos, 0.0, 1.0);
        }
    '''

    POSTPIXEL_FRAG_SOURCE_INTERFACE = '''
        uniform vec4 color;
        out vec4 fragColor;
        #define BLENDER_SRGB(x) (blender_srgb_to_framebuffer_space(x))
    '''

    POSTPIXEL_FRAG_SOURCE_MAIN = '''
        void main()
        {
            fragColor = BLENDER_SRGB(color);
        }
    '''

    # Store some values in a 'CurveGrab' object to be used at every grab update.

    class CurveGrab:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


    @staticmethod
    def falloffMenu(self, context):
        bmsProperties = context.scene.bmsProperties
        layout = self.layout

        # Compact enum prop (drop-down menu) with no label, shows the current mode better.
        layout.prop(bmsProperties, 'falloffMode', text='')# if BMS_INSTANCE.meshMode else layout.label(text='(Non-Mesh Mode)')

        layout.separator()
        row = layout.row(align=True)
        row.prop(bmsProperties, 'falloff')
        layout.separator()
        layout.prop(bmsProperties, 'falloffType', expand=True)
        layout.separator()

        # Same as in VIEW3D_MT_edit_curve_ctrlpoints from "space_view3d.py".
        if context.mode == 'EDIT_CURVE':
            layout.operator_menu_enum('curve.handle_type_set', 'type')

        layout.menu('BMS_MT_snap_menu') if BMS_INSTANCE.meshMode else layout.label(text='(Snap Unavailable)')
        layout.menu('BMS_MT_split_menu')

        layout.operator('bms.transform_settings')
        layout.operator('bms.extract_curve', text='Extract Curve')
        layout.separator()
        layout.prop(BMS_INSTANCE.obj, 'show_wire', toggle=True)
        layout.prop(BMS_INSTANCE.obj, 'show_all_edges', toggle=True)
        layout.prop(context.space_data.overlay, 'show_wireframes', text='Global Wireframes', toggle=True)
        layout.prop(context.space_data.overlay, 'wireframe_threshold', text='Global Threshold', slider=True)


    @staticmethod
    def projection3DHelper(self):
        # Draws all thick lines between the picked knots.
        if self.allPointsBuffer:
            gpuState = gpu.state
            oldDepthFunc = gpuState.depth_test_get()
            gpuState.depth_test_set('ALWAYS')

            gpuState.line_width_set(3)
            gpuState.point_size_set(5)

            tempVertexBuffer = gpu.types.GPUVertBuf(self.postViewFormat, len(self.allPointsBuffer))
            tempVertexBuffer.attr_fill(id='pos', data=self.allPointsBuffer)

            linesBatch = gpu.types.GPUBatch(type='LINE_STRIP', buf=tempVertexBuffer)
            pointsBatch = gpu.types.GPUBatch(type='POINTS', buf=tempVertexBuffer)

            self.postViewShader.bind()

            # Black lines.
            self.postViewShader.uniform_float('color', (0.05, 0.05, 0.1, 1.0))
            linesBatch.draw(self.postViewShader)

            # Blue intersected dots.
            self.postViewShader.uniform_float('color', (0.0, 0.627, 1.0, 1.0))
            pointsBatch.draw(self.postViewShader)

            gpu.shader.unbind()

            gpuState.line_width_set(1)
            gpuState.point_size_set(1)
            gpuState.depth_test_set(oldDepthFunc)


    @staticmethod
    def axisLock3DHelper(self):
        # Draws one infinite line for the locking axis, or two lines for the locking plane.
        gpu.state.line_width_set(1)
        self.axisLockBatch.draw(self.axisLockShader)


    @staticmethod
    def projection2DHelper(self):
        gpu.state.line_width_set(3)
        self.postPixelShader.bind()

        # Draw the knots, if any.
        if len(self.pickedKnotData):
            self.postPixelShader.uniform_float('scale', 1.0)

            perspectiveCompMatrix = self.perspectiveMatrix @ self.obj.matrix_world
            halfWidth = self.region.width * 0.5
            halfHeight = self.region.height * 0.5

            circleBuff = gpu.types.GPUVertBuf(self.postPixelFormat, len(self.baseCirclePoints))
            circleBuff.attr_fill(id='pos', data=self.baseCirclePoints)
            knotStrokeBatch = gpu.types.GPUBatch(type='LINE_LOOP', buf=circleBuff)
            knotFillBatch = gpu.types.GPUBatch(type='TRI_FAN', buf=circleBuff)

            hasDash = False
            for knotData in self.pickedKnotData:
                proj = perspectiveCompMatrix @ knotData[0] # Project the raycast knot location.
                if proj[3] > 0.0:
                    hasDash = True
                    proj = (halfWidth * (1.0 + proj[0] / proj[3]), halfHeight * (1.0 + proj[1] / proj[3]))
                    self.postPixelShader.uniform_float('offsetPos', proj)

                    # Blue fill.
                    self.postPixelShader.uniform_float('color', (0.0, 0.627, 1.0, 1.0))
                    knotFillBatch.draw(self.postPixelShader)

                    # Dark outline.
                    self.postPixelShader.uniform_float('color', (0.05, 0.05, 0.1, 1.0))
                    knotStrokeBatch.draw(self.postPixelShader)
                else:
                    hasDash = False

            if hasDash:
                # Draw the line towards the cursor. The 'proj' variable holds the last projected knot.
                self.postPixelShader.uniform_float('offsetPos', (0, 0))
                dashVertexBuffer = gpu.types.GPUVertBuf(self.postPixelFormat, 2)
                dashVertexBuffer.attr_fill(id='pos', data=(proj, self.eventCoords))
                gpu.types.GPUBatch(type='LINES', buf=dashVertexBuffer).draw(self.postPixelShader)

        # Draw the cursor knot.
        self.postPixelShader.uniform_float('color', (1.0, 1.0, float(not self.straightPressed), 1.0))
        self.postPixelShader.uniform_float('offsetPos', self.eventCoords)
        self.postPixelShader.uniform_float('scale', 1.0 if self.clickPressed else 1.25)

        dashVertexBuffer = gpu.types.GPUVertBuf(self.postPixelFormat, len(self.baseCirclePoints))
        dashVertexBuffer.attr_fill(id='pos', data=self.baseCirclePoints)
        gpu.types.GPUBatch(type='LINE_LOOP', buf=dashVertexBuffer).draw(self.postPixelShader)

        gpu.shader.unbind()
        gpu.state.line_width_set(1)

        if BMS_ADDON_PREFS.showKeymaps:
            fontID = 0
            blf.size(fontID, int(BMS_ADDON_PREFS.keymapsTextSize * self.uiScale))
            height = blf.dimensions(fontID, 'M')[1] * 2.0

            posX = height + height
            posY = height * 8

            blf.color(fontID, 0.0, 1.0, 1.0, 1.0)
            blf.position(fontID, posX, posY, 0)

            blf.draw(fontID, 'Bézier Mesh Shaper - Projection Mode')
            blf.color(fontID, 1.0, 1.0, 1.0, 1.0)
            posY -= height
            blf.position(fontID, posX, posY, 0)
            blf.draw(fontID, '(Left-click to place knots on mesh surface)')
            posY -= height
            blf.position(fontID, posX, posY, 0)
            confirmText = BMSShortcuts.confirm[2]
            if BMS_ADDON_PREFS.spaceConfirms:
                confirmText += '/Space'
            blf.draw(fontID, confirmText)
            posY -= height
            blf.position(fontID, posX, posY, 0)
            blf.draw(fontID, BMSShortcuts.cancel[2])
            posY -= height
            blf.position(fontID, posX, posY, 0)
            blf.draw(fontID, 'Remove Last Point: Backspace')
            posY -= height
            blf.position(fontID, posX, posY, 0)
            blf.draw(fontID, 'Straight Pick Mode: E (Hold)')


    @staticmethod
    def unbound2DHelper(self):
        fontID = 0
        blf.size(fontID, int(16.0 * self.uiScale))
        height = blf.dimensions(fontID, 'M')[1] * 2.0

        posX = height + height
        posY = height * 6

        blf.color(fontID, 0.0, 1.0, 1.0, 1.0)
        blf.position(fontID, posX, posY, 0)

        blf.draw(fontID, 'Bézier Mesh Shaper')
        posY -= height
        blf.color(fontID, 1.0, 1.0, 1.0, 1.0)
        blf.position(fontID, posX, posY, 0)
        blf.draw(fontID, 'Unbound Mode')
        posY -= height
        blf.position(fontID, posX, posY, 0)
        if self.unbindLabel:
            blf.draw(fontID, '(Press %s to re-bind)' % self.unbindLabel)


    @staticmethod
    def shortcuts2DHelper(self):
        fontID = 0
        blf.size(fontID, int(BMS_ADDON_PREFS.keymapsTextSize * self.uiScale))
        height = blf.dimensions(fontID, 'M')[1] * 2.0

        posX = height + height
        posY = height * 12

        blf.color(fontID, 0.0, 1.0, 1.0, 1.0)
        blf.position(fontID, posX, posY, 0)

        blf.draw(fontID, 'Bézier Mesh Shaper')
        blf.color(fontID, 1.0, 1.0, 1.0, 1.0)
        bmsShortcuts = BMSShortcuts
        posY -= height
        blf.position(fontID, posX, posY, 0)
        blf.draw(fontID, bmsShortcuts.confirm[2])
        posY -= height
        blf.position(fontID, posX, posY, 0)
        blf.draw(fontID, bmsShortcuts.cancel[2])
        posY -= height
        blf.position(fontID, posX, posY, 0)
        blf.draw(fontID, bmsShortcuts.undo[2] or bmsShortcuts.undo[0])
        posY -= height
        blf.position(fontID, posX, posY, 0)
        blf.draw(fontID, bmsShortcuts.redo[2] or bmsShortcuts.redo[0])
        posY -= height
        blf.position(fontID, posX, posY, 0)
        blf.draw(fontID, bmsShortcuts.settings[2] or bmsShortcuts.settings[0])
        posY -= height
        blf.position(fontID, posX, posY, 0)
        blf.draw(fontID, bmsShortcuts.increase[2] or bmsShortcuts.increase[0])
        posY -= height
        blf.position(fontID, posX, posY, 0)
        blf.draw(fontID, bmsShortcuts.decrease[2] or bmsShortcuts.decrease[0])
        posY -= height
        blf.position(fontID, posX, posY, 0)
        flag = 'ON' if self.bmsProperties.useDirection else 'OFF'
        blf.draw(fontID, 'Use Direction (' + flag + '): ' + (bmsShortcuts.direction[2] or ''))
        posY -= height
        blf.position(fontID, posX, posY, 0)
        flag = 'ON' if self.bmsProperties.useExtremes else 'OFF'
        blf.draw(fontID, 'Use Extremes (' + flag + '): ' + (bmsShortcuts.extremes[2] or ''))
        posY -= height
        blf.position(fontID, posX, posY, 0)
        blf.draw(fontID, bmsShortcuts.bindunbind[2] or bmsShortcuts.bindunbind[0])


    @classmethod
    def poll(cls, context):
        # Edit mode on a mesh object, or edit mode on a lattice object.
        return context.mode in {'EDIT_MESH', 'EDIT_LATTICE', 'EDIT_SURFACE'}


    def getToolMessage(self):
        extremes = 'ON' if self.bmsProperties.useExtremes else 'OFF'
        direction = 'ON' if self.bmsProperties.useDirection else 'OFF'
        return self.toolMessage % (extremes, direction) + '%.2f' % self.bmsProperties.falloff


    def tagRedrawAreas(self):
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                area.tag_redraw()


    def getGrabMessage(self):
        if self.curveGrab and self.curveGrab.axisLock:
            axisLock = self.curveGrab.axisLock
            axisMessage = (
                ('Locking ' if axisLock[0] else '')
                + ('Local ' if axisLock[2] else 'Global ')
                + (
                    ('X' if axisLock[1][0] else 'Y' if axisLock[1][1] else 'Z')
                    if axisLock[0] else
                    ('X' if axisLock[3][0] else 'Y' if axisLock[3][1] else 'Z')
                )
            )
        else:
            axisMessage = 'None'
        return self.grabMessage % axisMessage


    def updateInfo(self, message):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.header_text_set(message or None)


    def addDrawHandler(self, func, args, target):
        if target == 'POST_PIXEL':
            if self.active2DDrawHandler:
                bpy.types.SpaceView3D.draw_handler_remove(self.active2DDrawHandler, 'WINDOW')
            self.active2DDrawHandler = bpy.types.SpaceView3D.draw_handler_add(
                func, args, 'WINDOW', target
            )
        else:
            if self.active3DDrawHandler:
                self.clearAllDrawHandlers()
                #raise Exception('DEBUG: Conflicting 3D draw handlers')
            self.active3DDrawHandler = bpy.types.SpaceView3D.draw_handler_add(
                func, args, 'WINDOW', target
            )


    def clear3DDrawHandler(self):
        if self.active3DDrawHandler:
            bpy.types.SpaceView3D.draw_handler_remove(self.active3DDrawHandler, 'WINDOW')
            self.active3DDrawHandler = None


    def clearAllDrawHandlers(self):
        if self.active2DDrawHandler:
            bpy.types.SpaceView3D.draw_handler_remove(self.active2DDrawHandler, 'WINDOW')
            self.active2DDrawHandler = None
        self.clear3DDrawHandler()


    def onSubdivide(self, numberCuts):
        # This function is called by the 'BMS_OT_split' operator.
        # The menu with that operator is only accessible from the 'toolModal() -> onKeyMenu()' function.

        for knot in self.bezier_points:
            knot.select_control_point = True

        bpy.ops.curve.subdivide(number_cuts=numberCuts)

        for knot in self.bezier_points:
            knot.select_control_point = knot.select_left_handle = knot.select_right_handle = False

        # Remap all vertices to this new piecewise curve.
        if self.fullCurveRemap(fromSubdivide=True):
            if self.bmsProperties.falloffMode == 'OFF':
                self.report({'INFO'}, "Curve split. Change the falloff mode to 'Distance' or 'Connected' to use the curve")
            else:
                self.report({'INFO'}, 'Curve split successfully')
            self.updateDeform()
        else:
            # The remapping failed? Should never happen.
            pass


    def onSnap(self, snapMode):
        allBetweenVerts = self.allBetweenVerts or getattr(self, 'originalAllBetweenVerts', None)
        if allBetweenVerts:
            evalPoint = BezierUtils.evalPoint
            evalDerivative = BezierUtils.evalDerivative

            totalLength = 0
            NULL_VECTOR = Vector()
            offsetControlPoints = self.offsetControlPoints
            totalSegments = len(offsetControlPoints)
            lastSegmentIndex = totalSegments - 1
            halfStepComp = 1.0 - BMS_PLOT_HALFSTEP

            mappedVertices = self.mappedVertices
            bmVerts = self.bm.verts

            # Since we're remapping vertices in here, we need to remember their starting locations
            # to let the user eventually cancel the tool, if they want to.
            self.createOriginalLocations()

            # Create a deque holding the 'before' vertexData of the betweenVerts
            # (the primary vertices), to be used with undo.
            # At the end, another deque for the 'after' vertexData will also be created.
            beforeBetweenVertsData = deque(tuple(mappedVertices[bmVerts[betweenData[0]]])
                                           for betweenData in allBetweenVerts)

            # We process the first and last vertices separately, in order to make them have perfectly round
            # 0.0 and 1.0 parameters.
            allBetweenIter = iter(allBetweenVerts)

            # This is the first primary vertex:
            vIndex, segmentIndex = next(allBetweenIter)
            vertex = bmVerts[vIndex]
            controlPoints = offsetControlPoints[0]
            vertex.co = controlPoints[0]
            mappedVertices[vertex] = (
                vertex,
                0.0,
                vertex.co.copy(),
                NULL_VECTOR, # Zero vector, no offset.
                evalDerivative(0.0, controlPoints),
                segmentIndex,
                controlPoints,
                0.0,
                True
            )

            if snapMode in {'SNAP_SMOOTH', 'SNAP_SMOOTH_P'}:
                # Normal mode (keep the curve as it is).
                # We snap the 'allBetweenVerts' (the primary vertices) onto the whole piecewise curve.

                # Get the approximate arc length of each segment of the curve.
                lastPoint = offsetControlPoints[0][0]
                segmentLengths = [ ]
                segmentLengthPoints = [ ]

                for controlPoints in offsetControlPoints:
                    lengthPoints = [ ]
                    for p in interpolate_bezier(*controlPoints, BMS_PLOT_RESOLUTION):
                        totalLength += (p - lastPoint).length
                        lengthPoints.append(totalLength) # Partial curve length at each plotted segment point.
                        lastPoint = p
                    segmentLengths.append(totalLength) # Important: the segment lengths accumulate.
                    segmentLengthPoints.append(lengthPoints)

                if snapMode == 'SNAP_SMOOTH':
                    # Evenly distributed.
                    # Divide the total length by the number of steps needed to fit all vertices.
                    stepLength = totalLength / (len(allBetweenVerts) - 1)
                    nextDesiredLength = lambda index: index * stepLength
                else:
                    # Proportionally distributed.
                    # First pass, get the chordal lengths along the polyline of between verts.
                    stepLengths = [ ]
                    totalChordalLength = 0
                    lastCo = offsetControlPoints[0][0]
                    for betweenData in allBetweenVerts:
                        co = bmVerts[betweenData[0]].co
                        totalChordalLength += (co - lastCo).length
                        stepLengths.append(totalChordalLength)
                        lastCo = co
                    # Second pass, set their chordal lengths relative to the total curve length.
                    for index in range(len(stepLengths)):
                        stepLengths[index] = (stepLengths[index] / totalChordalLength) * totalLength
                    nextDesiredLength = lambda index: stepLengths[index]

                # Snap the primary vertices to the curve, based on their t-for-length. We find out what
                # their 't' parameters should be for them to be at even steps along the curve.

                newSegmentIndex = 0
                segmentLength = segmentLengths[newSegmentIndex] # Partial curve lengths "up to" that segment.
                currentLengthIndex = 0
                currentLengthPoints = segmentLengthPoints[newSegmentIndex]

                # Process the next vertices: from the second betweenVert until the second last.
                # The first and last betweenVerts are processed separately to ensure
                # perfect hardcoded parameters (t, co etc).
                for stepIndex in range(1, len(allBetweenVerts)-1):
                    desiredLength = nextDesiredLength(stepIndex)

                    # The 'allBetweenVerts' vertices are ordered, meaning they can only advance in point index
                    # and segment index from one vertex to the next.
                    if desiredLength > segmentLength:
                        while segmentLengths[newSegmentIndex] < desiredLength:
                            newSegmentIndex += 1
                        segmentLength = segmentLengths[newSegmentIndex]
                        currentLengthPoints = segmentLengthPoints[newSegmentIndex]
                        currentLengthIndex = 0
                    elif currentLengthIndex > 0:
                        currentLengthIndex -= 1 # Should help when there's more vertices than plotted points.

                    while currentLengthPoints[currentLengthIndex] < desiredLength:
                        currentLengthIndex += 1

                    previousLengthIndex = currentLengthIndex - 1
                    previousLength = currentLengthPoints[previousLengthIndex]

                    factor = (
                        (desiredLength - previousLength) / (currentLengthPoints[currentLengthIndex] - previousLength)
                    )
                    newT = (previousLengthIndex + factor) / BMS_PLOT_DIVISOR

                    # Similar code to 'genericInfluencesGen()', remapping the vertex to the curve but using
                    # the 'newT' and 'newSegmentIndex' found above.

                    vertex = bmVerts[next(allBetweenIter)[0]]
                    vCo = evalPoint(newT, offsetControlPoints[newSegmentIndex])
                    vertex.co = vCo

                    mappedVertices[vertex] = (
                        vertex,
                        0.0,
                        vCo,
                        NULL_VECTOR, # Zero vector, no offset.
                        evalDerivative(newT, offsetControlPoints[newSegmentIndex]),
                        newSegmentIndex,
                        offsetControlPoints[newSegmentIndex],
                        newT,
                        not (
                            (newSegmentIndex == 0 and newT < BMS_PLOT_HALFSTEP)
                            or (newSegmentIndex == lastSegmentIndex and newT > halfStepComp)
                        )
                    )

            elif snapMode in {'SNAP_STRAIGHT', 'SNAP_STRAIGHT_P'}:
                # Straight mode (straighten the curve before snapping).
                # We optimise the math since we're just snapping points to a sequence of lines.

                segmentLengths = [ ]
                bps = self.bezier_points
                useVectorHandle = BMS_ADDON_PREFS.useVectorHandleStraight
                for knotIndex in range(totalSegments):
                    knotA = bps[knotIndex]
                    knotB = bps[knotIndex+1]

                    # Set all knots to have the same handle types, depending on a preference.
                    if useVectorHandle:
                        knotA.handle_left_type = knotA.handle_right_type = 'VECTOR'
                        knotB.handle_left_type = knotB.handle_right_type = 'VECTOR'
                    else:
                        knotA.handle_left_type = knotA.handle_right_type = 'FREE'
                        knotB.handle_left_type = knotB.handle_right_type = 'FREE'

                    lineVec = knotB.co - knotA.co
                    totalLength += lineVec.length
                    segmentLengths.append(totalLength)

                    # Put P1 and P2 on thirds along the "linear" curve.
                    thirdOffset = lineVec * 0.33333333333333333
                    knotA.handle_right = knotA.co + thirdOffset
                    knotB.handle_left = knotB.co - thirdOffset
                # Also change the outside handles of the first and last knots of the curve, just for cosmetics.
                bps[0].handle_left = bps[0].co - (bps[0].handle_right - bps[0].co)
                bps[-1].handle_right = bps[-1].co - (bps[-1].handle_left - bps[-1].co)

                # Reset the reference knots of the "original" curve, since the curve was modified and reset
                # to a new initial state now.
                self.frozenControlPoints = tuple(
                    tuple(map(Vector, controlPoints)) for controlPoints in offsetControlPoints
                )
                self.mapControlPoints = self.frozenControlPoints

                if snapMode == 'SNAP_STRAIGHT':
                    # Evenly distributed.
                    stepLength = totalLength / (len(allBetweenVerts) - 1)
                    nextDesiredLength = lambda index: index * stepLength
                else:
                    # Proportionally distributed.
                    stepLengths = [ ]
                    totalChordalLength = 0
                    lastCo = offsetControlPoints[0][0]
                    for betweenData in allBetweenVerts:
                        co = bmVerts[betweenData[0]].co
                        totalChordalLength += (co - lastCo).length
                        stepLengths.append(totalChordalLength)
                        lastCo = co
                    for index in range(len(stepLengths)):
                        stepLengths[index] = (stepLengths[index] / totalChordalLength) * totalLength
                    nextDesiredLength = lambda index: stepLengths[index]

                newSegmentIndex = 0
                segmentLength = segmentLengths[newSegmentIndex]
                previousSegmentLength = 0.0

                allBetweenSet = set()

                for stepIndex in range(1, len(allBetweenVerts)-1):
                    desiredLength = nextDesiredLength(stepIndex)

                    if desiredLength > segmentLength:
                        previousSegmentLength = segmentLength
                        while segmentLengths[newSegmentIndex] < desiredLength:
                            newSegmentIndex += 1
                        segmentLength = segmentLengths[newSegmentIndex]

                    newT = (desiredLength - previousSegmentLength) / (segmentLength - previousSegmentLength)

                    vertex = bmVerts[next(allBetweenIter)[0]]
                    vCo = evalPoint(newT, offsetControlPoints[newSegmentIndex])
                    vertex.co = vCo

                    mappedVertices[vertex] = (
                        vertex,
                        0.0,
                        vCo,
                        NULL_VECTOR, # Zero vector, no offset.
                        evalDerivative(newT, offsetControlPoints[newSegmentIndex]),
                        newSegmentIndex,
                        offsetControlPoints[newSegmentIndex],
                        newT,
                        not (
                            (newSegmentIndex == 0 and newT < BMS_PLOT_HALFSTEP)
                            or (newSegmentIndex == lastSegmentIndex and newT > halfStepComp)
                        )
                    )
                    allBetweenSet.add(vertex)

            # Process the last primary vertex.
            vIndex, segmentIndex = next(allBetweenIter)
            vertex = bmVerts[vIndex]
            controlPoints = offsetControlPoints[-1]
            vertex.co = controlPoints[-1]
            mappedVertices[vertex] = (
                vertex,
                0.0,
                vertex.co.copy(),
                NULL_VECTOR,
                evalDerivative(1.0, controlPoints),
                segmentIndex,
                controlPoints,
                1.0,
                True
            )

            if snapMode in {'SNAP_STRAIGHT', 'SNAP_STRAIGHT_P'}:
                # Final setup when finishing the straight snap mode(s): set other vertices to
                # be remapped to the new shape of the curve.

                # Add the first and last primary vertices, since they were processed separately.
                allBetweenSet.add(bmVerts[allBetweenVerts[0][0]])
                allBetweenSet.add(bmVerts[allBetweenVerts[-1][0]])
                # Forget all non-primary vertices that were mapped.
                for vertex in set(mappedVertices) - allBetweenSet:
                    del mappedVertices[vertex]

                # The curve shape changed in this straight snap, so recreate the KDTrees and
                # the undo origin (the base undo step).
                self.segmentKDTrees = tuple(self.segmentsKDTreesGen(self.mapControlPoints))
                self.resetUndoStack()
                self.influencedSet.clear()
                self.lastFalloff = -1.0

            # Also update the 'self.influencedVertices' deque items (if needed), since it now holds references to
            # old 'vertexData' items that are now obsolete (i.e obsolete tangent vector, original vertex
            # location etc.).
            self.refreshInfluencedFromMapped()

            afterBetweenVertexData = deque(tuple(mappedVertices[bmVerts[betweenData[0]]])
                                           for betweenData in allBetweenVerts)
            self.pushVertexDataUndoStep(beforeBetweenVertsData, afterBetweenVertexData)

            # Show the snapped deformation right away.
            self.updateDeform()
        else:
            self.report({'WARNING'}, 'No primary vertices to snap, make sure ' \
            'the \'Force Primary Vertices\' preference is on')


    def onCopyCurve(self, context):
        # Create a copy of the curve as a new object in the same scene.
        name = 'BezierMeshShaper Curve Copy'
        newCurve = bpy.data.curves.new(name, 'CURVE')
        newCurve.dimensions = '3D'

        splineBPs = newCurve.splines.new('BEZIER').bezier_points
        splineBPs.add(self.startingLen-1)
        originalBPs = self.bezier_points
        for knotIndex, originalKnot in enumerate(self.bezier_points):
            splineKnot = splineBPs[knotIndex]

            splineKnot.co = originalKnot.co
            splineKnot.handle_left_type = originalKnot.handle_left_type
            splineKnot.handle_left = originalKnot.handle_left

            splineKnot.handle_right_type = originalKnot.handle_right_type
            splineKnot.handle_right = originalKnot.handle_right

        # From object_utils of 2.8+.
        curveObject = bpy.data.objects.new(name, newCurve)
        curveObject.matrix_world = self.obj.matrix_world
        layer_collection = context.layer_collection or context.view_layer.active_layer_collection
        layer_collection.collection.objects.link(curveObject)


    def onFalloffUpdate(self):
        self.updateInfo(self.getToolMessage())
        self.recalculateInfluences()
        self.updateDeform()


    def onFalloffTypeUpdate(self):
        self.weightFunc = BMS_WEIGHT_FUNCS[self.bmsProperties.falloffType]
        self.recalculateInfluences()
        self.updateDeform()


    def onKeyLessFalloff(self):
        # The change to 'BMSProperties.falloff' below will cause a call to 'onFalloffUpdate()', which
        # recalculates influences, updates the deform and updates info (the header bar text).
        self.bmsProperties.falloff /= 1.05


    def onKeyMoreFalloff(self):
        # The change to 'BMSProperties.falloff' below will cause a call to 'onFalloffUpdate()', which
        # recalculates influences, updates the deform and updates info (the header bar text).
        self.bmsProperties.falloff *= 1.05


    def onKeyUnbind(self):
        # Toggle the bind state of the curve.
        self.isUnbound = not self.isUnbound

        if self.isUnbound:
            # The user has just unbounded the curve.
            self.updateInfo(self.unboundMessage)
            self.report({'INFO'}, 'Unbound Mode (Edit Curve)')
            self.modalFunc = self.unboundModal
            self.addDrawHandler(self.unbound2DHelper,
                                (self,),
                                'POST_PIXEL')
            self.tagRedrawAreas()
        else:
            if BMS_ADDON_PREFS.showKeymaps:
                self.addDrawHandler(self.shortcuts2DHelper,
                                    (self,),
                                    'POST_PIXEL')
            else:
                self.clearAllDrawHandlers()
            self.tagRedrawAreas()
            # The user toggled the unbinding off, confirming it, so rebind the curve now.
            if self.fullCurveRemap():
                self.report({'INFO'}, 'Normal Mode (Deform Mesh)')
                self.updateInfo(self.getToolMessage())
                self.updateDeform()
                self.modalFunc = self.toolModal
            else:
                # Only 1 or 0 control points, cancel the tool.
                self.report({'WARNING'}, 'Not enough points in the curve, aborting')
                return False
        return True


    def onKeyCancelUnbind(self):
        # The user cancelled the unbinded curve. Go back to the tool modal state.
        self.isUnbound = False
        self.addDrawHandler(self.shortcuts2DHelper,
                            (self,),
                            'POST_PIXEL')
        self.tagRedrawAreas()
        self.updateInfo(self.getToolMessage())
        self.report({'INFO'}, 'Normal Mode (Deform Mesh)')

        bps = self.curve.splines[0].bezier_points
        if len(bps) != self.startingLen:
            # User is cancelling the unbounded mode with a different amount of knots on the curve.
            # Ignore this new curve and rebuild the original curve.
            self.curve.splines.clear()
            self.curve.splines.new('BEZIER')
            self.bezier_points = bps = self.curve.splines[0].bezier_points
            self.bezier_points.add(self.startingLen-1) # Add all but one knot, as the new spline already has one.
        else:
            self.curve.splines[0].use_cyclic_u = False # Force no cyclic mode.

        # Restore the last undo step (curve state).
        self.useUndoIndex()

        # Since some knots might have been removed and readded, update all references to their Vector attributes
        # as they might've become lost, including 'mappedVertices' and 'influencedVertices'.

        self.offsetControlPoints = updatedOffsetPoints = tuple(
            (
                bps[segmentIndex].co,
                bps[segmentIndex].handle_right,
                bps[segmentIndex+1].handle_left,
                bps[segmentIndex+1].co
            )
            for segmentIndex in range(self.startingLen-1)
        )

        mappedVertices = self.mappedVertices
        for vertex in mappedVertices:
            oldVertexData = mappedVertices[vertex]
            # Put the new references to control points inside the 'vertexData' tuple.
            mappedVertices[vertex] = oldVertexData[:6] + (updatedOffsetPoints[oldVertexData[5]],) + oldVertexData[7:]

        # Update references to old 'vertexData' instances in the 'self.influencedVertices' collection, if any.
        self.influencedVertices = deque(
            (mappedVertices[influenceData[0][0]], influenceData[1])
            for influenceData in self.influencedVertices
        )

        self.modalFunc = self.toolModal


    def onKeyDirection(self):
        toggledValue = not self.bmsProperties.useDirection
        self.bmsProperties.useDirection = toggledValue
        self.updateInfo(self.getToolMessage())
        if not toggledValue:
            bpy.context.space_data.overlay.show_curve_normals = False
        self.updateDeform()


    def onKeyMenu(self):
        # Bring a popup menu with operator settings.
        if BMS_ADDON_PREFS.menuType == 'DIALOG':
            bpy.context.window_manager.popup_menu(
                MESH_OT_bezier_mesh_shaper.falloffMenu, title='Proportional Editing Falloff'
            )
        else:
            bpy.ops.wm.call_menu_pie(name='BMS_MT_pie_menu')


    def onKeyExtremes(self):
        self.bmsProperties.useExtremes = not self.bmsProperties.useExtremes
        self.updateInfo(self.getToolMessage())
        self.updateDeform()


    def onKeyTilt(self):
        bpy.context.space_data.overlay.show_curve_normals = True


    def onKeyHistory(self):
        self.report({'INFO'}, 'Undo history not available')


    def onKeyRedo(self):
        if self.onRedo():
            #self.report({'INFO'}, 'Redo')
            pass
        else:
            self.report({'INFO'}, 'No more steps to redo')


    def onKeyUndo(self):
        if self.onUndo():
            #self.report({'INFO'}, 'Undo')
            pass
        else:
            self.report({'INFO'}, 'No more steps to undo')


    def getAllKeymaps(self, context):
        keyConfigs = context.window_manager.keyconfigs
        allKeymapData = { }
        unbindKeymapData = { }

        def _findKeymapItem(keymapItems, idname, shortcutName=None):
            global BMS_KEYMAP_ITEMS
            if idname in BMS_KEYMAP_ITEMS:
                return BMS_KEYMAP_ITEMS[idname]

            # Search for a keymap item.
            # There might be more than a single 'ed.undo' entry. One might be active and the other inactive
            # for example. So we try the first one and if it's active we use it, otherwise we search for another one.
            if idname in keymapItems:
                item = keymapItems[idname]
                if item.active:
                    if item.map_type == 'KEYBOARD':
                        # Encode key mods as bit flags.
                        data = item.type + str(item.shift*1 | item.ctrl*2 | item.alt*4 | item.oskey*8)
                        BMS_KEYMAP_ITEMS[idname] = data
                        if shortcutName:
                            getattr(BMSShortcuts, shortcutName)[1] = (
                                item.type, item.shift, item.ctrl, item.alt, item.oskey
                            )
                        return data
                    else:
                        return None
                else:
                    startIndex = keymapItems.find(idname)
                    for index in range(startIndex+1, len(keymapItems)):
                        item = keymapItems[index]
                        if item.active and item.idname == idname:
                            if item.map_type == 'KEYBOARD':
                                data = item.type + str(item.shift*1 | item.ctrl*2 | item.alt*4 | item.oskey*8)
                                BMS_KEYMAP_ITEMS[idname] = data
                                if shortcutName:
                                    getattr(BMSShortcuts, shortcutName)[1] = (
                                        item.type, item.shift, item.ctrl, item.alt, item.oskey
                                    )
                                return data
                            else:
                                return None
            return None

        # 'allKeymapData' is a dict used to override any relevant keymaps that are enabled.
        # This lets us do things like overrididing a request for the undo command with our own custom undo behavior.
        # See 'modal()' for the actual use.

        # The dict keys are the actual keyboard keys that need to be pressed, plus the stringified modifiers
        # for uniqueness. Each item is a tuple: ( shouldUpdateDeform, modalResult, callback ).

        # 'modifierFlags' = a bit-flag of the modifiers needed for the event: (shift * 1 | ctrl * 2 | alt * 4).

        keymapItems = keyConfigs.user.keymaps['Screen'].keymap_items

        # Undo. Defaults to Ctrl + Z.
        item = _findKeymapItem(keymapItems, 'ed.undo', shortcutName='undo')
        itemID = item if item else ('Z', 0|2|0|0)
        allKeymapData[itemID] = (True, 'RUNNING_MODAL', self.onKeyUndo)
        unbindKeymapData[itemID] = allKeymapData[itemID]

        # Redo. Defaults to Ctrl + Shift + Z.
        item = _findKeymapItem(keymapItems, 'ed.redo', shortcutName='redo')
        itemID = item if item else ('Z', 1|2|0|0)
        allKeymapData[itemID] = (True, 'RUNNING_MODAL', self.onKeyRedo)
        unbindKeymapData[itemID] = allKeymapData[itemID]

        # Undo history. Defaults to Ctrl + Alt + Z.
        item = _findKeymapItem(keymapItems, 'ed.undo_history')
        itemID = item if item else ('Z', 0|2|4|0)
        allKeymapData[itemID] = (False, 'RUNNING_MODAL', self.onKeyHistory)
        unbindKeymapData[itemID] = allKeymapData[itemID]

        # Knot tilt operator in curve edit mode. Defaults to Ctrl + T.
        item = _findKeymapItem(keyConfigs.user.keymaps['Curve'].keymap_items, 'transform.tilt')
        itemID = item if item else ('T', 0|2|0|0)
        allKeymapData[itemID] = (False, 'PASS_THROUGH', self.onKeyTilt)

        # Label for the "toggle curve unbind" keymap, displayed during unbound mode.
        unbindLabel = None

        # Optional custom keymaps from the standalone addon setup.
        userKeymap = keyConfigs.user.keymaps.get(BMS_KEYMAP_NAME, None)
        if userKeymap:
            for item in userKeymap.keymap_items:
                if hasattr(item.properties, 'name'):
                    name = item.properties.name
                    if name.startswith('BMS'):
                        itemID = item.type + str(item.shift*1 | item.ctrl*2 | item.alt*4 | item.oskey*8)
                        rawItemID = (item.type, item.shift, item.ctrl, item.alt, item.oskey)
                        allKeymapData[itemID] = (
                            False, # shouldUpdateDeform.
                            'RUNNING_MODAL', # modalResult.
                            getattr(self, name.rsplit(',', 1)[1]) # keymap item function.
                        )
                        if 'onKeyUnbind' in name:
                            BMSShortcuts.bindunbind[1] = rawItemID
                            unbindKeymapData[itemID] = allKeymapData[itemID]
                            unbindLabel = item.type.replace('_', ' ').title()
                            if item.shift:
                                unbindLabel += '+Shift'
                            if item.ctrl:
                                unbindLabel += '+Ctrl'
                            if item.alt:
                                unbindLabel += '+Alt'
                        elif 'onKeyLessFalloff' in name:
                            BMSShortcuts.increase[1] = rawItemID
                        elif 'onKeyMoreFalloff' in name:
                            BMSShortcuts.decrease[1] = rawItemID
                        elif 'onKeyDirection' in name:
                            BMSShortcuts.direction[1] = rawItemID
                        elif 'onKeyMenu' in name:
                            BMSShortcuts.settings[1] = rawItemID
                        elif 'onKeyExtremes' in name:
                            BMSShortcuts.extremes[1] = rawItemID

        self.allKeymapData = allKeymapData
        self.unbindKeymapData = unbindKeymapData
        self.unbindLabel = unbindLabel


    # See 'pushVertexDataUndoStep()' for more info.
    # As it's defined in toolModal(), after the keycombo is hit and this function
    # runs, a call to 'updateDeform()' will happen.
    # So all that's needed is to overwrite the vertexData from the appropriate source.
    def vertexDataUndoExec(self, vertexData):
        mappedVertices = self.mappedVertices
        for savedVertexData in vertexData:
            mappedVertices[savedVertexData[0]] = savedVertexData
        self.refreshInfluencedFromMapped()


    def useUndoIndex(self):
        # 'undoData' is the state of the scene under this undo index.
        undoData = self.undoStack[self.undoIndex]
        if 'vertexData' in undoData:
            self.vertexDataUndoExec(undoData['vertexData'])
        if 'cps' in undoData:
            controlPointData = undoData['cps']
            # Standard control-point undo step.
            for index, data in enumerate(controlPointData):
                self.bezier_points[index].co = data[0]
                self.bezier_points[index].handle_left = data[1]
                self.bezier_points[index].handle_right = data[2]
                self.bezier_points[index].tilt = data[3]
                self.bezier_points[index].radius = data[4]


    def onUndo(self):
        if self.undoIndex > 0:
            self.undoIndex -= 1
            self.useUndoIndex()
            return True
        return False


    def onRedo(self):
        if self.undoIndex < len(self.undoStack)-1:
            self.undoIndex += 1
            self.useUndoIndex()
            return True
        return False


    # Called before pushing new undo items onto the internal/imaginary undo stack
    # used by this tool.
    # This only drops the oldest step in case the limit has been reached, or
    # trims the stack in case the user undo'ed back to a middle step and is
    # pushing new steps at that spot (which discards the steps above that one).
    def prepareUndoStack(self):
        stackLen = len(self.undoStack)
        if stackLen and self.undoIndex < stackLen-1:
            # If we're on a lower step, clear all the higher steps so we can continue on from here.
            for x in range(self.undoIndex, stackLen-1):
                self.undoStack.pop()
        elif stackLen == BMS_UNDO_SIZE:
            # Pop ("forget") the first item.
            self.undoStack.popleft()
            self.undoIndex -= 1


    def buildCpsUndoData(self):
        return tuple(
            (bp.co.copy(), bp.handle_left.copy(), bp.handle_right.copy(), bp.tilt, bp.radius)
             for bp in self.bezier_points
        )


    def pushControlPointUndoStep(self):
        self.prepareUndoStack()
        self.undoStack.append({'cps': self.buildCpsUndoData()})
        self.undoIndex += 1


    def pushVertexDataUndoStep(self, beforeVertexData, afterVertexData):
        self.prepareUndoStack()
        # Store the previous vertexData state into the current undo
        # step, whatever it is.
        self.undoStack[self.undoIndex]['vertexData'] = beforeVertexData
        # Add a new step with the new vertexData state, as well as the current
        # control-point state.
        self.undoStack.append({'vertexData': afterVertexData,
                               'cps': self.buildCpsUndoData()})
        self.undoIndex += 1


    def resetUndoStack(self):
        self.undoIndex = 0
        self.undoStack = deque()
        # The very first undo step, the initial state of the curve.
        self.undoStack.append({'cps': self.buildCpsUndoData()})


    # Rebuilds the entire 'influencedVertices' deque.
    # Used after 'mappedVertices' dictionary gets changed.
    def refreshInfluencedFromMapped(self):
        mappedVertices = self.mappedVertices
        self.influencedVertices = deque(
            (mappedVertices[influenceData[0][0]], influenceData[1])
            for influenceData in self.influencedVertices
            if influenceData[0][0] in mappedVertices
        )


    def createOriginalLocations(self):
        # Store the starting positions of ALL vertices, to use with cancelling.
        if not hasattr(self, 'cancelOriginalLocations'):
            mappedVertices = self.mappedVertices
            self.cancelOriginalLocations = tuple(
                mappedVertices[vertex][2] if vertex in mappedVertices else vertex.co.copy()
                for vertex in self.bm.verts
            )


    def fullCurveRemap(self, fromSubdivide=False):
        if not len(self.curve.splines):
            return False # User deleted all splines.

        bps = self.curve.splines[0].bezier_points
        self.startingLen = len(bps)
        if self.startingLen < 2:
            return False # Not enough points on the curve, we need at least 2.

        self.createOriginalLocations() # Used with cancelling, if it happens.
        self.bezier_points = bps

        # Clear the undo stack and create a new undo origin (the base step).
        self.resetUndoStack()

        # Update control point references. Similar to 'initializeBezierCurve()'.
        offsetControlPoints = [ ]
        mapControlPoints = [ ]
        for segmentIndex in range(self.startingLen-1):
            knotA = bps[segmentIndex]
            knotB = bps[segmentIndex+1]

            # Reset the knot attributes, otherwise they get applied over and over on 'updateDeform()'.
            knotA.tilt = knotB.tilt = 0.0
            knotA.radius = knotB.radius = 1.0

            segmentPoints = (knotA.co, knotA.handle_right, knotB.handle_left, knotB.co)
            offsetControlPoints.append(segmentPoints)
            mapControlPoints.append(tuple(map(Vector, segmentPoints)))

        self.offsetControlPoints = offsetControlPoints
        self.frozenControlPoints = self.mapControlPoints = mapControlPoints

        # Recreate the KDTrees to this updated curve.
        self.segmentKDTrees = tuple(self.segmentsKDTreesGen(self.mapControlPoints))

        allBetweenVertsIndices = None
        if fromSubdivide and self.allBetweenVerts and not hasattr(self, 'originalAllBetweenIndices'):
            self.originalAllBetweenIndices = [bv[0] for bv in self.allBetweenVerts]

        # Similar setup as in 'enterTool()', except we don't initialize 'mappedVertices' with
        # 'allBetweenVertsMapGen()' since the modified curve might be far away from those vertices now.
        self.mappedVertices.clear() # Dict
        self.allBetweenVerts.clear() # Deque
        self.influencedVertices.clear() # Deque
        self.influencedSet.clear() # Set

        # Important: explicitly recalculate the vertex data of all primary vertices.

        if hasattr(self, 'originalAllBetweenIndices'):
            self.allBetweenVertsFullRemap(self.originalAllBetweenIndices)

        self.lastFalloff = -1.0 # To force an additive recalculation (remapping all vertices).
        self.recalculateInfluences()
        return True


    def getClosestT(self, vertexCo, closestPointIndex, controlPoints):
        if closestPointIndex == 0:
            tP0 = 0.0
            tP1 = BMS_PLOT_HALFSTEP
            tP2 = BMS_PLOT_STEP
        elif closestPointIndex == BMS_PLOT_DIVISOR:
            tP0 = 1.0 - BMS_PLOT_STEP
            tP1 = 1.0 - BMS_PLOT_HALFSTEP
            tP2 = 1.0
        else:
            tP1 = (closestPointIndex / BMS_PLOT_DIVISOR)
            tP0 = tP1 - BMS_PLOT_STEP
            tP2 = tP1 + BMS_PLOT_STEP

        # Evaluate the three neighbour points on the segment (parameter of middle point
        # is 'closestPointIndex'). Inline code from 'BezierUtils.evalPoint()', for slight speed up.
        _mt = 1.0 - tP0
        _mt2 = _mt*_mt
        _t2 = tP0*tP0
        P0 = (_mt*_mt2)*controlPoints[0] + (3.0*_mt2*tP0)*controlPoints[1] \
            + (3.0*_mt*_t2)*controlPoints[2] + (_t2*tP0)*controlPoints[3]

        _mt = 1.0 - tP1
        _mt2 = _mt*_mt
        _t2 = tP1*tP1
        P1 = (_mt*_mt2)*controlPoints[0] + (3.0*_mt2*tP1)*controlPoints[1] \
            + (3.0*_mt*_t2)*controlPoints[2] + (_t2*tP1)*controlPoints[3]

        _mt = 1.0 - tP2
        _mt2 = _mt*_mt
        _t2 = tP2*tP2
        P2 = (_mt*_mt2)*controlPoints[0] + (3.0*_mt2*tP2)*controlPoints[1] \
            + (3.0*_mt*_t2)*controlPoints[2] + (_t2*tP2)*controlPoints[3]

        # Make P1 a point on a quadratic Bézier (see https://stackoverflow.com/a/6712095).
        # t = 0.5; mt = 1.0 - t # Constant values, inlined below.
        # Original expression: (-mt*mt*P0 - t*t*P2 + P1) / (2.0 * mt * t)
        P1 = (-0.25*P0 - 0.25*P2 + P1) / 0.5
        # P0 and P2 remain the same.

        # Coefficients for the cubic function.
        a = P1 - P0
        b = P0 - P1 * 2.0 + P2
        c = a * 2.0
        d = P0 - vertexCo

        b2 = b @ b
        if b2 == 0.0:
            # Linear curve root, simpler.
            # (-d / c) from https://github.com/shril/CubicEquationSolver/blob/master/CubicEquationSolver.py#L31
            # (With 'd' and 'c' as defined in the source code from Gludion's article:
            # http://blog.gludion.com/2009/08/distance-to-quadratic-bezier-curve.html)
            rootA = -(d @ a) / (2.0 * (a @ a) + d @ b)
            return tP0 + (tP2 - tP0) * (0.0 if rootA < 0.0 else 1.0 if rootA > 1.0 else rootA)
        else:
            # Quadratic curve root, which involves a cubic / 3rd degree function to find the point projection.

            # These are not the cubic coefficients, but precomputed values that involve them.
            # (See lines 84, 85 of https://www.shadertoy.com/view/MdXBzB).
            ka = (3.0 * (a @ b)) / b2
            kb = (2.0 * (a @ a) + (d @ b)) / b2
            kc = (d @ a) / b2

            # Cubic equation solver by Trisomie21.
            # http://www.pouet.net/topic.php?which=9119&page=1#c429074
            p = kb - ka*ka / 3.0
            p3 = p*p*p
            q = ka * (2.0*ka*ka - 9.0*kb) / 27.0 + kc
            offset = -ka / 3.0
            kd = q*q + 4.0*p3 / 27.0
            if kd >= 0.0: # One root case.
                kd = sqrt(kd)
                x = (kd - q) / 2.0
                y = (-kd - q) / 2.0
                # In the lines below 0.33333... = 1/3
                rootA = offset \
                    + (x ** 0.33333333333333333 if x >= 0.0 else -((-x) ** 0.33333333333333333)) \
                    + (y ** 0.33333333333333333 if y >= 0.0 else -((-y) ** 0.33333333333333333))
                t = tP0 + (tP2 - tP0) * (0.0 if rootA < 0.0 else 1.0 if rootA > 1.0 else rootA)
                return tP0 + (tP2 - tP0) * (0.0 if rootA < 0.0 else 1.0 if rootA > 1.0 else rootA)
            else:
                # Three roots case, ignoring the third root as it's always the local maximum.
                u = sqrt(-p / 3.0)
                v = acos(-sqrt(-27.0 / p3) * q / 2.0) / 3.0
                m = cos(v)
                n = sin(v) * 1.73205080756887729 # 1.73205... = sqrt(3)
                rootA = offset + u * (m + m)
                rootB = offset - u * (n + m)
                #rootC = offset + u * (n - m) # Ignored root.

                # Evaluate the points of the segment (with inlined 'evalPoint()') using parameters from
                # 'rootA' and 'rootB', clamped to [0.0, 1.0]. Return the 't' that produces the closest point.
                deltaTP2TP0 = tP2 - tP0
                tA = tP0 + deltaTP2TP0 * (0.0 if rootA < 0.0 else 1.0 if rootA > 1.0 else rootA)
                _mt = 1.0 - tA
                _mt2 = _mt*_mt
                _t2 = tA*tA
                evalTA = (_mt*_mt2)*controlPoints[0] + (3.0*_mt2*tA)*controlPoints[1] \
                    + (3.0*_mt*_t2)*controlPoints[2] + (_t2*tA)*controlPoints[3]

                tB = tP0 + deltaTP2TP0 * (0.0 if rootB < 0.0 else 1.0 if rootB > 1.0 else rootB)
                _mt = 1.0 - tB
                _mt2 = _mt*_mt
                _t2 = tB*tB

                if (vertexCo - evalTA).length_squared \
                    < (vertexCo - ((_mt*_mt2)*controlPoints[0] + (3.0*_mt2*tB)*controlPoints[1] \
                    + (3.0*_mt*_t2)*controlPoints[2] + (_t2*tB)*controlPoints[3])).length_squared:
                    return tA
                return tB



    # To be called inside 'fullCurveRemap()', before 'recalculateInfluences()'.
    def allBetweenVertsFullRemap(self, allBetweenVertsIndices):
        # Local variables for slight speed up.
        mappedVertices = self.mappedVertices
        evalPoint = BezierUtils.evalPoint
        evalDerivative = BezierUtils.evalDerivative
        tempAllBetween    = [None] * len(allBetweenVertsIndices)
        tempAllBetweenMap = [None] * len(allBetweenVertsIndices)
        bmVerts = self.bm.verts

        falloff = self.bmsProperties.falloff
        segmentKDTrees = self.segmentKDTrees
        getClosestT = self.getClosestT
        infinity = float('inf')

        mapControlPoints = self.mapControlPoints
        offsetControlPoints = self.offsetControlPoints
        frozenControlPoints = self.frozenControlPoints

        halfStepComp = 1.0 - BMS_PLOT_HALFSTEP
        totalSegments = len(offsetControlPoints)
        lastSegmentIndex = totalSegments-1

        for dataIndex, vi in enumerate(allBetweenVertsIndices):
            vertex = bmVerts[vi]
            # Similar code to 'genericInfluencesGen()'.
            vCo = vertex.co
            closestDistance = infinity
            closestPointIndex = -1
            closestSegmentIndex = -1
            for segmentIndex in range(totalSegments):
                # The vertex is within the bounding-box of the curve segment, so get the segment
                # KDTree distance for finer comparison.
                result = self.segmentKDTrees[segmentIndex].find(vCo) # (co, index, distance)
                kdDistance = result[2]
                # IMPORTANT: unlike for other vertices, for primary vertices we always let them
                # pass the distance test, even if beyond the falloff.
                #if kdDistance < falloff and kdDistance < closestDistance:
                if kdDistance < closestDistance:
                    closestDistance = kdDistance
                    closestPointIndex = result[1]
                    closestSegmentIndex = segmentIndex

            # The vertex was close enough to the "polyline" of a segment.
            # Map it to that closest segment and set it as influenced.
            t = getClosestT(vCo, closestPointIndex, mapControlPoints[closestSegmentIndex])
            frozenPoints = frozenControlPoints[closestSegmentIndex] # Initial state of the curve segment.
            originalOffset = vCo - evalPoint(t, frozenPoints)
            closestDistance = originalOffset.length

            # Always let the primary vertex be mapped.
            vertexData = (
                vertex,
                0.0, # Make sure a primary vertex (if any) has 100% influence from the curve.
                vCo.copy(),
                originalOffset,
                evalDerivative(t, frozenPoints),
                closestSegmentIndex,
                offsetControlPoints[closestSegmentIndex],
                t,
                not (
                    (closestSegmentIndex == 0 and t < BMS_PLOT_HALFSTEP)
                    or (closestSegmentIndex == lastSegmentIndex and t > halfStepComp)
                )
            )
            tempAllBetween[dataIndex]    = (vi, closestSegmentIndex)
            tempAllBetweenMap[dataIndex] = (vertex, vertexData)
            mappedVertices[vertex] = vertexData
        self.allBetweenVertsMap = tempAllBetweenMap
        self.allBetweenVerts.clear()
        self.allBetweenVerts.extend(tempAllBetween)


    def allBetweenVertsMapGen(self):
        evalPoint = BezierUtils.evalPoint
        evalDerivative = BezierUtils.evalDerivative

        bmVerts = self.bm.verts

        segmentKDTrees = self.segmentKDTrees
        getClosestT = self.getClosestT

        mapControlPoints = self.mapControlPoints
        offsetControlPoints = self.offsetControlPoints
        frozenControlPoints = self.frozenControlPoints

        halfStepComp = 1.0 - BMS_PLOT_HALFSTEP
        lastSegmentIndex = len(mapControlPoints)-1

        for vIndex, closestSegmentIndex in self.allBetweenVerts:
            vertex = bmVerts[vIndex]

            vCo = vertex.co
            closestPointIndex = segmentKDTrees[closestSegmentIndex].find(vCo)[1]
            t = getClosestT(vCo, closestPointIndex, mapControlPoints[closestSegmentIndex])
            frozenPoints = frozenControlPoints[closestSegmentIndex]

            # See comments about vertex data in 'genericInfluencesGen()'.
            vertexData = (
                vertex,
                0.0, # Force zero distance, for maximum weight.
                vCo.copy(),
                vCo - evalPoint(t, frozenPoints),
                evalDerivative(t, frozenPoints),
                closestSegmentIndex,
                offsetControlPoints[closestSegmentIndex],
                t,
                not (
                    (closestSegmentIndex == 0 and t < BMS_PLOT_HALFSTEP)
                    or (closestSegmentIndex == lastSegmentIndex and t > halfStepComp)
                )
            )
            yield vertex, vertexData # (key, value) pair for the 'self.mappedVertices' dictionary.


    def genericInfluencesGen(self, iterable, falloff, isAdding):
        # Local variables for slight speed up.
        mappedVertices = self.mappedVertices
        influencedSet = self.influencedSet
        weightFunc = self.weightFunc

        if isAdding:
            evalPoint = BezierUtils.evalPoint
            evalDerivative = BezierUtils.evalDerivative

            segmentKDTrees = self.segmentKDTrees
            getClosestT = self.getClosestT
            infinity = float('inf')

            mapControlPoints = self.mapControlPoints
            offsetControlPoints = self.offsetControlPoints
            frozenControlPoints = self.frozenControlPoints

            halfStepComp = 1.0 - BMS_PLOT_HALFSTEP
            totalSegments = len(offsetControlPoints)
            lastSegmentIndex = totalSegments-1

            for vertex in iterable:
                # Since 'isAdding' is True (the falloff is bigger since the last time this function was called),
                # re-weight vertices that are already being influenced, and map vertices that fall within this
                # new larger falloff size.
                if vertex in influencedSet:
                    vertexData = mappedVertices[vertex]
                    closestDistance = vertexData[1]
                    yield vertexData, weightFunc(1.0 - closestDistance / falloff)

                elif vertex in mappedVertices:
                        vertexData = mappedVertices[vertex]
                        closestDistance = vertexData[1]
                        if closestDistance < falloff:
                            influencedSet.add(vertex)
                            yield vertexData, weightFunc(1.0 - closestDistance / falloff)
                else:
                    # If the vertex isn't influenced or mapped yet, see if it's within the falloff range of any
                    # of the curve segments right now, and map the vertex to that segment if so.
                    vCo = vertex.co
                    closestDistance = infinity
                    closestPointIndex = -1
                    closestSegmentIndex = -1
                    for segmentIndex in range(totalSegments):
                        # The vertex is within the bounding-box of the curve segment, so get the segment
                        # KDTree distance for finer comparison.
                        result = self.segmentKDTrees[segmentIndex].find(vCo) # (co, index, distance)
                        kdDistance = result[2]
                        if kdDistance < falloff and kdDistance < closestDistance:
                            closestDistance = kdDistance
                            closestPointIndex = result[1]
                            closestSegmentIndex = segmentIndex

                    if closestSegmentIndex != -1:
                        # The vertex was close enough to the "polyline" of a segment.
                        # Map it to that closest segment and set it as influenced.
                        t = getClosestT(vCo, closestPointIndex, mapControlPoints[closestSegmentIndex])
                        frozenPoints = frozenControlPoints[closestSegmentIndex] # Initial state of the curve segment.
                        originalOffset = vCo - evalPoint(t, frozenPoints)
                        closestDistance = originalOffset.length

                        if closestDistance < falloff:
                            # Vertex data is a tuple with this format:
                            vertexData = (
                                # 0) Reference to the BMVert object.
                                vertex,
                                # 1) Closest distance from the vertex to the segment it's bound to.
                                closestDistance,
                                # 2) Starting position of the vertex (before the operator began).
                                vCo.copy(),
                                # 3) Original offset, vector from vertex to nearest curve point.
                                originalOffset,
                                # 4) Original direction (the initial derivative at 't').
                                evalDerivative(t, frozenPoints),
                                # 5) Index of the segment the vertex is mapped to.
                                closestSegmentIndex,
                                # 6) Control points of the segment of the manipulatable curve the vertex is mapped to.
                                offsetControlPoints[closestSegmentIndex],
                                # 7) Parameter 't' of the projection of the vertex onto the curve segment.
                                t,
                                # 8) Boolean, True if this vertex is NOT an extremity vertex.
                                not (
                                    (closestSegmentIndex == 0 and t < BMS_PLOT_HALFSTEP)
                                    or (closestSegmentIndex == lastSegmentIndex and t > halfStepComp)
                                )
                            )
                            influencedSet.add(vertex)
                            mappedVertices[vertex] = vertexData
                            yield vertexData, weightFunc(1.0 - closestDistance / falloff)
        else:
            # Smaller falloff since last time, so reset the position of any vertices that fall outside of the
            # new falloff size, and re-weight the ones that are still inside it.
            for vertex in self.bm.verts:
                if vertex in influencedSet: # Ignore non-influenced vertices.
                    vertexData = mappedVertices[vertex]
                    closestDistance = vertexData[1]
                    if closestDistance < falloff:
                        yield vertexData, weightFunc(1.0 - closestDistance / falloff)
                    else:
                        # Don't yield this vertex that used to be influenced, and reset it to its original position.
                        influencedSet.remove(vertexData[0])
                        vertex.co = vertexData[2]


    def makeDistanceInfluences(self, falloff, isAdding):
        self.influencedVertices = deque(
            self.genericInfluencesGen(
                (v for v in self.bm.verts if not v.hide) if isAdding else None,
                falloff,
                isAdding
            )
        )


    def makeConnectedInfluences(self, falloff, isAdding):
        # The only difference between the 'makeConnected...' and 'makeDistance...' functions
        # is that 'makeConnected...' only operates on selected vertices.
        # These vertices were selected with the 'mesh.select_linked()' operator in 'initializeBezierCurve()'.
        self.influencedVertices = deque(
            self.genericInfluencesGen(
                (v for v in self.bm.verts if v.select and not v.hide) if isAdding else None,
                falloff,
                isAdding
            )
        )


    def makeOffInfluences(self):
        # Reset the position of all previously influenced vertices, as only the primary vertices will be
        # deformed from now on.
        mappedVertices = self.mappedVertices
        for vertex in self.influencedSet:
            vertex.co = mappedVertices[vertex][2]
        self.influencedSet.clear()

        if self.allBetweenVerts:
            bmVerts = self.bm.verts

            if not BMS_ADDON_PREFS.useAllBetween:
                self.mappedVertices.update(self.allBetweenVertsMap)

            self.influencedVertices = deque(
                (mappedVertices[bmVerts[betweenData[0]]], 1.0) for betweenData in self.allBetweenVerts
            )
        else:
            self.influencedVertices.clear()
        # Force an additive update if the user ever changes to 'DISTANCE' or 'CONNECTED' falloff modes.
        self.lastFalloff = -1.0


    def recalculateResetHelper(self):
        # Will only be called on meshes, not on wrapped non-mesh objects.
        if hasattr(self, 'cancelOriginalLocations'):
            originalLocations = self.cancelOriginalLocations
            for vertex in self.influencedSet:
                vertex.co = originalLocations[vertex.index]
        else:
            mappedVertices = self.mappedVertices
            for vertex in self.influencedSet:
                vertex.co = mappedVertices[vertex][2]
        self.influencedSet.clear()


    def recalculateInfluences(self):
        falloff = self.bmsProperties.falloff

        # Make a boolean flag to optimise the influence functions.
        # The boolean answers "is the new falloff bigger since the last 'recalculateInfluences()' call?"
        # It's always either adding more vertices to be influenced, or removing some of the already
        # influenced vertices that go outside the new falloff size.
        isAdding = falloff > self.lastFalloff
        self.lastFalloff = falloff

        # In case we're recalculating influences after changing between modes, we need to reset the positions
        # of any vertices being influenced because some might be suddenly not influenced anymore.
        falloffMode = self.bmsProperties.falloffMode
        if self.lastFalloffMode != falloffMode:
            # Change to the new mode.
            self.lastFalloffMode = falloffMode
            self.recalculateResetHelper()
            isAdding = True

        # Finally, recalculate influences.
        if falloffMode == 'DISTANCE':
            self.makeDistanceInfluences(falloff, isAdding)
        elif falloffMode == 'CONNECTED':
            self.makeConnectedInfluences(falloff, isAdding)
        else: # 'OFF'.
            self.makeOffInfluences()


    def updateDeform(self):
        if len(self.bezier_points) != self.startingLen:
            self.report({'WARNING'}, 'Different points in the curve detected, aborting')
            return False

        # Update the influenced vertex positions based on their parameters along the curve.

        evalPoint = BezierUtils.evalPoint
        evalDerivative = BezierUtils.evalDerivative
        bezierPoints = self.bezier_points

        useExtremes = self.bmsProperties.useExtremes
        useDirection = self.bmsProperties.useDirection

        # "Vertex data" structure: (
        #   0) BMVert,
        #   1) closestDistance,
        #   2) startCo,
        #   3) originalOffset,
        #   4) originalDir,
        #   5) closestSegmentIndex,
        #   6) controlPoints,
        #   7) t,
        #   8) isNotExtreme,
        # )
        #
        # "Influenced vertices" structure, a tuple of: (
        #    (
        #       0) vertexData,
        #       1) weight
        #    )
        # )

        segmentAttributes = self.segmentAttributes
        segmentAttributes.clear()

        if useDirection:
            # Precalculate the knot tilt and radius attributes, to make them faster to interpolate.
            lastTilt = bezierPoints[0].tilt
            lastRadius = bezierPoints[0].radius
            for segmentIndex in range(1, self.startingLen):
                thisTilt = bezierPoints[segmentIndex].tilt
                thisRadius = bezierPoints[segmentIndex].radius
                segmentAttributes.append((lastTilt, thisTilt - lastTilt, lastRadius, thisRadius - lastRadius))
                lastTilt = thisTilt
                lastRadius = thisRadius

            # Go through all influenced vertices.
            for vertexData, weight in self.influencedVertices:
                t = vertexData[7]
                attributes = segmentAttributes[vertexData[5]]
                tiltRotation = Quaternion(vertexData[4], attributes[0] + attributes[1] * t) # Tilt.
                deltaRotation = vertexData[4].rotation_difference(evalDerivative(t, vertexData[6]))

                if useExtremes or vertexData[8]:
                    scaledOffset = vertexData[3] * (attributes[2] + attributes[3] * t) # Radius.
                    newCo = evalPoint(t, vertexData[6]) + (deltaRotation @ tiltRotation @ scaledOffset)
                    vertexData[0].co = vertexData[2].lerp(newCo, weight)
                else:
                    vertexData[0].co = vertexData[2]
        else:
            # Precalculate the radii of each segment, ignore the tilts.
            lastRadius = bezierPoints[0].radius
            for segmentIndex in range(1, self.startingLen):
                thisRadius = bezierPoints[segmentIndex].radius
                segmentAttributes.append((lastRadius, thisRadius - lastRadius))
                lastRadius = thisRadius

            for vertexData, weight in self.influencedVertices:
                t = vertexData[7]
                attributes = segmentAttributes[vertexData[5]]

                if useExtremes or vertexData[8]:
                    scaledOffset = vertexData[3] * (attributes[0] + attributes[1] * t) # Radius.
                    newCo = evalPoint(t, vertexData[6]) + scaledOffset
                    vertexData[0].co = vertexData[2].lerp(newCo, weight)
                else:
                    vertexData[0].co = vertexData[2]

        self.bm.to_mesh(self.mesh)
        self.mesh.update()
        return True


    def segmentsKDTreesGen(self, originalControlPoints):
        # Generate a KDTree for the sampled points of each curve segment.
        # We could've created one big KDTree for all segments together, but having them separate makes
        # it easier to compare distances between different segments.
        for segmentIndex in range(len(originalControlPoints)):
            tree = kdtree.KDTree(BMS_PLOT_RESOLUTION)
            for pointIndex, p in enumerate(interpolate_bezier(*originalControlPoints[segmentIndex], BMS_PLOT_RESOLUTION)):
                tree.insert(p, pointIndex)
            tree.balance()
            yield tree


    def initializeBezierCurve(self, context, bm, knotVertices, selectedVertices, explicitPoints):
        _name = '_BezierMeshShaper'

        # 2.8+
        curve = bpy.data.curves.get(_name + ' Curve', None)
        if not curve:
            curve = bpy.data.curves.new(_name + ' Curve', 'CURVE')
        context.space_data.overlay.show_curve_normals = False
        curve.dimensions = '3D'
        curve.splines.clear()

        spline = curve.splines.new('BEZIER')
        curveDistance = BMS_ADDON_PREFS.curveDistance

        offsetControlPoints = deque() # Control points of the offset curve that you see and manipulate.
        mapControlPoints = deque() # Control points of an imaginary curve used only for finding the 't' value.

        # Deque of (vertexIndex, segmentIndex), for only the vertices used to fit the curve segments.
        # This is only filled when using the "connected-vertex-selection" and "separate-vertex-selection" modes.
        # We store the index of the BMVert instead of the BMVert itself, because after this function the BMVert
        # instances will be gone.
        # The deque is ordered from the first vertex in the sequence to the last.
        self.allBetweenVerts = deque()

        if explicitPoints:
            # This is the "projected-line-selection" mode.

            spline.bezier_points.add(len(explicitPoints)) # Note: len() of the list of lists, not the total points.
            for knotIndex, pointSequence in enumerate(explicitPoints):
                controlPoints = tuple(map(Vector, BezierUtils.fitBezierToVertices(pointSequence, curveDistance)))

                if knotIndex == 0:
                    spline.bezier_points[knotIndex].co = controlPoints[0]
                spline.bezier_points[knotIndex].handle_right = controlPoints[1]
                spline.bezier_points[knotIndex+1].handle_left = controlPoints[2]
                spline.bezier_points[knotIndex+1].co = controlPoints[3]

                offsetControlPoints.append(
                    (
                        spline.bezier_points[knotIndex].co,
                        spline.bezier_points[knotIndex].handle_right,
                        spline.bezier_points[knotIndex+1].handle_left,
                        spline.bezier_points[knotIndex+1].co
                    )
                )
                if curveDistance:
                    mapControlPoints.append(
                        tuple(map(Vector, BezierUtils.fitBezierToVertices(pointSequence, 0.0)))
                    )
                else:
                    mapControlPoints.append([controlPoint.copy() for controlPoint in controlPoints])

                # Consider the two vertices of every picked edge as the 'allBetweenVerts'.
                #self.allBetweenVerts.extend(
                #    (vertex.index, knotIndex)
                #    for vertex in chain.from_iterable(point.edge.verts for point in pointSequence if point.edge)
                #)
        else:
            # Not the projected mode. Choose between the "connected-vertices" or the "separate-vertices" modes.
            areAllConnected = True
            for v in selectedVertices:
                for e in v.link_edges:
                    if e.other_vert(v).select:
                        break
                else:
                    # One of the selected vertices wasn't connected to any other selected vertices.
                    # To get the connected-vertex-selection mode all selected vertices must be connected
                    # to at least one other selected vertex.
                    areAllConnected = False
                    break

            if areAllConnected:
                # This is the connected-vertex-selection mode.
                # Build a single curve segment from all these selected vertices.

                # Try to find either of the two vertices at the end of the sequence.
                startVertex = None
                for v in selectedVertices:
                    hasSelectedNeighbors = False
                    for e in v.link_edges:
                        if e.other_vert(v).select:
                            # If the vertex already had its 'hadSelectedNeighbors' flag set from a previous linked
                            # vertex, then it's not one of the extremity vertices.
                            if hasSelectedNeighbors:
                                break
                            else:
                                hasSelectedNeighbors = True
                    else:
                        startVertex = v
                        break

                if startVertex:
                    # Travel along the selected vertices, starting from 'startVertex'.
                    currentVertex = startVertex
                    temp = (startVertex,)
                    betweenVerts = deque(temp)
                    visitedVerts = set(temp)
                    while currentVertex:
                        otherVertex = next(
                            (
                                other for other in (e.other_vert(currentVertex) for e in currentVertex.link_edges)
                                if other.select and other != currentVertex and other not in visitedVerts
                            ),
                            None
                        )
                        if otherVertex:
                            betweenVerts.append(otherVertex)
                            visitedVerts.add(otherVertex)
                        currentVertex = otherVertex

                    spline.bezier_points.add(1) # New splines already come with 1 knot, so this makes it two.
                    self.allBetweenVerts.extend((vertex.index, 0) for vertex in betweenVerts)

                    controlPoints = tuple(map(Vector, BezierUtils.fitBezierToVertices(betweenVerts, curveDistance)))

                    spline.bezier_points[0].co = controlPoints[0]
                    spline.bezier_points[0].handle_right = controlPoints[1]
                    spline.bezier_points[1].handle_left = controlPoints[2]
                    spline.bezier_points[1].co = controlPoints[3]

                    # Re-read the vectors from the Bézier points, and not the ones from that 'controlPoints' tuple above,
                    # because there's a small floating point difference between the two and it causes some annoying
                    # vertex popping if it's not done this way.
                    offsetControlPoints.append(
                        (
                            spline.bezier_points[0].co,
                            spline.bezier_points[0].handle_right,
                            spline.bezier_points[1].handle_left,
                            spline.bezier_points[1].co
                        )
                    )
                    # Also fit a segment without any offset at all, used to compute the curve influences.
                    if curveDistance:
                        mapControlPoints.append(
                            tuple(map(Vector, BezierUtils.fitBezierToVertices(betweenVerts, 0.0)))
                        )
                    else:
                        mapControlPoints.append([controlPoint.copy() for controlPoint in controlPoints])
                else:
                    self.report({'WARNING'}, 'Cyclic selections not supported yet, aborting')
                    return False # Curve creation failed.
            else:
                # This is the separate-vertex-selection mode, specifying where the knot points are by
                # using the BMesh selection history.

                totalKnotVertices = len(knotVertices)
                if totalKnotVertices == 0:
                    # No selection history vertices, so try to pick any two from the selected vertices.
                    if selectedVertices and len(selectedVertices) > 1:
                        knotVertices = (selectedVertices[0], selectedVertices[-1])
                        totalKnotVertices = 2
                    else:
                        self.report({'WARNING'}, 'Selection history is empty. Try relesecting the vertices')
                        return False
                elif totalKnotVertices == 1:
                    knotVertexA = knotVertices[0]
                    knotVertices = (knotVertexA, next(v for v in bm.verts if v.select and v != knotVertexA))
                    totalKnotVertices = 2

                spline.bezier_points.add(totalKnotVertices-1) # Already comes with one knot, hence the '-1'.

                # Create each curve segment.
                for knotIndex in range(totalKnotVertices-1):
                    knotVertexA = knotVertices[knotIndex]
                    knotVertexB = knotVertices[knotIndex+1]

                    # Select all vertices between the two knot vertices.
                    # Try without face-stepping first.
                    bpy.ops.mesh.select_all(action='DESELECT')
                    knotVertexA.select = knotVertexB.select = True
                    bpy.ops.mesh.shortest_path_select(use_face_step=False)

                    # See if there are any sharp edge turns in what was selected. A sharp turn is when
                    # two selected edges share the same face (ignoring N-gon faces and N-pole vertices).

                    betweenVerts = deque()
                    useFaceStep = False

                    previousVertex = None
                    visitedFaces = set()
                    currentVertex = knotVertexA
                    while currentVertex:
                        # Remember the order in which the vertices are connected from knot A to knot B.
                        betweenVerts.append(currentVertex)

                        # If any inbetween vertices are 5-poles or more, switch to face-stepped selection.
                        if len(currentVertex.link_edges) > 4 and currentVertex != knotVertexA and currentVertex != knotVertexB:
                            useFaceStep = True
                            break
                        else:
                            # See if any quads or triangles have two edges selected (a "sharp turn" on the selection)
                            # and if so, stop crawling and try again below with the mesh.shortest_path_select() operator
                            # with use_face_step on.
                            for f in currentVertex.link_faces:
                                if f in visitedFaces or len(f.edges) > 4:
                                    continue
                                visitedFaces.add(f)

                                hasSelectedEdge = False
                                for e in f.edges:
                                    if e.select:
                                        if hasSelectedEdge:
                                            break
                                        else:
                                            hasSelectedEdge = True
                                else:
                                    continue # Continue to skip the below breaking of the parent loop, when no
                                             # "sharp turn" edge selection found.
                                # A sharp turn was found. Exit the parent loops and retry the shortest_path_select().
                                useFaceStep = True
                                currentVertex = None
                                break
                            else:
                                # Continue on to the next selected vertex.
                                oldCurrentVertex = currentVertex
                                currentVertex = next(
                                    (
                                        e.other_vert(currentVertex)
                                        for e in currentVertex.link_edges
                                        if e.select and e.other_vert(currentVertex) != previousVertex
                                    ),
                                    None
                                )
                                previousVertex = oldCurrentVertex
                                # If the next vertex in the selection was not found then we either traveled the entire
                                # selection (knotVertexB will be in 'betweenVerts'), or the two knot vertices happen
                                # to be on separate mesh parts.

                    if useFaceStep:
                        # Select the shortest path again but use face-stepping now.
                        bpy.ops.mesh.select_all(action='DESELECT')
                        knotVertexA.select = knotVertexB.select = True
                        bpy.ops.mesh.shortest_path_select(use_face_step=True)

                        betweenVerts.clear()
                        visitedFaces.clear()
                        previousVertex = None
                        currentVertex = knotVertexA

                        while currentVertex:
                            betweenVerts.append(currentVertex)

                            nextVertex = None
                            for f in currentVertex.link_faces:
                                if f not in visitedFaces:
                                    visitedFaces.add(f)
                                    for otherVertex in f.verts:
                                        if (
                                            otherVertex.select
                                            and otherVertex != currentVertex
                                            and otherVertex != previousVertex
                                        ):
                                            nextVertex = otherVertex
                                            break
                                    else:
                                        continue # Continue, to skip the breaking of the parent loop in the line below
                                    break        # when no 'nextVertex' is found.

                            if not nextVertex and (currentVertex.is_wire or currentVertex.is_boundary):
                                # Look in the linked edges when no next vertex was found in the linked faces.
                                nextVertex = next(
                                    (
                                        e.other_vert(currentVertex)
                                        for e in currentVertex.link_edges
                                        if e.select and e.other_vert(currentVertex) != previousVertex
                                    ),
                                    None
                                )
                            previousVertex = currentVertex
                            currentVertex = nextVertex

                    # Append the last vertex in case it couldn't be reached (separate mesh parts).
                    if betweenVerts[-1] != knotVertexB:
                        betweenVerts.append(knotVertexB)

                    betweenVertsIter = iter(betweenVerts)

                    # If there's multiple segments, skip the first vertex of the current 'betweenVerts' deque
                    # because it was already used in the last segment, as the last vertex. self.allBetweenVerts
                    # should only hold unique vertices, no duplicates.
                    if self.allBetweenVerts:
                        next(betweenVertsIter)

                    # 'knotIndex' is numerically the same as segment index.
                    self.allBetweenVerts.extend((vertex.index, knotIndex) for vertex in betweenVertsIter)

                    # Fit a cubic Bézier curve onto the vertices and get the 4 control points to it.
                    controlPoints = tuple(map(Vector, BezierUtils.fitBezierToVertices(betweenVerts, curveDistance)))

                    if knotIndex == 0:
                        # Only position the start knot on the first iteration.
                        # The start knot of future segments will be the same as the end knot of the previous segments.
                        spline.bezier_points[knotIndex].co = controlPoints[0]
                    spline.bezier_points[knotIndex].handle_right = controlPoints[1]
                    spline.bezier_points[knotIndex+1].handle_left = controlPoints[2]
                    spline.bezier_points[knotIndex+1].co = controlPoints[3]

                    offsetControlPoints.append(
                        (
                            spline.bezier_points[knotIndex].co,
                            spline.bezier_points[knotIndex].handle_right,
                            spline.bezier_points[knotIndex+1].handle_left,
                            spline.bezier_points[knotIndex+1].co
                        )
                    )
                    if curveDistance:
                        mapControlPoints.append(
                            tuple(map(Vector, BezierUtils.fitBezierToVertices(betweenVerts, 0.0)))
                        )
                    else:
                        mapControlPoints.append([controlPoint.copy() for controlPoint in controlPoints])
            # End of the "connected-vertex-selection" and "separate-vertex-selection" blocks.
        # End of the whole selection mode block.

        # Remember the selection to restore it back when the tool finishes \ is cancelled.
        # Store vertex indices instead of BMVert references because the BMesh instance will be lost by then.
        if selectedVertices or knotVertices:
            self.originalSelection = (tuple(v.index for v in selectedVertices), tuple(v.index for v in knotVertices))
        else:
            self.originalSelection = (None, None)

        # Use a linked selection for when the 'Connected' falloff mode is used.
        # We then filter vertices based on if they're selected or not.
        if self.meshMode: # Only do this when editing meshes, not wrapper objects.
            bpy.ops.mesh.select_linked(delimit=set())
        else:
            bm.select_linked() # Mimic the operator behavior on the wrapper class.

        self.weightFunc = BMS_WEIGHT_FUNCS[self.bmsProperties.falloffType]

        # Data to be used when recalculating curve influences on vertices.
        # Tuple of mathutils.KDTree objects, one tree for each segment, with points sampled from the segment.
        self.segmentKDTrees = tuple(self.segmentsKDTreesGen(mapControlPoints))

        # Cosmetic.
        # Align the left handle of the first knot of the first segment its right handle.
        knot = spline.bezier_points[0]
        knot.handle_left = knot.co + (knot.co - knot.handle_right)
        knot.handle_left_type = knot.handle_right_type = 'ALIGNED'
        # Do the same for the right handle of the last knot of the last segment.
        knot = spline.bezier_points[-1]
        knot.handle_right = knot.co + (knot.co - knot.handle_left)
        knot.handle_left_type = knot.handle_right_type = 'ALIGNED'

        bpy.ops.object.mode_set(mode='OBJECT')

        # Create or reuse the object container for the curve data.
        if _name in bpy.data.objects:
            # Object already exists.
            curveObject = bpy.data.objects[_name]
        else:
            # Object needs to be recreated (based on object_utils of 2.8+).
            curveObject = bpy.data.objects.new(_name, curve)

        # Always put the curve object in the master collection, so it's always selectable.
        # The user shouldn't really care where this object stays, as it's only useful
        # while the tool is running.
        if context.scene.collection not in curveObject.users_collection:
            context.scene.collection.objects.link(curveObject)

        if context.space_data.local_view:
            # If we're in Local View mode make sure the curve object is visible.
            curveObject.local_view_set(context.space_data, True)

        curveObject.matrix_world = self.obj.matrix_world

        bpy.ops.object.select_all(action = 'DESELECT')
        # Unhide the curve object for selection and visibility (both the viewport and global view-layer).
        curveObject.hide_select = curveObject.hide_viewport = False
        curveObject.hide_set(False)
        # Select the curve and enter its Edit mode.
        curveObject.select_set(True)
        bpy.context.view_layer.objects.active = curveObject
        bpy.ops.object.mode_set(mode='EDIT')

        bps = curve.splines[0].bezier_points
        self.bezier_points = bps

        # Perform the curve handle preselection, if on.
        if BMS_ADDON_PREFS.preselectInner:
            bps[0].select_right_handle = True
            bps[-1].select_left_handle = True

        if BMS_ADDON_PREFS.preselectOuter:
            bps[0].select_left_handle   = True
            bps[-1].select_right_handle = True

        # Used to detect control point removal from the curve.
        # This is not the amount of control points (4 per each segment), it's the amount of
        # knots (in Blender one knot holds the .handle_left, .co and .handle_right control points).
        self.startingLen = len(bps)

        # Remember the initial state of the knots of the manipulatable curve so that any vertices that become
        # mapped to the curve at a later moment can get a correct offset vector relative to that initial state.
        self.frozenControlPoints = tuple(tuple(map(Vector, controlPoints)) for controlPoints in offsetControlPoints)

        # Re-collect the references to the Vector data from each knot of the manipulatable curve, as these
        # references became lost after entering the curve Edit mode.
        # These references are to dynamic Vector objects that change value as the user manipulates the curve.
        self.offsetControlPoints = tuple(
            (
                bps[segmentIndex].co,
                bps[segmentIndex].handle_right,
                bps[segmentIndex+1].handle_left,
                bps[segmentIndex+1].co
            )
            for segmentIndex in range(self.startingLen-1)
        )
        self.mapControlPoints = mapControlPoints # Knots of the curve with zero offset distance from the mesh.
        self.curve = curve
        return True


    def initializeGL(self, perspectiveMatrix):
        self.postViewShader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.postViewFormat = self.postViewShader.format_calc()
        if bpy.app.version[0] >= 5:
            # For Blender 5.x and up.
            shaderInfo = gpu.types.GPUShaderCreateInfo()
            # Vertex interface.
            shaderInfo.vertex_in(0, 'VEC2', 'pos')
            # Blender 5.0.0 still seems to set this matrix up automatically, see this (line-broken):
            # https://projects.blender.org/blender/blender/src/commit/
            #6fe7ceef9fb895886d14b00151568694bfbd561b/source/blender/gpu/
            #intern/gpu_shader_interface.hh#L220
            shaderInfo.push_constant('MAT4', 'ModelViewProjectionMatrix')
            shaderInfo.push_constant('FLOAT', 'scale')
            shaderInfo.push_constant('VEC2', 'offsetPos')
            shaderInfo.vertex_source(self.POSTPIXEL_VERT_SOURCE_MAIN)
            # Fragment interface.
            shaderInfo.push_constant('VEC4', 'color')
            shaderInfo.fragment_out(0, 'VEC4', 'fragColor')
            shaderInfo.define('BLENDER_SRGB(x)', '(x)')
            shaderInfo.fragment_source(self.POSTPIXEL_FRAG_SOURCE_MAIN)
            self.postPixelShader = gpu.shader.create_from_info(shaderInfo)
        else:
            # Blender 4.x and lower.
            self.postPixelShader = gpu.types.GPUShader(
                vertexcode = (self.POSTPIXEL_VERT_SOURCE_INTERFACE +
                              self.POSTPIXEL_VERT_SOURCE_MAIN),
                fragcode = (self.POSTPIXEL_FRAG_SOURCE_INTERFACE +
                            self.POSTPIXEL_FRAG_SOURCE_MAIN)
            )
        self.postPixelFormat = self.postPixelShader.format_calc()

        RADIAN_STEP = 3.141592653589793 / 4 # or (2.PI / 8) = (PI / 4)
        RADIUS =  6.0
        self.baseCirclePoints = [
            Vector((cos(step*RADIAN_STEP)*RADIUS, -sin(step*RADIAN_STEP)*RADIUS)) for step in range(8)
        ]

        self.allPointsBuffer = None

        self.addDrawHandler(
            MESH_OT_bezier_mesh_shaper.projection3DHelper, (self,), 'POST_VIEW'
        )
        self.addDrawHandler(
            MESH_OT_bezier_mesh_shaper.projection2DHelper, (self,), 'POST_PIXEL'
        )


    def updatePointsBuffer(self):
        if len(self.allIntersectedPoints):
            matWorld = self.obj.matrix_world
            self.allPointsBuffer = tuple(
                matWorld @ point.co for point in chain.from_iterable(self.allIntersectedPoints)
            )
        else:
            self.allPointsBuffer = None


    def project3DPoint(self, vec4):
        temp = self.perspectiveMatrix @ self.obj.matrix_world @ vec4
        if temp[3] == 0.0:
            temp[3] = -0.0001
        return Vector(
            ((self.region.width * 0.5) * (1.0 + temp[0] / temp[3]), (self.region.height * 0.5) * (1.0 + temp[1] / temp[3]))
        )


    def selectVisibleEdges(self, context):
        bpy.ops.mesh.select_all(action = 'DESELECT')

        # 2.8+
        spaceShading = context.space_data.shading

        oldShadeMode = spaceShading.type
        if oldShadeMode == 'WIREFRAME':
            spaceShading.type = 'SOLID'
        else:
            oldShadeMode = None

        oldShowXRay = spaceShading.show_xray
        if oldShowXRay:
            spaceShading.show_xray = False
        else:
            oldShowXRay = None

        oldSelectMode = context.tool_settings.mesh_select_mode[:]
        context.tool_settings.mesh_select_mode = (False, False, True) # Face selection mode.
        bpy.ops.view3d.select_box(
            xmin=0, xmax=context.area.width, ymin=0, ymax=context.area.height, wait_for_input=False, mode='SET'
        )
        context.tool_settings.mesh_select_mode = oldSelectMode

        if oldShadeMode:
            context.space_data.viewport_shade = oldShadeMode
        if oldShowXRay:
            spaceShading.show_xray = oldShowXRay


    def inlineMakeRay(self, invViewMatrix, invPerspectiveMatrix):
        # Inline functions from 'view3d_utils', for speed up.
        if self.region3D.is_perspective:
            # 'region_2d_to_origin_3d'.
            rayOrigin = invViewMatrix.translation.copy()

            # 'region_2d_to_vector_3d'.
            out = Vector(((2.0 * self.eventCoords[0] / self.region.width) - 1.0,
                          (2.0 * self.eventCoords[1] / self.region.height) - 1.0,
                          -0.5
                          ))
            w = out.dot(invPerspectiveMatrix[3].xyz) + invPerspectiveMatrix[3][3]
            rayVector = ((invPerspectiveMatrix @ out) / w) - invViewMatrix.translation
        else:
            # 'region_2d_to_origin_3d'.
            dx = (2.0 * self.eventCoords[0] / self.region.width) - 1.0
            dy = (2.0 * self.eventCoords[1] / self.region.height) - 1.0
            rayOrigin = (
                (invPerspectiveMatrix.col[0].xyz * dx)
                + (invPerspectiveMatrix.col[1].xyz * dy)
                + invPerspectiveMatrix.translation
            )
            if self.region3D.view_perspective != 'CAMERA':
                origin_offset = invPerspectiveMatrix.col[2].xyz
                if origin_offset.length > 100.0:
                    origin_offset.length = 100.0
                rayOrigin -= origin_offset

            # 'region_2d_to_vector_3d'.
            rayVector = -invViewMatrix.col[2].xyz

        return rayVector, rayOrigin


    def quickRaycast(self, invViewMatrix, invPerspectiveMatrix):
        rayVector, rayOrigin = self.inlineMakeRay(invViewMatrix, invPerspectiveMatrix)
        rayOriginObj = self.invMatrixWorld @ rayOrigin
        return self.raycastTree.ray_cast(rayOriginObj, self.invMatrixWorld @ (rayVector+rayOrigin) - rayOriginObj)


    def tryAddRaycastKnot(self, context):
        invViewMatrix = self.region3D.view_matrix.inverted()
        invPerspectiveMatrix = self.region3D.perspective_matrix.inverted()
        raycast = self.quickRaycast(invViewMatrix, invPerspectiveMatrix)
        if raycast[0]:
            # If there's a previous knot then we can form a picked line.
            if len(self.pickedKnotData):
                # 1) Screen-project the latest knot and see if it's outside the view (in which case we can't use it).
                knotA, knotANormal = self.pickedKnotData[-1]
                tempProj = self.perspectiveMatrix @ self.obj.matrix_world @ knotA
                if tempProj[3] < 0.0:
                    self.report({'INFO'}, 'Please aim the view so the previous knot is visible')
                    return
                else:
                    knotAProj = self.project3DPoint(knotA)
                    if (knotAProj[0] < 0.0 or knotAProj[0] > self.region.width) \
                    or (knotAProj[1] < 0.0 or knotAProj[1] > self.region.height):
                        self.report({'INFO'}, 'Please aim the view so the previous knot is visible')
                        return

                knotB = raycast[0].to_4d()
                knotBNormal = raycast[1]
                self.pickedKnotData.append((knotB, knotBNormal))
                self.pickedFaceIndices.append(raycast[2])
                knotBProj = self.project3DPoint(knotB)

                # Test if the user wants to use straight picking (only two knots, no intersections).
                if self.straightPressed:
                    self.allIntersectedPoints.append(
                        (
                            BMSVirtualVertex(None, knotA.to_3d(), knotANormal, 0.0),
                            BMSVirtualVertex(None, knotB.to_3d(), knotBNormal, 1.0)
                        )
                    )
                    self.updatePointsBuffer()
                    return

                # Normal picking. Find all the points, if any, on the projected path between the two knots.

                knotABProj = knotBProj - knotAProj
                knotABProjNormalized = knotABProj.normalized()
                knotABProjLength = max(knotABProj.length, 0.001)

                # 2) Select all visible edges within the viewport.

                self.selectVisibleEdges(context)

                # 3) Project the vertices of selected edges to the screen, while checking for intersections
                # of these projected edges against the picked line.

                intersectedPoints = deque() # Use a deque for faster appends.

                projVertices = { } # Cache projected vertices (speed gain when fan-vertices are involved).
                matrixWorld = self.obj.matrix_world
                perspectiveMatrix = self.perspectiveMatrix
                perspectiveCompMatrix = perspectiveMatrix @ matrixWorld
                halfWidth = self.region.width * 0.5
                halfHeight = self.region.height * 0.5
                for edge in self.bm.edges:
                    if edge.select:

                        vertA = edge.verts[0]
                        if vertA not in projVertices:
                            vertAProj = perspectiveCompMatrix @ vertA.co.to_4d()
                            if vertAProj[3] > 0.0:
                                vertAProj = Vector((
                                    halfWidth * (1.0 + vertAProj[0] / vertAProj[3]),
                                    halfHeight * (1.0 + vertAProj[1] / vertAProj[3])
                                ))
                                projVertices[vertA] = vertAProj
                            else:
                                continue # Ignore this edge since this vertex goes behind the view.
                        else:
                            vertAProj = projVertices[vertA]

                        vertB = edge.verts[1]
                        if vertB not in projVertices:
                            vertBProj = perspectiveCompMatrix @ vertB.co.to_4d()
                            if vertBProj[3] > 0.0:
                                vertBProj = Vector((
                                    halfWidth * (1.0 + vertBProj[0] / vertBProj[3]),
                                    halfHeight * (1.0 + vertBProj[1] / vertBProj[3])
                                ))
                                projVertices[vertB] = vertBProj
                            else:
                                continue
                        else:
                            vertBProj = projVertices[vertB]

                        # Test the 2D intersection of the projected edge with the picked screen line.
                        intersect2DCo = intersect2D(knotAProj, knotBProj, vertAProj, vertBProj)
                        if intersect2DCo:
                            # Inline code from 'view3d_utils', same as in 'self.quickRaycast()' but using
                            # 'intersect2DCo' as the coordinates, instead of 'self.eventCoords'.
                            if self.region3D.is_perspective:
                                # 'region_2d_to_origin_3d'.
                                rayOrigin = invViewMatrix.translation.copy()
                                # 'region_2d_to_vector_3d'.
                                out = Vector(((2.0 * intersect2DCo[0] / self.region.width) - 1.0,
                                              (2.0 * intersect2DCo[1] / self.region.height) - 1.0,
                                              -0.5
                                              ))
                                w = out.dot(invPerspectiveMatrix[3].xyz) + invPerspectiveMatrix[3][3]
                                rayVector = ((invPerspectiveMatrix @ out) / w) - invViewMatrix.translation
                            else:
                                # 'region_2d_to_origin_3d'.
                                dx = (2.0 * intersect2DCo[0] / self.region.width) - 1.0
                                dy = (2.0 * intersect2DCo[1] / self.region.height) - 1.0
                                rayOrigin = (
                                    (invPerspectiveMatrix.col[0].xyz * dx)
                                    + (invPerspectiveMatrix.col[1].xyz * dy)
                                    + invPerspectiveMatrix.translation
                                )
                                if self.region3D.view_perspective != 'CAMERA':
                                    origin_offset = invPerspectiveMatrix.col[2].xyz
                                    if origin_offset.length > 100.0:
                                        origin_offset.length = 100.0
                                    rayOrigin -= origin_offset
                                rayVector = -invViewMatrix.col[2].xyz

                            vertACo = matrixWorld @ vertA.co
                            vertBCo = matrixWorld @ vertB.co
                            intersect3DCo = intersectLineLine(vertACo, vertBCo, rayOrigin, rayOrigin+rayVector*1e5)[0]

                            # See if the screen-projected 'intersect3DCo' location has less depth (Z) than the raycast
                            # location. Effectively, see if there's an occluding face in front of 'intersect3DCo'
                            # just like Blender's Knife tool code does, to filter out invisible intersection points.
                            rayOriginObj = self.invMatrixWorld @ rayOrigin
                            tempRaycast = self.raycastTree.ray_cast(
                                rayOriginObj, self.invMatrixWorld @ (rayVector+rayOrigin) - rayOriginObj
                            )
                            if not tempRaycast[0] or (
                                (perspectiveMatrix @ intersect3DCo.to_4d())[3]
                                <= (perspectiveCompMatrix @ tempRaycast[0].to_4d())[3]*1.0001 # Some tolerance.
                            ):
                                # Append this valid edge point.
                                # Calculate the 's' parameter of the 3D intersection point along the mesh edge.
                                s = (intersect3DCo - vertACo).length / (vertBCo - vertACo).length
                                intersectedPoints.append(
                                    BMSVirtualVertex(
                                        edge,
                                        vertA.co.lerp(vertB.co, s), # Use the object-space vertex locations.
                                        vertA.normal.lerp(vertB.normal, s).normalized(),
                                        (intersect2DCo - knotAProj).length / knotABProjLength # 't' along the picked line.
                                    )
                                )

                bpy.ops.mesh.select_all(action = 'DESELECT') # Clear the selection after 'selectVisibleEdges()'.

                # Add the two knots of the picked line as points. Use a 't' outside the [0, 1] range to
                # guarantee that they'll be the first / last points after sorted.
                intersectedPoints.appendleft(BMSVirtualVertex(None, knotA.to_3d(), knotANormal, -1.0))
                intersectedPoints.append(BMSVirtualVertex(None, knotB.to_3d(), knotBNormal, 2.0))

                if len(intersectedPoints) > 2:
                    # If there were any intersected points then sort them by their 't' parameter along
                    # the picked line.
                    self.allIntersectedPoints.append(sorted(intersectedPoints, key=self.bmsVertexTGetter))
                else:
                    # There might not be any intersected points when the user picks the same face twice.
                    self.allIntersectedPoints.append(intersectedPoints)

                self.updatePointsBuffer()
            else:
                # Otherwise, just add the new knot.
                self.pickedKnotData.append((raycast[0].to_4d(), raycast[1]))
                self.pickedFaceIndices.append(raycast[2])


    def acceptManipulation(self, window):
        # Enter a state that accepts a curve grab, if the user wants to do it.
        window.cursor_set('SCROLL_XY') # Change the cursor to inform of this change.
        if self.hideGrabHandles:
            try:
                # Blender 2.8X
                bpy.context.space_data.overlay.show_curve_handles = False
            except:
                # Blender 2.9X
                bpy.context.space_data.overlay.display_handle = 'NONE'
        self.acceptsManipulation = True
        self.curveGrab = None
        self.updateInfo(self.getGrabMessage())


    def blockManipulation(self, window):
        # Exit the state that accepts curve grabs.
        window.cursor_set('CROSSHAIR') # Go back to the curve-Edit-mode cursor.
        if self.hideGrabHandles:
            try:
                # Blender 2.8X
                bpy.context.space_data.overlay.show_curve_handles = True
            except:
                # Blender 2.9X
                bpy.context.space_data.overlay.display_handle = 'ALL'
        self.acceptsManipulation = False

        # If the user released the Ctrl keys while in grab mode, cancel the curve adjustment.
        if self.curveGrab:
            self.useUndoIndex()
            self.curveGrab = None

        self.updateInfo(self.getToolMessage())


    def updateAxisLockDrawHandler(self):
        axisLock = self.curveGrab.axisLock
        viewPlaneCo = self.curveGrab.viewPlaneCo
        if axisLock[0]:
            # Plane-locked data.
            axisLockBuffer = gpu.types.GPUVertBuf(self.axisLockFormat, 4)
            # See if it's in local mode, in which case we need to transform the axes before drawing them.
            if axisLock[2]:
                offsetAxis1 = (axisLock[4] @ axisLock[3][0]) * 10000.0
                offsetAxis2 = (axisLock[4] @ axisLock[3][1]) * 10000.0
            else:
                offsetAxis1 = axisLock[3][0] * 10000.0
                offsetAxis2 = axisLock[3][1] * 10000.0
            axisLockBuffer.attr_fill(
                id = self.axisLockPosAttr,
                data = (
                    viewPlaneCo - offsetAxis1,
                    viewPlaneCo + offsetAxis1,
                    viewPlaneCo - offsetAxis2,
                    viewPlaneCo + offsetAxis2
                )
            )
            color1 = ((axisLock[3][0] + Vector((0.5, 0.5, 0.5))) / 1.5).to_4d()
            color2 = ((axisLock[3][1] + Vector((0.5, 0.5, 0.5))) / 1.5).to_4d()
            axisLockBuffer.attr_fill(id=self.axisLockColorAttr, data=(color1, color1, color2, color2))
        else:
            # Axis-locked data.
            axisLockBuffer = gpu.types.GPUVertBuf(self.axisLockFormat, 2)
            offsetAxis = axisLock[1] * 10000.0
            axisLockBuffer.attr_fill(
                id=self.axisLockPosAttr, data=(viewPlaneCo - offsetAxis, viewPlaneCo + offsetAxis)
            )
            color = ((axisLock[3] + Vector((0.5, 0.5, 0.5))) / 1.5).to_4d()
            axisLockBuffer.attr_fill(id=self.axisLockColorAttr, data=(color, color))

        self.axisLockBatch = gpu.types.GPUBatch(type='LINES', buf=axisLockBuffer)


    def startAxisLockDrawHandler(self):
        if not self.active3DDrawHandler:
            # Lazily initialize GPU data.
            if not hasattr(self, 'axisLockShader'):
                self.axisLockShader = gpu.shader.from_builtin('FLAT_COLOR')
                #self.axisLockColorAttr = self.axisLockShader.attr_from_name('color')
                self.axisLockFormat = gpu.types.GPUVertFormat()
                self.axisLockPosAttr = self.axisLockFormat.attr_add(
                    id='pos', comp_type='F32', len=3, fetch_mode='FLOAT'
                )
                self.axisLockColorAttr = self.axisLockFormat.attr_add(
                    id='color', comp_type='F32', len=4, fetch_mode='FLOAT'
                )
            # Add the 3D axis draw handler.
            self.addDrawHandler(MESH_OT_bezier_mesh_shaper.axisLock3DHelper, (self,), 'POST_VIEW')
        # Regardless if the draw handler was already running, update the OpenGL data that'll be drawn.
        self.updateAxisLockDrawHandler()


    def startCurveGrab(self, event):
        self.eventCoords = event.mouse_region_x, event.mouse_region_y

        # These inverse matrices are reset each time the user starts a curve grab, or whenever
        # they change the view direction.
        invViewMatrix = self.region3D.view_matrix.inverted()
        invPerspectiveMatrix = self.region3D.perspective_matrix.inverted()

        # Get the viewport ray at the mouse coordinates, but in object space.
        rayVector, rayOrigin = self.inlineMakeRay(invViewMatrix, invPerspectiveMatrix)
        rayOriginObj = self.invMatrixWorld @ rayOrigin
        rayVectorObj = self.invMatrixWorld @ (rayOrigin+rayVector) # Vector length doesn't matter.

        # Get the nearest point of the nearest segment towards the viewport ray.
        offsetControlPoints = self.offsetControlPoints
        minDist = float('infinity')
        minRayPoint = offsetControlPoints[0][0]
        minPointIndex = 0
        minSegmentIndex = 0
        for segmentIndex in range(self.startingLen-1):
            for pointIndex, p in enumerate(interpolate_bezier(*offsetControlPoints[segmentIndex], BMS_PLOT_RESOLUTION)):
                rayPoint = intersectPointLine(p, rayOriginObj, rayVectorObj)[0]
                dist = (rayPoint - p).length_squared
                if dist < minDist:
                    minDist = dist
                    minRayPoint = rayPoint
                    minPointIndex = pointIndex
                    minSegmentIndex = segmentIndex

        # Make sure all knots of this segment use the 'FREE' handle type (if any are 'ALIGNED' they might misbehave).
        knotA = self.bezier_points[minSegmentIndex]
        knotB = self.bezier_points[minSegmentIndex+1]
        knotB.handle_left_type = knotB.handle_right_type = knotA.handle_left_type = knotA.handle_right_type = 'FREE'

        # Control points, and the parameter of the point on the curve that's closest to the viewport ray.
        controlPoints = self.offsetControlPoints[minSegmentIndex]
        t = self.getClosestT(minRayPoint, minPointIndex, controlPoints)
        mt = 1.0 - t
        mt2 = mt*mt
        t2 = t*t

        # Factors of the Bézier polynomial.
        k0 = mt2*mt
        k1 = 3.0*mt2*t
        k2 = 3.0*mt*t2
        k3 = t2*t

        viewPlaneNormal = self.region3D.view_rotation @ Vector((0, 0, 1))
        viewPlaneCo = self.obj.matrix_world @ BezierUtils.evalPoint(t, controlPoints)

        # Decide which control points to affect.

        totalSegments = self.startingLen-1
        lastSegmentIndex = totalSegments-1

        if event.shift:
            # Special-case for when Shift is pressed, a simpler adjustment affecting
            # only the tangent points of the grabbed segment (unless the end points are explicitly selected).

            if (minSegmentIndex == 0 and t == 0.0):
                squaresSum = k0*k0 + k1*k1 + k2*k2
                controlPointData = (
                    (controlPoints[0], k0),
                    (controlPoints[1], k1),
                    (controlPoints[2], k2)
                )
            elif (minSegmentIndex == lastSegmentIndex and t == 1.0):
                squaresSum = k1*k1 + k2*k2 + k3*k3
                controlPointData = (
                    (controlPoints[1], k1),
                    (controlPoints[2], k2),
                    (controlPoints[3], k3)
                )
            else:
                # Tangent points only, and ignore one of the tangents if the user is clearly manipulating a far
                # side of the curve.
                if t <= 0.333333333333333:
                    squaresSum = k1*k1
                    controlPointData = (
                        (controlPoints[1], k1),
                    )
                elif t >= 0.666666666666666:
                    squaresSum = k2*k2
                    controlPointData = (
                        (controlPoints[2], k2),
                    )
                else:
                    squaresSum = k1*k1 + k2*k2
                    controlPointData = (
                        (controlPoints[1], k1),
                        (controlPoints[2], k2)
                    )
        else:
            # Normal mode, decide which control points to affect based on the grabbed segment, the amount of
            # segments on the curve and the parameter 't' of the grabbed curve point. 'minSegmentIndex' stands
            # for "the index of the curve segment that is being grabbed".

            if (minSegmentIndex == 0 and t == 0.0) or (totalSegments > 1 and minSegmentIndex == lastSegmentIndex and t < 1.0):
                squaresSum = k0*k0 + k1*k1 + k2*k2
                controlPointData = (
                    (controlPoints[0], k0),
                    (controlPoints[1], k1),
                    (controlPoints[2], k2)
                )
            elif (minSegmentIndex == lastSegmentIndex and t == 1.0) or (totalSegments > 1 and minSegmentIndex == 0 and t > 0.0):
                squaresSum = k1*k1 + k2*k2 + k3*k3
                controlPointData = (
                    (controlPoints[1], k1),
                    (controlPoints[2], k2),
                    (controlPoints[3], k3)
                )
            elif totalSegments == 1:
                if t <= 0.333333333333333:
                    squaresSum = k1*k1
                    controlPointData = (
                        (controlPoints[1], k1),
                    )
                elif t >= 0.666666666666666:
                    squaresSum = k2*k2
                    controlPointData = (
                        (controlPoints[2], k2),
                    )
                else:
                    squaresSum = k1*k1 + k2*k2
                    controlPointData = (
                        (controlPoints[1], k1),
                        (controlPoints[2], k2)
                    )
            else:
                squaresSum = k0*k0 + k1*k1 + k2*k2 + k3*k3
                controlPointData = (
                    (controlPoints[0], k0),
                    (controlPoints[1], k1),
                    (controlPoints[2], k2),
                    (controlPoints[3], k3)
                )

        # Create the 'CurveGrab' instance.
        self.curveGrab = MESH_OT_bezier_mesh_shaper.CurveGrab(
            # The two viewport matrices for making rays.
            invViewMatrix = invViewMatrix,
            invPerspectiveMatrix = invPerspectiveMatrix,

            # Store some values to check if the user navigates while grabbing the curve, in which
            # case the inverse matrices need to be updated for correct raycasting.
            lastViewLocation = self.region3D.view_location.copy(),
            lastViewRotation = self.region3D.view_rotation.copy(),

            # Store the origin and normal of a screen-aligned plane.
            viewPlaneCo = viewPlaneCo,
            viewPlaneNormal = viewPlaneNormal,

            # Store the previous raycast point so there's something to get the offset from.
            lastTargetPoint = intersectLinePlane(rayOrigin, rayOrigin+rayVector, viewPlaneCo, viewPlaneNormal),

            # Control points of the curve segment being grabbed, along with their polynomial factors.
            controlPointData = controlPointData,

            # Values used in the adjustment formula.
            squaresSum = squaresSum,

            # Data used for axis locking / constraining (begins disabled):
            # (isPlaneLock, transformedAxis, isLocal, originalAxis).
            axisLock = None
        )

        # Switch to a different event processing function.
        self.modalFunc = self.grabModal


    def updateCurveGrab(self, event):
        grab = self.curveGrab

        # See if the user navigated while grabbing the curve (can happen with the Middle mouse button, or numpad).
        r3D = self.region3D
        if grab.lastViewLocation != r3D.view_location or grab.lastViewRotation != r3D.view_rotation:
            grab.lastViewLocation = r3D.view_location.copy()
            grab.lastViewRotation = r3D.view_rotation.copy()
            invViewMatrix = grab.invViewMatrix = r3D.view_matrix.inverted()
            invPerspectiveMatrix = grab.invPerspectiveMatrix = r3D.perspective_matrix.inverted()
            grab.viewPlaneNormal = r3D.view_rotation @ Vector((0, 0, 1))
        else:
            invViewMatrix = grab.invViewMatrix
            invPerspectiveMatrix = grab.invPerspectiveMatrix

        # Get the 3D mouse offset vector to be applied (in object space) to the control points.
        # This vector is constrained to a screen-aligned plane, or an axis line when axis-locked.
        self.eventCoords = event.mouse_region_x, event.mouse_region_y
        rayVector, rayOrigin = self.inlineMakeRay(invViewMatrix, invPerspectiveMatrix)
        axisLock = grab.axisLock
        if axisLock:
            # Axis-lock is active, so constrain movements.
            if axisLock[0]:
                # Plane lock.
                targetPoint = intersectLinePlane(rayOrigin, rayOrigin+rayVector, grab.viewPlaneCo, axisLock[1])
            else:
                # Axis lock.
                targetPoint = intersectLineLine(
                    grab.viewPlaneCo, grab.viewPlaneCo+axisLock[1], rayOrigin, rayOrigin+rayVector
                )[0]
        else:
            targetPoint = intersectLinePlane(rayOrigin, rayOrigin+rayVector, grab.viewPlaneCo, grab.viewPlaneNormal)

        deltaVec = (self.invMatrixWorld @ targetPoint) - (self.invMatrixWorld @ grab.lastTargetPoint)
        grab.lastTargetPoint = targetPoint # Important, reuse the current target point on the next update.

        # Adjust the segment control points based on mouse movement.
        # --------------------------------------------------------------------
        # Based on 'A Technique for the Direct Manipulation of Spline Curves'.
        # Richard H. Bartels & John C. Beatty, 1989

        if grab.squaresSum > 0.0:
            for controlPoint, factor in grab.controlPointData:
                controlPoint += deltaVec * (factor / grab.squaresSum)


    def axisLockCurveGrab(self, axisIndex, event):
        grab = self.curveGrab
        currentLock = grab.axisLock
        chosenAxis = BMS_GRAB_AXIS[axisIndex]

        # Axis lock format:
        # (isPlaneLock, transformedAxis, isLocal, originalAxis).

        if event.shift:
            # With Shift pressed, do a plane-lock of the chosen axis.

            if (not currentLock) or (not currentLock[0]) or (chosenAxis in currentLock[3]):
                # Go to global mode.
                grab.axisLock = (
                    True, chosenAxis, False, tuple(BMS_GRAB_AXIS[index] for index in BMS_GRAB_AXIS if index != axisIndex)
                )
                self.startAxisLockDrawHandler() # Start the 3D draw handler.

            elif currentLock[2]:
                # Disable locking, If it's already in local mode.
                grab.axisLock = None
                self.clear3DDrawHandler() # Remove the draw handler now that no locking is happening.

            else:
                # Go to local mode.
                # Important: remove the translation and scale from the object's world matrix before
                # transforming the axis vector with it.
                objMatNormalized = self.obj.matrix_world.to_3x3().normalized().to_4x4()
                # We send in the normalized object matrix as the 5th item for the drawing handler to use.
                grab.axisLock = (True,  objMatNormalized @ chosenAxis, True, currentLock[3], objMatNormalized)
                self.startAxisLockDrawHandler()
        else:
            # With Shift unpressed, just lock a single axis.

            if (not currentLock) or (chosenAxis != currentLock[3]):
                # Global mode.
                grab.axisLock = (False, chosenAxis, False, chosenAxis)
                self.startAxisLockDrawHandler()

            elif currentLock[2]:
                # Disable locking.
                grab.axisLock = None
                self.clear3DDrawHandler() # Remove the draw handler now that no locking is happening.

            else:
                # Local mode.
                grab.axisLock = (
                    False, self.obj.matrix_world.to_3x3().normalized().to_4x4() @ chosenAxis, True, chosenAxis
                )
                self.startAxisLockDrawHandler()

        # Reset the curve to the shape it had before the grab.
        self.useUndoIndex()
        # Then adjust the shape right now, so it doesn't snap at the next mouse movement.
        grab.lastTargetPoint = grab.viewPlaneCo
        self.updateCurveGrab(event)
        self.updateInfo(self.getGrabMessage())


    def hasCurveGrabMod(self, event):
        curveGrabKeys = self.curveGrabKeys
        return (
            (event.ctrl and 'LEFT_CTRL' in curveGrabKeys)
            or (event.alt and 'LEFT_ALT' in curveGrabKeys)
            or (event.shift and 'LEFT_SHIFT' in curveGrabKeys)
            or (event.oskey and 'OSKEY' in curveGrabKeys)
        )


    def endCurveGrab(self, event, window):
        self.curveGrab = None
        if not self.hasCurveGrabMod(event):
            self.blockManipulation(window)
        self.clear3DDrawHandler()
        self.modalFunc = self.toolModal


    def finishCurveGrab(self, event, window):
        # If the curve was being grabbed, record an undo step:
        if self.curveGrab:
            self.pushControlPointUndoStep()
            self.updateDeform()
        # Mouse-click was released, stop grabbing the curve.
        self.endCurveGrab(event, window)


    def end(self):
        # Restore the scene state, mostly things changed during 'invoke()'.

        # On 2.8+ we don't remove the curve object if it already exists, we just hide / unhide it
        # as needed (if we deleted it, when you use undo Blender will crash).
        curveObject = bpy.data.objects.get('_BezierMeshShaper', None)
        if curveObject:
            curveObject.hide_select = curveObject.hide_viewport = True
            curveObject.hide_set(True)

        self.updateInfo(None) # Clear all area headers.
        self.obj.show_wire = self.oldShowWire
        self.obj.show_all_edges = self.oldShowAllEdges

        # Restore mesh modifier visibility, if applicable.
        if hasattr(self, 'objModVisibility'):
            for index, visibility in enumerate(self.objModVisibility):
                if visibility:
                    self.obj.modifiers[index].show_viewport = True
        self.clearAllDrawHandlers()
        self.tagRedrawAreas()

        # Restore the curve color, if it was changed at all.
        # If the operator crashes before this point, the color will stay changed, unfortunately...
        if BMS_ADDON_PREFS.setCurveColor:
            BMS_USER_PREFS.themes[0].view_3d.wire_edit = self.oldWireColor

        global BMS_INSTANCE
        BMS_INSTANCE = None


    def onFinish(self):
        self.end()
        self.bm.free()

        # Send the mesh object back to Edit mode and restore the old selection, for convenience.
        self.obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj
        bpy.ops.object.mode_set(mode='EDIT')

        if self.meshMode:
            bpy.ops.mesh.select_all(action='DESELECT')
            if self.originalSelection[0] or self.originalSelection[1]:
                bm = bmesh.from_edit_mesh(self.mesh)
                bmVerts = bm.verts
                bmVerts.ensure_lookup_table()
                for vIndex in self.originalSelection[0]:
                    bmVerts[vIndex].select = True
                for vIndex in self.originalSelection[1]:
                    bm.select_history.add(bmVerts[vIndex])
                bm.select_flush(True) # In case it was on edge selection mode.
                bmesh.update_edit_mesh(self.mesh)


    def onCancel(self):
        # Restore the original locations of all vertices that were potentially manipulated.
        if hasattr(self, 'cancelOriginalLocations'):
            # In case the user has unbound the curve at least once.
            for vertex, originalLocation in zip(self.bm.verts, self.cancelOriginalLocations):
                vertex.co = originalLocation
        else:
            # In case the user didn't unbind, use only the data in the mapped vertices.
            for vertexData in self.mappedVertices.values():
                vertexData[0].co = vertexData[2]
        self.bm.to_mesh(self.mesh)

        self.onFinish()


    def popProjectionDeques(self):
        self.pickedKnotData.pop()
        self.pickedFaceIndices.pop()

        # This exausts earlier than the other deques as it needs 2 knots for every 1 segment.
        if self.allIntersectedPoints:
            self.allIntersectedPoints.pop()

        self.updatePointsBuffer()


    def finishProjection(self, context):
        self.clearAllDrawHandlers()

        # Select all picked faces to support the connected-only falloff mode, when coming in from a projection.
        # Inside initializeBezierCurve() the selection will then spread to the linked geometry.
        bmFaces = self.bm.faces
        for faceIndex in self.pickedFaceIndices:
            bmFaces[faceIndex].select = True

        if self.enterTool(
            context, self.bm, knotVertices=None, selectedVertices=None, explicitPoints=self.allIntersectedPoints
        ):
            del self.raycastTree
            del self.pickedKnotData
            del self.pickedFaceIndices
            del self.allIntersectedPoints
            return True
        else:
            return False


    def projectionModal(self, context, event):
        modalResult = None
        eventType = event.type

        if eventType == 'MOUSEMOVE':
            self.eventCoords = event.mouse_region_x, event.mouse_region_y
            context.area.tag_redraw()

        elif event.value == 'PRESS':

            if eventType == 'LEFTMOUSE':
                if self.useDoubleClick:
                    # Double-click logic.
                    currentTime = time()
                    if (currentTime - self.lastClickTime) <= self.doubleClickWaitTime:
                        if not self.finishProjection(context):
                            self.end()
                            return {'CANCELLED'}
                        else:
                            modalResult = {'RUNNING_MODAL'}
                    else:
                        context.window.cursor_set('NONE')
                        if self.quickRaycast(
                            self.region3D.view_matrix.inverted(), self.region3D.perspective_matrix.inverted()
                        )[0]:
                            self.clickPressed = True
                            context.area.tag_redraw()
                        modalResult = {'PASS_THROUGH'} if (event.shift or event.ctrl or event.alt) else {'RUNNING_MODAL'}
                        self.lastClickTime = time()
                else:
                    context.window.cursor_set('NONE')
                    if self.quickRaycast(
                        self.region3D.view_matrix.inverted(), self.region3D.perspective_matrix.inverted()
                    )[0]:
                        self.clickPressed = True
                        context.area.tag_redraw()
                    modalResult = {'PASS_THROUGH'} if (event.shift or event.ctrl or event.alt) else {'RUNNING_MODAL'}

            elif eventType == self.rightMouseIgnore:
                modalResult = {'PASS_THROUGH'}

            elif eventType == 'E':
                self.straightPressed = True
                context.area.tag_redraw()
                modalResult = {'RUNNING_MODAL'}

            elif eventType == 'BACK_SPACE':
                if len(self.pickedKnotData):
                    self.popProjectionDeques()
                    context.area.tag_redraw()
                else:
                    self.report({'INFO'}, 'No more knots to undo')

            elif eventType == 'TAB':
                modalResult = {'RUNNING_MODAL'}

            elif (
                eventType in {'RET', 'NUMPAD_ENTER', self.spaceConfirms, self.rightMouseConfirms}
                and not (event.ctrl or event.shift or event.alt)
            ):
                if len(self.pickedKnotData) > 1:
                    # Finish this projection mode and try to enter the tool mode.
                    if not self.finishProjection(context):
                        self.end() # If it fails, end the tool.
                        return {'CANCELLED'}
                    else:
                        modalResult = {'RUNNING_MODAL'}
                else:
                    context.window.cursor_set('CROSSHAIR')
                    self.end()
                    return {'CANCELLED'}

            elif eventType in {'ESC', self.rightMouseCancel}:
                context.window.cursor_set('CROSSHAIR')
                self.end()
                modalResult = {'CANCELLED'}

        elif event.value == 'RELEASE':
            if eventType == 'LEFTMOUSE':
                self.clickPressed = False
                self.tryAddRaycastKnot(context)
                context.area.tag_redraw()

            elif eventType == 'E':
                self.straightPressed = False
                context.area.tag_redraw()
                modalResult = {'RUNNING_MODAL'}

        return modalResult if modalResult else {'PASS_THROUGH'}


    def unboundModal(self, context, event):
        modalResult = None

        if context.active_operator != self.lastOperator:
            self.lastOperator = context.active_operator
            self.updateInfo(self.unboundMessage)

        if event.value == 'PRESS':
            eventType = event.type

            if (
                eventType in {'RET', 'NUMPAD_ENTER', self.spaceConfirms, self.rightMouseConfirms}
                and not (event.ctrl or event.shift or event.alt)
            ):
                if not self.onKeyUnbind(): # In case there's only 0 or 1 Bézier points, cancel the tool.
                    self.onCancel()
                    modalResult = {'CANCELLED'}
                else:
                    modalResult = {'RUNNING_MODAL'}

            elif eventType in {'ESC', self.rightMouseCancel}:
                self.onKeyCancelUnbind()
                modalResult = {'RUNNING_MODAL'}

            elif eventType == self.clickMouseName and self.useDoubleClick:
                # Double-click logic.
                currentTime = time()
                if (currentTime - self.lastClickTime) <= self.doubleClickWaitTime:
                    if not self.onKeyUnbind():
                        self.onCancel()
                        modalResult = {'CANCELLED'}
                    else:
                        modalResult = {'RUNNING_MODAL'}
                else:
                    self.lastClickTime = time()

            else:
                keymapData = self.unbindKeymapData.get(
                    eventType + str(event.shift*1|event.ctrl*2|event.alt*4|event.oskey*8), None
                )
                if keymapData:
                    if keymapData[2].__name__ == 'onKeyUnbind':
                        keymapData[2]()
                    else:
                        # Override the undo, redo and undo-history commands to avoid conflicts.
                        self.report({'INFO'}, 'Command not available in unbound mode')
                    modalResult = {'RUNNING_MODAL'}

                elif eventType == 'TAB':
                    self.report({'INFO'}, 'Tab not available. Use Enter to finish or Esc to cancel the tool')
                    modalResult = {'RUNNING_MODAL'}

        return modalResult if modalResult else {'PASS_THROUGH'}


    def grabModal(self, context, event):
        eventType = event.type

        if eventType == 'MOUSEMOVE':
            self.updateCurveGrab(event)

        elif event.value == 'PRESS':
            # Confirm the curve grab.
            if (
                # "If there's a click or confirmation key, and the user is not holding any modifier keys that aren't
                # the grab mode modifier key (to allow for custom navigation keymaps), then finish the curve grab."
                eventType in {'RET', 'NUMPAD_ENTER', self.clickMouseName, self.spaceConfirms, self.rightMouseConfirms}
                and not ((event.ctrl or event.alt or event.shift or event.oskey) and not self.hasCurveGrabMod(event))
            ):
                self.finishCurveGrab(event, context.window)
                return {'RUNNING_MODAL'}

            # Cancel the curve grab.
            elif eventType in {'ESC', self.rightMouseCancel}:
                self.useUndoIndex()
                self.endCurveGrab(event, context.window)
                return {'RUNNING_MODAL'}

            # Customization: axis lock keys.
            elif eventType == 'X':
                self.axisLockCurveGrab(0, event)
                return {'RUNNING_MODAL'}

            elif eventType == 'Y':
                self.axisLockCurveGrab(1, event)
                return {'RUNNING_MODAL'}

            elif eventType == 'Z':
                self.axisLockCurveGrab(2, event)
                return {'RUNNING_MODAL'}

            else:
                if self.allKeymapData.get(eventType + str(event.shift*1|event.ctrl*2|event.alt*4|event.oskey*8), None):
                    return {'RUNNING_MODAL'} # Prevent undo, redo, undo-history, falloff etc. from being used.

        elif self.dragImmediately and event.value == 'RELEASE' and eventType == self.clickMouseName:
            # For when the user has set the 'Edit -> Transform: Release Confirms' preference.
            self.finishCurveGrab(event, context.window)

        return {'PASS_THROUGH'}


    def toolModal(self, context, event):
        shouldUpdateDeform = False
        modalResult = None

        # The only way to know when the Grab / Rotate / Scale operation was used on a curve point
        # is by seeing if the active operator of the context has changed since the last event.
        if context.active_operator != self.lastOperator:
            self.lastOperator = context.active_operator
            self.pushControlPointUndoStep()
            self.updateInfo(self.getToolMessage()) # Need to reset the header on operator changes.
            shouldUpdateDeform = True

        eventType = event.type

        # Keypress event handling.
        if event.value == 'PRESS':
            anyModifiers = (event.shift or event.ctrl or event.alt or event.oskey)

            if eventType in {'RET', 'NUMPAD_ENTER', self.spaceConfirms, self.rightMouseConfirms} and not anyModifiers:
                self.onFinish()
                modalResult = {'FINISHED'}

            elif eventType in {'ESC', self.rightMouseCancel} and not anyModifiers:
                self.onCancel()
                modalResult = {'CANCELLED'}

            elif eventType in self.curveGrabKeys:
                if not self.acceptsManipulation:
                    self.acceptManipulation(context.window)
                modalResult = {'PASS_THROUGH'}

            elif eventType == self.clickMouseName:
                if self.useDoubleClick:
                    # Double-click logic.
                    currentTime = time()
                    if (currentTime - self.lastClickTime) <= self.doubleClickWaitTime:
                        self.onFinish()
                        modalResult = {'FINISHED'}
                    else:
                        if self.acceptsManipulation:
                            self.startCurveGrab(event)
                            modalResult = {'RUNNING_MODAL'}
                        self.lastClickTime = time()
                else:
                    if self.acceptsManipulation:
                        self.startCurveGrab(event)
                        modalResult = {'RUNNING_MODAL'}

            elif eventType == self.rightMouseIgnore:
                modalResult = {'PASS_THROUGH'}

            else:
                # Get the "overriden" keymap association and call its function.
                keymapData = self.allKeymapData.get(
                    eventType + str(event.shift*1|event.ctrl*2|event.alt*4|event.oskey*8), None
                )
                if keymapData:
                    shouldUpdateDeform, modalResultString, func = keymapData
                    modalResult = {modalResultString}

                    # Stop accepting the grab mode, if it's active.
                    if self.acceptsManipulation:
                        self.blockManipulation(context.window)

                    func() # Call the function assigned to this item.

                elif eventType == 'TAB':
                    self.report({'INFO'}, 'Tab not available. Use Enter to finish or Esc to cancel the tool')
                    modalResult = {'RUNNING_MODAL'}

        elif self.acceptsManipulation and event.value == 'RELEASE':
            if eventType in self.curveGrabKeys:
                # Curve grab modifier key was released, exit curve grab "accepting" state.
                self.blockManipulation(context.window)
                modalResult = {'PASS_THROUGH'}

        if shouldUpdateDeform and not self.updateDeform():
            # The user added or deleted control points from the curve, better cancel because it's broken now.
            self.onCancel()
            return{'CANCELLED'}

        return modalResult if modalResult else {'PASS_THROUGH'}


    def modal(self, context, event):
        # 2.8X: cancel the tool in case the user does something that changes the context area.
        if context.area != self.startArea:
            self.report({'INFO'}, 'Tool area changed. Tool cancelled.')
            self.end()
            return {'CANCELLED'}
        # 2.8X only: prevent clicks outside of the UI region where the operator started.
        if (
            (event.mouse_region_x < 0 or event.mouse_region_x > context.region.width)
            or (event.mouse_region_y < 0 or event.mouse_region_y > context.region.height)
        ):
            return {'RUNNING_MODAL'} # Consume the event so the user can't interact outside the region.
        return self.modalFunc(context, event)


    def enterProjection(self, context, bm, event):
        self.bm = bm

        from mathutils import bvhtree
        self.raycastTree = bvhtree.BVHTree.FromBMesh(bm)

        self.region = context.region
        self.region3D = context.region_data
        self.perspectiveMatrix = context.region_data.perspective_matrix
        self.invMatrixWorld = self.obj.matrix_world.inverted()

        self.pickedKnotData = deque()
        self.pickedFaceIndices = deque()
        # The deque below holds other deques that hold BMSVirtualVertex objects as the points on the segment (including
        # the two extremity points).
        self.allIntersectedPoints = deque()

        self.bmsVertexTGetter = attrgetter('t')

        self.eventCoords = (event.mouse_region_x, event.mouse_region_y) if event else (0, 0)
        self.straightPressed = False
        self.clickPressed = False
        self.curveGrab = None

        rmbString = '/RMB' if (self.rightMouseCancel and not self.rightMouseConfirms) else ''
        self.projectionMessage = ('Enter/PadEnter%s: start tool | ' % ('/Space' if self.spaceConfirms else '')) + \
                                 'Esc' + rmbString + ': cancel | Backspace: remove last point | E: straight pick mode ' \
                                 '(no intersections) | Left-click to place knots on mesh surface'
        self.updateInfo(self.projectionMessage)

        self.initializeGL(context.region_data.perspective_matrix)

        self.modalFunc = self.projectionModal
        context.area.tag_redraw()
        context.window.cursor_set('NONE')


    def enterTool(self, context, bm, knotVertices, selectedVertices, explicitPoints):
        # For 2.8+. Helps to undo this operator, because curve Edit mode operations are also
        # added to the undo history.
        bpy.ops.ed.undo_push(message="Start Bezier Mesh Shaper")

        # Startup action(s) for before the curve is initialized.
        startupAction = self.startupAction
        if startupAction == 'ALIGNED':
            # Consider it a single two-point segment, using the two end points.
            if knotVertices and len(knotVertices) > 1:
                explicitPoints = ((knotVertices[0], knotVertices[-1]),)
            else:
                explicitPoints = ((selectedVertices[0], selectedVertices[-1]),)
            knotVertices = ()

        # Create the main curve.
        if not self.initializeBezierCurve(context, bm, knotVertices, selectedVertices, explicitPoints):
            return False
        bm.free()

        # After switching to the curve Edit mode in 'initializeBezierCurve()', all mesh modifiers will
        # display in their viewport visibility.
        # Temporarily set their viewport visibility to be the same as their Edit mode visibility (as if we're still
        # in edit mode). This is restored in 'end()'.
        objModVisibility = deque()
        for modifier in self.obj.modifiers:
            if modifier.show_viewport and not modifier.show_in_editmode:
                modifier.show_viewport = False
                objModVisibility.append(True)
            else:
                objModVisibility.append(False)
        if objModVisibility:
            self.objModVisibility = objModVisibility # Only create this attribute if necessary.

        # Create a BMesh outside of the mesh edit mode, to efficiently deform it while in the curve edit mode.
        if self.meshMode:
            self.bm = bmesh.new()
            if self.mesh.shape_keys:
                # Handle shape-keyed meshes.
                self.bm.from_mesh(self.mesh, use_shape_key=True, shape_key_index=self.obj.active_shape_key_index)
                if self.obj.active_shape_key_index > 0 and self.obj.active_shape_key.value == 0.0:
                    self.report({'INFO'}, 'Editing a shape key with zero strength, no changes will be seen')
            else:
                self.bm.from_mesh(self.mesh)
            self.bm.verts.ensure_lookup_table()
        else:
            pass # Editing lattice, external BMesh not needed.

        # Mapped Vertices:
        # Dictionary with 'BMVert' vertices as keys and "vertexData" as values (see 'genericInfluencesGen()' for info).
        # These vertices are mapped to a segment, but not necessarily influenced (depends on the current falloff size).
        self.allBetweenVertsMap = self.allBetweenVertsMapGen()
        self.mappedVertices = dict(self.allBetweenVertsMap) if BMS_ADDON_PREFS.useAllBetween else { }

        # Influenced Vertices:
        # Deque with (vertexData, weight) pairs for each 'BMVert' that is being influenced right now.
        self.influencedVertices = deque()
        # Used to quickly test if a vertex is being influenced or not, and because we can't modify
        # 'influencedVertices' and at the same time append to it in the 'recalculateInfluences()' function.
        # Start with 'allBetweenVerts' vertices, if any, which will always stay influenced.
        self.influencedSet = set(self.mappedVertices)

        # Used in 'updateDeform()' to interpolate the knot values (tilt & radius).
        self.segmentAttributes = deque()

        self.lastFalloffMode = self.bmsProperties.falloffMode
        self.lastFalloff = -1.0 # To force an additive update in the call below.

        # Startup actions for after the curve is initialized:
        if self.startupAction.startswith('SNAP_'):
            self.onSnap(self.startupAction)
        # Normal tool startup, add the rest of vertices that already started within the falloff size.
        self.recalculateInfluences()

        # Create the empty undo stack.
        self.resetUndoStack()

        self.lastOperator = context.active_operator

        self.getAllKeymaps(context)
        # Used with the curve grab mode, changes behavior on mouse release.
        self.dragImmediately = BMS_USER_PREFS.inputs.use_drag_immediately

        # Curve grabbing data.
        self.region = context.region # Used in 'inlineMakeRay()'.
        self.region3D = context.region_data
        self.invMatrixWorld = self.obj.matrix_world.inverted()
        self.acceptsManipulation = False
        self.curveGrab = None
        curveGrabPref = BMS_ADDON_PREFS.grabModeModifer
        self.curveGrabKeys = set(curveGrabPref.split('|')) # Use the preference string to make a set.

        handleVisibility = BMS_ADDON_PREFS.handleVisibility
        self.hideGrabHandles = (handleVisibility == 'NOTGRAB')
        try:
            # Blender 2.8X
            context.space_data.overlay.show_curve_handles = not (handleVisibility == 'NEVER')
        except:
            # Blender 2.9X - 'View3DOverlay.show_curve_handles' attribute was removed in favor of
            # '.display_handle', an enum property.
            context.space_data.overlay.display_handle = 'NONE' if (handleVisibility == 'NEVER') else 'ALL'

        confirmString = 'Enter/PadEnter%s:' % ('/Space' if self.spaceConfirms else '')
        if 'CTRL' in curveGrabPref:
            grabString = 'Hold Ctrl: grab mode | '
        elif 'ALT' in curveGrabPref:
            grabString = 'Hold Alt: grab mode | '
        elif 'OSKEY' in curveGrabPref:
            grabString = 'Hold Cmd: grab mode | '
        else:
            grabString = ''
        dragString = '-Drag' if self.dragImmediately else ''

        self.projectionMessage = None
        self.toolMessage = confirmString + ' confirm | ' \
                           'Esc' + ('/RMB' if self.rightMouseCancel else '') + ': cancel | ' \
                           + grabString + 'Use Extremes (%s) | Use Direction (%s) | Falloff size: '
        self.grabMessage = 'GRAB MODE | Click' + dragString + ': grab curve |' \
        ' Shift+Click' + dragString + ': grab tangents only | X/Y/Z (+ Shift optional): ' \
        'constrain to global/local axis (%s)'
        self.unboundMessage = 'UNBOUND MODE | ' + confirmString + 'confirm | ' \
                              'Esc' + ('/RMB' if self.rightMouseCancel else '') + ': cancel | ' \
                              'Freely adjust the curve.'
        self.updateInfo(self.getToolMessage())

        # Finish setting up the shortcuts data.
        # Some setup was already done in getAllKeymaps().
        BMSShortcuts.translateAll()
        if BMS_ADDON_PREFS.showKeymaps:
            self.addDrawHandler(self.shortcuts2DHelper, (self,), 'POST_PIXEL')

        if BMS_ADDON_PREFS.setCurveColor:
            view3DTheme = BMS_USER_PREFS.themes[0].view_3d
            self.oldWireColor = view3DTheme.wire_edit.copy()
            view3DTheme.wire_edit = BMS_ADDON_PREFS.curveColor

        self.modalFunc = self.toolModal
        return True


    def getToolMode(self, knotVertices, selectedVertices):
        if len(selectedVertices) == 1:
            self.report({'WARNING'}, 'Please select more than one vertex')
            return 0 # Cancel.
        elif not (len(knotVertices) or len(selectedVertices)):
            return 1 # Projected mode (let the user project the segments).
        return 2 # Standard mode (use the preselected vertices).


    def invoke(self, context, event):
        # Set a global reference to this instance, used by some external functions.
        global BMS_INSTANCE
        if not BMS_INSTANCE:
            BMS_INSTANCE = self

        self.bmsProperties = context.scene.bmsProperties
        self.startArea = context.area

        self.active2DDrawHandler = None
        self.active3DDrawHandler = None
        # Used with font drawing in the 2D draw handlers.
        self.uiScale = getattr(BMS_USER_PREFS.view, 'ui_scale', 1.0)

        keyconfigPrefs = context.window_manager.keyconfigs.active.preferences
        self.clickMouseName = 'LEFTMOUSE' if (not keyconfigPrefs or keyconfigPrefs.select_mouse == 'LEFT') else 'RIGHTMOUSE'

        # Right-mouse-click handling. These strings are used in the modal functions to check for keypress events.
        rmAction = BMS_ADDON_PREFS.rightMouseAction
        if rmAction == 'CONFIRM':
            self.rightMouseCancel = ''
            self.rightMouseConfirms = 'RIGHTMOUSE'
            self.rightMouseIgnore = None
        elif rmAction == 'CANCEL':
            self.rightMouseCancel = 'RIGHTMOUSE' if self.clickMouseName == 'LEFTMOUSE' else ''
            self.rightMouseConfirms = ''
            self.rightMouseIgnore = None
        else:
            self.rightMouseCancel = self.rightMouseConfirms = ''
            self.rightMouseIgnore = 'RIGHTMOUSE'

        self.spaceConfirms = 'SPACE' if BMS_ADDON_PREFS.spaceConfirms else ''

        if BMS_ADDON_PREFS.useDoubleClick:
            self.useDoubleClick = True
            self.doubleClickWaitTime = BMS_USER_PREFS.inputs.mouse_double_click_time / 1000.0 # From Blender settings.
            self.lastClickTime = time() - 1.0 # Start in the past to avoid a click issue with the projection mode.
        else:
            self.useDoubleClick = False

        self.obj = context.active_object

        self.oldShowWire = self.obj.show_wire
        self.oldShowAllEdges = self.obj.show_all_edges
        self.obj.show_wire = True
        self.obj.show_all_edges = True

        self.isUnbound = False

        if context.mode == 'EDIT_MESH':
            self.meshMode = True
            self.mesh = self.obj.data

            bm = bmesh.from_edit_mesh(self.mesh)
            bmVertType = bmesh.types.BMVert
            knotVertices = tuple(element for element in bm.select_history if isinstance(element, bmVertType))
            selectedVertices = tuple(v for v in bm.verts if v.select)

            status = self.getToolMode(knotVertices, selectedVertices)
            if status == 0:
                # Something went wrong, abort.
                self.end()
                return {'CANCELLED'}
            elif status == 1:
                # Projected mode, a preliminary mode where you choose knot locations on the mesh surface.
                # Test some conditions first.
                if self.mesh.shape_keys and len(self.mesh.shape_keys.key_blocks) > 1:
                    # Projected mode doesn't work with shape-keyed meshes yet, sorry.
                    self.report({'WARNING'}, 'Projection mode not available with shape keys, try selecting some vertices')
                    BMS_INSTANCE = None # Need to set to None since we're not calling 'self.end()' to do that for us.
                    return {'CANCELLED'}
                elif self.startupAction != 'NORMAL':
                    # Projected mode doesn't work with the startup snap modes, as snaps need selected vertices.
                    # The same for the "aligned tangents" startup mode.
                    self.report({'INFO'}, 'Please select two or more vertices to use this action')
                    BMS_INSTANCE = None
                    return {'CANCELLED'}
                else:
                    self.enterProjection(context, bm, event)
            else:
                # Vertex selection mode, enters the tool right away based on selected vertices.
                if not self.enterTool(context, bm, knotVertices, selectedVertices, None):
                    self.end()
                    return {'CANCELLED'}
        elif context.mode in {'EDIT_LATTICE', 'EDIT_SURFACE'}:
            # Editing a lattice or NURBS surface.
            self.meshMode = False
            # Use a wrapper class to edit objects as if they were meshes.
            wrapper = BMSLatticeMesh(self.obj) if context.mode == 'EDIT_LATTICE' else BMSNURBSMesh(self.obj)

            NULL_VECTOR = Vector()
            explicitPoints = wrapper.explicitPoints()
            if not explicitPoints:
                self.report({'WARNING'}, 'Please select 2 points')
                BMS_INSTANCE = None
                return {'CANCELLED'}
            if len(explicitPoints) != 2:
                self.report({'WARNING'}, 'Please only select 2 points')
                BMS_INSTANCE = None
                return {'CANCELLED'}

            # Send the selected points inside an iterable, to mimic 'self.allIntersectedPoints' from projection mode
            # that leads to logic creating the curve straight from a list (of lists) of points, instead of
            # traversing the "mesh" to find them.
            self.mesh = self.bm = wrapper
            if not self.enterTool(context, self.bm, None, None, [explicitPoints]):
                self.end()
                return {'CANCELLED'}
        else:
            BMS_INSTANCE = None
            return {'CANCELLED'}

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


    def execute(self, context):
        return self.invoke(context, None)


class BezierMeshShaperPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    curveDistance: bpy.props.FloatProperty(
        name = 'Curve Distance',
        description = 'Distance between the curve and the mesh (default: 0.0)',
        min = 0.0,
        max = 0.5,
        default = 0.0,
        precision = 3,
        unit = 'LENGTH'
    )

    secondaryMenu: bpy.props.EnumProperty(
        name = 'Secondary Menu',
        description = 'Show a second menu item on the Vertices menu (Ctrl+V), to call Bézier Mesh Shaper with a ' \
        'startup action',
        items = (
            ('0', 'None', 'Do not show a second menu item', 0),
            ('1', 'Snap Straight', 'Straightens the curve, then snaps vertices', 1),
            ('2', 'Snap Smooth', 'Snaps the primary vertices to the curve as it is', 2),
            ('3', 'Straight (Proportional)', 'Straightens the curve, then snaps vertices '\
            'but keeps their relative distances', 3),
            ('4', 'Snap Smooth (Proportional)', 'Snaps the primary vertices to the curve but keeps '\
            'their relative distances', 4),
            ('5', 'Aligned Tangents', 'Start the tool with the curve set to Aligned tangents (straight line ' \
            'between the two end points)', 5)
        ),
        default = '1'
    )

    useAllBetween: bpy.props.BoolProperty(
        name = 'Force Primary Vertices',
        description = 'Force the primary vertices (the ones you selected, used to fit the curve) to have 100% influence ' \
        'from the curve. Best disabled on highly dense meshes (default: on)',
        default = True
    )

    useVectorHandleStraight: bpy.props.BoolProperty(
        name = 'Snap Straight vector handles',
        description = 'When using the Snap Straight operation, automatically set all knot handle types to "Vector" (default: off)',
        default = False
    )

    handleVisibility: bpy.props.EnumProperty(
        name = 'Curve Handle Visibility',
        items = (
            ('ALWAYS', 'Always Visible', 'Always show the curve handles', 'IPO_BEZIER', 0),
            ('NOTGRAB', 'Hide in Grab Mode', 'Only hide the handles when in grab mode (with Ctrl + Click)', \
            'IPO_EASE_IN_OUT', 1),
            ('NEVER', 'Always Hidden', 'Always hide the curve handles', 'IPO_EASE_IN_OUT', 2)
        ),
        description = 'Visibility of the curve handles when starting the tool',
        default = 'NOTGRAB'
    )

    menuType: bpy.props.EnumProperty(
        name = 'Menu Type',
        items = (
            ('DIALOG', 'Dialog Menu', 'Traditional dialog menu', 'COLLAPSEMENU', 0),
            ('PIE', 'Pie Menu', 'Circular pie menu', 'ANTIALIASED', 1),
        ),
        description = 'Type of menu to use for the tool settings',
        default = 'DIALOG'
    )

    preselectInner: bpy.props.BoolProperty(
        name = 'Preselect Inner Handles',
        description = 'Preselect the two inside curve handles as soon as the tool starts (default: off)',
        default = False
    )

    preselectOuter: bpy.props.BoolProperty(
        name = 'Preselect Outer Handles',
        description = 'Preselect the two outside curve handles as soon as the tool starts (default: off)',
        default = False
    )

    spaceConfirms: bpy.props.BoolProperty(
        name = 'Space Key Confirms',
        description = 'Use the Space key to confirm the tool (besides Enter/PadEnter) (default: on)',
        default = True
    )

    rightMouseAction: bpy.props.EnumProperty(
        name = 'Right Mouse Action',
        description = 'What to do when the right mouse button is clicked (default: Cancel)',
        items = (
            ('CANCEL', 'Cancel', 'Right click cancels the tool', 0),
            ('CONFIRM', 'Confirm', 'Right click confirms the tool', 1),
            ('NOTHING', 'Nothing', 'Right click is ignored (use this with custom navigation keymaps etc.)', 2)
        ),
        default = 'CANCEL'
    )

    grabModeModifer: bpy.props.EnumProperty(
        name = 'Grab Mode Modifier',
        description = 'Modifier key for the special curve "grab" mode, while the tool is on (default: Ctrl)',
        items = (
            ('OSKEY', 'Cmd', 'Cmd key from MacOS', 0),
            ('LEFT_ALT|RIGHT_ALT', 'Alt', 'Alt modifier key', 2),
            ('LEFT_CTRL|RIGHT_CTRL', 'Ctrl', 'Ctrl modifier key', 3),
            ('|', '(None)', 'Disables the grab mode', 4)
        ),
        default = 'LEFT_CTRL|RIGHT_CTRL'
    )

    useDoubleClick: bpy.props.BoolProperty(
        name = 'Double-Click Confirms',
        description = 'Double-clicking your "select" mouse button confirms the tool (default: off)',
        default = False
    )

    setCurveColor: bpy.props.BoolProperty(
        name = 'Set Curve Color',
        description = 'Temporarily change the theme color of the curve so it\'s more visible (restored after ' \
        'the tool ends) (default: off)',
        default = False
    )

    curveColor: bpy.props.FloatVectorProperty(
        name = 'Curve Color',
        description = 'Temporarily change the theme color of the curve so it\'s more visible (restored after ' \
        'the tool ends) (default: off)',
        size = 3,
        default = (0.0, 0.92156, 0.74509), # (0, 235, 190) RGB, in float format (RGB / 255.0).
        subtype = 'COLOR_GAMMA',
        min = 0.0, max = 1.0
    )

    showKeymaps: bpy.props.BoolProperty(
        name = 'Show Keymaps On Screen',
        description = 'Show a list of common keymaps while using the tool (default: on)',
        default = True
    )

    keymapsTextSize: bpy.props.IntProperty(
        name = 'Text Size',
        description = 'Size of the keymaps text on-screen (default: 16)',
        min = 8,
        max = 32,
        default = 16,
        subtype = 'UNSIGNED'
    )


    def draw(self, context):
        layout = self.layout

        mainCol = layout.column(align=False)
        mainCol.alignment = 'CENTER'

        subRow = mainCol.row(align=False)
        subRow.alignment = 'CENTER'
        subSubRow = subRow.row(align=True)
        subSubRow.alignment = 'RIGHT'
        subSubRow.label(text='Secondary Menu:')
        subSubRow.prop(self, 'secondaryMenu', text='')
        subRow.prop(self, 'curveDistance', slider=True)

        mainCol.separator()

        subRow = mainCol.row(align=True)
        subRow.alignment = 'CENTER'
        subRow.prop(self, 'useAllBetween')
        subRow.prop(self, 'useVectorHandleStraight')

        #mainCol.separator()

        #subRow = mainCol.row(align=True)
        #subRow.alignment = 'CENTER'
        #subRow.label(text='Curve Handle Visibility:')
        #subRow.prop(self, 'handleVisibility', text='')

        mainCol.separator()

        subRow = mainCol.row(align=False)
        subRow.alignment = 'CENTER'
        subCol = subRow.column(align=True)
        subCol.alignment = 'RIGHT'
        subCol.prop(self, 'preselectInner')
        subCol.prop(self, 'preselectOuter')

        subCol = subRow.column(align=True)
        subCol.alignment = 'LEFT'
        subCol.label(text='Curve Handle Visibility:')
        subCol.prop(self, 'handleVisibility', text='')

        mainCol.separator()

        subRow = mainCol.row(align=True)
        subRow.alignment = 'CENTER'
        subRow.prop(self, 'menuType')

        mainCol.separator()

        subRow = mainCol.row(align=True)
        subRow.alignment = 'CENTER'
        subCol = subRow.column(align=True)
        subCol.prop(self, 'setCurveColor', text='Set Curve Color' + ('' if self.setCurveColor else '...'))
        if self.setCurveColor:
            subCol.prop(self, 'curveColor', text='')
        else:
            pass #subCol.label(text='') # Empty space.

        # Keymaps.
        layout.separator()
        try:
            mainRow = layout.row(align=True)
            mainRow.alignment = 'CENTER'

            colKeymaps = mainRow.column()

            headerRow = colKeymaps.row(align=True)
            headerRow.alignment = 'CENTER'
            headerRow.label(text='Keymaps:')
            headerRow = colKeymaps.row(align=True)
            headerRow.alignment = 'CENTER'
            headerRow.prop(self, 'showKeymaps')
            col = headerRow.row(align=True)
            col.enabled = self.showKeymaps
            col.alignment = 'LEFT'
            col.prop(self, 'keymapsTextSize')

            colKeymaps.separator()

            keymap = context.window_manager.keyconfigs.user.keymaps[BMS_KEYMAP_NAME]
            colKeymaps.context_pointer_set("keymap", keymap) # For the 'wm.keyitem_restore' operator.

            for item in keymap.keymap_items:
                if hasattr(item.properties, 'name') and item.properties.name.startswith('BMS'):
                    subCol = colKeymaps.column(align=True)

                    headerRow = subCol.row()
                    nameRow = headerRow.row()
                    nameRow.alignment = 'LEFT'
                    nameRow.label(text=item.properties.name.split(',')[1] + ':')

                    subRow = subCol.row()
                    subRow.scale_x = 0.75
                    subRow.alignment = 'CENTER'
                    subRow.prop(item, 'type', text='', full_event=True)
                    subRow.prop(item, 'shift_ui', toggle=True, expand=False)
                    subRow.prop(item, 'ctrl_ui', toggle=True, expand=False)
                    subRow.prop(item, 'alt_ui', toggle=True, expand=False)

                    if item.is_user_modified:
                        restoreRow = headerRow.row()
                        restoreRow.alignment = 'RIGHT'
                        restoreRow.operator('preferences.keyitem_restore', text='', icon='BACK').item_id = item.id

                    colKeymaps.separator()
                    colKeymaps.separator()

            # Note about undo/redo hotkeys.
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.label(text='Note: undo / redo / tilt will use the same hotkeys as set in Blender.')

            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.prop(self, 'spaceConfirms')
            row.prop(self, 'useDoubleClick')

            row = layout.row(align=True)
            row.alignment = 'CENTER'
            subRow = row.row(align=True)
            subRow.alignment = 'RIGHT'
            subRow.label(text='Right Mouse Action:')
            subRow.prop(self, 'rightMouseAction', text='')
            subRow.label(text='Grab Mode Key:')
            subRow.prop(self, 'grabModeModifer', text='')

        except:
            layout.label(text='No keymaps found.', icon='ERROR')

        box = layout.box()
        col = box.column(align=True)
        col.label(text='LOCATION:')
        col.label(text='(Edit mode) Mesh > Vertices > Bezier Mesh Shaper')
        col.label(text='Hotkey: right-click that menu and choose Add \ Change Shortcut.')
        col.label(text='(Or add operator \'mesh.bezier_mesh_shaper\' to the 3D View > Mesh input category.)')
        col = box.column(align=True)
        col.label(text='HOW TO USE:')
        col.label(text='Select two or more vertices where you want the curve knots to appear, then activate the tool.')
        col.label(text='Grab / rotate / scale the curve knots to sculpt the geometry, then press Enter to finish or Esc to cancel.')


_CLASSES = (
    BMSProperties,
    BMS_OT_transform_settings,
    BMS_OT_split,
    BMS_OT_snap,
    BMS_OT_export_curve,
    BMS_MT_split_menu,
    BMS_MT_snap_menu,
    BMS_MT_pie_menu,
    MESH_OT_bezier_mesh_shaper,
    BezierMeshShaperPreferences
)


def bezierMeshShaperMenu(self, context):
    if context.mode == 'EDIT_MESH':
        # Only draw this Specials menu item when the vertex or edge selection modes are active.
        selectMode = context.tool_settings.mesh_select_mode
        if selectMode[0] or selectMode[1]:
            self.layout.separator()
            # Add a menu item for the normal tool.
            self.layout.operator(
                MESH_OT_bezier_mesh_shaper.bl_idname, text=MESH_OT_bezier_mesh_shaper.bl_label
            ).startupAction = 'NORMAL'

            # See if the user wants a secondary menu item.
            if BMS_ADDON_PREFS.secondaryMenu != '0':
                startupAction, label = BMS_SECONDARY_MENU[int(BMS_ADDON_PREFS.secondaryMenu) - 1]
                self.layout.operator(
                    MESH_OT_bezier_mesh_shaper.bl_idname, text=MESH_OT_bezier_mesh_shaper.bl_label + label
                ).startupAction = startupAction

    else:
        # Edit lattice context menu.
        self.layout.separator()
        self.layout.operator(
            MESH_OT_bezier_mesh_shaper.bl_idname, text=MESH_OT_bezier_mesh_shaper.bl_label
        ).startupAction = 'NORMAL'


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)

    # Setting the global after the addon preferences class is registered.
    global BMS_ADDON_PREFS
    addonEntry = BMS_USER_PREFS.addons.get(__name__, None)
    BMS_ADDON_PREFS = addonEntry.preferences if addonEntry else BMSRuntimeDefaults()
    global BMS_INSTANCE
    BMS_INSTANCE = None

    # Create some customizable keymaps.
    # They are all deactivated, as we just want the UI widgets they make. Also, for some reason
    # a keymap item for a custom operator will not "remember" what keys were assigned to it, even
    # if you save your user preferences.
    # So instead of using "mesh.bezier_mesh_shaper" for the keymap items, we're using "wm.call_menu", and
    # storing some data in its '.properties.name' attribute. Since they're not enabled, it makes no difference.
    keymapItems = bpy.context.window_manager.keyconfigs.addon.keymaps.new(
        BMS_KEYMAP_NAME, space_type='VIEW_3D', region_type='WINDOW'
    ) . keymap_items

    kmi = keymapItems.new('wm.call_menu', 'TAB', 'PRESS')
    kmi.properties.name = 'BMS,Toggle Unbind Curve,onKeyUnbind'
    kmi.active = False

    kmi = keymapItems.new('wm.call_menu','PAGE_DOWN', 'PRESS')
    kmi.properties.name = 'BMS,Decrease Falloff Size,onKeyLessFalloff'
    kmi.active = False

    kmi = keymapItems.new('wm.call_menu', 'PAGE_UP', 'PRESS')
    kmi.properties.name = 'BMS,Increase Falloff Size,onKeyMoreFalloff'
    kmi.active = False

    kmi = keymapItems.new('wm.call_menu', 'E', 'PRESS')
    kmi.properties.name = 'BMS,Toggle "Use Direction",onKeyDirection'
    kmi.active = False

    kmi = keymapItems.new('wm.call_menu', 'W', 'PRESS')
    kmi.properties.name = 'BMS,Settings Menu,onKeyMenu'
    kmi.active = False

    kmi = keymapItems.new('wm.call_menu', 'Q', 'PRESS')
    kmi.properties.name = 'BMS,Toggle "Use Extremes",onKeyExtremes'
    kmi.active = False

    # Register the scene property group, where we store our operator settings.
    bpy.types.Scene.bmsProperties = bpy.props.PointerProperty(type=BMSProperties)

    # Add the tool to the Mesh > Vertices menu.
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(bezierMeshShaperMenu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(bezierMeshShaperMenu)
    bpy.types.VIEW3D_MT_edit_lattice_context_menu.append(bezierMeshShaperMenu)
    bpy.types.VIEW3D_MT_edit_curve_context_menu.append(bezierMeshShaperMenu)


def unregister():
    global BMS_INSTANCE
    try:
        if BMS_INSTANCE:
            BMS_INSTANCE.onCancel()
    except:
        pass # Probably trying to unregister after an error occurred.
    BMS_INSTANCE = None

    allKeymaps = bpy.context.window_manager.keyconfigs.addon.keymaps
    keymap = allKeymaps.get(BMS_KEYMAP_NAME)
    if keymap:
        keymapItems = keymap.keymap_items
        toDelete = tuple(
            item for item in keymapItems if item.idname == 'wm.call_menu' and item.properties.name.startswith('BMS')
        )
        for item in toDelete:
            keymapItems.remove(item)

    del bpy.types.Scene.bmsProperties
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(bezierMeshShaperMenu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(bezierMeshShaperMenu)
    bpy.types.VIEW3D_MT_edit_lattice_context_menu.remove(bezierMeshShaperMenu)
    bpy.types.VIEW3D_MT_edit_curve_context_menu.remove(bezierMeshShaperMenu)

    for cls in _CLASSES:
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
