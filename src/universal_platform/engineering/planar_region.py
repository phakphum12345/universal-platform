"""Validated CAD-neutral planar regions using exact binary64 predicates.

Coordinates are interpreted as their exact represented IEEE-754 values.
This model validates boundaries and holes; it does not perform Booleans.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from json import dumps
from typing import Any, ClassVar, Mapping
import re

from .errors import InvalidModelError
from .primitive_geometry import Vec2
from .quantity import LENGTH, Quantity

PRECISION_POLICY = "binary64-exact-rational-v1"
MAX_PLANAR_BOUNDARY_EDGES = 2048
_REGION_ID = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_FIELDS = {"schema_version", "region_id", "frame_id", "length_unit",
           "precision_policy", "outer_boundary", "holes"}


def _q(value: float) -> Fraction:
    return Fraction.from_float(float(value))


def _point(point: Vec2) -> tuple[Fraction, Fraction]:
    return _q(point.x), _q(point.y)


def _orient(a: Vec2, b: Vec2, c: Vec2) -> Fraction:
    ax, ay = _point(a)
    bx, by = _point(b)
    cx, cy = _point(c)
    return (bx-ax)*(cy-ay)-(by-ay)*(cx-ax)


def _on_segment(a: Vec2, b: Vec2, p: Vec2) -> bool:
    if _orient(a, b, p) != 0:
        return False
    return (min(_q(a.x), _q(b.x)) <= _q(p.x) <= max(_q(a.x), _q(b.x))
            and min(_q(a.y), _q(b.y)) <= _q(p.y) <= max(_q(a.y), _q(b.y)))


def _segments_intersect(a: Vec2, b: Vec2, c: Vec2, d: Vec2) -> bool:
    o1, o2, o3, o4 = _orient(a, b, c), _orient(a, b, d), _orient(c, d, a), _orient(c, d, b)
    if ((o1 > 0 > o2) or (o2 > 0 > o1)) and ((o3 > 0 > o4) or (o4 > 0 > o3)):
        return True
    return ((o1 == 0 and _on_segment(a, b, c))
            or (o2 == 0 and _on_segment(a, b, d))
            or (o3 == 0 and _on_segment(c, d, a))
            or (o4 == 0 and _on_segment(c, d, b)))


def _signed_area2(points: tuple[Vec2, ...]) -> Fraction:
    total = Fraction(0)
    for index, point in enumerate(points):
        following = points[(index+1) % len(points)]
        x1, y1 = _point(point)
        x2, y2 = _point(following)
        total += x1*y2-x2*y1
    return total


def _point_location(point: Vec2, polygon: tuple[Vec2, ...]) -> str:
    winding = 0
    for index, start in enumerate(polygon):
        end = polygon[(index+1) % len(polygon)]
        if _on_segment(start, end, point):
            return "BOUNDARY"
        if _q(start.y) <= _q(point.y):
            if _q(end.y) > _q(point.y) and _orient(start, end, point) > 0:
                winding += 1
        elif _q(end.y) <= _q(point.y) and _orient(start, end, point) < 0:
            winding -= 1
    return "INSIDE" if winding else "OUTSIDE"


def _canonical_loop(raw: Any, label: str, *, counter_clockwise: bool) -> tuple[Vec2, ...]:
    if not isinstance(raw, tuple) or len(raw) < 3:
        raise InvalidModelError(f"{label} requires at least three immutable Vec2 points")
    if any(not isinstance(point, Vec2) for point in raw):
        raise InvalidModelError(f"{label} points must be Vec2 records")
    keys = tuple(_point(point) for point in raw)
    if len(set(keys)) != len(keys):
        raise InvalidModelError(f"{label} cannot contain duplicate or repeated closing vertices")
    if len(raw) > MAX_PLANAR_BOUNDARY_EDGES:
        raise InvalidModelError(f"{label} exceeds the {MAX_PLANAR_BOUNDARY_EDGES}-edge resource limit")
    area2 = _signed_area2(raw)
    if area2 == 0:
        raise InvalidModelError(f"{label} must have non-zero exact signed area")
    count = len(raw)
    for index in range(count):
        previous, current, following = raw[index-1], raw[index], raw[(index+1) % count]
        if _orient(previous, current, following) == 0:
            ax, ay = _point(previous)
            bx, by = _point(current)
            cx, cy = _point(following)
            if (bx-ax)*(cx-bx)+(by-ay)*(cy-by) < 0:
                raise InvalidModelError(f"{label} contains overlapping adjacent edges")
        for other in range(index+1, count):
            if other == index+1 or (index == 0 and other == count-1):
                continue
            if _segments_intersect(current, raw[(index+1) % count],
                                   raw[other], raw[(other+1) % count]):
                raise InvalidModelError(f"{label} must be a simple polygon without touching or crossing edges")
    points = raw if ((area2 > 0) == counter_clockwise) else tuple(reversed(raw))
    start = min(range(len(points)), key=lambda i: (_q(points[i].x), _q(points[i].y)))
    return points[start:] + points[:start]


def _loops_intersect(first: tuple[Vec2, ...], second: tuple[Vec2, ...]) -> bool:
    return any(
        _segments_intersect(first[i], first[(i+1) % len(first)],
                            second[j], second[(j+1) % len(second)])
        for i in range(len(first)) for j in range(len(second))
    )


@dataclass(frozen=True, slots=True)
class PlanarRegion:
    """One connected planar region: CCW outer loop and zero or more CW holes."""

    region_id: str
    frame_id: str
    length_unit: str
    outer_boundary: tuple[Vec2, ...]
    holes: tuple[tuple[Vec2, ...], ...] = ()
    precision_policy: str = PRECISION_POLICY

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    MAX_BOUNDARY_EDGES: ClassVar[int] = MAX_PLANAR_BOUNDARY_EDGES

    def __post_init__(self) -> None:
        if not isinstance(self.region_id, str) or not _REGION_ID.fullmatch(self.region_id):
            raise InvalidModelError("region_id must be a stable lowercase identifier")
        if not isinstance(self.frame_id, str) or not self.frame_id.strip():
            raise InvalidModelError("frame_id is required")
        if not isinstance(self.length_unit, str) or not self.length_unit:
            raise InvalidModelError("length_unit is required")
        try:
            if Quantity.of(1.0, self.length_unit).dimension != LENGTH:
                raise InvalidModelError("length_unit must have length dimension")
        except Exception as exc:
            if isinstance(exc, InvalidModelError):
                raise
            raise InvalidModelError(f"Unsupported planar region length_unit: {self.length_unit}") from exc
        if self.precision_policy != PRECISION_POLICY:
            raise InvalidModelError("unsupported planar region precision_policy")
        outer = _canonical_loop(self.outer_boundary, "outer_boundary", counter_clockwise=True)
        if not isinstance(self.holes, tuple):
            raise InvalidModelError("holes must be an immutable tuple of boundaries")
        holes = tuple(_canonical_loop(hole, f"holes[{index}]", counter_clockwise=False)
                      for index, hole in enumerate(self.holes))
        edge_count = len(outer) + sum(len(hole) for hole in holes)
        if edge_count > MAX_PLANAR_BOUNDARY_EDGES:
            raise InvalidModelError(f"planar region exceeds the {MAX_PLANAR_BOUNDARY_EDGES}-edge total resource limit")
        for index, hole in enumerate(holes):
            if _loops_intersect(outer, hole):
                raise InvalidModelError(f"holes[{index}] touches or crosses the outer boundary")
            if any(_point_location(point, outer) != "INSIDE" for point in hole):
                raise InvalidModelError(f"holes[{index}] must be strictly inside the outer boundary")
            for previous_index, previous in enumerate(holes[:index]):
                if _loops_intersect(previous, hole):
                    raise InvalidModelError(f"holes[{index}] touches or crosses holes[{previous_index}]")
                if (_point_location(hole[0], previous) != "OUTSIDE"
                        or _point_location(previous[0], hole) != "OUTSIDE"):
                    raise InvalidModelError("holes cannot overlap or nest")
        object.__setattr__(self, "outer_boundary", outer)
        object.__setattr__(self, "holes", holes)

    @property
    def boundary_edge_count(self) -> int:
        return len(self.outer_boundary) + sum(len(hole) for hole in self.holes)

    @property
    def area_exact(self) -> Fraction:
        outer = abs(_signed_area2(self.outer_boundary)) / 2
        removed = sum(abs(_signed_area2(hole)) / 2 for hole in self.holes)
        return outer-removed

    @property
    def area(self) -> float:
        return float(self.area_exact)

    @property
    def canonical_sha256(self) -> str:
        encoded = dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return sha256(encoded.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        def boundary(points: tuple[Vec2, ...]) -> list[dict[str, float]]:
            return [{"x": float(point.x), "y": float(point.y)} for point in points]
        return {
            "schema_version": self.SCHEMA_VERSION,
            "region_id": self.region_id,
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "precision_policy": self.precision_policy,
            "outer_boundary": boundary(self.outer_boundary),
            "holes": [boundary(hole) for hole in self.holes],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PlanarRegion":
        if not isinstance(value, Mapping) or set(value) != _FIELDS:
            raise InvalidModelError("PlanarRegion snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("unsupported PlanarRegion schema_version")
        raw_outer, raw_holes = value["outer_boundary"], value["holes"]
        if not isinstance(raw_outer, (list, tuple)) or not isinstance(raw_holes, (list, tuple)):
            raise InvalidModelError("outer_boundary and holes must be arrays")
        def points(raw: Any, label: str) -> tuple[Vec2, ...]:
            if not isinstance(raw, (list, tuple)):
                raise InvalidModelError(f"{label} must be an array")
            result = []
            for point in raw:
                if not isinstance(point, Mapping) or set(point) != {"x", "y"}:
                    raise InvalidModelError(f"{label} point requires exactly x and y")
                result.append(Vec2(point["x"], point["y"]))
            return tuple(result)
        result = cls(
            region_id=value["region_id"], frame_id=value["frame_id"],
            length_unit=value["length_unit"],
            outer_boundary=points(raw_outer, "outer_boundary"),
            holes=tuple(points(hole, f"holes[{index}]") for index, hole in enumerate(raw_holes)),
            precision_policy=value["precision_policy"],
        )
        if result.to_dict() != dict(value):
            raise InvalidModelError("PlanarRegion snapshot is not in canonical normalized form")
        return result
