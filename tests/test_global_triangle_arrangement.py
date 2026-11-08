from fractions import Fraction

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.triangle_fragment_arrangement import RationalPlane
from universal_platform.engineering.global_triangle_arrangement import (
    arrange_triangle_mesh_globally,
)

F = Fraction


def p(x, y, z=0):
    return (F(x), F(y), F(z))


def plane_x(x):
    return RationalPlane(0, (p(x, -1, -1), p(x, 3, -1), p(x, 0, 1)))


def test_global_registry_unifies_shared_vertices_and_reports_shared_edge_adjacency():
    mesh = (
        (p(0, 0), p(1, 0), p(1, 1)),
        (p(0, 0), p(1, 1), p(0, 1)),
    )
    result = arrange_triangle_mesh_globally(mesh, ())
    assert len(result.vertices) == 5
    assert len(result.faces) == 2
    shared = [edge for edge in result.edges if len(edge.incident_face_ids) == 2]
    assert len(shared) == 1
    assert result.adjacent_face_pairs == ((0, 1),)
    assert all(report.area_conserved for report in result.coverage_reports)


def test_global_multi_facet_split_preserves_exact_coordinates_and_source_coverage():
    mesh = (
        (p(0, 0), p(2, 0), p(0, 2)),
        (p(2, 0), p(2, 2), p(0, 2)),
    )
    result = arrange_triangle_mesh_globally(mesh, (plane_x(1),))
    assert len(result.coverage_reports) == 2
    assert all(report.area_conserved for report in result.coverage_reports)
    assert all(type(value) is Fraction for vertex in result.vertices
               for value in vertex.point)
    assert len(result.faces) > len(mesh)


def test_global_resource_limits_fail_closed():
    with pytest.raises(InvalidModelError, match="max_fragments"):
        arrange_triangle_mesh_globally(((p(0, 0), p(2, 0), p(0, 2)),),
                                       (plane_x(1),), max_fragments=1)
    with pytest.raises(InvalidModelError, match="max_edges"):
        arrange_triangle_mesh_globally(((p(0, 0), p(1, 0), p(0, 1)),),
                                       (), max_edges=2)


def test_global_identity_does_not_tolerance_weld_nearby_coordinates():
    mesh = (
        (p(0, 0), p(1, 0), p(0, 1)),
        ((F(0), F(0), F(0)), (F(1), F(0), F(0)),
         (F(0), F(1) + F(1, 10**12), F(0))),
    )
    result = arrange_triangle_mesh_globally(mesh, ())
    points = {vertex.point for vertex in result.vertices}
    assert len(result.vertices) == 4
    assert p(0, 1) in points
    assert (F(0), F(1) + F(1, 10**12), F(0)) in points


def test_non_exact_or_degenerate_source_is_rejected():
    with pytest.raises(InvalidModelError, match="exact Fraction"):
        arrange_triangle_mesh_globally((((0.0, 0.0, 0.0), p(1, 0), p(0, 1)),), ())
    with pytest.raises(InvalidModelError, match="non-degenerate"):
        arrange_triangle_mesh_globally(((p(0, 0), p(1, 1), p(2, 2)),), ())


def test_global_topology_reports_exact_t_junction_candidates():
    mesh = (
        (p(0, 0), p(2, 0), p(0, 2)),
        (p(1, 0), p(1, -1), p(2, -1)),
    )
    result = arrange_triangle_mesh_globally(mesh, ())
    point_ids = {vertex.point: vertex.vertex_id for vertex in result.vertices}
    expected = (point_ids[p(0, 0)], point_ids[p(2, 0)], point_ids[p(1, 0)])
    assert expected in result.t_junctions


def test_global_topology_scan_fails_closed_at_budget():
    mesh = ((p(0, 0), p(2, 0), p(0, 2)),)
    with pytest.raises(InvalidModelError, match="max_topology_checks"):
        arrange_triangle_mesh_globally(mesh, (), max_topology_checks=1)


def test_global_edge_registry_subdivides_long_edge_for_cross_facet_adjacency():
    # Face 0 has one long edge (0,0)-(2,0). Face 1 uses the two exact
    # subsegments through (1,0); all three edge records must share incidence.
    mesh = (
        (p(0, 0), p(2, 0), p(0, 2)),
        (p(0, 0), p(1, 0), p(0, -1)),
        (p(1, 0), p(2, 0), p(2, -1)),
    )
    result = arrange_triangle_mesh_globally(mesh, ())
    ids = {vertex.point: vertex.vertex_id for vertex in result.vertices}
    left = tuple(sorted((ids[p(0, 0)], ids[p(1, 0)])))
    right = tuple(sorted((ids[p(1, 0)], ids[p(2, 0)])))
    by_edge = {edge.vertex_ids: edge.incident_face_ids for edge in result.edges}
    assert tuple(sorted(result.faces[i].source_triangle_index for i in by_edge[left])) == (0, 1)
    assert tuple(sorted(result.faces[i].source_triangle_index for i in by_edge[right])) == (0, 2)
    assert left not in result.boundary_edge_ids
    assert right not in result.boundary_edge_ids
    assert (ids[p(0, 0)], ids[p(2, 0)], ids[p(1, 0)]) in result.t_junctions
    assert len(result.faces) > 3
    assert len(result.fragments) == len(result.faces)
    # The returned face set is conforming: no registered vertex lies strictly
    # inside any returned face edge.
    for edge in result.edges:
        first = result.vertices[edge.vertex_ids[0]].point
        second = result.vertices[edge.vertex_ids[1]].point
        direction = tuple(second[i] - first[i] for i in range(3))
        length_squared = sum((direction[i] * direction[i] for i in range(3)), F(0))
        for candidate in result.vertices:
            if candidate.point in (first, second):
                continue
            offset = tuple(candidate.point[i] - first[i] for i in range(3))
            cross = (
                direction[1] * offset[2] - direction[2] * offset[1],
                direction[2] * offset[0] - direction[0] * offset[2],
                direction[0] * offset[1] - direction[1] * offset[0],
            )
            projection = sum((direction[i] * offset[i] for i in range(3)), F(0))
            assert cross != (F(0), F(0), F(0)) or not (0 < projection < length_squared)
