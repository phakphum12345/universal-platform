from fractions import Fraction

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.triangle_coverage_oracle import (
    certify_triangle_partition,
    coplanar_contact_is_covered,
    coplanar_triangle_intersection_geometry,
    coplanar_triangle_intersection_kind,
)

F = Fraction


def p(x, y, z=0):
    return (F(x), F(y), F(z))


SOURCE = (p(0, 0), p(2, 0), p(0, 2))
LEFT_LOWER = (p(0, 0), p(1, 0), p(1, 1))
LEFT_UPPER = (p(0, 0), p(1, 1), p(0, 2))
RIGHT = (p(1, 0), p(2, 0), p(1, 1))


def test_oracle_certifies_exact_partition():
    result = certify_triangle_partition(SOURCE, (LEFT_LOWER, LEFT_UPPER, RIGHT))
    assert result.certified
    assert result.source_area == F(2)
    assert result.fragment_area_sum == F(2)
    assert result.outside_fragment_indices == ()
    assert result.overlapping_fragment_pairs == ()
    assert result.duplicate_fragment_pairs == ()
    assert result.non_coplanar_fragment_indices == ()


def test_oracle_detects_duplicate_and_overlapping_fragments():
    result = certify_triangle_partition(SOURCE, (LEFT_LOWER, LEFT_LOWER, RIGHT))
    assert not result.certified
    assert (0, 1) in result.duplicate_fragment_pairs
    assert (0, 1) in result.overlapping_fragment_pairs


def test_oracle_detects_gap_even_when_fragments_are_individually_inside():
    result = certify_triangle_partition(SOURCE, (LEFT_LOWER, RIGHT))
    assert not result.certified
    assert result.outside_fragment_indices == ()
    assert result.fragment_area_sum < result.source_area


def test_oracle_detects_fragment_outside_source():
    outside = (p(2, 0), p(3, 0), p(2, 1))
    result = certify_triangle_partition(SOURCE, (outside,))
    assert not result.certified
    assert result.outside_fragment_indices == (0,)


def test_oracle_rejects_projectively_identical_but_non_coplanar_partition():
    # All three fragments have the same XY projection as a valid partition,
    # but are translated off the source plane. A 2D-only oracle would certify
    # this invalid 3D coverage.
    shifted = tuple(
        tuple((point[0], point[1], F(1)) for point in triangle)
        for triangle in (LEFT_LOWER, LEFT_UPPER, RIGHT)
    )
    result = certify_triangle_partition(SOURCE, shifted)
    assert not result.certified
    assert result.non_coplanar_fragment_indices == (0, 1, 2)


def test_oracle_rejects_degenerate_or_non_exact_fragment_input():
    with pytest.raises(InvalidModelError, match="non-degenerate"):
        certify_triangle_partition(SOURCE, ((p(0, 0), p(1, 0), p(2, 0)),))
    with pytest.raises(InvalidModelError, match="exact Fraction"):
        certify_triangle_partition(SOURCE, (((0.0, 0.0, 0.0), p(1, 0), p(0, 1)),))


def test_oracle_fails_closed_when_pairwise_budget_is_exceeded():
    with pytest.raises(InvalidModelError, match="max_pairwise_checks"):
        certify_triangle_partition(SOURCE, (LEFT_LOWER, LEFT_UPPER, RIGHT),
                                   max_pairwise_checks=2)


def test_oracle_fails_closed_when_rational_coordinate_budget_is_exceeded():
    huge = F(1 << 20)
    oversized = ((p(0, 0), p(1, 0), (F(0), F(1), huge)),)
    with pytest.raises(InvalidModelError, match="max_coordinate_bits"):
        certify_triangle_partition(SOURCE, oversized, max_coordinate_bits=8)


def test_coplanar_contact_must_be_covered_by_the_positive_area_overlay_closure():
    overlap = ((F(0), F(0)), (F(2), F(0)), (F(2), F(2)), (F(0), F(2)))
    assert coplanar_contact_is_covered(((F(0), F(0)), (F(0), F(2))), (overlap,))
    assert coplanar_contact_is_covered(((F(1), F(1)),), (overlap,))
    assert not coplanar_contact_is_covered(
        ((F(-1), F(0)), (F(1), F(0))), (overlap,)
    )
    assert not coplanar_contact_is_covered(
        ((F(3), F(3)),), (overlap,)
    )


def test_coplanar_intersection_geometry_preserves_contact_segment():
    first = (p(0, 0), p(2, 0), p(0, 2))
    second = (p(2, 0), p(2, 2), p(0, 2))
    geometry = coplanar_triangle_intersection_geometry(first, second)
    assert geometry is not None
    _, polygon = geometry
    assert len(set(polygon)) >= 2
    assert coplanar_contact_is_covered(
        polygon,
        (((F(0), F(0)), (F(2), F(0)), (F(2), F(2)), (F(0), F(2))),),
    )



def test_oracle_preflights_fragment_count_and_pair_work_before_geometry_validation():
    malformed = object()
    with pytest.raises(InvalidModelError, match="max_pairwise_checks"):
        certify_triangle_partition(
            SOURCE, (malformed, malformed, malformed), max_pairwise_checks=2
        )
    with pytest.raises(InvalidModelError, match="max_fragments"):
        certify_triangle_partition(SOURCE, (malformed, malformed), max_fragments=1)


