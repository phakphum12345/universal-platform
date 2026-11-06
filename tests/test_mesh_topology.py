from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from universal_platform.engineering import (
    BoxSolid,
    MeshTopologyAnalysis,
    Vec3,
    analyze_mesh_topology,
    tessellate_box,
    validate_triangle_mesh,
)
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.mesh import TriangleMesh


def _mesh_with_disjoint_boxes() -> TriangleMesh:
    first = tessellate_box(BoxSolid("box.topology.a", "world", Vec3(1, 1, 1), "m"))
    second = tessellate_box(BoxSolid("box.topology.b", "world", Vec3(1, 1, 1), "m"))
    shifted = tuple(Vec3(v.x + 3.0, v.y, v.z) for v in second.vertices)
    vertices = first.vertices + shifted
    triangles = first.triangles + tuple(
        tuple(index + len(first.vertices) for index in face) for face in second.triangles
    )
    return TriangleMesh(
        "compound.disjoint", "world", "m", "BOX", first.source_geometry_sha256,
        vertices, triangles,
    )


def _mesh_with_vertex_touching_boxes() -> tuple[TriangleMesh, int]:
    first = tessellate_box(BoxSolid("box.touch.a", "world", Vec3(1, 1, 1), "m"))
    second = tessellate_box(BoxSolid("box.touch.b", "world", Vec3(1, 1, 1), "m"))
    first_index = {
        (vertex.x, vertex.y, vertex.z): index
        for index, vertex in enumerate(first.vertices)
    }
    vertices = list(first.vertices)
    second_map = []
    shared_index = first_index[(1.0, 1.0, 1.0)]
    for vertex in second.vertices:
        point = (vertex.x + 1.0, vertex.y + 1.0, vertex.z + 1.0)
        if point == (1.0, 1.0, 1.0):
            second_map.append(shared_index)
        else:
            second_map.append(len(vertices))
            vertices.append(Vec3(*point))
    triangles = first.triangles + tuple(
        tuple(second_map[index] for index in face) for face in second.triangles
    )
    mesh = TriangleMesh(
        "compound.vertex-touch", "world", "m", "BOX", first.source_geometry_sha256,
        tuple(vertices), triangles,
    )
    return mesh, shared_index


def test_box_topology_analysis_reports_one_clean_shell_but_keeps_self_intersection_unknown():
    mesh = tessellate_box(BoxSolid("box.analysis", "part.frame", Vec3(2, 3, 4), "mm"))
    before = mesh.to_dict()
    result = analyze_mesh_topology(mesh)

    assert result.face_component_count == 1
    assert result.face_components == (tuple(range(12)),)
    assert result.exact_duplicate_vertex_groups == ()
    assert result.near_coincident_vertex_groups == ()
    assert result.nonmanifold_vertex_indices == ()
    assert result.unused_vertex_indices == ()
    assert result.diagnostic_status == "NO_TOPOLOGY_ISSUES_FOUND"
    assert result.self_intersection_status == "UNKNOWN"
    assert result.solid_id == mesh.solid_id
    assert result.frame_id == mesh.frame_id
    assert result.length_unit == mesh.length_unit
    assert result.vertex_count == len(mesh.vertices)
    assert result.triangle_count == len(mesh.triangles)
    assert len(result.mesh_snapshot_sha256) == 64
    assert mesh.to_dict() == before


def test_topology_analysis_finds_edge_disconnected_shells():
    mesh = _mesh_with_disjoint_boxes()
    assert validate_triangle_mesh(mesh).valid

    result = analyze_mesh_topology(mesh)

    assert result.face_component_count == 2
    assert result.face_components == (tuple(range(12)), tuple(range(12, 24)))
    assert "DISCONNECTED_FACE_COMPONENTS:2" in result.issues
    assert result.self_intersection_status == "UNKNOWN"


def test_topology_analysis_detects_pinched_vertex_fan_beyond_edge_incidence():
    mesh, shared_vertex = _mesh_with_vertex_touching_boxes()
    assert validate_triangle_mesh(mesh).valid

    result = analyze_mesh_topology(mesh)

    assert result.face_component_count == 2
    assert shared_vertex in result.nonmanifold_vertex_indices
    assert f"NONMANIFOLD_VERTEX_FAN:{shared_vertex}" in result.issues


