from __future__ import annotations

from copy import deepcopy
from math import cos, pi
from pathlib import Path
import json

import pytest

from universal_platform.engineering import BoxSolid, CylinderSolid, Vec3
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.mesh import (
    TriangleMesh,
    tessellate_box,
    tessellate_cylinder,
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
    assert schema["properties"]["source_kind"]["enum"] == ["BOX", "CYLINDER"]
