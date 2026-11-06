"""Dependency-free 2D Boolean operations for convex polygon profiles.

Results are deterministic convex-cell decompositions. This is not a general
polygon/B-rep kernel; concave loops, arcs and hole-bearing profiles fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import ClassVar

from .errors import InvalidModelError
from .primitive_geometry import Vec2


class ProfileBooleanOperation(str, Enum):
    UNION = "UNION"
    INTERSECTION = "INTERSECTION"
    DIFFERENCE = "DIFFERENCE"


def _cross(a: Vec2, b: Vec2, p: Vec2) -> float:
    return (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x)


def _area(points: tuple[Vec2, ...]) -> float:
    origin = points[0]
    return sum(
        (points[i].x - origin.x) * (points[(i + 1) % len(points)].y - origin.y)
        - (points[(i + 1) % len(points)].x - origin.x) * (points[i].y - origin.y)
        for i in range(1, len(points) - 1)
    ) / 2.0


def _scale(points: tuple[Vec2, ...]) -> float:
    return max(
        max(point.x for point in points) - min(point.x for point in points),
        max(point.y for point in points) - min(point.y for point in points),
        1e-300,
    )


def _clean(points: list[Vec2], coordinate_eps: float, area_eps: float) -> tuple[Vec2, ...]:
    cleaned: list[Vec2] = []
    for point in points:
        if not cleaned or ((point.x - cleaned[-1].x) ** 2 + (point.y - cleaned[-1].y) ** 2) > coordinate_eps**2:
            cleaned.append(point)
    if len(cleaned) > 1 and ((cleaned[0].x - cleaned[-1].x) ** 2 + (cleaned[0].y - cleaned[-1].y) ** 2) <= coordinate_eps**2:
        cleaned.pop()
    if len(cleaned) < 3:
        return ()
    result = tuple(cleaned)
    if abs(_area(result)) <= area_eps:
        return ()
    if _area(result) < 0:
        result = tuple(reversed(result))
    # Stable cyclic origin; preserve the CCW boundary order.
    start = min(range(len(result)), key=lambda i: (result[i].x, result[i].y))
    return result[start:] + result[:start]


def _validate_convex_loop(points: tuple[Vec2, ...], label: str) -> tuple[Vec2, ...]:
    if not isinstance(points, tuple) or len(points) < 3 or any(not isinstance(p, Vec2) for p in points):
        raise InvalidModelError(f"{label} requires at least three immutable Vec2 points")
    if any(not isfinite(float(v)) for p in points for v in (p.x, p.y)):
        raise InvalidModelError(f"{label} coordinates must be finite")
    if len({(p.x, p.y) for p in points}) != len(points):
        raise InvalidModelError(f"{label} cannot contain duplicate vertices")
    scale = _scale(points)
    cross_eps = 1e-12 * scale * scale
    area_eps = 1e-12 * scale * scale
    if abs(_area(points)) <= area_eps:
        raise InvalidModelError(f"{label} must have non-zero area")
    signs = []
    for index in range(len(points)):
        value = _cross(points[index], points[(index + 1) % len(points)], points[(index + 2) % len(points)])
        if abs(value) > cross_eps:
            signs.append(value > 0)
    if not signs or any(sign != signs[0] for sign in signs):
        raise InvalidModelError(f"{label} must be a convex simple polygon")
    return points if _area(points) > 0 else tuple(reversed(points))


@dataclass(frozen=True, slots=True)
class ProfileLoop:
    profile_id: str
    points: tuple[Vec2, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise InvalidModelError("profile_id must be a non-empty string")
        object.__setattr__(self, "points", _validate_convex_loop(self.points, "profile"))


@dataclass(frozen=True, slots=True)
class ProfileBooleanResult:
    schema_version: str
    operation: ProfileBooleanOperation
    first_profile_id: str
    second_profile_id: str
    regions: tuple[tuple[Vec2, ...], ...]

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise InvalidModelError("unsupported ProfileBooleanResult schema_version")
        if not isinstance(self.operation, ProfileBooleanOperation):
            raise InvalidModelError("operation must be a ProfileBooleanOperation")
        if not isinstance(self.regions, tuple):
            raise InvalidModelError("regions must be an immutable tuple")
        if any(not isinstance(loop, tuple) or len(loop) < 3 or any(not isinstance(p, Vec2) for p in loop)
               for loop in self.regions):
            raise InvalidModelError("each result region must be an immutable polygon loop")

    @property
    def area(self) -> float:
        return sum(abs(_area(region)) for region in self.regions)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "operation": self.operation.value,
            "first_profile_id": self.first_profile_id,
            "second_profile_id": self.second_profile_id,
            "regions": [[{"x": point.x, "y": point.y} for point in region] for region in self.regions],
            "area": self.area,
            "region_count": len(self.regions),
            "limitations": [
                "Inputs must be convex simple polygon loops without arcs or holes.",
                "Output is a deterministic convex-cell decomposition; adjacent cells are not dissolved.",
                "Floating-point predicates use scale-relative tolerances.",
                "No B-rep, mesh, manufacturing, physical validation or certification is implied.",
            ],
        }


def _clip_half_plane(subject: tuple[Vec2, ...], a: Vec2, b: Vec2,
                     keep_left: bool, coordinate_eps: float, cross_eps: float) -> tuple[Vec2, ...]:
    if not subject:
        return ()
    output: list[Vec2] = []
    previous = subject[-1]
    previous_distance = _cross(a, b, previous)
    previous_inside = previous_distance >= -cross_eps if keep_left else previous_distance <= cross_eps
    for current in subject:
        current_distance = _cross(a, b, current)
        current_inside = current_distance >= -cross_eps if keep_left else current_distance <= cross_eps
        if current_inside != previous_inside:
            denominator = previous_distance - current_distance
            if abs(denominator) > cross_eps:
                t = previous_distance / denominator
                output.append(Vec2(
                    previous.x + t * (current.x - previous.x),
                    previous.y + t * (current.y - previous.y),
                ))
        if current_inside:
            output.append(current)
        previous, previous_distance, previous_inside = current, current_distance, current_inside
    return _clean(output, coordinate_eps, cross_eps)


def _clip(subject: tuple[Vec2, ...], clipper: tuple[Vec2, ...], keep_inside: bool,
          coordinate_eps: float, cross_eps: float) -> tuple[Vec2, ...]:
    result = subject
    for index, a in enumerate(clipper):
        result = _clip_half_plane(result, a, clipper[(index + 1) % len(clipper)],
                                  keep_inside, coordinate_eps, cross_eps)
        if not result:
            break
    return result


def _difference(subject: tuple[Vec2, ...], clipper: tuple[Vec2, ...],
                coordinate_eps: float, cross_eps: float) -> tuple[tuple[Vec2, ...], ...]:
    remainder = subject
    pieces: list[tuple[Vec2, ...]] = []
    for index, a in enumerate(clipper):
        b = clipper[(index + 1) % len(clipper)]
        outside = _clip_half_plane(remainder, a, b, False, coordinate_eps, cross_eps)
        if outside:
            pieces.append(outside)
        remainder = _clip_half_plane(remainder, a, b, True, coordinate_eps, cross_eps)
        if not remainder:
            break
    return tuple(pieces)


def _region_key(region: tuple[Vec2, ...]) -> tuple[float, float, float, float, float, tuple[tuple[float, float], ...]]:
    return (
        min(p.x for p in region), min(p.y for p in region),
        max(p.x for p in region), max(p.y for p in region),
        abs(_area(region)), tuple((p.x, p.y) for p in region),
    )


def boolean_profiles(operation: ProfileBooleanOperation, first: ProfileLoop,
                     second: ProfileLoop) -> ProfileBooleanResult:
    """Apply a convex-polygon Boolean operation and return deterministic convex cells."""
    if not isinstance(operation, ProfileBooleanOperation):
        raise InvalidModelError("operation must be a ProfileBooleanOperation")
    if not isinstance(first, ProfileLoop) or not isinstance(second, ProfileLoop):
        raise InvalidModelError("first and second must be ProfileLoop records")

    combined = first.points + second.points
    scale = _scale(combined)
    coordinate_eps = 1e-12 * scale
    cross_eps = 1e-12 * scale * scale

    if operation is ProfileBooleanOperation.INTERSECTION:
        regions = (_clip(first.points, second.points, True, coordinate_eps, cross_eps),)
    elif operation is ProfileBooleanOperation.DIFFERENCE:
        regions = _difference(first.points, second.points, coordinate_eps, cross_eps)
    else:
        # A union is represented as A plus a non-overlapping partition of B\A.
        regions = (first.points,) + _difference(second.points, first.points, coordinate_eps, cross_eps)

    normalized = []
    for region in regions:
        cleaned = _clean(list(region), coordinate_eps, cross_eps)
        if cleaned:
            normalized.append(cleaned)
    normalized.sort(key=_region_key)
    return ProfileBooleanResult(
        ProfileBooleanResult.SCHEMA_VERSION, operation, first.profile_id, second.profile_id,
        tuple(normalized),
    )
