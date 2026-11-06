from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from universal_platform.engineering import (
    BoxSolid, analyze_mesh_intersections, tessellate_box, validate_triangle_mesh,
)
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh
from universal_platform.engineering.mesh_intersection import MeshIntersectionAnalysis


def _combine_boxes(offset_x: float) -> TriangleMesh:
    first = tessellate_box(BoxSolid("intersection.a", "world", Vec3(1, 1, 1), "m"))
    second = tessellate_box(BoxSolid("intersection.b", "world", Vec3(1, 1, 1), "m"))
    shifted = tuple(Vec3(v.x + offset_x, v.y, v.z) for v in second.vertices)
    vertices = first.vertices + shifted
    triangles = first.triangles + tuple(
        tuple(index + len(first.vertices) for index in face) for face in second.triangles
    )
    return TriangleMesh(
        "intersection.compound", "world", "m", "BOX",
        first.source_geometry_sha256, vertices, triangles,
    )


def test_disjoint_closed_boxes_have_no_intersections_and_keep_provenance():
    mesh = _combine_boxes(3.0)
    assert validate_triangle_mesh(mesh).valid
    before = mesh.to_dict()
    result = analyze_mesh_intersections(mesh)
    assert result.status == "NO_INTERSECTIONS_FOUND"
    assert result.candidate_pair_count_complete
    assert result.checked_pair_count == result.candidate_pair_count
    assert result.intersections == ()
    assert result.solid_id == mesh.solid_id
    assert result.frame_id == mesh.frame_id
    assert len(result.mesh_snapshot_sha256) == 64
    assert mesh.to_dict() == before


def test_overlapping_closed_boxes_report_geometric_intersections_deterministically():
    mesh = _combine_boxes(0.5)
    assert validate_triangle_mesh(mesh).valid
    first = analyze_mesh_intersections(mesh)
    second = analyze_mesh_intersections(mesh)
    assert first.status == "INTERSECTIONS_FOUND"
    assert first.intersections
    assert first.to_dict() == second.to_dict()
    assert all(pair.triangle_a < pair.triangle_b for pair in first.intersections)


def test_single_box_reports_only_expected_shared_edge_adjacency():
    mesh = tessellate_box(BoxSolid("intersection.box", "world", Vec3(1, 2, 3), "m"))
    result = analyze_mesh_intersections(mesh)
    assert result.status == "NO_INTERSECTIONS_FOUND"
    assert result.intersections == ()


def test_candidate_limit_fails_closed_and_never_claims_no_intersections():
    mesh = tessellate_box(BoxSolid("intersection.limit", "world", Vec3(1, 1, 1), "m"))
    result = analyze_mesh_intersections(mesh, max_candidate_pairs=1)
    assert result.status == "UNKNOWN"
    assert result.candidate_pair_count == 2
    assert not result.candidate_pair_count_complete
    assert result.checked_pair_count == 0
    assert result.unresolved_reasons == ("RESOURCE_LIMIT_EXCEEDED",)


def test_invalid_structural_mesh_is_rejected_before_analysis():
    mesh = tessellate_box(BoxSolid("intersection.invalid", "world", Vec3(1, 1, 1), "m"))
    faces = list(mesh.triangles)
    faces[0] = (0, 1, 999)
    invalid = TriangleMesh(mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
                           mesh.source_geometry_sha256, mesh.vertices, tuple(faces))
    with pytest.raises(InvalidModelError):
        analyze_mesh_intersections(invalid)


def test_result_round_trip_is_strict_and_schema_matches():
    mesh = tessellate_box(BoxSolid("intersection.schema", "world", Vec3(1, 1, 1), "m"))
    result = analyze_mesh_intersections(mesh)
    assert MeshIntersectionAnalysis.from_dict(result.to_dict()) == result
    malformed = deepcopy(result.to_dict())
    malformed["status"] = "PASS"
    with pytest.raises(InvalidModelError):
        MeshIntersectionAnalysis.from_dict(malformed)
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "geometry" /
                         "mesh-intersection-analysis.schema.json").read_text())
    assert set(result.to_dict()) == set(schema["required"])
    assert schema["additionalProperties"] is False


