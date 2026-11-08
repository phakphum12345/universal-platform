from fractions import Fraction

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.triangle_coverage_oracle import certify_triangle_partition

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
