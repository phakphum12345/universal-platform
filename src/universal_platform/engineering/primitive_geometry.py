"""CAD-neutral analytic primitives and deterministic geometry model.

This is an offline geometry foundation, not a B-rep CAD kernel, mesh engine or
manufacturability validator.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import product
from math import isfinite, pi, sqrt
from typing import Any, ClassVar
import re

from .errors import InvalidModelError
from .frame_graph import FrameGraph
from .geometry import BoundingBox, Box, Cylinder, Vec3
from .quantity import LENGTH, Quantity

_ID = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")


def _validate_identity(solid_id: str, frame_id: str, unit: str) -> None:
    if not isinstance(solid_id, str) or not _ID.fullmatch(solid_id):
        raise InvalidModelError("solid_id must be a stable lowercase identifier")
    if not isinstance(frame_id, str) or not frame_id.strip():
        raise InvalidModelError("solid frame_id is required")
    if not isinstance(unit, str) or not unit:
        raise InvalidModelError("solid length_unit is required")
    try:
        quantity = Quantity.of(1.0, unit)
    except Exception as exc:
        raise InvalidModelError(f"Unsupported solid length unit: {unit}") from exc
    if quantity.dimension != LENGTH:
        raise InvalidModelError("solid length_unit must have length dimension")


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise InvalidModelError(f"{label} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class Vec2:
    x: float
    y: float

    def __post_init__(self) -> None:
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(float(v))
               for v in (self.x, self.y)):
            raise InvalidModelError("2D profile coordinates must be finite numeric values")

def _polygon_signed_area(points: tuple[Vec2, ...]) -> float:
    origin = points[0]
    return sum(
        (points[i].x-origin.x)*(points[(i+1)%len(points)].y-origin.y) -
        (points[(i+1)%len(points)].x-origin.x)*(points[i].y-origin.y)
        for i in range(1, len(points)-1)
    ) / 2.0


def _validate_simple_loop(points: tuple[Vec2, ...], label: str) -> None:
    if not isinstance(points, tuple) or len(points) < 3:
        raise InvalidModelError(f"{label} requires at least three immutable Vec2 points")
    if any(not isinstance(point, Vec2) for point in points):
        raise InvalidModelError(f"{label} points must be Vec2 records")
    keys = tuple((point.x, point.y) for point in points)
    if len(keys) != len(set(keys)):
        raise InvalidModelError(f"{label} cannot contain duplicate vertices")
    count = len(points)
    for i in range(count):
        a, b = points[i], points[(i+1) % count]
        for j in range(i+1, count):
            if j == i+1 or (i == 0 and j == count-1):
                continue
            if _segments_intersect(a, b, points[j], points[(j+1) % count]):
                raise InvalidModelError(f"{label} must be a simple non-self-intersecting polygon")
    scale = max(
        max(point.x for point in points) - min(point.x for point in points),
        max(point.y for point in points) - min(point.y for point in points),
    )
    if scale <= 0 or abs(_polygon_signed_area(points)) <= 1e-12 * scale**2:
        raise InvalidModelError(f"{label} area must be positive")


def _point_in_polygon(point: Vec2, polygon: tuple[Vec2, ...]) -> bool:
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current.y > point.y) != (previous.y > point.y):
            crossing_x = (previous.x-current.x) * (point.y-current.y) / (previous.y-current.y) + current.x
            if point.x < crossing_x:
                inside = not inside
        previous = current
    return inside


def _loops_intersect(first: tuple[Vec2, ...], second: tuple[Vec2, ...]) -> bool:
    return any(
        _segments_intersect(first[i], first[(i+1) % len(first)],
                            second[j], second[(j+1) % len(second)])
        for i in range(len(first)) for j in range(len(second))
    )



def _cross2(a: Vec2, b: Vec2, c: Vec2) -> float:
    return (b.x-a.x)*(c.y-a.y) - (b.y-a.y)*(c.x-a.x)


def _on_segment(a: Vec2, b: Vec2, p: Vec2, eps: float = 1e-12) -> bool:
    return (min(a.x,b.x)-eps <= p.x <= max(a.x,b.x)+eps and
            min(a.y,b.y)-eps <= p.y <= max(a.y,b.y)+eps)


def _segments_intersect(a: Vec2, b: Vec2, c: Vec2, d: Vec2) -> bool:
    scale = max(abs(b.x-a.x), abs(b.y-a.y), abs(d.x-c.x), abs(d.y-c.y),
                abs(c.x-a.x), abs(c.y-a.y), 1e-300)
    cross_eps, coordinate_eps = 1e-12*scale*scale, 1e-12*scale
    o1, o2, o3, o4 = _cross2(a,b,c), _cross2(a,b,d), _cross2(c,d,a), _cross2(c,d,b)
    eps = cross_eps
    if ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps)) and (
        (o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps)
    ):
        return True
    return ((abs(o1) <= eps and _on_segment(a,b,c,coordinate_eps)) or
            (abs(o2) <= eps and _on_segment(a,b,d,coordinate_eps)) or
            (abs(o3) <= eps and _on_segment(c,d,a,coordinate_eps)) or
            (abs(o4) <= eps and _on_segment(c,d,b,coordinate_eps)))


@dataclass(frozen=True, slots=True)
class ExtrudedProfileSolid:
    solid_id: str
    frame_id: str
    profile: tuple[Vec2, ...]
    height: float
    length_unit: str = "m"
    holes: tuple[tuple[Vec2, ...], ...] = ()

    KIND: ClassVar[str] = "EXTRUDED_PROFILE"

    def __post_init__(self) -> None:
        _validate_identity(self.solid_id, self.frame_id, self.length_unit)
        _validate_simple_loop(self.profile, "extruded outer profile")
        if not isinstance(self.holes, tuple):
            raise InvalidModelError("extruded profile holes must be an immutable tuple of loops")
        for index, hole in enumerate(self.holes):
            _validate_simple_loop(hole, f"extruded profile hole {index}")
            if _loops_intersect(self.profile, hole) or not all(_point_in_polygon(point, self.profile) for point in hole):
                raise InvalidModelError("extruded profile holes must lie strictly inside the outer profile without touching it")
        for i, first in enumerate(self.holes):
            for second in self.holes[i+1:]:
                if (_loops_intersect(first, second) or _point_in_polygon(first[0], second)
                        or _point_in_polygon(second[0], first)):
                    raise InvalidModelError("extruded profile holes must not intersect, overlap or nest")
        scale = max(
            max(point.x for point in self.profile) - min(point.x for point in self.profile),
            max(point.y for point in self.profile) - min(point.y for point in self.profile),
        )
        if self.area <= 1e-12 * scale**2:
            raise InvalidModelError("extruded profile net area must be positive")
        height = _number(self.height, "extrusion height")
        if height <= 0:
            raise InvalidModelError("extrusion height must be positive")
        object.__setattr__(self, "height", height)

    @property
    def area(self) -> float:
        return abs(_polygon_signed_area(self.profile)) - sum(abs(_polygon_signed_area(hole)) for hole in self.holes)

    @property
    def perimeter(self) -> float:
        loops = (self.profile, *self.holes)
        return sum(
            sqrt((loop[(i+1)%len(loop)].x-loop[i].x)**2 +
                 (loop[(i+1)%len(loop)].y-loop[i].y)**2)
            for loop in loops for i in range(len(loop))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.KIND, "solid_id": self.solid_id, "frame_id": self.frame_id,
            "profile": [{"x": point.x, "y": point.y} for point in self.profile],
            "height": self.height, "unit": self.length_unit,
            **({"holes": [[{"x": point.x, "y": point.y} for point in hole] for hole in self.holes]} if self.holes else {}),
        }


@dataclass(frozen=True, slots=True)
class BoxSolid:
    solid_id: str
    frame_id: str
    dimensions: Vec3
    length_unit: str = "m"

    KIND: ClassVar[str] = "BOX"

    def __post_init__(self) -> None:
        _validate_identity(self.solid_id, self.frame_id, self.length_unit)
        if not isinstance(self.dimensions, Vec3):
            raise InvalidModelError("BoxSolid dimensions must be Vec3")
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               for value in (self.dimensions.x, self.dimensions.y, self.dimensions.z)):
            raise InvalidModelError("BoxSolid dimensions must be numeric")
        Box(self.dimensions.x, self.dimensions.y, self.dimensions.z)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.KIND,
            "solid_id": self.solid_id,
            "frame_id": self.frame_id,
            "dimensions": {
                "x": self.dimensions.x,
                "y": self.dimensions.y,
                "z": self.dimensions.z,
                "unit": self.length_unit,
            },
        }


@dataclass(frozen=True, slots=True)
class CylinderSolid:
    solid_id: str
    frame_id: str
    radius: float
    height: float
    length_unit: str = "m"

    KIND: ClassVar[str] = "CYLINDER"

    def __post_init__(self) -> None:
        _validate_identity(self.solid_id, self.frame_id, self.length_unit)
        radius = _number(self.radius, "cylinder radius")
        height = _number(self.height, "cylinder height")
        Cylinder(radius, height)
        object.__setattr__(self, "radius", radius)
        object.__setattr__(self, "height", height)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.KIND,
            "solid_id": self.solid_id,
            "frame_id": self.frame_id,
            "radius": self.radius,
            "height": self.height,
            "unit": self.length_unit,
        }


SolidPrimitive = BoxSolid | CylinderSolid | ExtrudedProfileSolid


@dataclass(frozen=True, slots=True)
class FramedBounds3:
    frame_id: str
    bounds: BoundingBox
    length_unit: str


@dataclass(frozen=True, slots=True)
class PrimitiveGeometryModel:
    frame_graph: FrameGraph
    solids: tuple[SolidPrimitive, ...]

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.frame_graph, FrameGraph):
            raise InvalidModelError("frame_graph must be a FrameGraph")
        if not isinstance(self.solids, tuple) or any(
            not isinstance(item, (BoxSolid, CylinderSolid, ExtrudedProfileSolid)) for item in self.solids
        ):
            raise InvalidModelError("solids must be an immutable tuple of supported primitives")
        solid_ids = tuple(item.solid_id for item in self.solids)
        if len(solid_ids) != len(set(solid_ids)):
            raise InvalidModelError("solid IDs must be unique")
        for solid in self.solids:
            if solid.frame_id not in self.frame_graph.frames:
                raise InvalidModelError(f"solid references an unknown frame: {solid.frame_id}")
            if self.frame_graph.length_unit is not None and solid.length_unit != self.frame_graph.length_unit:
                raise InvalidModelError("solid and FrameGraph length units must match")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "frame_graph": self.frame_graph.to_dict(),
            "solids": [item.to_dict() for item in sorted(self.solids, key=lambda item: item.solid_id)],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PrimitiveGeometryModel":
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "frame_graph", "solids"}:
            raise InvalidModelError("PrimitiveGeometryModel snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("Unsupported PrimitiveGeometryModel schema_version")
        if not isinstance(value["frame_graph"], Mapping):
            raise InvalidModelError("frame_graph must be a FrameGraph snapshot")
        raw_solids = value["solids"]
        if not isinstance(raw_solids, (list, tuple)):
            raise InvalidModelError("solids must be an array")
        graph = FrameGraph.from_dict(value["frame_graph"])
        solids: list[SolidPrimitive] = []
        for raw in raw_solids:
            if not isinstance(raw, Mapping):
                raise InvalidModelError("solid snapshot must be an object")
            kind = raw.get("kind")
            if kind == BoxSolid.KIND:
                if set(raw) != {"kind", "solid_id", "frame_id", "dimensions"}:
                    raise InvalidModelError("BoxSolid snapshot has missing or unknown fields")
                dims = raw["dimensions"]
                if not isinstance(dims, Mapping) or set(dims) != {"x", "y", "z", "unit"}:
                    raise InvalidModelError("BoxSolid dimensions require x, y, z and unit")
                solids.append(BoxSolid(
                    raw["solid_id"], raw["frame_id"],
                    Vec3(_number(dims["x"], "box x"), _number(dims["y"], "box y"), _number(dims["z"], "box z")),
                    dims["unit"],
                ))
            elif kind == CylinderSolid.KIND:
                if set(raw) != {"kind", "solid_id", "frame_id", "radius", "height", "unit"}:
                    raise InvalidModelError("CylinderSolid snapshot has missing or unknown fields")
                solids.append(CylinderSolid(
                    raw["solid_id"], raw["frame_id"],
                    _number(raw["radius"], "cylinder radius"),
                    _number(raw["height"], "cylinder height"),
                    raw["unit"],
                ))
            elif kind == ExtrudedProfileSolid.KIND:
                required = {"kind", "solid_id", "frame_id", "profile", "height", "unit"}
                if not required.issubset(raw) or set(raw) - (required | {"holes"}):
                    raise InvalidModelError("ExtrudedProfileSolid snapshot has missing or unknown fields")
                raw_profile = raw["profile"]
                if not isinstance(raw_profile, (list, tuple)):
                    raise InvalidModelError("extruded profile must be an array")
                points = []
                for point in raw_profile:
                    if not isinstance(point, Mapping) or set(point) != {"x", "y"}:
                        raise InvalidModelError("profile point requires x and y")
                    points.append(Vec2(_number(point["x"], "profile x"), _number(point["y"], "profile y")))
                raw_holes = raw.get("holes", [])
                if not isinstance(raw_holes, (list, tuple)):
                    raise InvalidModelError("extruded profile holes must be an array of loops")
                holes = []
                for raw_hole in raw_holes:
                    if not isinstance(raw_hole, (list, tuple)):
                        raise InvalidModelError("extruded profile hole must be an array")
                    hole_points = []
                    for point in raw_hole:
                        if not isinstance(point, Mapping) or set(point) != {"x", "y"}:
                            raise InvalidModelError("profile hole point requires x and y")
                        hole_points.append(Vec2(_number(point["x"], "hole x"), _number(point["y"], "hole y")))
                    holes.append(tuple(hole_points))
                solids.append(ExtrudedProfileSolid(
                    raw["solid_id"], raw["frame_id"], tuple(points),
                    _number(raw["height"], "extrusion height"), raw["unit"], tuple(holes),
                ))
            else:
                raise InvalidModelError(f"Unsupported primitive solid kind: {kind}")
        return cls(graph, tuple(solids))

    def _solid(self, solid_id: str) -> SolidPrimitive:
        for solid in self.solids:
            if solid.solid_id == solid_id:
                return solid
        raise InvalidModelError(f"Unknown solid: {solid_id}")

    def volume(self, solid_id: str) -> Quantity:
        solid = self._solid(solid_id)
        factor = Quantity.of(1.0, solid.length_unit).si_value
        if isinstance(solid, BoxSolid):
            value = Box(solid.dimensions.x, solid.dimensions.y, solid.dimensions.z).volume
        elif isinstance(solid, CylinderSolid):
            value = Cylinder(solid.radius, solid.height).volume
        else:
            value = solid.area * solid.height
        return Quantity(value * factor**3, (3, 0, 0, 0, 0), "m3")

    def surface_area(self, solid_id: str) -> Quantity:
        solid = self._solid(solid_id)
        factor = Quantity.of(1.0, solid.length_unit).si_value
        if isinstance(solid, BoxSolid):
            x, y, z = solid.dimensions.x, solid.dimensions.y, solid.dimensions.z
            value = 2.0 * (x*y + x*z + y*z)
        elif isinstance(solid, CylinderSolid):
            value = 2.0 * pi * solid.radius * (solid.radius + solid.height)
        else:
            value = 2.0 * solid.area + solid.perimeter * solid.height
        return Quantity(value * factor**2, (2, 0, 0, 0, 0), "m2")

    def bounding_box(self, solid_id: str, target_frame: str) -> FramedBounds3:
        solid = self._solid(solid_id)
        transform = self.frame_graph.transform_between(solid.frame_id, target_frame)
        if target_frame == solid.frame_id:
            if isinstance(solid, BoxSolid):
                local = Box(solid.dimensions.x, solid.dimensions.y, solid.dimensions.z).bounds
            elif isinstance(solid, CylinderSolid):
                local = Cylinder(solid.radius, solid.height).bounds
            else:
                xs = [point.x for point in solid.profile]
                ys = [point.y for point in solid.profile]
                local = BoundingBox(Vec3(min(xs), min(ys), 0.0), Vec3(max(xs), max(ys), solid.height))
            return FramedBounds3(target_frame, local, solid.length_unit)
        if transform.length_unit != solid.length_unit:
            raise InvalidModelError("solid and transform length units do not match")
        if isinstance(solid, BoxSolid):
            xs, ys, zs = (0.0, solid.dimensions.x), (0.0, solid.dimensions.y), (0.0, solid.dimensions.z)
            points = [transform.apply_point(Vec3(x, y, z)) for x, y, z in product(xs, ys, zs)]
            minimum = Vec3(min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))
            maximum = Vec3(max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))
        elif isinstance(solid, ExtrudedProfileSolid):
            points = [
                transform.apply_point(Vec3(point.x, point.y, z))
                for point in solid.profile for z in (0.0, solid.height)
            ]
            minimum = Vec3(min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))
            maximum = Vec3(max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))
        else:
            axis = (transform.rotation[0][2], transform.rotation[1][2], transform.rotation[2][2])
            center = transform.apply_point(Vec3(0.0, 0.0, solid.height / 2.0))
            half_height = solid.height / 2.0
            extents = tuple(
                abs(component) * half_height + solid.radius * sqrt(max(0.0, 1.0 - component**2))
                for component in axis
            )
            minimum = Vec3(center.x-extents[0], center.y-extents[1], center.z-extents[2])
            maximum = Vec3(center.x+extents[0], center.y+extents[1], center.z+extents[2])
        return FramedBounds3(target_frame, BoundingBox(minimum, maximum), solid.length_unit)
