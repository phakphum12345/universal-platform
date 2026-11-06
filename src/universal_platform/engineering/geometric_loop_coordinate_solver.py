"""Local generalized-coordinate fitting against geometric joint constraints.

Body poses are fixed caller inputs. The solver adjusts only declared
coordinates, uses their explicit bounds/scales, and reports local convergence
without claiming that arbitrary mechanism configurations are reachable.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .errors import InvalidModelError
from .geometric_loop_closure import (
    GeometricLoopClosureResult,
    evaluate_geometric_loop_closure,
)
from .joint_constraints import generate_joint_constraints
from .mechanism_loops import analyze_loop_topology
from .mechanism_model import MechanismModel
from .nonlinear_solver import (
    NonlinearConstraint,
    NonlinearSolveResult,
    NonlinearSolveStatus,
    NonlinearSolverOptions,
    VariableBound,
    solve_nonlinear_constraints,
)
from .transforms import RigidTransform


class GeometricLoopCoordinateSolveStatus(str, Enum):
    CONVERGED = "CONVERGED"
    NOT_CONVERGED = "NOT_CONVERGED"


@dataclass(frozen=True, slots=True)
class GeometricLoopCoordinateSolveResult:
    schema_version: str
    status: GeometricLoopCoordinateSolveStatus
    solver_result: NonlinearSolveResult
    geometric_evaluation: GeometricLoopClosureResult
    coordinate_ids: tuple[str, ...]
    limitations: tuple[str, ...] = (
        "Only generalized-coordinate values are solver variables; body poses are fixed caller inputs",
        "The solver is local damped least squares and does not establish global reachability or uniqueness",
        "A failed solve is NOT_CONVERGED, not proof of geometric unreachability",
        "No branch discovery, collision/contact, dynamics, physical feasibility or certification",
    )

    @property
    def coordinate_values(self) -> dict[str, float]:
        return self.solver_result.values

    @property
    def all_satisfied(self) -> bool:
        return (
            self.status is GeometricLoopCoordinateSolveStatus.CONVERGED
            and self.solver_result.all_constraints_satisfied
            and self.geometric_evaluation.all_satisfied
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "all_satisfied": self.all_satisfied,
            "coordinate_ids": list(self.coordinate_ids),
            "coordinate_values": self.coordinate_values,
            "solver_result": self.solver_result.to_dict(),
            "geometric_evaluation": self.geometric_evaluation.to_dict(),
            "limitations": list(self.limitations),
        }


def solve_geometric_loop_coordinates(
    model: MechanismModel,
    body_poses: Mapping[str, RigidTransform],
    initial_coordinate_values: Mapping[str, float],
    *,
    translation_tolerance_m: float = 1e-8,
    rotation_tolerance_rad: float = 1e-8,
    options: NonlinearSolverOptions | None = None,
) -> GeometricLoopCoordinateSolveResult:
    """Fit generalized coordinates to fixed body poses using all joint rows.

    Every joint residual participates in the solve, not only loop-closing
    edges. This prevents an apparently closed cycle from hiding an invalid
    spanning-tree joint. Coordinate bounds and characteristic scales are
    forwarded from the normalized model to the nonlinear solver.
    """
    topology = analyze_loop_topology(model)
    if not topology.loops:
        raise InvalidModelError("Geometric loop coordinate solving requires a graph loop")
    generated = generate_joint_constraints(
        model,
        translation_tolerance_m=translation_tolerance_m,
        rotation_tolerance_rad=rotation_tolerance_rad,
    )
    # Validate exact input coverage, finiteness, limits, body frames and placements
    # before handing any callbacks to the numerical solver.
    generated.evaluate(body_poses, initial_coordinate_values)

    coordinates = {
        item.coordinate_id: item for item in model.generalized_coordinates
    }
    variable_names = tuple(sorted(coordinates))
    if not variable_names:
        raise InvalidModelError(
            "Geometric loop coordinate solving requires generalized coordinates"
        )
    if options is not None and options.jacobian_method.value == "analytic":
        raise InvalidModelError(
            "Geometric loop coordinate solving supports solver finite differences only"
        )

    definitions = generated.definitions
    cache_key: tuple[float, ...] | None = None
    cache_values: dict[str, float] = {}

    def make_residual(constraint_id: str):
        def residual(state: Mapping[str, float]) -> float:
            nonlocal cache_key, cache_values
            key = tuple(float(state[name]) for name in variable_names)
            if key != cache_key:
                current = {name: state[name] for name in variable_names}
                evaluation = generated.evaluate(body_poses, current)
                cache_values = {
                    item.constraint_id: item.value for item in evaluation.residuals
                }
                cache_key = key
            return cache_values[constraint_id]
        return residual

    constraints = tuple(
        NonlinearConstraint(
            item.constraint_id,
            make_residual(item.constraint_id),
            tolerance=item.tolerance,
            scale=item.tolerance,
        )
        for item in definitions
    )
    bounds = {
        name: VariableBound(
            lower=coordinates[name].lower_limit,
            upper=coordinates[name].upper_limit,
        )
        for name in variable_names
    }
    variable_scales = {
        name: float(coordinates[name].scale) for name in variable_names
    }
    solved = solve_nonlinear_constraints(
        variable_names,
        initial_coordinate_values,
        constraints,
        bounds=bounds,
        options=options,
        variable_scales=variable_scales,
    )
    geometric = evaluate_geometric_loop_closure(
        model,
        body_poses,
        solved.values,
        translation_tolerance_m=translation_tolerance_m,
        rotation_tolerance_rad=rotation_tolerance_rad,
    )
    status = (
        GeometricLoopCoordinateSolveStatus.CONVERGED
        if solved.status is NonlinearSolveStatus.CONVERGED and geometric.all_satisfied
        else GeometricLoopCoordinateSolveStatus.NOT_CONVERGED
    )
    return GeometricLoopCoordinateSolveResult(
        "1.0", status, solved, geometric, variable_names
    )
