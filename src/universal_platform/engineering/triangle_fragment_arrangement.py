"""Exact-rational multi-plane arrangement for individual source triangles.

This bounded primitive subdivides independent triangles by an ordered set of
planes. It does not construct a global mesh arrangement, weld vertices across
source facets, classify solid membership, or assemble Boolean shells.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from .errors import InvalidModelError

RationalPoint3 = tuple[Fraction, Fraction, Fraction]
RationalTriangle3 = tuple[RationalPoint3, RationalPoint3, RationalPoint3]


@dataclass(frozen=True, slots=True)
class RationalPlane:
    """A plane identified by three exact-rational, non-collinear points."""

    plane_index: int
    vertices: RationalTriangle3

    def __post_init__(self) -> None:
        if (isinstance(self.plane_index, bool) or not isinstance(self.plane_index, int)
                or self.plane_index < 0):
            raise InvalidModelError("plane_index must be a non-negative integer")
        _validate_triangle(self.vertices, "plane")


@dataclass(frozen=True, slots=True)
class RationalTriangleFragment:
    """An oriented exact triangle and its ordered half-space provenance."""

    source_triangle_index: int
    side_signature: tuple[str, ...]
    vertices: RationalTriangle3

    def __post_init__(self) -> None:
        if (isinstance(self.source_triangle_index, bool)
                or not isinstance(self.source_triangle_index, int)
                or self.source_triangle_index < 0):
            raise InvalidModelError("source_triangle_index must be a non-negative integer")
        if not isinstance(self.side_signature, tuple) or any(
            side not in {"POSITIVE", "NEGATIVE", "COPLANAR"} for side in self.side_signature
        ):
            raise InvalidModelError("side_signature contains an unsupported side")
        _validate_triangle(self.vertices, "fragment")


def _validate_point(point: object, label: str) -> None:
    if (not isinstance(point, tuple) or len(point) != 3
            or any(not isinstance(value, Fraction) for value in point)):
        raise InvalidModelError(f"{label} must be a 3D tuple of exact Fractions")


def _sub(a: RationalPoint3, b: RationalPoint3) -> RationalPoint3:
    return tuple(a[i] - b[i] for i in range(3))  # type: ignore[return-value]


def _cross(a: RationalPoint3, b: RationalPoint3) -> RationalPoint3:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a: RationalPoint3, b: RationalPoint3) -> Fraction:
    return sum((a[i] * b[i] for i in range(3)), Fraction(0))


def _validate_triangle(vertices: object, label: str) -> None:
    if not isinstance(vertices, tuple) or len(vertices) != 3:
        raise InvalidModelError(f"{label} must contain exactly three vertices")
    for point in vertices:
        _validate_point(point, label)
    if len(set(vertices)) != 3:
        raise InvalidModelError(f"{label} vertices must be distinct")
    if _cross(_sub(vertices[1], vertices[0]), _sub(vertices[2], vertices[0])) == (0, 0, 0):
        raise InvalidModelError(f"{label} triangle must be non-degenerate")


def _dedupe(points: list[RationalPoint3]) -> list[RationalPoint3]:
    result: list[RationalPoint3] = []
    for point in points:
        if not result or point != result[-1]:
            result.append(point)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result


def _clip(vertices: RationalTriangle3, plane_vertices: RationalTriangle3,
          normal: RationalPoint3, keep_positive: bool) -> list[RationalPoint3]:
    output: list[RationalPoint3] = []
    previous = vertices[-1]
    d_previous = _dot(normal, _sub(previous, plane_vertices[0]))
    previous_inside = d_previous >= 0 if keep_positive else d_previous <= 0
    for current in vertices:
        d_current = _dot(normal, _sub(current, plane_vertices[0]))
        current_inside = d_current >= 0 if keep_positive else d_current <= 0
        if previous_inside != current_inside:
            ratio = d_previous / (d_previous - d_current)
            output.append(tuple(
                previous[axis] + ratio * (current[axis] - previous[axis])
                for axis in range(3)
            ))  # type: ignore[arg-type]
        if current_inside:
            output.append(current)
        previous, d_previous, previous_inside = current, d_current, current_inside
    return _dedupe(output)


def _triangulate(polygon: list[RationalPoint3], source_normal: RationalPoint3
                 ) -> list[RationalTriangle3]:
    if len(polygon) < 3:
        return []
    # Canonical anchor makes identical convex arrangement cells triangulate
    # identically even when they originate from different source-face cycles.
    anchor_index = polygon.index(min(polygon))
    polygon = polygon[anchor_index:] + polygon[:anchor_index]
    result: list[RationalTriangle3] = []
    for index in range(1, len(polygon) - 1):
        triangle = (polygon[0], polygon[index], polygon[index + 1])
        normal = _cross(_sub(triangle[1], triangle[0]), _sub(triangle[2], triangle[0]))
        orientation = _dot(normal, source_normal)
        if orientation == 0:
            continue
        if orientation < 0:
            raise InvalidModelError("fragment winding differs from its source triangle")
        result.append(triangle)
    return result


def _area2(triangle: RationalTriangle3, reference_normal: RationalPoint3) -> Fraction:
    return _dot(_cross(_sub(triangle[1], triangle[0]),
                       _sub(triangle[2], triangle[0])), reference_normal)


def _check_bit_limit(triangle: RationalTriangle3, max_coordinate_bits: int) -> None:
    for point in triangle:
        for value in point:
            if (abs(value.numerator).bit_length() > max_coordinate_bits
                    or value.denominator.bit_length() > max_coordinate_bits):
                raise InvalidModelError("rational coordinate exceeded max_coordinate_bits")


def arrange_triangles_by_planes(
    triangles: Iterable[RationalTriangle3],
    planes: Iterable[RationalPlane],
    *,
    max_fragments: int = 4096,
    max_coordinate_bits: int = 4096,
) -> tuple[RationalTriangleFragment, ...]:
    """Split source triangles by ordered planes using exact Fraction arithmetic.

    Planes are applied in caller order. A plane that does not strictly separate
    a fragment appends POSITIVE, NEGATIVE, or COPLANAR provenance without
    changing its geometry. Strictly separating planes clip both half-spaces,
    triangulate deterministically, preserve source winding, and verify exact
    area conservation. Resource limits are fail-closed.
    """
    if (isinstance(max_fragments, bool) or not isinstance(max_fragments, int)
            or max_fragments < 1):
        raise InvalidModelError("max_fragments must be a positive integer")
    if (isinstance(max_coordinate_bits, bool) or not isinstance(max_coordinate_bits, int)
            or max_coordinate_bits < 1):
        raise InvalidModelError("max_coordinate_bits must be a positive integer")
    source_items = tuple(triangles)
    plane_items = tuple(planes)
    if len({plane.plane_index for plane in plane_items}) != len(plane_items):
        raise InvalidModelError("plane indices must be unique")
    if not source_items:
        raise InvalidModelError("at least one source triangle is required")
    if len(source_items) > max_fragments:
        raise InvalidModelError("source triangle count exceeded max_fragments")

    fragments: list[RationalTriangleFragment] = []
    for source_index, source in enumerate(source_items):
        _validate_triangle(source, "source")
        _check_bit_limit(source, max_coordinate_bits)
        fragments.append(RationalTriangleFragment(source_index, (), source))

    for plane in plane_items:
        normal = _cross(_sub(plane.vertices[1], plane.vertices[0]),
                        _sub(plane.vertices[2], plane.vertices[0]))
        next_fragments: list[RationalTriangleFragment] = []
        for fragment in fragments:
            distances = tuple(_dot(normal, _sub(point, plane.vertices[0]))
                              for point in fragment.vertices)
            has_positive = any(value > 0 for value in distances)
            has_negative = any(value < 0 for value in distances)
            if not (has_positive and has_negative):
                side = ("COPLANAR" if not has_positive and not has_negative
                        else "POSITIVE" if has_positive else "NEGATIVE")
                next_fragments.append(RationalTriangleFragment(
                    fragment.source_triangle_index,
                    fragment.side_signature + (side,), fragment.vertices,
                ))
                continue

            source_normal = _cross(_sub(fragment.vertices[1], fragment.vertices[0]),
                                   _sub(fragment.vertices[2], fragment.vertices[0]))
            original_area2 = _dot(source_normal, source_normal)
            positive = _triangulate(_clip(fragment.vertices, plane.vertices, normal, True),
                                    source_normal)
            negative = _triangulate(_clip(fragment.vertices, plane.vertices, normal, False),
                                    source_normal)
            if not positive or not negative:
                raise InvalidModelError("strict plane split produced an empty half-space")
            if sum((_area2(item, source_normal) for item in positive + negative),
                   Fraction(0)) != original_area2:
                raise InvalidModelError("multi-plane split failed exact area conservation")
            for side, pieces in (("POSITIVE", positive), ("NEGATIVE", negative)):
                for piece in pieces:
                    _check_bit_limit(piece, max_coordinate_bits)
                    next_fragments.append(RationalTriangleFragment(
                        fragment.source_triangle_index,
                        fragment.side_signature + (side,), piece,
                    ))
            if len(next_fragments) > max_fragments:
                raise InvalidModelError("arrangement exceeded max_fragments")
        fragments = next_fragments
    if len(fragments) > max_fragments:
        raise InvalidModelError("arrangement exceeded max_fragments")
    return tuple(fragments)
