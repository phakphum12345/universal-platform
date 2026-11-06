"""Frame-bound spatial points and displacement vectors.

These records carry a frame ID and explicit length unit. They are not general
force/velocity vectors or rigid-body poses.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

from .errors import InvalidModelError
from .frame_graph import FrameGraph
from .geometry import Vec3
from .quantity import LENGTH, Quantity


def _validate_frame_and_unit(frame_id: str, length_unit: str) -> None:
    if not isinstance(frame_id, str) or not frame_id.strip():
        raise InvalidModelError("frame_id must be a non-empty stable identifier")
    if not isinstance(length_unit, str) or not length_unit:
        raise InvalidModelError("length_unit is required")
    try:
        quantity = Quantity.of(1.0, length_unit)
    except Exception as exc:
        raise InvalidModelError(f"Unsupported spatial length unit: {length_unit}") from exc
    if quantity.dimension != LENGTH:
        raise InvalidModelError("Spatial coordinates require a length unit")


def _read_snapshot(value: Mapping[str, Any], expected_kind: str) -> tuple[str, Vec3, str]:
    expected = {"schema_version", "kind", "frame_id", "coordinates"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise InvalidModelError("Framed coordinate snapshot has missing or unknown fields")
    if value["schema_version"] != "1.0":
        raise InvalidModelError("Unsupported framed coordinate schema_version")
    if value["kind"] != expected_kind:
        raise InvalidModelError(f"Expected framed coordinate kind {expected_kind}")
    raw = value["coordinates"]
    if not isinstance(raw, Mapping) or set(raw) != {"x", "y", "z", "unit"}:
        raise InvalidModelError("Framed coordinates require x, y, z and unit")
    components = (raw["x"], raw["y"], raw["z"])
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in components):
        raise InvalidModelError("Framed coordinate components must be numeric")
    frame_id = value["frame_id"]
    length_unit = raw["unit"]
    _validate_frame_and_unit(frame_id, length_unit)
    return frame_id, Vec3(*(float(item) for item in components)), length_unit


@dataclass(frozen=True, slots=True)
class FramedPoint3:
    """A spatial point whose coordinates are expressed in one named frame."""

    frame_id: str
    value: Vec3
    length_unit: str = "m"

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    KIND: ClassVar[str] = "POINT"

    def __post_init__(self) -> None:
        _validate_frame_and_unit(self.frame_id, self.length_unit)
        if not isinstance(self.value, Vec3):
            raise InvalidModelError("FramedPoint3 value must be Vec3")

    def transform_to(self, graph: FrameGraph, target_frame: str) -> "FramedPoint3":
        if not isinstance(graph, FrameGraph):
            raise InvalidModelError("transform_to requires a FrameGraph")
        if not isinstance(target_frame, str) or not target_frame.strip():
            raise InvalidModelError("target_frame must be a non-empty identifier")
        transform = graph.transform_between(self.frame_id, target_frame)
        if target_frame == self.frame_id:
            return self
        if transform.length_unit != self.length_unit:
            raise InvalidModelError("Point and FrameGraph length units do not match")
        return FramedPoint3(target_frame, transform.apply_point(self.value), self.length_unit)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "kind": self.KIND,
            "frame_id": self.frame_id,
            "coordinates": {
                "x": self.value.x, "y": self.value.y, "z": self.value.z,
                "unit": self.length_unit,
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FramedPoint3":
        frame_id, point, unit = _read_snapshot(value, cls.KIND)
        return cls(frame_id, point, unit)


@dataclass(frozen=True, slots=True)
class FramedVector3:
    """A spatial displacement vector; translation is never applied to it."""

    frame_id: str
    value: Vec3
    length_unit: str = "m"

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    KIND: ClassVar[str] = "VECTOR"

    def __post_init__(self) -> None:
        _validate_frame_and_unit(self.frame_id, self.length_unit)
        if not isinstance(self.value, Vec3):
            raise InvalidModelError("FramedVector3 value must be Vec3")

    def transform_to(self, graph: FrameGraph, target_frame: str) -> "FramedVector3":
        if not isinstance(graph, FrameGraph):
            raise InvalidModelError("transform_to requires a FrameGraph")
        transform = graph.transform_between(self.frame_id, target_frame)
        if target_frame == self.frame_id:
            return self
        if transform.length_unit != self.length_unit:
            raise InvalidModelError("Vector and FrameGraph length units do not match")
        return FramedVector3(target_frame, transform.apply_vector(self.value), self.length_unit)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "kind": self.KIND,
            "frame_id": self.frame_id,
            "coordinates": {
                "x": self.value.x, "y": self.value.y, "z": self.value.z,
                "unit": self.length_unit,
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FramedVector3":
        frame_id, vector, unit = _read_snapshot(value, cls.KIND)
        return cls(frame_id, vector, unit)
