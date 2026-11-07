"""Versioned, dependency-free parametric 2D sketch constraints.

This first solver adapter intentionally supports points and straight segments only.
It delegates numerical work to the bounded nonlinear equality solver and exposes
rank/termination diagnostics rather than claiming a unique or fully constrained
solution.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import atan2, hypot, isfinite
from typing import ClassVar, Mapping

from .errors import InvalidModelError, SolverError
from .quantity import LENGTH, Quantity
from .nonlinear_solver import (
    NonlinearConstraint,
    NonlinearSolveResult,
    NonlinearSolverOptions,
    solve_nonlinear_constraints,
)


class SketchConstraintKind(str, Enum):
    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"
    COINCIDENT = "COINCIDENT"
    DISTANCE = "DISTANCE"
    HORIZONTAL_DISTANCE = "HORIZONTAL_DISTANCE"
    VERTICAL_DISTANCE = "VERTICAL_DISTANCE"
    FIX_X = "FIX_X"
    FIX_Y = "FIX_Y"
    PARALLEL = "PARALLEL"
    PERPENDICULAR = "PERPENDICULAR"
    EQUAL_LENGTH = "EQUAL_LENGTH"
    ANGLE = "ANGLE"
    TANGENT = "TANGENT"
    RADIUS = "RADIUS"


@dataclass(frozen=True, slots=True)
class SketchPoint:
    point_id: str
    x: float
    y: float

    def __post_init__(self) -> None:
        if not isinstance(self.point_id, str) or not self.point_id.strip():
            raise InvalidModelError("sketch point_id must be non-empty")
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not isfinite(float(value)) for value in (self.x, self.y)):
            raise InvalidModelError("sketch point coordinates must be finite numbers")


@dataclass(frozen=True, slots=True)
class SketchSegment:
    segment_id: str
    start_point_id: str
    end_point_id: str

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.segment_id, self.start_point_id, self.end_point_id)):
            raise InvalidModelError("sketch segment identifiers must be non-empty")
        if self.start_point_id == self.end_point_id:
            raise InvalidModelError("sketch segment endpoints must be distinct")


@dataclass(frozen=True, slots=True)
class SketchArc:
    arc_id: str
    center_point_id: str
    start_point_id: str
    end_point_id: str
    clockwise: bool = False

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.arc_id, self.center_point_id,
                             self.start_point_id, self.end_point_id)):
            raise InvalidModelError("sketch arc identifiers must be non-empty")
        if len({self.center_point_id, self.start_point_id, self.end_point_id}) != 3:
            raise InvalidModelError("sketch arc center, start and end point references must be distinct")
        if not isinstance(self.clockwise, bool):
            raise InvalidModelError("sketch arc clockwise must be boolean")


@dataclass(frozen=True, slots=True)
class SketchConstraint:
    constraint_id: str
    kind: SketchConstraintKind
    point_ids: tuple[str, ...]
    value: float | None = None
    tolerance: float = 1e-8
    segment_ids: tuple[str, ...] = ()
    arc_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.constraint_id, str) or not self.constraint_id.strip():
            raise InvalidModelError("sketch constraint_id must be non-empty")
        if not isinstance(self.kind, SketchConstraintKind):
            raise InvalidModelError("sketch constraint kind is unsupported")
        if not isinstance(self.point_ids, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.point_ids
        ):
            raise InvalidModelError("sketch point_ids must be an immutable tuple of identifiers")
        if self.kind in (SketchConstraintKind.ANGLE, SketchConstraintKind.RADIUS):
            expected = 0
        elif self.kind is SketchConstraintKind.TANGENT:
            expected = 1
        elif self.kind in (SketchConstraintKind.PARALLEL, SketchConstraintKind.PERPENDICULAR, SketchConstraintKind.EQUAL_LENGTH):
            expected = 4
        else:
            expected = 1 if self.kind in (SketchConstraintKind.FIX_X, SketchConstraintKind.FIX_Y) else 2
        if len(self.point_ids) != expected:
            raise InvalidModelError(f"{self.kind.value} requires {expected} point identifier(s)")
        if not isinstance(self.segment_ids, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.segment_ids
        ):
            raise InvalidModelError("sketch segment_ids must be an immutable tuple of identifiers")
        expected_segments = 2 if self.kind is SketchConstraintKind.ANGLE else (
            1 if self.kind is SketchConstraintKind.TANGENT else 0
        )
        if len(self.segment_ids) != expected_segments or len(set(self.segment_ids)) != len(self.segment_ids):
            raise InvalidModelError(f"{self.kind.value} requires {expected_segments} distinct segment identifier(s)")
        if not isinstance(self.arc_ids, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.arc_ids
        ):
            raise InvalidModelError("sketch arc_ids must be an immutable tuple of identifiers")
        expected_arcs = 1 if self.kind in (SketchConstraintKind.TANGENT, SketchConstraintKind.RADIUS) else 0
        if len(self.arc_ids) != expected_arcs or len(set(self.arc_ids)) != len(self.arc_ids):
            raise InvalidModelError(f"{self.kind.value} requires {expected_arcs} distinct arc identifier(s)")
        if len(set(self.point_ids)) != len(self.point_ids):
            raise InvalidModelError("a sketch constraint cannot repeat a point")
        needs_value = self.kind in (
            SketchConstraintKind.DISTANCE,
            SketchConstraintKind.HORIZONTAL_DISTANCE,
            SketchConstraintKind.VERTICAL_DISTANCE,
            SketchConstraintKind.FIX_X,
            SketchConstraintKind.FIX_Y,
            SketchConstraintKind.ANGLE,
            SketchConstraintKind.RADIUS,
        )
        if needs_value != (self.value is not None):
            raise InvalidModelError("constraint value is required only for dimensional/fixed/angle/radius constraints")
        if self.value is not None and (
            isinstance(self.value, bool) or not isinstance(self.value, (int, float))
            or not isfinite(float(self.value))
        ):
            raise InvalidModelError("sketch constraint value must be finite")
        if self.kind is SketchConstraintKind.DISTANCE and self.value is not None and self.value < 0:
            raise InvalidModelError("distance must be non-negative")
        if self.kind is SketchConstraintKind.ANGLE and self.value is not None and not -3.141592653589793 <= self.value <= 3.141592653589793:
            raise InvalidModelError("angle must be expressed in radians within [-pi, pi]")
        if self.kind is SketchConstraintKind.RADIUS and self.value is not None and self.value <= 0:
            raise InvalidModelError("radius must be finite and positive")
        if isinstance(self.tolerance, bool) or not isinstance(self.tolerance, (int, float)) or (
            not isfinite(float(self.tolerance)) or self.tolerance <= 0
        ):
            raise InvalidModelError("sketch constraint tolerance must be finite and positive")


@dataclass(frozen=True, slots=True)
class ParametricSketch:
    sketch_id: str
    frame_id: str
    length_unit: str
    points: tuple[SketchPoint, ...]
    segments: tuple[SketchSegment, ...] = ()
    constraints: tuple[SketchConstraint, ...] = ()
    arcs: tuple[SketchArc, ...] = ()

    SCHEMA_VERSION: ClassVar[str] = "1.2"
    SUPPORTED_SCHEMA_VERSIONS: ClassVar[tuple[str, ...]] = ("1.0", "1.1", "1.2")

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.sketch_id, self.frame_id, self.length_unit)):
            raise InvalidModelError("sketch_id, frame_id and length_unit are required")
        try:
            if Quantity.of(1.0, self.length_unit).dimension != LENGTH:
                raise InvalidModelError("sketch length_unit must have length dimension")
        except InvalidModelError:
            raise
        except Exception as exc:
            raise InvalidModelError(f"unsupported sketch length_unit: {self.length_unit}") from exc
        if not isinstance(self.points, tuple) or not self.points or any(
            not isinstance(item, SketchPoint) for item in self.points
        ):
            raise InvalidModelError("a sketch requires an immutable tuple of points")
        if not isinstance(self.segments, tuple) or any(
            not isinstance(item, SketchSegment) for item in self.segments
        ):
            raise InvalidModelError("segments must be an immutable tuple of SketchSegment")
        if not isinstance(self.constraints, tuple) or any(
            not isinstance(item, SketchConstraint) for item in self.constraints
        ):
            raise InvalidModelError("constraints must be an immutable tuple of SketchConstraint")
        if not isinstance(self.arcs, tuple) or any(
            not isinstance(item, SketchArc) for item in self.arcs
        ):
            raise InvalidModelError("arcs must be an immutable tuple of SketchArc")
        point_ids = [item.point_id for item in self.points]
        segment_ids = [item.segment_id for item in self.segments]
        constraint_ids = [item.constraint_id for item in self.constraints]
        arc_ids = [item.arc_id for item in self.arcs]
        if len(point_ids) != len(set(point_ids)):
            raise InvalidModelError("sketch point identifiers must be unique")
        if len(segment_ids) != len(set(segment_ids)):
            raise InvalidModelError("sketch segment identifiers must be unique")
        if len(constraint_ids) != len(set(constraint_ids)):
            raise InvalidModelError("sketch constraint identifiers must be unique")
        if len(arc_ids) != len(set(arc_ids)):
            raise InvalidModelError("sketch arc identifiers must be unique")
        known = set(point_ids)
        for segment in self.segments:
            if segment.start_point_id not in known or segment.end_point_id not in known:
                raise InvalidModelError("sketch segment references an unknown point")
        for arc in self.arcs:
            if any(point_id not in known for point_id in (
                arc.center_point_id, arc.start_point_id, arc.end_point_id
            )):
                raise InvalidModelError("sketch arc references an unknown point")
            center = next(point for point in self.points if point.point_id == arc.center_point_id)
            start = next(point for point in self.points if point.point_id == arc.start_point_id)
            end = next(point for point in self.points if point.point_id == arc.end_point_id)
            sx, sy = start.x - center.x, start.y - center.y
            ex, ey = end.x - center.x, end.y - center.y
            start_radius, end_radius = hypot(sx, sy), hypot(ex, ey)
            if min(start_radius, end_radius, hypot(end.x - start.x, end.y - start.y)) <= 1e-12:
                raise InvalidModelError("sketch arc requires distinct, non-degenerate radial endpoints")
            cross, dot = sx * ey - sy * ex, sx * ex + sy * ey
            if abs(cross) <= 1e-12 * start_radius * end_radius and dot > 0:
                raise InvalidModelError("sketch arc start and end must define a non-zero angular sweep")
        known_segments, known_arcs = set(segment_ids), set(arc_ids)
        for constraint in self.constraints:
            if any(point_id not in known for point_id in constraint.point_ids):
                raise InvalidModelError("sketch constraint references an unknown point")
            if any(segment_id not in known_segments for segment_id in constraint.segment_ids):
                raise InvalidModelError("sketch constraint references an unknown segment")
            if any(arc_id not in known_arcs for arc_id in constraint.arc_ids):
                raise InvalidModelError("sketch constraint references an unknown arc")
            if constraint.kind is SketchConstraintKind.TANGENT:
                segment = next(item for item in self.segments if item.segment_id == constraint.segment_ids[0])
                arc = next(item for item in self.arcs if item.arc_id == constraint.arc_ids[0])
                contact = constraint.point_ids[0]
                if contact not in (segment.start_point_id, segment.end_point_id) or contact not in (
                    arc.start_point_id, arc.end_point_id
                ):
                    raise InvalidModelError("tangent contact point must be shared by the segment and arc endpoints")
        for arc in self.arcs:
            radius_count = sum(
                constraint.kind is SketchConstraintKind.RADIUS and constraint.arc_ids == (arc.arc_id,)
                for constraint in self.constraints
            )
            if radius_count != 1:
                raise InvalidModelError("each sketch arc requires exactly one RADIUS constraint")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "sketch_id": self.sketch_id,
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "points": [{"point_id": p.point_id, "x": float(p.x), "y": float(p.y)} for p in self.points],
            "segments": [
                {"segment_id": s.segment_id, "start_point_id": s.start_point_id,
                 "end_point_id": s.end_point_id} for s in self.segments
            ],
            "constraints": [
                ({"constraint_id": c.constraint_id, "kind": c.kind.value,
                  "point_ids": list(c.point_ids), "value": c.value, "tolerance": float(c.tolerance),
                  **({"segment_ids": list(c.segment_ids)} if c.segment_ids else {}),
                  **({"arc_ids": list(c.arc_ids)} if c.arc_ids else {})})
                for c in self.constraints
            ],
            "arcs": [
                {"arc_id": arc.arc_id, "center_point_id": arc.center_point_id,
                 "start_point_id": arc.start_point_id, "end_point_id": arc.end_point_id,
                 "clockwise": arc.clockwise}
                for arc in self.arcs
            ],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ParametricSketch":
        required = {"schema_version", "sketch_id", "frame_id", "length_unit",
                    "points", "segments", "constraints"}
        if not isinstance(value, Mapping) or value.get("schema_version") not in cls.SUPPORTED_SCHEMA_VERSIONS:
            raise InvalidModelError("ParametricSketch snapshot has missing or unsupported schema_version")
        schema_version = value["schema_version"]
        expected_fields = required | ({"arcs"} if schema_version == "1.2" else set())
        if set(value) != expected_fields:
            raise InvalidModelError("ParametricSketch snapshot has missing or unknown fields")
        raw_points, raw_segments, raw_constraints = value["points"], value["segments"], value["constraints"]
        raw_arcs = value.get("arcs", [])
        if (not isinstance(raw_points, (list, tuple)) or not isinstance(raw_segments, (list, tuple))
                or not isinstance(raw_constraints, (list, tuple)) or not isinstance(raw_arcs, (list, tuple))):
            raise InvalidModelError("ParametricSketch points, segments, constraints and arcs must be arrays")
        points = []
        for raw in raw_points:
            if not isinstance(raw, Mapping) or set(raw) != {"point_id", "x", "y"}:
                raise InvalidModelError("ParametricSketch point requires exactly point_id, x and y")
            points.append(SketchPoint(raw["point_id"], raw["x"], raw["y"]))
        segments = []
        for raw in raw_segments:
            if not isinstance(raw, Mapping) or set(raw) != {"segment_id", "start_point_id", "end_point_id"}:
                raise InvalidModelError("ParametricSketch segment has missing or unknown fields")
            segments.append(SketchSegment(raw["segment_id"], raw["start_point_id"], raw["end_point_id"]))
        constraints = []
        for raw in raw_constraints:
            required_constraint_fields = {"constraint_id", "kind", "point_ids", "value", "tolerance"}
            allowed_constraint_fields = (
                required_constraint_fields,
                required_constraint_fields | {"segment_ids"},
                required_constraint_fields | {"arc_ids"},
                required_constraint_fields | {"segment_ids", "arc_ids"},
            )
            if not isinstance(raw, Mapping) or set(raw) not in allowed_constraint_fields:
                raise InvalidModelError("ParametricSketch constraint has missing or unknown fields")
            if schema_version == "1.0" and ({"segment_ids", "arc_ids"} & set(raw)):
                raise InvalidModelError("ParametricSketch v1.0 cannot contain segment_ids or arc_ids")
            if schema_version == "1.1" and "arc_ids" in raw:
                raise InvalidModelError("ParametricSketch v1.1 cannot contain arc_ids")
            if not isinstance(raw["point_ids"], (list, tuple)):
                raise InvalidModelError("ParametricSketch constraint point_ids must be an array")
            try:
                kind = SketchConstraintKind(raw["kind"])
            except (TypeError, ValueError) as exc:
                raise InvalidModelError("unsupported ParametricSketch constraint kind") from exc
            segment_ids, arc_ids = raw.get("segment_ids", ()), raw.get("arc_ids", ())
            if not isinstance(segment_ids, (list, tuple)) or not isinstance(arc_ids, (list, tuple)):
                raise InvalidModelError("ParametricSketch constraint segment_ids and arc_ids must be arrays")
            constraints.append(SketchConstraint(
                raw["constraint_id"], kind, tuple(raw["point_ids"]),
                raw["value"], raw["tolerance"], tuple(segment_ids), tuple(arc_ids),
            ))
        arcs = []
        for raw in raw_arcs:
            if not isinstance(raw, Mapping) or set(raw) != {
                "arc_id", "center_point_id", "start_point_id", "end_point_id", "clockwise"
            }:
                raise InvalidModelError("ParametricSketch arc has missing or unknown fields")
            arcs.append(SketchArc(
                raw["arc_id"], raw["center_point_id"], raw["start_point_id"],
                raw["end_point_id"], raw["clockwise"],
            ))
        return cls(
            value["sketch_id"], value["frame_id"], value["length_unit"],
            tuple(points), tuple(segments), tuple(constraints), tuple(arcs),
        )


@dataclass(frozen=True, slots=True)
class ParametricSketchSolveResult:
    sketch_id: str
    frame_id: str
    length_unit: str
    points: tuple[SketchPoint, ...]
    solver: NonlinearSolveResult

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    @property
    def converged(self) -> bool:
        return self.solver.all_constraints_satisfied

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "sketch_id": self.sketch_id,
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "points": [{"point_id": p.point_id, "x": float(p.x), "y": float(p.y)} for p in self.points],
            "solver": self.solver.to_dict(),
            "converged": self.converged,
            "limitations": [
                "2D points, straight segments and circular-arc references; no splines or construction geometry",
                "Local nonlinear solve; no uniqueness or global convergence guarantee",
                "Rank is threshold-dependent; underconstrained sketches may have multiple valid solutions",
                "No automatic constraint inference, drag solver, or CAD feature history",
            ],
        }


def solve_parametric_sketch(
    sketch: ParametricSketch,
    *,
    options: NonlinearSolverOptions | None = None,
) -> ParametricSketchSolveResult:
    """Solve supported sketch equalities from the supplied initial coordinates."""
    if not isinstance(sketch, ParametricSketch):
        raise InvalidModelError("solve_parametric_sketch requires a ParametricSketch")
    names = tuple(
        name for point in sketch.points
        for name in (f"{point.point_id}.x", f"{point.point_id}.y")
    )
    initial = {
        name: value
        for point in sketch.points
        for name, value in ((f"{point.point_id}.x", float(point.x)),
                            (f"{point.point_id}.y", float(point.y)))
    }
    point_by_id = {point.point_id: point for point in sketch.points}
    segment_by_id = {segment.segment_id: segment for segment in sketch.segments}
    arc_by_id = {arc.arc_id: arc for arc in sketch.arcs}
    equations: list[NonlinearConstraint] = []

    def coordinate(state: Mapping[str, float], point_id: str, axis: str) -> float:
        return state[f"{point_id}.{axis}"]

    for item in sketch.constraints:
        ids = item.point_ids
        tol = float(item.tolerance)
        if item.kind is SketchConstraintKind.HORIZONTAL:
            equations.append(NonlinearConstraint(
                item.constraint_id, lambda v, a=ids[0], b=ids[1]: coordinate(v, b, "y") - coordinate(v, a, "y"),
                tolerance=tol,
            ))
        elif item.kind is SketchConstraintKind.VERTICAL:
            equations.append(NonlinearConstraint(
                item.constraint_id, lambda v, a=ids[0], b=ids[1]: coordinate(v, b, "x") - coordinate(v, a, "x"),
                tolerance=tol,
            ))
        elif item.kind is SketchConstraintKind.COINCIDENT:
            equations.extend((
                NonlinearConstraint(item.constraint_id + "::x",
                    lambda v, a=ids[0], b=ids[1]: coordinate(v, b, "x") - coordinate(v, a, "x"),
                    tolerance=tol),
                NonlinearConstraint(item.constraint_id + "::y",
                    lambda v, a=ids[0], b=ids[1]: coordinate(v, b, "y") - coordinate(v, a, "y"),
                    tolerance=tol),
            ))
        elif item.kind in (SketchConstraintKind.PARALLEL, SketchConstraintKind.PERPENDICULAR, SketchConstraintKind.EQUAL_LENGTH):
            a, b, c, d = ids
            first = point_by_id[b]
            first_start = point_by_id[a]
            second_start = point_by_id[c]
            second_end = point_by_id[d]
            if hypot(first.x - first_start.x, first.y - first_start.y) <= 1e-12 or hypot(
                second_end.x - second_start.x, second_end.y - second_start.y
            ) <= 1e-12:
                raise InvalidModelError("relational sketch constraints require non-degenerate segment vectors")
            if item.kind is SketchConstraintKind.PARALLEL:
                residual = lambda v, a=a, b=b, c=c, d=d: (
                    (coordinate(v, b, "x") - coordinate(v, a, "x")) *
                    (coordinate(v, d, "y") - coordinate(v, c, "y")) -
                    (coordinate(v, b, "y") - coordinate(v, a, "y")) *
                    (coordinate(v, d, "x") - coordinate(v, c, "x"))
                )
            elif item.kind is SketchConstraintKind.PERPENDICULAR:
                residual = lambda v, a=a, b=b, c=c, d=d: (
                    (coordinate(v, b, "x") - coordinate(v, a, "x")) *
                    (coordinate(v, d, "x") - coordinate(v, c, "x")) +
                    (coordinate(v, b, "y") - coordinate(v, a, "y")) *
                    (coordinate(v, d, "y") - coordinate(v, c, "y"))
                )
            else:
                residual = lambda v, a=a, b=b, c=c, d=d: (
                    hypot(coordinate(v, b, "x") - coordinate(v, a, "x"),
                          coordinate(v, b, "y") - coordinate(v, a, "y")) -
                    hypot(coordinate(v, d, "x") - coordinate(v, c, "x"),
                          coordinate(v, d, "y") - coordinate(v, c, "y"))
                )
            equations.append(NonlinearConstraint(item.constraint_id, residual, tolerance=tol))
        elif item.kind is SketchConstraintKind.RADIUS:
            arc = arc_by_id[item.arc_ids[0]]
            center_id, start_id, end_id = (
                arc.center_point_id, arc.start_point_id, arc.end_point_id
            )
            center, start, end = point_by_id[center_id], point_by_id[start_id], point_by_id[end_id]
            if hypot(start.x - center.x, start.y - center.y) <= 1e-12 or hypot(
                end.x - center.x, end.y - center.y
            ) <= 1e-12:
                raise InvalidModelError("radius constraint requires non-degenerate arc endpoints")
            target = float(item.value)
            equations.extend((
                NonlinearConstraint(
                    item.constraint_id + "::start",
                    lambda v, c=center_id, p=start_id, r=target: hypot(
                        coordinate(v, p, "x") - coordinate(v, c, "x"),
                        coordinate(v, p, "y") - coordinate(v, c, "y"),
                    ) - r,
                    tolerance=tol,
                ),
                NonlinearConstraint(
                    item.constraint_id + "::end",
                    lambda v, c=center_id, p=end_id, r=target: hypot(
                        coordinate(v, p, "x") - coordinate(v, c, "x"),
                        coordinate(v, p, "y") - coordinate(v, c, "y"),
                    ) - r,
                    tolerance=tol,
                ),
            ))
        elif item.kind is SketchConstraintKind.TANGENT:
            segment = segment_by_id[item.segment_ids[0]]
            arc = arc_by_id[item.arc_ids[0]]
            contact = item.point_ids[0]
            line_start, line_end, center = (
                segment.start_point_id, segment.end_point_id, arc.center_point_id
            )
            line = (
                point_by_id[line_end].x - point_by_id[line_start].x,
                point_by_id[line_end].y - point_by_id[line_start].y,
            )
            radial = (
                point_by_id[contact].x - point_by_id[center].x,
                point_by_id[contact].y - point_by_id[center].y,
            )
            if hypot(*line) <= 1e-12 or hypot(*radial) <= 1e-12:
                raise InvalidModelError("tangent constraint requires non-degenerate line and radius vectors")

            def tangent_residual(v, a=line_start, b=line_end, c=center, p=contact):
                ux = coordinate(v, b, "x") - coordinate(v, a, "x")
                uy = coordinate(v, b, "y") - coordinate(v, a, "y")
                rx = coordinate(v, p, "x") - coordinate(v, c, "x")
                ry = coordinate(v, p, "y") - coordinate(v, c, "y")
                denominator = hypot(ux, uy) * hypot(rx, ry)
                return (ux * rx + uy * ry) / max(denominator, 1e-24)

            equations.append(NonlinearConstraint(item.constraint_id, tangent_residual, tolerance=tol))
        elif item.kind is SketchConstraintKind.ANGLE:
            first, second = (segment_by_id[key] for key in item.segment_ids)
            a, b = first.start_point_id, first.end_point_id
            c, d = second.start_point_id, second.end_point_id
            first_length = hypot(point_by_id[b].x - point_by_id[a].x, point_by_id[b].y - point_by_id[a].y)
            second_length = hypot(point_by_id[d].x - point_by_id[c].x, point_by_id[d].y - point_by_id[c].y)
            if first_length <= 1e-12 or second_length <= 1e-12:
                raise InvalidModelError("angle constraint requires non-degenerate segments")
            target = float(item.value)

            def angle_residual(v, a=a, b=b, c=c, d=d, target=target):
                ux = coordinate(v, b, "x") - coordinate(v, a, "x")
                uy = coordinate(v, b, "y") - coordinate(v, a, "y")
                vx = coordinate(v, d, "x") - coordinate(v, c, "x")
                vy = coordinate(v, d, "y") - coordinate(v, c, "y")
                return atan2(ux * vy - uy * vx, ux * vx + uy * vy) - target

            equations.append(NonlinearConstraint(item.constraint_id, angle_residual, tolerance=tol))
        elif item.kind is SketchConstraintKind.DISTANCE:
            target = float(item.value)
            equations.append(NonlinearConstraint(
                item.constraint_id,
                lambda v, a=ids[0], b=ids[1], d=target: hypot(
                    coordinate(v, b, "x") - coordinate(v, a, "x"),
                    coordinate(v, b, "y") - coordinate(v, a, "y"),
                ) - d,
                tolerance=tol,
            ))
        elif item.kind is SketchConstraintKind.HORIZONTAL_DISTANCE:
            target = float(item.value)
            equations.append(NonlinearConstraint(
                item.constraint_id,
                lambda v, a=ids[0], b=ids[1], d=target: coordinate(v, b, "x") - coordinate(v, a, "x") - d,
                tolerance=tol,
            ))
        elif item.kind is SketchConstraintKind.VERTICAL_DISTANCE:
            target = float(item.value)
            equations.append(NonlinearConstraint(
                item.constraint_id,
                lambda v, a=ids[0], b=ids[1], d=target: coordinate(v, b, "y") - coordinate(v, a, "y") - d,
                tolerance=tol,
            ))
        elif item.kind is SketchConstraintKind.FIX_X:
            target = float(item.value)
            equations.append(NonlinearConstraint(
                item.constraint_id,
                lambda v, a=ids[0], d=target: coordinate(v, a, "x") - d,
                tolerance=tol,
            ))
        elif item.kind is SketchConstraintKind.FIX_Y:
            target = float(item.value)
            equations.append(NonlinearConstraint(
                item.constraint_id,
                lambda v, a=ids[0], d=target: coordinate(v, a, "y") - d,
                tolerance=tol,
            ))

    if not equations:
        raise SolverError("Parametric sketch requires at least one supported constraint")
    solved = solve_nonlinear_constraints(names, initial, equations, options=options)
    values = solved.values
    for arc in sketch.arcs:
        center, start, end = arc.center_point_id, arc.start_point_id, arc.end_point_id
        start_radius = hypot(values[f"{start}.x"] - values[f"{center}.x"], values[f"{start}.y"] - values[f"{center}.y"])
        end_radius = hypot(values[f"{end}.x"] - values[f"{center}.x"], values[f"{end}.y"] - values[f"{center}.y"])
        chord = hypot(values[f"{end}.x"] - values[f"{start}.x"], values[f"{end}.y"] - values[f"{start}.y"])
        if min(start_radius, end_radius, chord) <= 1e-12:
            raise SolverError("arc constraints produced degenerate radial endpoints or a zero-length chord")
    for item in sketch.constraints:
        if item.kind is SketchConstraintKind.RADIUS:
            arc = arc_by_id[item.arc_ids[0]]
            center, start, end = (
                arc.center_point_id, arc.start_point_id, arc.end_point_id
            )
            for point_id in (start, end):
                if hypot(values[f"{point_id}.x"] - values[f"{center}.x"],
                         values[f"{point_id}.y"] - values[f"{center}.y"]) <= 1e-12:
                    raise SolverError("radius constraint produced a degenerate arc endpoint")
        if item.kind is SketchConstraintKind.TANGENT:
            segment = segment_by_id[item.segment_ids[0]]
            arc = arc_by_id[item.arc_ids[0]]
            a, b, c, p = (
                segment.start_point_id, segment.end_point_id,
                arc.center_point_id, item.point_ids[0]
            )
            line_length = hypot(values[f"{b}.x"] - values[f"{a}.x"], values[f"{b}.y"] - values[f"{a}.y"])
            radial_length = hypot(values[f"{p}.x"] - values[f"{c}.x"], values[f"{p}.y"] - values[f"{c}.y"])
            if line_length <= 1e-12 or radial_length <= 1e-12:
                raise SolverError("tangent constraint produced a degenerate line or radius vector")
        if item.kind is SketchConstraintKind.ANGLE:
            first, second = (segment_by_id[key] for key in item.segment_ids)
            for segment in (first, second):
                a, b = segment.start_point_id, segment.end_point_id
                if hypot(values[f"{b}.x"] - values[f"{a}.x"], values[f"{b}.y"] - values[f"{a}.y"]) <= 1e-12:
                    raise SolverError("angle constraint produced a degenerate segment")
        if item.kind in (SketchConstraintKind.PARALLEL, SketchConstraintKind.PERPENDICULAR, SketchConstraintKind.EQUAL_LENGTH):
            a, b, c, d = item.point_ids
            first_length = hypot(values[f"{b}.x"] - values[f"{a}.x"], values[f"{b}.y"] - values[f"{a}.y"])
            second_length = hypot(values[f"{d}.x"] - values[f"{c}.x"], values[f"{d}.y"] - values[f"{c}.y"])
            if first_length <= 1e-12 or second_length <= 1e-12:
                raise SolverError("relational sketch constraint produced a degenerate segment")
    points = tuple(
        SketchPoint(point.point_id, values[f"{point.point_id}.x"], values[f"{point.point_id}.y"])
        for point in sketch.points
    )
    return ParametricSketchSolveResult(
        sketch.sketch_id, sketch.frame_id, sketch.length_unit, points, solved
    )
