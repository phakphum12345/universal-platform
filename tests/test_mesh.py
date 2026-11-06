from __future__ import annotations

from copy import deepcopy
from math import cos, pi
from pathlib import Path
import json

import pytest

from universal_platform.engineering import BoxSolid, CylinderSolid, ExtrudedProfileSolid, Vec2
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.mesh import (
    TriangleMesh,
    tessellate_box,
    tessellate_cylinder,
    tessellate_extruded_profile,
    validate_triangle_mesh,
)


def test_box_tessellation_is_closed_oriented_and_matches_analytic_metrics():
    solid = BoxSolid("box.main", "world", Vec3(2.0, 3.0, 4.0), "m")
    mesh = tessellate_box(solid)
    result = validate_triangle_mesh(mesh)

    assert result.valid
    assert result.watertight
    assert result.consistently_oriented
    assert result.vertex_count == 8
    assert result.triangle_count == 12
    assert result.boundary_edge_count == 0
    assert result.nonmanifold_edge_count == 0
    assert result.winding_conflict_count == 0
    assert result.signed_volume == pytest.approx(24.0)
    assert result.surface_area == pytest.approx(52.0)
    assert mesh.frame_id == "world"
    assert mesh.length_unit == "m"


def test_cylinder_tessellation_respects_chordal_tolerance_and_is_closed():
    solid = CylinderSolid("cylinder.main", "part.frame", 10.0, 25.0, "mm")
    tolerance = 0.25
    mesh = tessellate_cylinder(solid, tolerance)
    result = validate_triangle_mesh(mesh)
    segments = (len(mesh.vertices) - 2) // 2
    actual_error = solid.radius * (1.0 - cos(pi / segments))

    assert result.valid
    assert result.watertight
    assert result.consistently_oriented
    assert result.boundary_edge_count == 0
    assert result.nonmanifold_edge_count == 0
    assert result.winding_conflict_count == 0
    assert result.signed_volume > 0
    assert result.surface_area > 0
    assert actual_error <= tolerance
    assert mesh.chordal_tolerance == tolerance
    assert mesh.frame_id == "part.frame"
    assert mesh.length_unit == "mm"


def test_mesh_serialization_is_deterministic_and_round_trips_strictly():
    solid = CylinderSolid("cylinder.roundtrip", "world", 2.0, 5.0, "cm")
    mesh = tessellate_cylinder(solid, 0.05)
    snapshot = mesh.to_dict()

    assert mesh.to_dict() == snapshot
    assert TriangleMesh.from_dict(snapshot) == mesh
    assert TriangleMesh.from_dict(snapshot).to_dict() == snapshot


def test_mesh_schema_rejects_unknown_fields_and_wrong_version():
    solid = BoxSolid("box.schema", "world", Vec3(1.0, 2.0, 3.0), "m")
    snapshot = tessellate_box(solid).to_dict()
    malformed = deepcopy(snapshot)
    malformed["unexpected"] = True
    with pytest.raises(InvalidModelError):
        TriangleMesh.from_dict(malformed)
    malformed = deepcopy(snapshot)
    malformed["schema_version"] = "2.0"
    with pytest.raises(InvalidModelError):
        TriangleMesh.from_dict(malformed)


def test_mesh_validator_reports_out_of_range_face_indices():
    solid = BoxSolid("box.index", "world", Vec3(1.0, 1.0, 1.0), "m")
    mesh = tessellate_box(solid)
    faces = list(mesh.triangles)
    faces[0] = (0, 1, 999)
    invalid = TriangleMesh(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices, tuple(faces),
    )
    result = validate_triangle_mesh(invalid)

    assert not result.valid
    assert "FACE_INDEX_OUT_OF_RANGE:0" in result.issues


def test_mesh_validator_detects_open_surface_and_degenerate_faces():
    solid = BoxSolid("box.open", "world", Vec3(1.0, 1.0, 1.0), "m")
    mesh = tessellate_box(solid)
    open_mesh = TriangleMesh(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices, mesh.triangles[:-1],
    )
    result = validate_triangle_mesh(open_mesh)
    assert not result.valid
    assert not result.watertight
    assert result.boundary_edge_count > 0

    degenerate_faces = list(mesh.triangles)
    degenerate_faces[0] = (0, 0, 1)
    degenerate = TriangleMesh(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices, tuple(degenerate_faces),
    )
    result = validate_triangle_mesh(degenerate)
    assert not result.valid
    assert result.degenerate_triangle_count == 1