def test_pair_limit_rejects_boolean_and_out_of_range_values():
    mesh = tessellate_box(BoxSolid("intersection.options", "world", Vec3(1, 1, 1), "m"))
    for value in (True, 0, -1, 5_000_001):
        with pytest.raises(InvalidModelError):
            analyze_mesh_intersections(mesh, max_candidate_pairs=value)



def _raw_pair_mesh(points, faces) -> TriangleMesh:
    return TriangleMesh(
        "pair.reference", "world", "m", "BOX", "0" * 64,
        tuple(Vec3(*point) for point in points), tuple(tuple(face) for face in faces),
    )


def test_exact_narrow_phase_classifies_proper_crossing_and_coplanar_overlap():
    from universal_platform.engineering.mesh_intersection import _pair_intersection

    crossing = _raw_pair_mesh(
        [(0, 0, 0), (2, 0, 0), (0, 2, 0),
         (1, -1, -1), (1, 2, -1), (1, 0, 1)],
        [(0, 1, 2), (3, 4, 5)],
    )
    assert _pair_intersection(crossing, 0, 1) == "PROPER_INTERSECTION"

    overlap = _raw_pair_mesh(
        [(0, 0, 0), (2, 0, 0), (0, 2, 0),
         (1, 0, 0), (3, 0, 0), (1, 2, 0)],
        [(0, 1, 2), (3, 4, 5)],
    )
    assert _pair_intersection(overlap, 0, 1) == "COPLANAR_OVERLAP"


def test_exact_narrow_phase_distinguishes_unshared_contact_and_duplicate_facets():
    from universal_platform.engineering.mesh_intersection import _pair_intersection

    contact = _raw_pair_mesh(
        [(0, 0, 0), (2, 0, 0), (0, 2, 0),
         (2, 0, 0), (3, -1, 0), (3, 1, 0)],
        [(0, 1, 2), (3, 4, 5)],
    )
    assert _pair_intersection(contact, 0, 1) == "UNSHARED_CONTACT"

    duplicate = _raw_pair_mesh(
        [(0, 0, 0), (2, 0, 0), (0, 2, 0),
         (0, 2, 0), (2, 0, 0), (0, 0, 0)],
        [(0, 1, 2), (3, 4, 5)],
    )
    assert _pair_intersection(duplicate, 0, 1) == "DUPLICATE_FACET"


def test_expected_shared_edge_and_vertex_adjacency_are_not_false_positives():
    from universal_platform.engineering.mesh_intersection import _pair_intersection

    opposite_edge = _raw_pair_mesh(
        [(0, 0, 0), (2, 0, 0), (0, 2, 0), (1, -1, 0)],
        [(0, 1, 2), (1, 0, 3)],
    )
    assert _pair_intersection(opposite_edge, 0, 1) is None

    shared_vertex = _raw_pair_mesh(
        [(0, 0, 0), (2, 0, 0), (0, 2, 0), (2, 1, 0), (1, 2, 0)],
        [(0, 1, 2), (0, 3, 4)],
    )
    assert _pair_intersection(shared_vertex, 0, 1) == "ADJACENT_VERTEX_CROSSING"


def test_shared_edge_same_side_overlap_is_an_adjacent_foldover():
    from universal_platform.engineering.mesh_intersection import _pair_intersection

    foldover = _raw_pair_mesh(
        [(0, 0, 0), (2, 0, 0), (0, 2, 0), (1, 1, 0)],
        [(0, 1, 2), (1, 0, 3)],
    )
    assert _pair_intersection(foldover, 0, 1) == "ADJACENT_FOLDOVER"
