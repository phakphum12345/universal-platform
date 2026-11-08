from fractions import Fraction

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.triangle_fragment_arrangement import (
    RationalPlane,
    arrange_triangles_by_planes,
)

F = Fraction


def point(x, y, z=0):
    return (F(x), F(y), F(z))


def triangle():
    return (point(0, 0), point(2, 0), point(0, 2))


def vertical_plane(x):
    return RationalPlane(x, (point(x, -1, -1), point(x, 3, -1), point(x, 0, 1)))


def horizontal_plane(y):
    return RationalPlane(y + 10, (point(-1, y, -1), point(3, y, -1), point(0, y, 1)))


def signed_area2(item):
    a, b, c = item.vertices
    ux = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    vx = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (ux[1] * vx[2] - ux[2] * vx[1],
             ux[2] * vx[0] - ux[0] * vx[2],
             ux[0] * vx[1] - ux[1] * vx[0])
    return cross[2]


def test_two_planes_split_exactly_without_float_round_trip():
    result = arrange_triangles_by_planes(
        (triangle(),), (vertical_plane(1), horizontal_plane(1))
    )
    assert len(result) >= 3
    assert all(len(item.side_signature) == 2 for item in result)
    assert all(item.source_triangle_index == 0 for item in result)
    assert sum((signed_area2(item) for item in result), F(0)) == F(4)
    assert all(type(value) is Fraction for item in result
               for vertex in item.vertices for value in vertex)


def test_convex_arrangement_cell_triangulation_is_cycle_independent():
    a, b, c = triangle()
    planes = (vertical_plane(1), horizontal_plane(1))
    first = arrange_triangles_by_planes(((a, b, c),), planes)
    rotated = arrange_triangles_by_planes(((b, c, a),), planes)
    first_faces = {tuple(sorted(item.vertices)) for item in first}
    rotated_faces = {tuple(sorted(item.vertices)) for item in rotated}
    assert first_faces == rotated_faces


def test_ordered_plane_provenance_is_deterministic():
    planes = (vertical_plane(1), horizontal_plane(1))
    first = arrange_triangles_by_planes((triangle(),), planes)
    second = arrange_triangles_by_planes((triangle(),), planes)
    assert first == second
    assert all(item.side_signature[0] in {"POSITIVE", "NEGATIVE"} for item in first)


def test_non_separating_and_coplanar_planes_preserve_geometry():
    source = triangle()
    same_side = RationalPlane(4, (point(3, -1, -1), point(3, 3, -1), point(3, 0, 1)))
    coplanar = RationalPlane(5, (point(0, 0), point(2, 0), point(0, 2)))
    result = arrange_triangles_by_planes((source,), (same_side, coplanar))
    assert len(result) == 1
    assert result[0].vertices == source
    assert result[0].side_signature == ("NEGATIVE", "COPLANAR")


def test_resource_limits_and_invalid_exact_inputs_fail_closed():
    with pytest.raises(InvalidModelError, match="max_fragments"):
        arrange_triangles_by_planes((triangle(),), (vertical_plane(1),),
                                    max_fragments=1)
    with pytest.raises(InvalidModelError, match="max_coordinate_bits"):
        arrange_triangles_by_planes((triangle(),), (), max_coordinate_bits=1)
    huge_plane = RationalPlane(
        9, (point(1 << 20, -1, -1), point(1 << 20, 3, -1), point(1 << 20, 0, 1))
    )
    with pytest.raises(InvalidModelError, match="max_coordinate_bits"):
        arrange_triangles_by_planes((triangle(),), (huge_plane,), max_coordinate_bits=8)
    with pytest.raises(InvalidModelError, match="RationalPlane"):
        arrange_triangles_by_planes((triangle(),), (object(),))
    with pytest.raises(InvalidModelError, match="unique"):
        arrange_triangles_by_planes((triangle(),),
                                    (vertical_plane(1), vertical_plane(2 - 1)))
    with pytest.raises(InvalidModelError, match="exact Fractions"):
        arrange_triangles_by_planes((((0.0, 0.0, 0.0), point(1, 0), point(0, 1)),), ())


def test_degenerate_plane_is_rejected():
    with pytest.raises(InvalidModelError, match="non-degenerate"):
        RationalPlane(1, (point(0, 0), point(1, 1), point(2, 2)))