def test_topology_analysis_reports_exact_duplicates_and_unused_vertices():
    mesh = tessellate_box(BoxSolid("box.duplicate", "world", Vec3(1, 1, 1), "m"))
    duplicated = TriangleMesh(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices + (mesh.vertices[0],), mesh.triangles,
    )

    result = analyze_mesh_topology(duplicated)

    assert result.exact_duplicate_vertex_groups == ((0, 8),)
    assert result.unused_vertex_indices == (8,)
    assert "DUPLICATE_VERTEX_COORDINATES:0,8" in result.issues
    assert "UNUSED_VERTEX:8" in result.issues


def test_topology_analysis_near_coincident_tolerance_is_explicit_and_non_mutating():
    mesh = tessellate_box(BoxSolid("box.near", "world", Vec3(1, 1, 1), "m"))
    near_vertex = Vec3(mesh.vertices[0].x + 0.005, mesh.vertices[0].y, mesh.vertices[0].z)
    extended = TriangleMesh(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices + (near_vertex,), mesh.triangles,
    )
    before = extended.to_dict()

    exact_only = analyze_mesh_topology(extended)
    tolerant = analyze_mesh_topology(extended, coincident_tolerance=0.01)

    assert exact_only.near_coincident_vertex_groups == ()
    assert tolerant.near_coincident_vertex_groups == ((0, 8),)
    assert tolerant.coincident_tolerance == 0.01
    assert extended.to_dict() == before


def test_topology_analysis_is_deterministic_and_round_trips_strictly():
    mesh = _mesh_with_disjoint_boxes()
    first = analyze_mesh_topology(mesh, coincident_tolerance=0.001)
    second = analyze_mesh_topology(mesh, coincident_tolerance=0.001)

    assert first.to_dict() == second.to_dict()
    assert MeshTopologyAnalysis.from_dict(first.to_dict()) == first
    assert MeshTopologyAnalysis.from_dict(first.to_dict()).to_dict() == first.to_dict()

    malformed = deepcopy(first.to_dict())
    malformed["unexpected"] = True
    with pytest.raises(InvalidModelError):
        MeshTopologyAnalysis.from_dict(malformed)
    malformed = deepcopy(first.to_dict())
    malformed["face_component_count"] += 1
    with pytest.raises(InvalidModelError):
        MeshTopologyAnalysis.from_dict(malformed)
    malformed = deepcopy(first.to_dict())
    malformed["self_intersection_status"] = "PASS"
    with pytest.raises(InvalidModelError):
        MeshTopologyAnalysis.from_dict(malformed)
    malformed = deepcopy(first.to_dict())
    malformed["face_components"][0][0] = 999
    with pytest.raises(InvalidModelError):
        MeshTopologyAnalysis.from_dict(malformed)


def test_topology_analysis_schema_matches_serialized_shape():
    mesh = tessellate_box(BoxSolid("box.topology.schema", "world", Vec3(1, 1, 1), "m"))
    snapshot = analyze_mesh_topology(mesh).to_dict()
    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "geometry" / "mesh-topology-analysis.schema.json").read_text()
    )
    assert set(snapshot) == set(schema["required"])
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["self_intersection_status"]["const"] == "UNKNOWN"
    assert schema["additionalProperties"] is False


def test_topology_analysis_rejects_bad_tolerance_and_comparison_budget():
    mesh = tessellate_box(BoxSolid("box.topology.limit", "world", Vec3(1, 1, 1), "m"))
    with pytest.raises(InvalidModelError):
        analyze_mesh_topology(mesh, coincident_tolerance=-1.0)
    with pytest.raises(InvalidModelError):
        analyze_mesh_topology(mesh, coincident_tolerance=float("inf"))
    with pytest.raises(InvalidModelError):
        analyze_mesh_topology(mesh, coincident_tolerance=100.0, max_neighbor_comparisons=1)
    with pytest.raises(InvalidModelError):
        analyze_mesh_topology(mesh, max_neighbor_comparisons=0)


def test_topology_analysis_skips_invalid_faces_without_crashing():
    mesh = tessellate_box(BoxSolid("box.topology.invalid-face", "world", Vec3(1, 1, 1), "m"))
    faces = list(mesh.triangles)
    faces[0] = (0, 1, 999)
    malformed = TriangleMesh(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices, tuple(faces),
    )

    result = analyze_mesh_topology(malformed)

    assert result.triangle_count == len(mesh.triangles)
    assert result.face_component_count >= 1
    assert result.self_intersection_status == "UNKNOWN"
