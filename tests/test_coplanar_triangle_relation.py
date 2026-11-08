from fractions import Fraction

from universal_platform.engineering.triangle_coverage_oracle import (
    coplanar_triangle_intersection_kind,
)

F = Fraction


def p(x, y, z=0):
    return (F(x), F(y), F(z))


def test_exact_coplanar_triangle_relation_distinguishes_overlap_contact_disjoint():
    source = (p(0, 0), p(2, 0), p(0, 2))
    overlap = (p(0, 0), p(2, 0), p(2, 2))
    contact = (p(0, 0), p(2, 0), p(2, -1))
    disjoint = (p(3, 0), p(4, 0), p(3, 1))
    non_coplanar = (p(0, 0, 1), p(2, 0, 1), p(0, 2, 1))
    assert coplanar_triangle_intersection_kind(source, overlap) == "AREA_OVERLAP"
    assert coplanar_triangle_intersection_kind(source, contact) == "CONTACT"
    assert coplanar_triangle_intersection_kind(source, disjoint) == "DISJOINT"
    assert coplanar_triangle_intersection_kind(source, non_coplanar) == "NON_COPLANAR"
