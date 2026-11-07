"""Deterministic conversion of solved closed line-sketch loops to PlanarRegion v1.0.

Only disjoint, strictly nested or disjoint simple loops are accepted. Touching,
crossing, branching, open or ambiguous topology fails closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from typing import ClassVar

from .errors import InvalidModelError
from .parametric_sketch import ParametricSketch, ParametricSketchSolveResult
from .planar_region import (
    PlanarRegion,
    _loops_intersect,
    _point_location,
    _signed_area2,
)
from .primitive_geometry import Vec2


@dataclass(frozen=True, slots=True)
class SketchRegionConversionResult:
    source_sketch_id: str
    source_sketch_sha256: str
    regions: tuple[PlanarRegion, ...]

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    ALGORITHM_VERSION: ClassVar[str] = "closed-line-loop-containment-v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm_version": self.ALGORITHM_VERSION,
            "source_sketch_id": self.source_sketch_id,
            "source_sketch_sha256": self.source_sketch_sha256,
            "regions": [region.to_dict() for region in self.regions],
        }


def _extract_cycles(sketch: ParametricSketch) -> tuple[tuple[str, ...], ...]:
    if not sketch.segments:
        raise InvalidModelError("sketch-to-region conversion requires closed segments")
    adjacency: dict[str, list[str]] = {point.point_id: [] for point in sketch.points}
    edge_keys: set[tuple[str, str]] = set()
    for segment in sketch.segments:
        key = tuple(sorted((segment.start_point_id, segment.end_point_id)))
        if key in edge_keys:
            raise InvalidModelError("duplicate undirected sketch segments are ambiguous")
        edge_keys.add(key)
        adjacency[segment.start_point_id].append(segment.end_point_id)
        adjacency[segment.end_point_id].append(segment.start_point_id)
    for point_id, neighbors in adjacency.items():
        if len(neighbors) != 2:
            raise InvalidModelError(
                f"closed sketch topology requires degree 2 at point {point_id!r}; got {len(neighbors)}"
            )
    remaining = set(adjacency)
    cycles: list[tuple[str, ...]] = []
    while remaining:
        start = min(remaining)
        first = min(adjacency[start])
        cycle = [start]
        previous, current = start, first
        while current != start:
            if current in cycle:
                raise InvalidModelError("sketch graph contains a repeated vertex before cycle closure")
            cycle.append(current)
            candidates = [item for item in adjacency[current] if item != previous]
            if len(candidates) != 1:
                raise InvalidModelError("sketch loop traversal is ambiguous")
            previous, current = current, candidates[0]
            if len(cycle) > len(adjacency):
                raise InvalidModelError("sketch loop traversal exceeded the vertex bound")
        if len(cycle) < 3:
            raise InvalidModelError("closed sketch loops require at least three vertices")
        remaining.difference_update(cycle)
        cycles.append(tuple(cycle))
    return tuple(cycles)


def sketch_to_planar_regions(
    sketch: ParametricSketch,
    solved: ParametricSketchSolveResult,
) -> SketchRegionConversionResult:
    """Convert a converged sketch's closed simple loops to exact PlanarRegion records.

    Loop nesting uses exact binary64-rational point-location predicates. Even-depth
    loops are material components; their immediate odd-depth children are holes.
    Islands nested inside holes become independent output regions.
    """
    if not isinstance(sketch, ParametricSketch) or not isinstance(solved, ParametricSketchSolveResult):
        raise InvalidModelError("sketch_to_planar_regions requires a sketch and its solve result")
    if (solved.sketch_id, solved.frame_id, solved.length_unit) != (
        sketch.sketch_id, sketch.frame_id, sketch.length_unit
    ):
        raise InvalidModelError("solved sketch identity, frame and unit must match source sketch")
    if sketch.arcs:
        raise InvalidModelError("sketch-to-region conversion does not yet support circular arcs")
    if not solved.converged:
        raise InvalidModelError("cannot convert a sketch whose constraints did not converge")
    point_ids = {point.point_id for point in sketch.points}
    solved_points = {point.point_id: point for point in solved.points}
    if set(solved_points) != point_ids:
        raise InvalidModelError("solved sketch point set does not match source sketch")

    cycle_ids = _extract_cycles(sketch)
    loops: list[tuple[str, ...]] = []
    regions_for_validation: list[PlanarRegion] = []
    for index, cycle in enumerate(cycle_ids):
        points = tuple(Vec2(solved_points[item].x, solved_points[item].y) for item in cycle)
        validation = PlanarRegion(
            f"validation.loop.{index:04d}", sketch.frame_id, sketch.length_unit, points
        )
        loops.append(cycle)
        regions_for_validation.append(validation)
    canonical_loops = [item.outer_boundary for item in regions_for_validation]

    for first in range(len(canonical_loops)):
        for second in range(first + 1, len(canonical_loops)):
            if _loops_intersect(canonical_loops[first], canonical_loops[second]):
                raise InvalidModelError("distinct sketch loops may not touch or cross")

    parents: list[int | None] = [None] * len(canonical_loops)
    areas = [abs(_signed_area2(loop)) for loop in canonical_loops]
    for child, loop in enumerate(canonical_loops):
        containers = [
            parent for parent, candidate in enumerate(canonical_loops)
            if parent != child and areas[parent] > areas[child]
            and _point_location(loop[0], candidate) == "INSIDE"
        ]
        if containers:
            parents[child] = min(containers, key=lambda item: areas[item])

    depths: list[int] = [0] * len(canonical_loops)
    for index in range(len(canonical_loops)):
        visited: set[int] = set()
        parent = parents[index]
        while parent is not None:
            if parent in visited or parent == index:
                raise InvalidModelError("sketch loop containment graph contains a cycle")
            visited.add(parent)
            depths[index] += 1
            parent = parents[parent]

    sketch_digest = sha256(dumps(
        sketch.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    material_indices = sorted(
        (index for index, depth in enumerate(depths) if depth % 2 == 0),
        key=lambda index: tuple(sorted(loops[index])),
    )
    output: list[PlanarRegion] = []
    for output_index, outer_index in enumerate(material_indices):
        hole_indices = [
            index for index, parent in enumerate(parents)
            if parent == outer_index and depths[index] == depths[outer_index] + 1
        ]
        outer = canonical_loops[outer_index]
        holes = tuple(canonical_loops[index] for index in sorted(
            hole_indices, key=lambda item: tuple(sorted(loops[item]))
        ))
        region_id = f"sketch.{sketch_digest[:12]}.region.{output_index:04d}"
        output.append(PlanarRegion(
            region_id, sketch.frame_id, sketch.length_unit, outer, holes
        ))

    return SketchRegionConversionResult(sketch.sketch_id, sketch_digest, tuple(output))
