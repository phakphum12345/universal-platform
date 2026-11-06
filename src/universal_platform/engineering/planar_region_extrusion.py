"""Validated conversion from exact PlanarRegion v1.0 to an extruded solid.

This adapter preserves the region's frame/unit and source digest. It creates an
analytic straight-edged ExtrudedProfileSolid; meshing remains an explicit,
separate call through tessellate_extruded_profile.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Mapping

from .errors import InvalidModelError
from .planar_region import PlanarRegion
from .primitive_geometry import ExtrudedProfileSolid, Vec2


@dataclass(frozen=True, slots=True)
class PlanarRegionExtrusionResult:
    source_region_id: str
    source_region_sha256: str
    solid: ExtrudedProfileSolid

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    ALGORITHM_VERSION: ClassVar[str] = "planar-region-straight-extrusion-v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm_version": self.ALGORITHM_VERSION,
            "source_region_id": self.source_region_id,
            "source_region_sha256": self.source_region_sha256,
            "solid": self.solid.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "PlanarRegionExtrusionResult":
        required = {"schema_version", "algorithm_version", "source_region_id", "source_region_sha256", "solid"}
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("PlanarRegionExtrusionResult snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION or value["algorithm_version"] != cls.ALGORITHM_VERSION:
            raise InvalidModelError("unsupported PlanarRegionExtrusionResult version")
        source_id, digest = value["source_region_id"], value["source_region_sha256"]
        if not isinstance(source_id, str) or not source_id.strip():
            raise InvalidModelError("source_region_id must be a non-empty string")
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise InvalidModelError("source_region_sha256 must be a lowercase SHA-256 digest")
        raw = value["solid"]
        required_solid = {"kind", "solid_id", "frame_id", "profile", "height", "unit"}
        if not isinstance(raw, Mapping) or not required_solid.issubset(raw) or set(raw) - (required_solid | {"holes"}):
            raise InvalidModelError("extruded solid snapshot has missing or unsupported fields")
        if raw["kind"] != ExtrudedProfileSolid.KIND:
            raise InvalidModelError("extrusion result must contain an EXTRUDED_PROFILE solid")

        def parse_loop(items: object, label: str) -> tuple[Vec2, ...]:
            if not isinstance(items, (list, tuple)):
                raise InvalidModelError(f"{label} must be an array")
            points = []
            for point in items:
                if not isinstance(point, Mapping) or set(point) != {"x", "y"}:
                    raise InvalidModelError(f"{label} point requires x and y")
                points.append(Vec2(point["x"], point["y"]))
            return tuple(points)

        profile = parse_loop(raw["profile"], "profile")
        raw_holes = raw.get("holes", [])
        if not isinstance(raw_holes, (list, tuple)):
            raise InvalidModelError("holes must be an array")
        holes = tuple(parse_loop(hole, "hole") for hole in raw_holes)
        solid = ExtrudedProfileSolid(
            raw["solid_id"], raw["frame_id"], profile, raw["height"], raw["unit"], holes
        )
        return cls(source_id, digest, solid)


def extrude_planar_region(
    region: PlanarRegion,
    solid_id: str,
    height: float,
) -> PlanarRegionExtrusionResult:
    """Convert a validated PlanarRegion into a straight-edged extrusion.

    The region frame and length unit are preserved exactly as metadata. No
    scaling, rotation, repair, snapping or implicit unit conversion is done.
    """
    if not isinstance(region, PlanarRegion):
        raise InvalidModelError("extrude_planar_region requires a PlanarRegion")
    solid = ExtrudedProfileSolid(
        solid_id=solid_id,
        frame_id=region.frame_id,
        profile=region.outer_boundary,
        height=height,
        length_unit=region.length_unit,
        holes=region.holes,
    )
    return PlanarRegionExtrusionResult(
        source_region_id=region.region_id,
        source_region_sha256=region.canonical_sha256,
        solid=solid,
    )