def test_mesh_validator_detects_inconsistent_face_winding():
    solid = BoxSolid("box.winding", "world", Vec3(1.0, 1.0, 1.0), "m")
    mesh = tessellate_box(solid)
    faces = list(mesh.triangles)
    a, b, c = faces[0]
    faces[0] = (a, c, b)
    invalid = TriangleMesh(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices, tuple(faces),
    )
    result = validate_triangle_mesh(invalid)

    assert not result.valid
    assert result.winding_conflict_count > 0


def test_cylinder_rejects_invalid_tolerance_and_resource_excess():
    solid = CylinderSolid("cylinder.tolerance", "world", 1.0, 2.0, "m")
    with pytest.raises(InvalidModelError):
        tessellate_cylinder(solid, 0.0)
    with pytest.raises(InvalidModelError):
        tessellate_cylinder(solid, -0.1)
    with pytest.raises(InvalidModelError):
        tessellate_cylinder(solid, 1e-20)


def test_mesh_schema_matches_serialized_shape():
    solid = BoxSolid("box.schema.fixture", "world", Vec3(1.0, 1.0, 1.0), "m")
    snapshot = tessellate_box(solid).to_dict()
    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "geometry" / "triangle-mesh.schema.json").read_text()
    )
    assert schema["properties"]["schema_version"]["const"] == snapshot["schema_version"]
    assert set(snapshot) == set(schema["required"])
    assert schema["properties"]["source_kind"]["enum"] == ["BOX", "CYLINDER", "EXTRUDED_PROFILE"]


def test_mesh_rejects_non_length_units():
    solid = BoxSolid("box.unit", "world", Vec3(1.0, 1.0, 1.0), "m")
    mesh = tessellate_box(solid).to_dict()
    mesh["length_unit"] = "kg"
    with pytest.raises(InvalidModelError):
        TriangleMesh.from_dict(mesh)

def _l_profile(solid_id: str, points=None) -> ExtrudedProfileSolid:
    profile = points or (
        Vec2(0, 0), Vec2(2, 0), Vec2(2, 1),
        Vec2(1, 1), Vec2(1, 2), Vec2(0, 2),
    )
    return ExtrudedProfileSolid(solid_id, "profile.frame", profile, 4.0, "m")


def test_concave_straight_profile_tessellation_matches_analytic_metrics():
    solid = _l_profile("profile.concave")
    mesh = tessellate_extruded_profile(solid)
    result = validate_triangle_mesh(mesh)

    assert result.valid
    assert result.watertight
    assert result.consistently_oriented
    assert result.vertex_count == 12
    assert result.triangle_count == 20
    assert result.boundary_edge_count == 0
    assert result.nonmanifold_edge_count == 0
    assert result.winding_conflict_count == 0
    assert result.signed_volume == pytest.approx(12.0)
    assert result.surface_area == pytest.approx(38.0)
    assert mesh.source_kind == "EXTRUDED_PROFILE"
    assert mesh.frame_id == "profile.frame"
    assert mesh.length_unit == "m"


def test_profile_tessellation_is_consistent_for_clockwise_and_counterclockwise_loops():
    ccw = _l_profile("profile.ccw")
    cw = _l_profile("profile.cw", tuple(reversed(ccw.profile)))
    ccw_mesh = tessellate_extruded_profile(ccw)
    cw_mesh = tessellate_extruded_profile(cw)

    assert validate_triangle_mesh(ccw_mesh).valid
    assert validate_triangle_mesh(cw_mesh).valid
    assert validate_triangle_mesh(ccw_mesh).signed_volume == pytest.approx(12.0)
    assert validate_triangle_mesh(cw_mesh).signed_volume == pytest.approx(12.0)
    assert validate_triangle_mesh(cw_mesh).surface_area == pytest.approx(38.0)


def test_profile_tessellation_handles_collinear_boundary_vertices():
    points = (
        Vec2(0, 0), Vec2(1, 0), Vec2(2, 0),
        Vec2(2, 1), Vec2(0, 1),
    )
    solid = ExtrudedProfileSolid("profile.collinear", "world", points, 3.0, "cm")
    mesh = tessellate_extruded_profile(solid)
    result = validate_triangle_mesh(mesh)

    assert result.valid
    assert result.signed_volume == pytest.approx(6.0)
    assert result.surface_area == pytest.approx(22.0)


