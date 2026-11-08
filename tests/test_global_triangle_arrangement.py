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
    # Two coplanar source facets share the exact diagonal (0,0)-(1,1).
    mesh = (
        (p(0, 0), p(1, 0), p(1, 1)),
        (p(0, 0), p(1, 1), p(0, 1)),
    )
    result = arrange_triangle_mesh_globally(mesh, ())
    assert len(result.vertices) == 4
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
