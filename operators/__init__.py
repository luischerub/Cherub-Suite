import bpy

from .delete_half_mirror import CHERUBPIES_OT_DeleteHalfMirror
from .add_hotkey import CHERUBPIES_OT_AddHotkey
from .uv_boundary import (
    CHERUBPIES_OT_MarkFaceBoundary,
    CHERUBPIES_OT_UnmarkFaceBoundary,
)

from .uv_window import CHERUBPIES_OT_CallUvWindow
from .proportional_objects import (
    CHERUBPIES_OT_ProportionalSmooth,
    CHERUBPIES_OT_ProportionalRoot,
    CHERUBPIES_OT_ProportionalConstant,
    CHERUBPIES_OT_ProportionalSharp,
    CHERUBPIES_OT_ProportionalSphere,
    CHERUBPIES_OT_ProportionalRandom,
    CHERUBPIES_OT_ProportionalLinear,
)
from .proportional_edits import (
    CHERUBPIES_OT_ProportionalEditToggle,
    CHERUBPIES_OT_ProportionalEditConnected,
    CHERUBPIES_OT_ProportionalEditConstant,
    CHERUBPIES_OT_ProportionalEditLinear,
    CHERUBPIES_OT_ProportionalEditProjected,
    CHERUBPIES_OT_ProportionalEditRandom,
    CHERUBPIES_OT_ProportionalEditRoot,
    CHERUBPIES_OT_ProportionalEditSharp,
    CHERUBPIES_OT_ProportionalEditSmooth,
    CHERUBPIES_OT_ProportionalEditSphere,
)
from .selection_origin import CHERUBPIES_OT_SelectionToWorldOrigin
from .cursor_center import CHERUBPIES_OT_SelectionCursorToCenter
from .shapekeys_bake_to_attr import CHERUB_OT_BakeShapeKeysToAttributes
from .shapekeys_mesh_unifier import CHERUB_OT_UnifyMeshesToShapeKeys
from .assetlib_render_assets import CHERUB_OT_AssetLibRender
from .assetlib_assign_thumb import CHERUB_OT_AssetLibAssignThumb
from .bezier_deform import (
    BezierDeformProperties,
    MESH_OT_bezier_deform,
)
from .edgetools_flow import CHERUB_OT_EdgeFlow
from .edgetools_linear import CHERUB_OT_EdgeLinear
from .edgetools_curve import CHERUB_OT_EdgeCurve
from .edgetools_vertex_curve import CHERUB_OT_VertexCurve
from ..lib.UVSquares.uv_squares import (
    UV_PT_UvSquares,
    UV_PT_UvSquaresByShape,
    UV_PT_RipFaces,
    UV_PT_JoinFaces,
    UV_PT_SnapToAxis,
    UV_PT_SnapToAxisWithEqual,
)

classes = [
    CHERUBPIES_OT_DeleteHalfMirror,
    CHERUBPIES_OT_AddHotkey,
    CHERUBPIES_OT_ProportionalSmooth,
    CHERUBPIES_OT_ProportionalRoot,
    CHERUBPIES_OT_ProportionalConstant,
    CHERUBPIES_OT_ProportionalSharp,
    CHERUBPIES_OT_ProportionalSphere,
    CHERUBPIES_OT_ProportionalRandom,
    CHERUBPIES_OT_ProportionalLinear,
    CHERUBPIES_OT_ProportionalEditToggle,
    CHERUBPIES_OT_ProportionalEditConnected,
    CHERUBPIES_OT_ProportionalEditConstant,
    CHERUBPIES_OT_ProportionalEditLinear,
    CHERUBPIES_OT_ProportionalEditProjected,
    CHERUBPIES_OT_ProportionalEditRandom,
    CHERUBPIES_OT_ProportionalEditRoot,
    CHERUBPIES_OT_ProportionalEditSharp,
    CHERUBPIES_OT_ProportionalEditSmooth,
    CHERUBPIES_OT_ProportionalEditSphere,
    CHERUBPIES_OT_SelectionCursorToCenter,
    CHERUBPIES_OT_MarkFaceBoundary,
    CHERUBPIES_OT_UnmarkFaceBoundary,
    CHERUBPIES_OT_SelectionToWorldOrigin,
    CHERUB_OT_BakeShapeKeysToAttributes,
    CHERUB_OT_UnifyMeshesToShapeKeys,
    CHERUB_OT_AssetLibRender,
    CHERUB_OT_AssetLibAssignThumb,
    BezierDeformProperties,
    MESH_OT_bezier_deform,
    CHERUB_OT_EdgeFlow,
    CHERUB_OT_EdgeLinear,
    CHERUB_OT_EdgeCurve,
    CHERUB_OT_VertexCurve,
    UV_PT_UvSquares,
    UV_PT_UvSquaresByShape,
    UV_PT_RipFaces,
    UV_PT_JoinFaces,
    UV_PT_SnapToAxis,
    UV_PT_SnapToAxisWithEqual,
    CHERUBPIES_OT_CallUvWindow,
]
