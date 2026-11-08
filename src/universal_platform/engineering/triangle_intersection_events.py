"""Exact transverse triangle-pair intersection segment extraction.

This is a bounded arrangement primitive for a future faceted Boolean kernel.
It reports exact rational segment endpoints for proper transverse crossings;
it does not split triangles, classify solid membership, or assemble solids.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, ClassVar, Mapping

from .errors import InvalidModelError
from .mesh import TriangleMesh
from .mesh_intersection import (
    _POINT,
    _cross,
    _dot,
    _edge_plane_points,
    _inside3,
    _pair_intersection,
    _q,
    _sub,
)

_RATIONAL_POINT = tuple[Fraction, Fraction, Fraction]
_RESULT_FIELDS = {
    "schema_version", "algorithm_version", "triangle_a", "triangle_b",
    "start", "end",
}


@dataclass(frozen=True, slots=True)
class TriangleIntersectionSegment:
    """Canonical exact-rational segment shared by two source triangles."""

    triangle_a: int
    triangle_b: int
    start: _RATIONAL_POINT
    end: _RATIONAL_POINT

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    ALGORITHM_VERSION: ClassVar[str] = "exact-transverse-triangle-segment-v1"

    def __post_init__(self) -> None:
        if (isinstance(self.triangle_a, bool) or not isinstance(self.triangle_a, int)
                or isinstance(self.triangle_b, bool) or not isinstance(self.triangle_b, int)
                or self.triangle_a < 0 or self.triangle_b <= self.triangle_a):
            raise InvalidModelError("triangle indices must be ordered non-negative integers")
        for label, point in (("start", self.start), ("end", self.end)):
            if (not isinstance(point, tuple) or len(point) != 3
                    or any(not isinstance(value, Fraction) for value in point)):
                raise InvalidModelError(f"{label} must be a 3D tuple of exact Fractions")
        if self.start >= self.end:
            raise InvalidModelError("segment endpoints must be distinct and lexicographically ordered")

    def to_dict(self) -> dict[str, Any]:
        def encode(point: _RATIONAL_POINT) -> list[list[int]]:
            return [[value.numerator, value.denominator] for value in point]

        return {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm_version": self.ALGORITHM_VERSION,
            "triangle_a": self.triangle_a,
            "triangle_b": self.triangle_b,
            "start": encode(self.start),
            "end": encode(self.end),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TriangleIntersectionSegment":
        if not isinstance(value, Mapping) or set(value) != _RESULT_FIELDS:
            raise InvalidModelError("TriangleIntersectionSegment has missing or unknown fields")
        if (value["schema_version"] != cls.SCHEMA_VERSION
                or value["algorithm_version"] != cls.ALGORITHM_VERSION):
            raise InvalidModelError("unsupported triangle intersection segment version")

        def decode(raw: object, label: str) -> _RATIONAL_POINT:
            if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                raise InvalidModelError(f"{label} must contain three rational coordinates")
            coordinates = []
            for pair in raw:
                if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                        or isinstance(pair[0], bool) or not isinstance(pair[0], int)
                        or isinstance(pair[1], bool) or not isinstance(pair[1], int)
                        or pair[1] <= 0):
                    raise InvalidModelError(f"{label} contains an invalid rational coordinate")
                rational = Fraction(pair[0], pair[1])
                if (rational.numerator, rational.denominator) != (pair[0], pair[1]):
                    raise InvalidModelError(f"{label} rational coordinates must be canonical")
                coordinates.append(rational)
            return tuple(coordinates)  # type: ignore[return-value]

        return cls(
            triangle_a=value["triangle_a"],
            triangle_b=value["triangle_b"],
            start=decode(value["start"], "start"),
            end=decode(value["end"], "end"),
        )


def extract_transverse_triangle_intersection(
    mesh: TriangleMesh, triangle_a: int, triangle_b: int,
) -> TriangleIntersectionSegment | None:
    """Return the exact segment for a proper transverse triangle crossing.

    Disjoint pairs return None. Coplanar overlap, point/edge contact, duplicate
    facets and other non-transverse classifications fail closed with
    InvalidModelError. The input mesh is read-only and need not be a closed
    surface because this primitive operates on a single triangle pair.
    """
    if not isinstance(mesh, TriangleMesh):
        raise InvalidModelError("mesh must be a TriangleMesh")
    if (isinstance(triangle_a, bool) or not isinstance(triangle_a, int)
            or isinstance(triangle_b, bool) or not isinstance(triangle_b, int)):
        raise InvalidModelError("triangle indices must be integers")
    if triangle_a == triangle_b:
        raise InvalidModelError("triangle pair must contain two distinct triangles")
    if not (0 <= triangle_a < len(mesh.triangles)
            and 0 <= triangle_b < len(mesh.triangles)):
        raise InvalidModelError("triangle index is outside the source mesh")
    first, second = sorted((triangle_a, triangle_b))
    face_a, face_b = mesh.triangles[first], mesh.triangles[second]
    if len(set(face_a)) != 3 or len(set(face_b)) != 3:
        raise InvalidModelError("triangle pair contains repeated vertex indices")

    def exact_triangle(face: tuple[int, int, int]) -> tuple[_POINT, _POINT, _POINT]:
        return tuple(
            (_q(mesh.vertices[index].x), _q(mesh.vertices[index].y), _q(mesh.vertices[index].z))
            for index in face
        )  # type: ignore[return-value]

    a, b = exact_triangle(face_a), exact_triangle(face_b)
    normal_a = _cross(_sub(a[1], a[0]), _sub(a[2], a[0]))
    normal_b = _cross(_sub(b[1], b[0]), _sub(b[2], b[0]))
    zero = (Fraction(0), Fraction(0), Fraction(0))
    if normal_a == zero or normal_b == zero:
        raise InvalidModelError("triangle pair contains a degenerate triangle")

    classification = _pair_intersection(mesh, first, second)
    if classification is None:
        return None
    if classification != "PROPER_INTERSECTION":
        raise InvalidModelError(
            f"triangle pair classification {classification} is outside the transverse segment profile"
        )

    points = _edge_plane_points(a, b) | _edge_plane_points(b, a)
    if len(points) != 2:
        raise InvalidModelError("proper transverse intersection did not produce exactly two endpoints")
    start, end = sorted(points)
    if start == end:
        raise InvalidModelError("transverse intersection segment has zero length")

    midpoint = tuple((start[axis] + end[axis]) / 2 for axis in range(3))
    if not (_inside3(midpoint, a, strict=True) and _inside3(midpoint, b, strict=True)):
        raise InvalidModelError("intersection segment is not strictly interior to both triangles")
    for point in (start, end):
        if (_dot(normal_a, _sub(point, a[0])) != 0
                or _dot(normal_b, _sub(point, b[0])) != 0
                or not _inside3(point, a) or not _inside3(point, b)):
            raise InvalidModelError("intersection endpoint failed exact plane/triangle verification")

    return TriangleIntersectionSegment(first, second, start, end)