def test_profile_tessellation_supports_one_through_hole():
    outer = (Vec2(0, 0), Vec2(4, 0), Vec2(4, 4), Vec2(0, 4))
    hole = (Vec2(1, 1), Vec2(1, 2), Vec2(2, 2), Vec2(2, 1))
    solid = ExtrudedProfileSolid("profile.hole", "world", outer, 2.0, "m", (hole,))
    mesh = tessellate_extruded_profile(solid)
    result = validate_triangle_mesh(mesh)

    assert result.valid
    assert result.watertight
    assert result.consistently_oriented
    assert result.boundary_edge_count == 0
    assert result.nonmanifold_edge_count == 0
    assert result.winding_conflict_count == 0
    assert result.signed_volume == pytest.approx(30.0)
    assert result.surface_area == pytest.approx(70.0)
    assert len(mesh.vertices) == 16


def test_profile_tessellation_supports_multiple_disjoint_holes():
    outer = (Vec2(0, 0), Vec2(10, 0), Vec2(10, 10), Vec2(0, 10))
    hole1 = (Vec2(1, 1), Vec2(1, 2), Vec2(2, 2), Vec2(2, 1))
    hole2 = (Vec2(6, 6), Vec2(6, 8), Vec2(8, 8), Vec2(8, 6))
    solid = ExtrudedProfileSolid("profile.multihole", "world", outer, 1.0, "m", (hole1, hole2))
    mesh = tessellate_extruded_profile(solid)
    result = validate_triangle_mesh(mesh)

    assert result.valid
    assert result.watertight
    assert result.consistently_oriented
    assert result.signed_volume == pytest.approx(95.0)
    assert result.surface_area == pytest.approx(242.0)


def test_profile_arc_tessellation_requires_tolerance_and_respects_chord_error():
    curved = ExtrudedProfileSolid(
        "profile.curved", "world",
        (Vec2(0, 0), Vec2(2, 0), Vec2(0, 2)), 1.0, "m",
        arc_sweeps_rad=(0.5, 0.0, 0.0),
        segment_ids=("edge.arc", "edge.line1", "edge.line2"),
    )
    with pytest.raises(InvalidModelError):
        tessellate_extruded_profile(curved)
    mesh = tessellate_extruded_profile(curved, chordal_tolerance=0.01)
    result = validate_triangle_mesh(mesh)

    assert result.valid
    assert result.watertight
    assert result.consistently_oriented
    assert result.signed_volume > 0
    assert mesh.chordal_tolerance == 0.01
    assert len(mesh.vertices) > 6
    with pytest.raises(InvalidModelError):
        tessellate_extruded_profile(curved, chordal_tolerance=0.0)
    with pytest.raises(InvalidModelError):
        tessellate_extruded_profile(curved, chordal_tolerance=1e-20)


def test_profile_mesh_snapshot_round_trip_preserves_provenance():
    mesh = tessellate_extruded_profile(_l_profile("profile.roundtrip"))
    restored = TriangleMesh.from_dict(mesh.to_dict())
    assert restored == mesh
    assert validate_triangle_mesh(restored).valid

def test_profile_hole_winding_is_normalized_and_deterministic():
    outer = (Vec2(0, 0), Vec2(4, 0), Vec2(4, 4), Vec2(0, 4))
    hole_cw = (Vec2(1, 1), Vec2(1, 2), Vec2(2, 2), Vec2(2, 1))
    hole_ccw = tuple(reversed(hole_cw))
    cw_solid = ExtrudedProfileSolid("profile.hole.cw", "world", outer, 2.0, "m", (hole_cw,))
    ccw_solid = ExtrudedProfileSolid("profile.hole.ccw", "world", outer, 2.0, "m", (hole_ccw,))
    cw_mesh = tessellate_extruded_profile(cw_solid)
    ccw_mesh = tessellate_extruded_profile(ccw_solid)

    assert validate_triangle_mesh(cw_mesh).valid
    assert validate_triangle_mesh(ccw_mesh).valid
    assert validate_triangle_mesh(ccw_mesh).signed_volume == pytest.approx(30.0)
    assert validate_triangle_mesh(ccw_mesh).surface_area == pytest.approx(70.0)
    assert tessellate_extruded_profile(cw_solid).to_dict() == cw_mesh.to_dict()
