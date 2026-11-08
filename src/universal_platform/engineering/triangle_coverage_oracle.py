"""Independent exact-rational coverage oracle for coplanar triangle partitions.

The oracle projects a source triangle to a non-degenerate coordinate plane,
then uses exact convex polygon clipping and shoelace area. It certifies
coverage only when every fragment is contained in the source, pairwise
interior intersections have zero area, and the fragment-area sum equals the
source area. No tolerance or floating-point arithmetic is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from .errors import InvalidModelError
from .triangle_fragment_arrangement import RationalPoint3, RationalTriangle3

Point2 = tuple[Fraction, Fraction]


@dataclass(frozen=True, slots=True)
class ExactCoverageResult:
    source_area: Fraction
    fragment_area_sum: Fraction
    outside_fragment_indices: tuple[int, ...]
    overlapping_fragment_pairs: tuple[tuple[int, int], ...]
    duplicate_fragment_pairs: tuple[tuple[int, int], ...]
    pairwise_checks: int
    certified: bool


def _cross2(a: Point2, b: Point2, c: Point2) -> Fraction:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _project(point: RationalPoint3, drop_axis: int) -> Point2:
    axes = tuple(axis for axis in range(3) if axis != drop_axis)
    return (point[axes[0]], point[axes[1]])


def _signed_double_area(poly: Sequence[Point2]) -> Fraction:
    if len(poly) < 3:
        return Fraction(0)
    return sum((poly[i][0] * poly[(i + 1) % len(poly)][1]
                - poly[(i + 1) % len(poly)][0] * poly[i][1]
                for i in range(len(poly))), Fraction(0))


def _clip_convex(subject: Sequence[Point2], clip: Sequence[Point2]) -> list[Point2]:
    output = list(subject)
    clip_poly = list(clip)
    if _signed_double_area(clip_poly) < 0:
        clip_poly.reverse()
    for edge_index, edge_start in enumerate(clip_poly):
        edge_end = clip_poly[(edge_index + 1) % len(clip_poly)]
        input_poly = output
        output = []
        if not input_poly:
            break
        previous = input_poly[-1]
        previous_side = _cross2(edge_start, edge_end, previous)
        for current in input_poly:
            current_side = _cross2(edge_start, edge_end, current)
            if (previous_side >= 0) != (current_side >= 0):
                ratio = previous_side / (previous_side - current_side)
                output.append((
                    previous[0] + ratio * (current[0] - previous[0]),
                    previous[1] + ratio * (current[1] - previous[1]),
                ))
            if current_side >= 0:
                output.append(current)
            previous, previous_side = current, current_side
        compact: list[Point2] = []
        for point in output:
            if not compact or compact[-1] != point:
                compact.append(point)
        if len(compact) > 1 and compact[0] == compact[-1]:
            compact.pop()
        output = compact
    return output


def _area(poly: Sequence[Point2]) -> Fraction:
    return abs(_signed_double_area(poly)) / 2


def _project_triangle(triangle: RationalTriangle3, drop_axis: int) -> tuple[Point2, Point2, Point2]:
    projected = tuple(_project(point, drop_axis) for point in triangle)
    if _area(projected) == 0:
        raise InvalidModelError("coverage oracle received degenerate projected triangle")
    return projected  # type: ignore[return-value]


def certify_triangle_partition(
    source: RationalTriangle3,
    fragments: Sequence[RationalTriangle3],
    *,
    max_pairwise_checks: int = 1_000_000,
) -> ExactCoverageResult:
    """Certify an exact non-overlapping partition of one source triangle."""
    if (isinstance(max_pairwise_checks, bool) or not isinstance(max_pairwise_checks, int)
            or max_pairwise_checks < 1):
        raise InvalidModelError("max_pairwise_checks must be a positive integer")
    count = len(fragments)
    checks = count + count * (count - 1) // 2
    if checks > max_pairwise_checks:
        raise InvalidModelError("coverage oracle exceeded max_pairwise_checks")
    a, b, c = source
    normal = (
        (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
        (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
        (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]),
    )
    drop_axis = max(range(3), key=lambda axis: abs(normal[axis]))
    if normal[drop_axis] == 0:
        raise InvalidModelError("coverage oracle source triangle is degenerate")
    source_2d = _project_triangle(source, drop_axis)
    source_area = _area(source_2d)
    projected = [_project_triangle(fragment, drop_axis) for fragment in fragments]
    areas = [_area(triangle) for triangle in projected]
    outside = tuple(
        index for index, triangle in enumerate(projected)
        if _area(_clip_convex(triangle, source_2d)) != areas[index]
    )
    overlaps: list[tuple[int, int]] = []
    duplicates: list[tuple[int, int]] = []
    for first in range(count):
        for second in range(first + 1, count):
            if areas[first] == areas[second] and set(projected[first]) == set(projected[second]):
                duplicates.append((first, second))
            if _area(_clip_convex(projected[first], projected[second])) > 0:
                overlaps.append((first, second))
    fragment_sum = sum(areas, Fraction(0))
    certified = not outside and not overlaps and fragment_sum == source_area
    return ExactCoverageResult(
        source_area, fragment_sum, outside, tuple(overlaps), tuple(duplicates),
        checks, certified,
    )
