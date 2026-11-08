from copy import deepcopy
from fractions import Fraction

import pytest

from universal_platform.engineering import (
    TriangleIntersectionSegment,
    extract_transverse_triangle_intersection,
)
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh


def raw_pair(points, faces):
    return TriangleMesh(
        "pair.event", "world", "m", "BOX", "0" * 64,
        tuple(Vec3(*point) for point in points),
        tuple(tuple(face) for face in faces),
    )


def crossing_pair():
    return raw_pair(
        [
            (0, 0, 0), (2, 0, 0), (0, 2, 0),
            (1, -1, -1), (1, 2, -1), (1, 0, 1),
        ],
        [(0, 1, 2), (3, 4, 5)],
    )


def test_transverse_pair_returns_exact_canonical_segment():
    mesh = crossing_pair()
    before = mesh.to_dict()
    result = extract_transverse_triangle_intersection(mesh, 0, 1)

    assert result is not None
    assert result.triangle_a == 0
    assert result.triangle_b == 1
    assert result.start == (Fraction(1), Fraction(0), Fraction(0))
    assert result.end == (Fraction(1), Fraction(1), Fraction(0))
    assert mesh.to_dict() == before


def test_pair_order_does_not_change_segment_identity():
    mesh = crossing_pair()
    forward = extract_transverse_triangle_intersection(mesh, 0, 1)
    reverse = extract_transverse_triangle_intersection(mesh, 1, 0)
    assert forward == reverse


def test_disjoint_triangle_pair_returns_none():
    mesh = raw_pair(
        [
            (0, 0, 0), (1, 0, 0), (0, 1, 0),
            (3, 0, 0), (4, 0, 0), (3, 1, 0),
        ],
        [(0, 1, 2), (3, 4, 5)],
    )
    assert extract_transverse_triangle_intersection(mesh, 0, 1) is None


def test_coplanar_overlap_and_point_contact_fail_closed():
    overlap = raw_pair(
        [
            (0, 0, 0), (2, 0, 0), (0, 2, 0),
            (1, 0, 0), (3, 0, 0), (1, 2, 0),
        ],
        [(0, 1, 2), (3, 4, 5)],
    )
    with pytest.raises(InvalidModelError, match="COPLANAR_OVERLAP"):
        extract_transverse_triangle_intersection(overlap, 0, 1)

    contact = raw_pair(
        [
            (0, 0, 0), (2, 0, 0), (0, 2, 0),
            (2, 0, 0), (3, -1, 0), (3, 1, 0),
        ],
        [(0, 1, 2), (3, 4, 5)],
    )
    with pytest.raises(InvalidModelError, match="UNSHARED_CONTACT"):
        extract_transverse_triangle_intersection(contact, 0, 1)


def test_invalid_indices_and_degenerate_triangles_are_rejected():
    mesh = crossing_pair()
    for pair in ((0, 0), (0, 2), (True, 1), (-1, 1)):
        with pytest.raises(InvalidModelError):
            extract_transverse_triangle_intersection(mesh, *pair)

    degenerate = raw_pair(
        [(0, 0, 0), (1, 1, 1), (2, 2, 2), (0, 1, 0), (1, 0, 1), (0, 0, 1)],
        [(0, 1, 2), (3, 4, 5)],
    )
    with pytest.raises(InvalidModelError, match="degenerate"):
        extract_transverse_triangle_intersection(degenerate, 0, 1)


def test_segment_snapshot_is_strict_and_round_trips_exactly():
    result = extract_transverse_triangle_intersection(crossing_pair(), 0, 1)
    assert result is not None
    snapshot = result.to_dict()
    assert TriangleIntersectionSegment.from_dict(snapshot) == result

    malformed = deepcopy(snapshot)
    malformed["start"][0] = [2, 2]
    with pytest.raises(InvalidModelError, match="canonical"):
        TriangleIntersectionSegment.from_dict(malformed)

    malformed = deepcopy(snapshot)
    malformed["end"][0] = [1, 0]
    with pytest.raises(InvalidModelError, match="invalid rational"):
        TriangleIntersectionSegment.from_dict(malformed)

    malformed = dict(snapshot, extra=True)
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        TriangleIntersectionSegment.from_dict(malformed)


def test_segment_model_rejects_noncanonical_endpoint_order_and_equal_points():
    point = (Fraction(0), Fraction(0), Fraction(0))
    later = (Fraction(1), Fraction(0), Fraction(0))
    with pytest.raises(InvalidModelError):
        TriangleIntersectionSegment(0, 1, later, point)
    with pytest.raises(InvalidModelError):
        TriangleIntersectionSegment(0, 1, point, point)
