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


SolidPrimitive = BoxSolid | CylinderSolid


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
            not isinstance(item, (BoxSolid, CylinderSolid)) for item in self.solids
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
        else:
            value = Cylinder(solid.radius, solid.height).volume
        return Quantity(value * factor**3, (3, 0, 0, 0, 0), "m3")

    def surface_area(self, solid_id: str) -> Quantity:
        solid = self._solid(solid_id)
        factor = Quantity.of(1.0, solid.length_unit).si_value
        if isinstance(solid, BoxSolid):
            x, y, z = solid.dimensions.x, solid.dimensions.y, solid.dimensions.z
            value = 2.0 * (x*y + x*z + y*z)
        else:
            value = 2.0 * pi * solid.radius * (solid.radius + solid.height)
        return Quantity(value * factor**2, (2, 0, 0, 0, 0), "m2")

    def bounding_box(self, solid_id: str, target_frame: str) -> FramedBounds3:
        solid = self._solid(solid_id)
        transform = self.frame_graph.transform_between(solid.frame_id, target_frame)
        if target_frame == solid.frame_id:
            local = (
                Box(solid.dimensions.x, solid.dimensions.y, solid.dimensions.z).bounds
                if isinstance(solid, BoxSolid)
                else Cylinder(solid.radius, solid.height).bounds
            )
            return FramedBounds3(target_frame, local, solid.length_unit)
        if transform.length_unit != solid.length_unit:
            raise InvalidModelError("solid and transform length units do not match")
        if isinstance(solid, BoxSolid):
            xs, ys, zs = (0.0, solid.dimensions.x), (0.0, solid.dimensions.y), (0.0, solid.dimensions.z)
            points = [transform.apply_point(Vec3(x, y, z)) for x, y, z in product(xs, ys, zs)]
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