def test_oracle_enforces_aggregate_rational_bit_budget():
    with pytest.raises(InvalidModelError, match="aggregate rational bit budget"):
        certify_triangle_partition(
            SOURCE, (LEFT_LOWER,), max_aggregate_rational_bits=8
        )


def test_coplanar_triangle_intersection_classifies_point_and_edge_contacts():
    first = (p(0, 0), p(1, 0), p(0, 1))
    point_touch = (p(1, 0), p(2, 0), p(2, 1))
    edge_touch = (p(0, 0), p(1, 0), p(1, -1))
    assert coplanar_triangle_intersection_kind(first, point_touch) == "CONTACT"
    assert coplanar_triangle_intersection_kind(first, edge_touch) == "CONTACT"


def test_coplanar_triangle_intersection_detects_extremely_narrow_exact_overlap():
    epsilon = F(1, 1 << 80)
    first = (p(0, 0), p(1, 0), p(0, 1))
    sliver = (
        (F(1) - epsilon, F(0), F(0)),
        (F(1), F(0), F(0)),
        (F(1) - epsilon, epsilon, F(0)),
    )
    assert coplanar_triangle_intersection_kind(first, sliver) == "AREA_OVERLAP"
    geometry = coplanar_triangle_intersection_geometry(first, sliver)
    assert geometry is not None
    assert len(geometry[1]) >= 3


def test_contact_closure_accepts_adjacent_overlay_intervals_but_rejects_gap():
    left = ((F(0), F(0)), (F(1), F(0)), (F(1), F(1)), (F(0), F(1)))
    right = ((F(1), F(0)), (F(2), F(0)), (F(2), F(1)), (F(1), F(1)))
    segment = ((F(0), F(1, 2)), (F(2), F(1, 2)))
    assert coplanar_contact_is_covered(segment, (left, right))

    gap_left = ((F(0), F(0)), (F(9, 10), F(0)),
                (F(9, 10), F(1)), (F(0), F(1)))
    gap_right = ((F(11, 10), F(0)), (F(2), F(0)),
                 (F(2), F(1)), (F(11, 10), F(1)))
    assert not coplanar_contact_is_covered(segment, (gap_left, gap_right))



def test_coplanar_contact_requires_the_complete_input_to_be_a_point_or_segment():
    overlap = ((F(0), F(0)), (F(2), F(0)), (F(2), F(2)), (F(0), F(2)))
    # The farthest pair is fully covered, but the third point is not on that
    # segment. It is not a valid point/segment contact and must fail closed.
    malformed = ((F(0), F(0)), (F(2), F(0)), (F(1), F(1)))
    assert not coplanar_contact_is_covered(malformed, (overlap,))


def test_coplanar_contact_accepts_multi_fragment_edge_closure_and_shared_vertex():
    left = ((F(0), F(0)), (F(1), F(0)), (F(1), F(1)), (F(0), F(1)))
    middle = ((F(1), F(0)), (F(2), F(0)), (F(2), F(1)), (F(1), F(1)))
    right = ((F(2), F(0)), (F(3), F(0)), (F(3), F(1)), (F(2), F(1)))
    edge = ((F(0), F(1, 2)), (F(1), F(1, 2)),
            (F(2), F(1, 2)), (F(3), F(1, 2)))
    assert coplanar_contact_is_covered(edge, (right, left, middle))
    assert coplanar_contact_is_covered(((F(1), F(1)),), (left, middle))


def test_coplanar_contact_rejects_disconnected_overlay_with_uncovered_interval():
    left = ((F(0), F(0)), (F(1), F(0)), (F(1), F(1)), (F(0), F(1)))
    right = ((F(2), F(0)), (F(3), F(0)), (F(3), F(1)), (F(2), F(1)))
    edge = ((F(0), F(1, 2)), (F(3), F(1, 2)))
    assert not coplanar_contact_is_covered(edge, (left, right))



def test_oracle_certifies_partition_with_shared_interior_vertex_and_zero_area_contacts():
    center = p(F(1, 2), F(1, 2))
    fragments = (
        (SOURCE[0], SOURCE[1], center),
        (SOURCE[1], SOURCE[2], center),
        (SOURCE[2], SOURCE[0], center),
    )
    result = certify_triangle_partition(SOURCE, fragments)
    assert result.certified
    assert result.source_area == F(2)
    assert result.fragment_area_sum == F(2)
    assert result.overlapping_fragment_pairs == ()
    assert result.duplicate_fragment_pairs == ()


def test_oracle_rejects_disconnected_fragment_regions_even_without_overlap_or_outside_points():
    first = (p(0, 0), p(F(1, 2), 0), p(0, F(1, 2)))
    second = (p(1, 0), p(F(3, 2), 0), p(1, F(1, 2)))
    result = certify_triangle_partition(SOURCE, (first, second))
    assert not result.certified
    assert result.outside_fragment_indices == ()
    assert result.overlapping_fragment_pairs == ()
    assert result.fragment_area_sum < result.source_area
