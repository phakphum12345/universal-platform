"""Deterministic conversion of solved line/arc sketch loops to PlanarRegion v1.0.

Circular arcs are tessellated with an explicit maximum chord error. Topology
validation remains fail-closed and uses the PlanarRegion exact represented-
binary64 predicates after tessellation; this is not an exact curved kernel.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from math import acos, atan2, ceil, cos, hypot, isfinite, pi, sin
from typing import ClassVar

from .errors import InvalidModelError
from .parametric_sketch import (
    ParametricSketch, ParametricSketchSolveResult, SketchArc, SketchSegment,
)
from .planar_region import (
    MAX_PLANAR_BOUNDARY_EDGES, PlanarRegion, _loops_intersect,
    _point_location, _signed_area2,
)
from .primitive_geometry import Vec2


DEFAULT_ARC_CHORD_ERROR = 0.01


@dataclass(frozen=True, slots=True)
class SketchRegionConversionResult:
    source_sketch_id: str
    source_sketch_sha256: str
    regions: tuple[PlanarRegion, ...]

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    ALGORITHM_VERSION: ClassVar[str] = "line-arc-tessellation-containment-v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm_version": self.ALGORITHM_VERSION,
            "source_sketch_id": self.source_sketch_id,
            "source_sketch_sha256": self.source_sketch_sha256,
            "regions": [region.to_dict() for region in self.regions],
        }


@dataclass(frozen=True, slots=True)
class _BoundaryEdge:
    kind: str
    edge_id: str
    start_point_id: str
    end_point_id: str


def _extract_cycles(sketch: ParametricSketch) -> tuple[tuple[_BoundaryEdge, ...], ...]:
    if not sketch.segments and not sketch.arcs:
        raise InvalidModelError("sketch-to-region conversion requires closed segments or arcs")
    adjacency: dict[str, list[_BoundaryEdge]] = {}
    edge_keys: set[tuple[str, str]] = set()
    center_ids = {arc.center_point_id for arc in sketch.arcs}
    for segment in sketch.segments:
        edge = _BoundaryEdge("segment", segment.segment_id,
                             segment.start_point_id, segment.end_point_id)
        key = tuple(sorted((edge.start_point_id, edge.end_point_id)))
        if key in edge_keys:
            raise InvalidModelError("duplicate undirected sketch boundary edges are ambiguous")
        edge_keys.add(key)
        adjacency.setdefault(edge.start_point_id, []).append(edge)
        adjacency.setdefault(edge.end_point_id, []).append(edge)
    for arc in sketch.arcs:
        edge = _BoundaryEdge("arc", arc.arc_id, arc.start_point_id, arc.end_point_id)
        key = tuple(sorted((edge.start_point_id, edge.end_point_id)))
        if key in edge_keys:
            raise InvalidModelError("duplicate undirected sketch boundary edges are ambiguous")
        edge_keys.add(key)
        adjacency.setdefault(edge.start_point_id, []).append(edge)
        adjacency.setdefault(edge.end_point_id, []).append(edge)

    point_ids = {point.point_id for point in sketch.points}
    if not center_ids.issubset(point_ids):
        raise InvalidModelError("arc center references must resolve")
    boundary_ids = set(adjacency)
    if boundary_ids & center_ids:
        raise InvalidModelError("arc center points cannot also be boundary vertices")
    if boundary_ids | center_ids != point_ids:
        raise InvalidModelError("sketch contains unused points outside its boundary and arc centers")
    for point_id, edges in adjacency.items():
        if len(edges) != 2:
            raise InvalidModelError(
                f"closed sketch topology requires degree 2 at point {point_id!r}; got {len(edges)}"
            )

    remaining = set(adjacency)
    cycles: list[tuple[_BoundaryEdge, ...]] = []
    while remaining:
        start = min(remaining)
        first = min(adjacency[start], key=lambda e: (
            e.end_point_id if e.start_point_id == start else e.start_point_id,
            e.kind, e.edge_id,
        ))
        cycle: list[_BoundaryEdge] = []
        previous_point, current_point = start, (
            first.end_point_id if first.start_point_id == start else first.start_point_id
        )
        current_edge = first
        visited_points = {start}
        while True:
            cycle.append(_BoundaryEdge(
                current_edge.kind, current_edge.edge_id, previous_point, current_point
            ))
            if current_point == start:
                break
            if current_point in visited_points:
                raise InvalidModelError("sketch graph contains a repeated vertex before cycle closure")
            visited_points.add(current_point)
            candidates = [edge for edge in adjacency[current_point] if edge != current_edge]
            if len(candidates) != 1:
                raise InvalidModelError("sketch loop traversal is ambiguous")
            previous_point = current_point
            current_edge = candidates[0]
            current_point = (
                current_edge.end_point_id if current_edge.start_point_id == previous_point
                else current_edge.start_point_id
            )
            if len(cycle) > len(adjacency):
                raise InvalidModelError("sketch loop traversal exceeded the vertex bound")
        if len(cycle) < 3:
            raise InvalidModelError("closed sketch loops require at least three boundary edges")
        remaining.difference_update(visited_points)
        cycles.append(tuple(cycle))
    return tuple(cycles)


def _arc_points(
    arc: SketchArc,
    points: dict[str, Vec2],
    *,
    chord_error: float,
) -> tuple[Vec2, ...]:
    center, start, end = (
        points[arc.center_point_id], points[arc.start_point_id], points[arc.end_point_id]
    )
    radius_start = hypot(start.x - center.x, start.y - center.y)
    radius_end = hypot(end.x - center.x, end.y - center.y)
    if radius_start <= 0.0 or radius_end <= 0.0:
        raise InvalidModelError("circular arc radius must be positive")
    radial_tolerance = max(1e-10, chord_error * 1e-6)
    if abs(radius_start - radius_end) > radial_tolerance:
        raise InvalidModelError("circular arc endpoints must lie on the same circle")
    radius = (radius_start + radius_end) / 2.0
    if chord_error >= radius:
        raise InvalidModelError("arc chord_error must be smaller than the arc radius")
    start_angle = atan2(start.y - center.y, start.x - center.x)
    end_angle = atan2(end.y - center.y, end.x - center.x)
    if arc.clockwise:
        sweep = -((start_angle - end_angle) % (2.0 * pi))
    else:
        sweep = (end_angle - start_angle) % (2.0 * pi)
    if abs(sweep) <= 1e-14 or abs(sweep) >= 2.0 * pi - 1e-14:
        raise InvalidModelError("circular arc must have a non-zero sweep smaller than one revolution")
    max_step = 2.0 * acos(max(-1.0, min(1.0, 1.0 - chord_error / radius)))
    if not isfinite(max_step) or max_step <= 0.0:
        raise InvalidModelError("arc chord_error cannot produce a finite tessellation")
    count = max(1, ceil(abs(sweep) / max_step))
    if count + 1 > MAX_PLANAR_BOUNDARY_EDGES:
        raise InvalidModelError("circular arc tessellation exceeds the planar boundary resource limit")
    samples = [start]
    for index in range(1, count):
        angle = start_angle + sweep * index / count
        samples.append(Vec2(
            center.x + radius * cos(angle),
            center.y + radius * sin(angle),
        ))
    samples.append(end)
    return tuple(samples)


def _cycle_points(
    cycle: tuple[_BoundaryEdge, ...],
    sketch: ParametricSketch,
    point_by_id: dict[str, Vec2],
    arc_by_id: dict[str, SketchArc],
    *,
    chord_error: float,
) -> tuple[Vec2, ...]:
    output: list[Vec2] = []
    for edge in cycle:
        if edge.kind == "segment":
            samples = (point_by_id[edge.start_point_id], point_by_id[edge.end_point_id])
        else:
            arc = arc_by_id[edge.edge_id]
            samples = _arc_points(arc, point_by_id, chord_error=chord_error)
            if edge.start_point_id != arc.start_point_id:
                samples = tuple(reversed(samples))
        if samples[0] != point_by_id[edge.start_point_id] or samples[-1] != point_by_id[edge.end_point_id]:
            raise InvalidModelError("sketch boundary edge endpoints do not match the solved sketch")
        if not output:
            output.extend(samples[:-1])
        else:
            if output[-1] != samples[0]:
                raise InvalidModelError("sketch boundary edges do not share the same solved endpoint")
            output.extend(samples[1:-1])
    if len(output) < 3:
        raise InvalidModelError("tessellated sketch loop requires at least three vertices")
    return tuple(output)


def sketch_to_planar_regions(
    sketch: ParametricSketch,
    solved: ParametricSketchSolveResult,
    *,
    chord_error: float = DEFAULT_ARC_CHORD_ERROR,
) -> SketchRegionConversionResult:
    """Convert converged closed sketch loops to canonical PlanarRegion records.

    Arc chord error is expressed in the sketch length unit. Curves are approximated
    by deterministic line segments; PlanarRegion validation then checks the
    resulting polygon topology exactly for the represented binary64 coordinates.
    """
    if not isinstance(sketch, ParametricSketch) or not isinstance(solved, ParametricSketchSolveResult):
        raise InvalidModelError("sketch_to_planar_regions requires a sketch and its solve result")
    if isinstance(chord_error, bool) or not isinstance(chord_error, (int, float)) or (
        not isfinite(float(chord_error)) or chord_error <= 0
    ):
        raise InvalidModelError("chord_error must be a finite positive length")
    chord_error = float(chord_error)
    if (solved.sketch_id, solved.frame_id, solved.length_unit) != (
        sketch.sketch_id, sketch.frame_id, sketch.length_unit
    ):
        raise InvalidModelError("solved sketch identity, frame and unit must match source sketch")
    if not solved.converged:
        raise InvalidModelError("cannot convert a sketch whose constraints did not converge")
    point_ids = {point.point_id for point in sketch.points}
    solved_points = {point.point_id: point for point in solved.points}
    if set(solved_points) != point_ids:
        raise InvalidModelError("solved sketch point set does not match source sketch")

    point_by_id = {key: Vec2(value.x, value.y) for key, value in solved_points.items()}
    arc_by_id = {arc.arc_id: arc for arc in sketch.arcs}
    cycles = _extract_cycles(sketch)
    loops: list[tuple[Vec2, ...]] = []
    regions_for_validation: list[PlanarRegion] = []
    total_edges = 0
    for index, cycle in enumerate(cycles):
        boundary = _cycle_points(
            cycle, sketch, point_by_id, arc_by_id, chord_error=chord_error
        )
        total_edges += len(boundary)
        if total_edges > MAX_PLANAR_BOUNDARY_EDGES:
            raise InvalidModelError("tessellated sketch exceeds the planar boundary resource limit")
        validation = PlanarRegion(
            f"validation.loop.{index:04d}", sketch.frame_id, sketch.length_unit, boundary
        )
        loops.append(boundary)
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
        key=lambda index: tuple(sorted(
            (float(point.x), float(point.y)) for point in loops[index]
        )),
    )
    output: list[PlanarRegion] = []
    for output_index, outer_index in enumerate(material_indices):
        hole_indices = [
            index for index, parent in enumerate(parents)
            if parent == outer_index and depths[index] == depths[outer_index] + 1
        ]
        outer = canonical_loops[outer_index]
        holes = tuple(canonical_loops[index] for index in sorted(
            hole_indices, key=lambda item: tuple(sorted(
                (float(point.x), float(point.y)) for point in loops[item]
            ))
        ))
        region_id = f"sketch.{sketch_digest[:12]}.region.{output_index:04d}"
        output.append(PlanarRegion(
            region_id, sketch.frame_id, sketch.length_unit, outer, holes
        ))

    return SketchRegionConversionResult(sketch.sketch_id, sketch_digest, tuple(output))
