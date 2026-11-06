"""Exact-predicate Boolean operations for validated PlanarRegion inputs.

This dependency-free arrangement engine operates on the exact rational values
represented by input binary64 coordinates. Generated intersections are rounded
once to binary64 for the public PlanarRegion model; the result reports the
coordinate and area rounding error. Ambiguous branching topology and bounded resource exhaustion fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from hashlib import sha256
from json import dumps
from typing import ClassVar, Mapping
from functools import cmp_to_key

from .errors import InvalidModelError
from .planar_region import PlanarRegion, _point
from .primitive_geometry import Vec2

_Point = tuple[Fraction, Fraction]
_Edge = tuple[_Point, _Point]
_MAX_INPUT_EDGES = 256
_MAX_EDGE_PAIRS = _MAX_INPUT_EDGES * (_MAX_INPUT_EDGES - 1) // 2


class PlanarRegionBooleanOperation(str, Enum):
    UNION = "UNION"
    INTERSECTION = "INTERSECTION"
    DIFFERENCE = "DIFFERENCE"
    SYMMETRIC_DIFFERENCE = "SYMMETRIC_DIFFERENCE"


def _sub(a: _Point, b: _Point) -> _Point:
    return a[0] - b[0], a[1] - b[1]


def _add(a: _Point, b: _Point) -> _Point:
    return a[0] + b[0], a[1] + b[1]


def _mul(a: _Point, value: Fraction) -> _Point:
    return a[0] * value, a[1] * value


def _cross(a: _Point, b: _Point) -> Fraction:
    return a[0] * b[1] - a[1] * b[0]


def _on_segment(a: _Point, b: _Point, p: _Point) -> bool:
    return (_cross(_sub(b, a), _sub(p, a)) == 0
            and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))


def _parameter(a: _Point, b: _Point, p: _Point) -> Fraction:
    delta = _sub(b, a)
    return ((p[0] - a[0]) / delta[0] if delta[0] != 0
            else (p[1] - a[1]) / delta[1])


def _split_pair(first: _Edge, second: _Edge) -> tuple[set[Fraction], set[Fraction]]:
    a, b = first
    c, d = second
    r, s = _sub(b, a), _sub(d, c)
    offset = _sub(c, a)
    denominator = _cross(r, s)
    first_values: set[Fraction] = set()
    second_values: set[Fraction] = set()
    if denominator != 0:
        t = _cross(offset, s) / denominator
        u = _cross(offset, r) / denominator
        if 0 <= t <= 1 and 0 <= u <= 1:
            first_values.add(t)
            second_values.add(u)
    elif _cross(offset, r) == 0:
        for point in (c, d):
            if _on_segment(a, b, point):
                first_values.add(_parameter(a, b, point))
        for point in (a, b):
            if _on_segment(c, d, point):
                second_values.add(_parameter(c, d, point))
    return first_values, second_values


def _location(point: _Point, loop: tuple[_Point, ...]) -> str:
    winding = 0
    for index, start in enumerate(loop):
        end = loop[(index + 1) % len(loop)]
        if _on_segment(start, end, point):
            return "BOUNDARY"
        if start[1] <= point[1]:
            if end[1] > point[1] and _cross(_sub(end, start), _sub(point, start)) > 0:
                winding += 1
        elif end[1] <= point[1] and _cross(_sub(end, start), _sub(point, start)) < 0:
            winding -= 1
    return "INSIDE" if winding else "OUTSIDE"


def _contains(point: _Point, region: PlanarRegion) -> bool:
    outer = tuple(_point(p) for p in region.outer_boundary)
    location = _location(point, outer)
    if location == "BOUNDARY":
        raise InvalidModelError("Boolean side sample is topologically ambiguous")
    if location == "OUTSIDE":
        return False
    for hole in region.holes:
        hole_points = tuple(_point(p) for p in hole)
        location = _location(point, hole_points)
        if location == "BOUNDARY":
            raise InvalidModelError("Boolean side sample is topologically ambiguous")
        if location == "INSIDE":
            return False
    return True


def _operation_value(first: bool, second: bool,
                     operation: PlanarRegionBooleanOperation) -> bool:
    if operation is PlanarRegionBooleanOperation.UNION:
        return first or second
    if operation is PlanarRegionBooleanOperation.INTERSECTION:
        return first and second
    if operation is PlanarRegionBooleanOperation.DIFFERENCE:
        return first and not second
    return first != second


def _point_segment_distance2(point: _Point, edge: _Edge) -> Fraction:
    a, b = edge
    direction = _sub(b, a)
    offset = _sub(point, a)
    length2 = direction[0] ** 2 + direction[1] ** 2
    projection = offset[0] * direction[0] + offset[1] * direction[1]
    if projection <= 0:
        delta = offset
        return delta[0] ** 2 + delta[1] ** 2
    if projection >= length2:
        delta = _sub(point, b)
        return delta[0] ** 2 + delta[1] ** 2
    cross = _cross(direction, offset)
    return cross ** 2 / length2


def _side_samples(edge: _Edge, all_edges: tuple[_Edge, ...]) -> tuple[_Point, _Point]:
    a, b = edge
    direction = _sub(b, a)
    midpoint = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    length2 = direction[0] ** 2 + direction[1] ** 2
    distances = [_point_segment_distance2(midpoint, other)
                 for other in all_edges if other != edge and other != (b, a)]
    positive = [distance for distance in distances if distance > 0]
    if len(positive) != len(distances):
        raise InvalidModelError("Boolean arrangement contains unresolved overlapping edges")
    nearest2 = min(positive) if positive else Fraction(1)
    # The normal displacement is provably less than one eighth of the
    # nearest-segment distance, without introducing square roots.
    scale = nearest2 / (8 * (1 + length2) * (1 + nearest2))
    normal = (-direction[1] * scale, direction[0] * scale)
    return _add(midpoint, normal), _sub(midpoint, normal)


def _loop_area2(loop: tuple[_Point, ...]) -> Fraction:
    total = Fraction(0)
    for index, point in enumerate(loop):
        following = loop[(index + 1) % len(loop)]
        total += point[0] * following[1] - following[0] * point[1]
    return total


def _angle_compare(first: _Point, second: _Point) -> int:
    """Compare vector polar angles counter-clockwise using exact rational predicates."""
    first_half = 0 if first[1] > 0 or (first[1] == 0 and first[0] >= 0) else 1
    second_half = 0 if second[1] > 0 or (second[1] == 0 and second[0] >= 0) else 1
    if first_half != second_half:
        return -1 if first_half < second_half else 1
    cross = _cross(first, second)
    if cross > 0:
        return -1
    if cross < 0:
        return 1
    return 0


def _stitch(directed: set[_Edge]) -> tuple[tuple[_Point, ...], ...]:
    """Stitch oriented boundaries using the clockwise predecessor rule.

    At a point-contact vertex, choose the outgoing boundary half-edge immediately
    clockwise from the reverse incoming direction. This is the deterministic
    planar rotation-system rule that keeps point-touching material components
    as separate cycles instead of producing a figure-eight boundary.
    """
    outgoing: dict[_Point, list[_Point]] = {}
    incoming: dict[_Point, list[_Point]] = {}
    for start, end in directed:
        outgoing.setdefault(start, []).append(end)
        incoming.setdefault(end, []).append(start)
    vertices = set(outgoing) | set(incoming)
    successor: dict[_Edge, _Edge] = {}
    for vertex in vertices:
        ins = incoming.get(vertex, [])
        outs = outgoing.get(vertex, [])
        if len(ins) != len(outs) or not ins:
            raise InvalidModelError("Boolean output has unbalanced boundary incidence")
        ordered_outs = sorted(
            outs,
            key=cmp_to_key(lambda a, b: _angle_compare(_sub(a, vertex), _sub(b, vertex))),
        )
        for first, second in zip(ordered_outs, ordered_outs[1:]):
            if _angle_compare(_sub(first, vertex), _sub(second, vertex)) == 0:
                raise InvalidModelError("Boolean output has coincident outgoing branches")
        used_outgoing: set[_Point] = set()
        for previous in sorted(ins):
            reverse_direction = _sub(previous, vertex)
            candidates = [
                point for point in ordered_outs
                if _angle_compare(_sub(point, vertex), reverse_direction) != 0
            ]
            if not candidates:
                raise InvalidModelError("Boolean output has no unambiguous outgoing boundary")
            clockwise_predecessors = [
                point for point in candidates
                if _angle_compare(_sub(point, vertex), reverse_direction) < 0
            ]
            chosen = clockwise_predecessors[-1] if clockwise_predecessors else candidates[-1]
            if chosen in used_outgoing:
                raise InvalidModelError("Boolean output boundary rotation is ambiguous")
            used_outgoing.add(chosen)
            successor[(previous, vertex)] = (vertex, chosen)

    unused = set(directed)
    loops: list[tuple[_Point, ...]] = []
    while unused:
        first = min(unused)
        start = first[0]
        current = first
        points = [start]
        for _ in range(len(directed) + 1):
            if current not in unused:
                raise InvalidModelError("Boolean boundary traversal reuses an edge")
            unused.remove(current)
            endpoint = current[1]
            if endpoint == start:
                break
            if endpoint in points:
                raise InvalidModelError("Boolean boundary cycle repeats a vertex")
            points.append(endpoint)
            following = successor.get(current)
            if following is None:
                raise InvalidModelError("Boolean boundary traversal has no successor")
            current = following
        else:
            raise InvalidModelError("Boolean boundary traversal exceeded its edge budget")
        if len(points) < 3 or _loop_area2(tuple(points)) == 0:
            raise InvalidModelError("Boolean arrangement produced a degenerate boundary")
        loops.append(tuple(points))
    return tuple(sorted(loops, key=lambda loop: (min(loop), len(loop), loop)))


@dataclass(frozen=True, slots=True)
class PlanarRegionBooleanResult:
    operation: PlanarRegionBooleanOperation
    first_region_id: str
    second_region_id: str
    first_region_sha256: str
    second_region_sha256: str
    frame_id: str
    length_unit: str
    regions: tuple[PlanarRegion, ...]
    segment_pair_count: int
    max_coordinate_rounding_error: float
    area_rounding_error: float

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    ALGORITHM_VERSION: ClassVar[str] = "exact-rational-arrangement-v1"

    @property
    def area(self) -> float:
        return sum(region.area for region in self.regions)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm_version": self.ALGORITHM_VERSION,
            "operation": self.operation.value,
            "first_region_id": self.first_region_id,
            "second_region_id": self.second_region_id,
            "first_region_sha256": self.first_region_sha256,
            "second_region_sha256": self.second_region_sha256,
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "regions": [region.to_dict() for region in self.regions],
            "region_count": len(self.regions),
            "segment_pair_count": self.segment_pair_count,
            "area": self.area,
            "max_coordinate_rounding_error": self.max_coordinate_rounding_error,
            "area_rounding_error": self.area_rounding_error,
            "limitations": [
                "Branching output boundaries with ambiguous rotation fail closed.",
                "Circular arcs, splines, 3D Booleans and B-rep are not supported.",
                "Generated intersections are rounded to binary64 and error is reported.",
                "Resource limits reject the operation; no partial result is returned.",
                "No manufacturing, physical validation or certification is implied."
            ],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "PlanarRegionBooleanResult":
        required = {
            "schema_version", "algorithm_version", "operation", "first_region_id",
            "second_region_id", "first_region_sha256", "second_region_sha256",
            "frame_id", "length_unit", "regions", "region_count",
            "segment_pair_count", "area", "max_coordinate_rounding_error",
            "area_rounding_error", "limitations",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("PlanarRegionBooleanResult snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION or value["algorithm_version"] != cls.ALGORITHM_VERSION:
            raise InvalidModelError("unsupported PlanarRegionBooleanResult version")
        try:
            operation = PlanarRegionBooleanOperation(value["operation"])
        except (TypeError, ValueError) as exc:
            raise InvalidModelError("unsupported PlanarRegionBooleanResult operation") from exc
        for key in ("first_region_id", "second_region_id", "frame_id", "length_unit"):
            if not isinstance(value[key], str) or not value[key].strip():
                raise InvalidModelError(f"{key} must be a non-empty string")
        for key in ("first_region_sha256", "second_region_sha256"):
            digest = value[key]
            if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise InvalidModelError(f"{key} must be a lowercase SHA-256 digest")
        raw_regions = value["regions"]
        if not isinstance(raw_regions, (list, tuple)):
            raise InvalidModelError("regions must be an array")
        regions = tuple(PlanarRegion.from_dict(item) for item in raw_regions)
        if any(region.frame_id != value["frame_id"] or region.length_unit != value["length_unit"]
               for region in regions):
            raise InvalidModelError("result region frame/unit does not match its envelope")
        if isinstance(value["region_count"], bool) or value["region_count"] != len(regions):
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
            "Point-touching or branching output boundaries fail closed.",
            "Circular arcs, splines, 3D Booleans and B-rep are not supported.",
            "Generated intersections are rounded to binary64 and error is reported.",
            "Resource limits reject the operation; no partial result is returned.",
            "No manufacturing, physical validation or certification is implied."
        ]
        if value["limitations"] != limitations:
            raise InvalidModelError("result limitations do not match the versioned contract")
        return cls(
            operation=operation,
            first_region_id=value["first_region_id"],
            second_region_id=value["second_region_id"],
            first_region_sha256=value["first_region_sha256"],
            second_region_sha256=value["second_region_sha256"],
            frame_id=value["frame_id"],
            length_unit=value["length_unit"],
            regions=regions,
            segment_pair_count=pair_count,
            max_coordinate_rounding_error=float(value["max_coordinate_rounding_error"]),
            area_rounding_error=float(value["area_rounding_error"]),
        )


def boolean_planar_regions(
    first: PlanarRegion,
    second: PlanarRegion,
    operation: PlanarRegionBooleanOperation,
) -> PlanarRegionBooleanResult:
    """Apply a deterministic exact-predicate Boolean to two PlanarRegion inputs."""
    if not isinstance(first, PlanarRegion) or not isinstance(second, PlanarRegion):
        raise InvalidModelError("Boolean inputs must be PlanarRegion records")
    if not isinstance(operation, PlanarRegionBooleanOperation):
        raise InvalidModelError("operation must be a PlanarRegionBooleanOperation")
    if first.frame_id != second.frame_id or first.length_unit != second.length_unit:
        raise InvalidModelError("Boolean inputs must share the same frame and length unit")
    raw_edges: list[_Edge] = []
    for region in (first, second):
        for loop in (region.outer_boundary, *region.holes):
            points = tuple(_point(point) for point in loop)
            raw_edges.extend((points[index], points[(index + 1) % len(points)])
                             for index in range(len(points)))
    if len(raw_edges) > _MAX_INPUT_EDGES:
        raise InvalidModelError(f"Boolean input exceeds {_MAX_INPUT_EDGES} total edges")
    pair_count = len(raw_edges) * (len(raw_edges) - 1) // 2
    if pair_count > _MAX_EDGE_PAIRS:
        raise InvalidModelError("Boolean segment-pair resource limit exceeded")

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
        left_value = _operation_value(_contains(left, first), _contains(left, second), operation)
        right_value = _operation_value(_contains(right, first), _contains(right, second), operation)
        if left_value != right_value:
            selected.add(edge if left_value else (edge[1], edge[0]))

    rational_loops = _stitch(selected) if selected else ()
    outer_loops = [loop for loop in rational_loops if _loop_area2(loop) > 0]
    hole_loops = [loop for loop in rational_loops if _loop_area2(loop) < 0]
    assignments: dict[int, list[tuple[_Point, ...]]] = {i: [] for i in range(len(outer_loops))}
    for hole in hole_loops:
        containers = [i for i, outer in enumerate(outer_loops)
                      if _location(hole[0], outer) == "INSIDE"]
        if not containers:
            raise InvalidModelError("Boolean output contains an uncontained hole")
        owner = min(containers, key=lambda i: abs(_loop_area2(outer_loops[i])))
        assignments[owner].append(hole)

    digest_seed = dumps({
        "operation": operation.value,
        "first": first.canonical_sha256,
        "second": second.canonical_sha256,
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
                    raise InvalidModelError("Boolean intersection is outside finite binary64 range")
                max_error = max(max_error, float(abs(Fraction.from_float(fx) - x)),
                                float(abs(Fraction.from_float(fy) - y)))
                points.append(Vec2(fx, fy))
            converted.append(tuple(points))
        output_regions.append(PlanarRegion(
            region_id=f"boolean.{result_seed[:12]}.{index}",
            frame_id=first.frame_id,
            length_unit=first.length_unit,
            outer_boundary=converted[0],
            holes=tuple(converted[1:]),
        ))
    rounded_area = sum((region.area_exact for region in output_regions), Fraction(0))
    area_error = abs(rounded_area - exact_area)
    return PlanarRegionBooleanResult(
        operation=operation,
        first_region_id=first.region_id,
        second_region_id=second.region_id,
        first_region_sha256=first.canonical_sha256,
        second_region_sha256=second.canonical_sha256,
        frame_id=first.frame_id,
        length_unit=first.length_unit,
        regions=tuple(output_regions),
        segment_pair_count=pair_count,
        max_coordinate_rounding_error=max_error,
        area_rounding_error=float(area_error),
    )
