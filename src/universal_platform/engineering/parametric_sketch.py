"""Versioned, dependency-free parametric 2D sketch constraints.

This first solver adapter intentionally supports points and straight segments only.
It delegates numerical work to the bounded nonlinear equality solver and exposes
rank/termination diagnostics rather than claiming a unique or fully constrained
solution.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import hypot, isfinite
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
class SketchConstraint:
    constraint_id: str
    kind: SketchConstraintKind
    point_ids: tuple[str, ...]
    value: float | None = None
    tolerance: float = 1e-8

    def __post_init__(self) -> None:
        if not isinstance(self.constraint_id, str) or not self.constraint_id.strip():
            raise InvalidModelError("sketch constraint_id must be non-empty")
        if not isinstance(self.kind, SketchConstraintKind):
            raise InvalidModelError("sketch constraint kind is unsupported")
        if not isinstance(self.point_ids, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.point_ids
        ):
            raise InvalidModelError("sketch point_ids must be an immutable tuple of identifiers")
        if self.kind in (SketchConstraintKind.PARALLEL, SketchConstraintKind.PERPENDICULAR, SketchConstraintKind.EQUAL_LENGTH):
            expected = 4
        else:
            expected = 1 if self.kind in (SketchConstraintKind.FIX_X, SketchConstraintKind.FIX_Y) else 2
        if len(self.point_ids) != expected:
            raise InvalidModelError(f"{self.kind.value} requires {expected} point identifier(s)")
        if len(set(self.point_ids)) != len(self.point_ids):
            raise InvalidModelError("a sketch constraint cannot repeat a point")
        needs_value = self.kind in (
            SketchConstraintKind.DISTANCE,
            SketchConstraintKind.HORIZONTAL_DISTANCE,
            SketchConstraintKind.VERTICAL_DISTANCE,
            SketchConstraintKind.FIX_X,
            SketchConstraintKind.FIX_Y,
        )
        if needs_value != (self.value is not None):
            raise InvalidModelError("constraint value is required only for dimensional/fixed constraints")
        if self.value is not None and (
            isinstance(self.value, bool) or not isinstance(self.value, (int, float))
            or not isfinite(float(self.value))
        ):
            raise InvalidModelError("sketch constraint value must be finite")
        if self.kind is SketchConstraintKind.DISTANCE and self.value is not None and self.value < 0:
            raise InvalidModelError("distance must be non-negative")
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

    SCHEMA_VERSION: ClassVar[str] = "1.0"

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
        point_ids = [item.point_id for item in self.points]
        segment_ids = [item.segment_id for item in self.segments]
        constraint_ids = [item.constraint_id for item in self.constraints]
        if len(point_ids) != len(set(point_ids)):
            raise InvalidModelError("sketch point identifiers must be unique")
        if len(segment_ids) != len(set(segment_ids)):
            raise InvalidModelError("sketch segment identifiers must be unique")
        if len(constraint_ids) != len(set(constraint_ids)):
            raise InvalidModelError("sketch constraint identifiers must be unique")
        known = set(point_ids)
        for segment in self.segments:
            if segment.start_point_id not in known or segment.end_point_id not in known:
                raise InvalidModelError("sketch segment references an unknown point")
        for constraint in self.constraints:
            if any(point_id not in known for point_id in constraint.point_ids):
                raise InvalidModelError("sketch constraint references an unknown point")

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
                {"constraint_id": c.constraint_id, "kind": c.kind.value,
                 "point_ids": list(c.point_ids), "value": c.value, "tolerance": float(c.tolerance)}
                for c in self.constraints
            ],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ParametricSketch":
        required = {"schema_version", "sketch_id", "frame_id", "length_unit",
                    "points", "segments", "constraints"}
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("ParametricSketch snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("unsupported ParametricSketch schema_version")
        raw_points, raw_segments, raw_constraints = value["points"], value["segments"], value["constraints"]
        if not isinstance(raw_points, (list, tuple)) or not isinstance(raw_segments, (list, tuple)) or not isinstance(raw_constraints, (list, tuple)):
            raise InvalidModelError("ParametricSketch points, segments and constraints must be arrays")
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
            if not isinstance(raw, Mapping) or set(raw) != {"constraint_id", "kind", "point_ids", "value", "tolerance"}:
                raise InvalidModelError("ParametricSketch constraint has missing or unknown fields")
            if not isinstance(raw["point_ids"], (list, tuple)):
                raise InvalidModelError("ParametricSketch constraint point_ids must be an array")
            try:
                kind = SketchConstraintKind(raw["kind"])
            except (TypeError, ValueError) as exc:
                raise InvalidModelError("unsupported ParametricSketch constraint kind") from exc
            constraints.append(SketchConstraint(
                raw["constraint_id"], kind, tuple(raw["point_ids"]),
                raw["value"], raw["tolerance"],
            ))
        return cls(
            value["sketch_id"], value["frame_id"], value["length_unit"],
            tuple(points), tuple(segments), tuple(constraints),
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
                "2D points and straight segments only; no arcs, splines or construction geometry",
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
    for item in sketch.constraints:
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
