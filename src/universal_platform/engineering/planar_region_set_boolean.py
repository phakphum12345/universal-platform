"""Set-level exact-predicate Boolean operations over PlanarRegion inputs.

The input sequence defines the operand order for DIFFERENCE. UNION and
INTERSECTION combine the complete set; SYMMETRIC_DIFFERENCE uses odd/even
membership. The implementation is dependency-free and bounded.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from json import dumps
from typing import ClassVar, Iterable, Mapping

from .errors import InvalidModelError
from .planar_boolean import (
    PlanarRegionBooleanOperation,
    _Edge,
    _Point,
    _add,
    _contains,
    _location,
    _loop_area2,
    _mul,
    _side_samples,
    _split_pair,
    _stitch,
    _sub,
)
from .planar_region import PlanarRegion, _point
from .primitive_geometry import Vec2

_MAX_INPUT_EDGES = 256
_MAX_EDGE_PAIRS = _MAX_INPUT_EDGES * (_MAX_INPUT_EDGES - 1) // 2


@dataclass(frozen=True, slots=True)
class PlanarRegionSetBooleanResult:
    operation: PlanarRegionBooleanOperation
    input_region_ids: tuple[str, ...]
    input_region_sha256: tuple[str, ...]
    frame_id: str
    length_unit: str
    regions: tuple[PlanarRegion, ...]
    segment_pair_count: int
    max_coordinate_rounding_error: float
    area_rounding_error: float

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    ALGORITHM_VERSION: ClassVar[str] = "exact-rational-region-set-arrangement-v1"

    @property
    def area(self) -> float:
        return sum(region.area for region in self.regions)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm_version": self.ALGORITHM_VERSION,
            "operation": self.operation.value,
            "input_region_ids": list(self.input_region_ids),
            "input_region_sha256": list(self.input_region_sha256),
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "regions": [region.to_dict() for region in self.regions],
            "region_count": len(self.regions),
            "segment_pair_count": self.segment_pair_count,
            "area": self.area,
            "max_coordinate_rounding_error": self.max_coordinate_rounding_error,
            "area_rounding_error": self.area_rounding_error,
            "limitations": [
                "DIFFERENCE uses the first region as minuend and the union of remaining regions as subtrahend.",
                "Unambiguous point-only contacts remain separate output components; ambiguous branching, coincident outgoing directions and invalid hole topology fail closed.",
                "Circular arcs, splines, 3D Booleans and B-rep are not supported.",
                "Generated intersections are rounded to binary64 and error is reported.",
                "Resource limits reject the operation; no partial result is returned.",
                "No manufacturing, physical validation or certification is implied."
            ],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "PlanarRegionSetBooleanResult":
        required = {
            "schema_version", "algorithm_version", "operation", "input_region_ids",
            "input_region_sha256", "frame_id", "length_unit", "regions",
            "region_count", "segment_pair_count", "area",
            "max_coordinate_rounding_error", "area_rounding_error", "limitations",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("PlanarRegionSetBooleanResult snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION or value["algorithm_version"] != cls.ALGORITHM_VERSION:
            raise InvalidModelError("unsupported PlanarRegionSetBooleanResult version")
        try:
            operation = PlanarRegionBooleanOperation(value["operation"])
        except (TypeError, ValueError) as exc:
            raise InvalidModelError("unsupported PlanarRegionSetBooleanResult operation") from exc
        ids, digests = value["input_region_ids"], value["input_region_sha256"]
        if not isinstance(ids, (list, tuple)) or len(ids) < 2 or any(not isinstance(item, str) or not item.strip() for item in ids):
            raise InvalidModelError("input_region_ids must contain at least two non-empty IDs")
        if not isinstance(digests, (list, tuple)) or len(digests) != len(ids):
            raise InvalidModelError("input_region_sha256 must match input_region_ids")
        if any(not isinstance(item, str) or len(item) != 64 or any(ch not in "0123456789abcdef" for ch in item) for item in digests):
            raise InvalidModelError("input_region_sha256 entries must be lowercase SHA-256 digests")
        for key in ("frame_id", "length_unit"):
            if not isinstance(value[key], str) or not value[key].strip():
                raise InvalidModelError(f"{key} must be a non-empty string")
        raw_regions = value["regions"]
        if not isinstance(raw_regions, (list, tuple)):
            raise InvalidModelError("regions must be an array")
        regions = tuple(PlanarRegion.from_dict(item) for item in raw_regions)
        if any(region.frame_id != value["frame_id"] or region.length_unit != value["length_unit"] for region in regions):
            raise InvalidModelError("result region frame/unit does not match its envelope")
        if isinstance(value["region_count"], bool) or not isinstance(value["region_count"], int) or value["region_count"] != len(regions):
            raise InvalidModelError("region_count does not match regions")
        pair_count = value["segment_pair_count"]
        if isinstance(pair_count, bool) or not isinstance(pair_count, int) or not 0 <= pair_count <= _MAX_EDGE_PAIRS:
            raise InvalidModelError("segment_pair_count is outside the supported resource bound")
        for key in ("area", "max_coordinate_rounding_error", "area_rounding_error"):
            metric = value[key]
            if isinstance(metric, bool) or not isinstance(metric, (int, float)) or not __import__("math").isfinite(float(metric)) or metric < 0:
                raise InvalidModelError(f"{key} must be a finite non-negative number")
        if float(value["area"]) != sum(region.area for region in regions):
            raise InvalidModelError("area does not match the serialized output regions")
        limitations = [
            "DIFFERENCE uses the first region as minuend and the union of remaining regions as subtrahend.",
            "Unambiguous point-only contacts remain separate output components; ambiguous branching, coincident outgoing directions and invalid hole topology fail closed.",
            "Circular arcs, splines, 3D Booleans and B-rep are not supported.",
            "Generated intersections are rounded to binary64 and error is reported.",
            "Resource limits reject the operation; no partial result is returned.",
            "No manufacturing, physical validation or certification is implied."
        ]
        if value["limitations"] != limitations:
            raise InvalidModelError("result limitations do not match the versioned contract")
        return cls(
            operation=operation,
            input_region_ids=tuple(ids),
            input_region_sha256=tuple(digests),
            frame_id=value["frame_id"],
            length_unit=value["length_unit"],
            regions=regions,
            segment_pair_count=pair_count,
            max_coordinate_rounding_error=float(value["max_coordinate_rounding_error"]),
            area_rounding_error=float(value["area_rounding_error"]),
        )


def _set_membership(point: _Point, regions: tuple[PlanarRegion, ...],
                    operation: PlanarRegionBooleanOperation) -> bool:
    membership = tuple(_contains(point, region) for region in regions)
    if operation is PlanarRegionBooleanOperation.UNION:
        return any(membership)
    if operation is PlanarRegionBooleanOperation.INTERSECTION:
        return all(membership)
    if operation is PlanarRegionBooleanOperation.DIFFERENCE:
        return membership[0] and not any(membership[1:])
    return sum(membership) % 2 == 1


def boolean_planar_region_set(
    regions: Iterable[PlanarRegion],
    operation: PlanarRegionBooleanOperation,
) -> PlanarRegionSetBooleanResult:
    """Apply a set Boolean to two or more regions in one exact arrangement.

    UNION is the union of all inputs; INTERSECTION is their common intersection;
    DIFFERENCE is the first input minus the union of all remaining inputs;
    SYMMETRIC_DIFFERENCE is odd/even membership across all inputs.
    """
    operands = tuple(regions)
    if len(operands) < 2:
        raise InvalidModelError("region-set Boolean requires at least two input regions")
    if any(not isinstance(region, PlanarRegion) for region in operands):
        raise InvalidModelError("all region-set Boolean inputs must be PlanarRegion records")
    if not isinstance(operation, PlanarRegionBooleanOperation):
        raise InvalidModelError("operation must be a PlanarRegionBooleanOperation")
    frame_id, length_unit = operands[0].frame_id, operands[0].length_unit
    if any(region.frame_id != frame_id or region.length_unit != length_unit for region in operands[1:]):
        raise InvalidModelError("all region-set Boolean inputs must share the same frame and length unit")

    raw_edges: list[_Edge] = []
    for region in operands:
        for loop in (region.outer_boundary, *region.holes):
            points = tuple(_point(point) for point in loop)
            raw_edges.extend((points[index], points[(index + 1) % len(points)]) for index in range(len(points)))
    if len(raw_edges) > _MAX_INPUT_EDGES:
        raise InvalidModelError(f"Boolean region set exceeds {_MAX_INPUT_EDGES} total edges")
    pair_count = len(raw_edges) * (len(raw_edges) - 1) // 2
    if pair_count > _MAX_EDGE_PAIRS:
        raise InvalidModelError("Boolean region-set segment-pair resource limit exceeded")

    parameters = [{Fraction(0), Fraction(1)} for _ in raw_edges]
    for first_index in range(len(raw_edges)):
        for second_index in range(first_index + 1, len(raw_edges)):
            left, right = _split_pair(raw_edges[first_index], raw_edges[second_index])
            parameters[first_index].update(left)
            parameters[second_index].update(right)

    atomic: set[_Edge] = set()
    for edge, values in zip(raw_edges, parameters):
        start, end = edge
        direction = _sub(end, start)
        ordered = sorted(values)
        for low, high in zip(ordered, ordered[1:]):
            if low == high:
                continue
            a = _add(start, _mul(direction, low))
            b = _add(start, _mul(direction, high))
            atomic.add((a, b) if a < b else (b, a))
    all_edges = tuple(sorted(atomic))
    selected: set[_Edge] = set()
    for edge in all_edges:
        left, right = _side_samples(edge, all_edges)
        left_value = _set_membership(left, operands, operation)
        right_value = _set_membership(right, operands, operation)
        if left_value != right_value:
            selected.add(edge if left_value else (edge[1], edge[0]))

    rational_loops = _stitch(selected) if selected else ()
    outer_loops = [loop for loop in rational_loops if _loop_area2(loop) > 0]
    hole_loops = [loop for loop in rational_loops if _loop_area2(loop) < 0]
    assignments: dict[int, list[tuple[_Point, ...]]] = {i: [] for i in range(len(outer_loops))}
    for hole in hole_loops:
        containers = [i for i, outer in enumerate(outer_loops) if _location(hole[0], outer) == "INSIDE"]
        if not containers:
            raise InvalidModelError("Boolean region-set output contains an uncontained hole")
        owner = min(containers, key=lambda i: abs(_loop_area2(outer_loops[i])))
        assignments[owner].append(hole)

    digest_seed = dumps({
        "operation": operation.value,
        "inputs": [region.canonical_sha256 for region in operands],
    }, sort_keys=True, separators=(",", ":"))
    result_seed = sha256(digest_seed.encode("utf-8")).hexdigest()
    output_regions: list[PlanarRegion] = []
    max_error = 0.0
    exact_area = Fraction(0)
    for index, outer in enumerate(outer_loops):
        loops = (outer, *sorted(assignments[index], key=lambda loop: (min(loop), len(loop), loop)))
        exact_area += sum((_loop_area2(loop) / 2 for loop in loops), Fraction(0))
        converted: list[tuple[Vec2, ...]] = []
        for loop in loops:
            points = []
            for x, y in loop:
                fx, fy = float(x), float(y)
                if not (float("-inf") < fx < float("inf") and float("-inf") < fy < float("inf")):
                    raise InvalidModelError("Boolean region-set intersection is outside finite binary64 range")
                max_error = max(max_error, float(abs(Fraction.from_float(fx) - x)),
                                float(abs(Fraction.from_float(fy) - y)))
                points.append(Vec2(fx, fy))
            converted.append(tuple(points))
        output_regions.append(PlanarRegion(
            region_id=f"boolean-set.{result_seed[:12]}.{index}",
            frame_id=frame_id,
            length_unit=length_unit,
            outer_boundary=converted[0],
            holes=tuple(converted[1:]),
        ))
    rounded_area = sum((region.area_exact for region in output_regions), Fraction(0))
    return PlanarRegionSetBooleanResult(
        operation=operation,
        input_region_ids=tuple(region.region_id for region in operands),
        input_region_sha256=tuple(region.canonical_sha256 for region in operands),
        frame_id=frame_id,
        length_unit=length_unit,
        regions=tuple(output_regions),
        segment_pair_count=pair_count,
        max_coordinate_rounding_error=max_error,
        area_rounding_error=float(abs(rounded_area - exact_area)),
    )
