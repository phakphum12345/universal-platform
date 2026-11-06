"""Integrated position, mobility, velocity and acceleration analysis.

The pipeline composes the existing normalized mechanism, explicit loop residual
bridge and mobility Jacobian contract. It does not synthesize geometric joint
equations, Jacobians or time-derivative bias terms: those remain explicit,
caller-supplied engineering inputs with provenance labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Mapping

from .errors import InvalidModelError
from .mechanism_loops import (
    LoopClosureConstraint,
    LoopClosureResult,
    LoopClosureStatus,
    solve_mechanism_loops,
)
from .mechanism_mobility import (
    ConstraintJacobian,
    MobilityAnalysisResult,
    MobilityFormulation,
    analyze_mechanism_mobility,
)
from .mechanism_model import MechanismModel
from .nonlinear_solver import (
    NonlinearConstraint,
    NonlinearSolveResult,
    NonlinearSolveStatus,
    NonlinearSolverOptions,
    solve_nonlinear_constraints,
)


RESULT_SCHEMA_VERSION = "1.0"


class BranchContinuityStatus(str, Enum):
    INITIAL_CONFIGURATION = "INITIAL_CONFIGURATION"
    CONTINUOUS = "CONTINUOUS"
    BRANCH_SWITCH = "BRANCH_SWITCH"


@dataclass(frozen=True, slots=True)
class MechanismKinematicsInput:
    """Complete caller-supplied data for one mechanism configuration."""

    model: MechanismModel
    ground_link_id: str
    formulation: MobilityFormulation
    coordinate_ids: tuple[str, ...]
    configuration_id: str
    branch_id: str
    initial_coordinates: Mapping[str, float]
    loop_constraints: tuple[LoopClosureConstraint, ...]
    jacobian: ConstraintJacobian
    velocity_bias: tuple[float, ...]
    acceleration_bias: tuple[float, ...]
    initial_velocity: Mapping[str, float]
    initial_acceleration: Mapping[str, float]
    velocity_bias_source: str
    acceleration_bias_source: str
    reference_constraint_rank: int | None = None
    rank_tolerance: float = 1e-10


@dataclass(frozen=True, slots=True)
class DerivativeKinematicsResult:
    """Velocity or acceleration equality solve plus uniqueness assessment."""

    quantity: str
    solver_result: NonlinearSolveResult
    solution_uniqueness: str
    source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "quantity": self.quantity,
            "status": self.solver_result.status.value,
            "values": self.solver_result.values,
            "solution_uniqueness": self.solution_uniqueness,
            "source": self.source,
            "solver_result": self.solver_result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class MechanismKinematicsResult:
    schema_version: str
    model_id: str
    model_revision: str
    ground_link_id: str
    formulation: MobilityFormulation
    configuration_id: str
    branch_id: str
    coordinate_ids: tuple[str, ...]
    previous_configuration_id: str | None
    continuity_status: BranchContinuityStatus
    position: LoopClosureResult
    mobility: MobilityAnalysisResult | None
    velocity: DerivativeKinematicsResult | None
    acceleration: DerivativeKinematicsResult | None
    status: str
    skipped_stages: tuple[str, ...]
    velocity_bias_source: str
    acceleration_bias_source: str

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, versioned snapshot with source provenance."""
        return {
            "schema_version": self.schema_version,
            "model": {
                "model_id": self.model_id,
                "revision": self.model_revision,
                "ground_link_id": self.ground_link_id,
                "formulation": self.formulation.value,
            },
            "configuration": {
                "configuration_id": self.configuration_id,
                "branch_id": self.branch_id,
                "coordinate_ids": list(self.coordinate_ids),
                "previous_configuration_id": self.previous_configuration_id,
                "continuity_status": self.continuity_status.value,
            },
            "position": self.position.to_dict(),
            "mobility": None if self.mobility is None else self.mobility.to_dict(),
            "velocity": None if self.velocity is None else self.velocity.to_dict(),
            "acceleration": (
                None if self.acceleration is None else self.acceleration.to_dict()
            ),
            "status": self.status,
            "skipped_stages": list(self.skipped_stages),
            "provenance": {
                "position_constraint_ids": [
                    item.constraint_id for item in self.position.solver_result.residuals
                ],
                "jacobian_source": (
                    None if self.mobility is None else self.mobility.jacobian_source
                ),
                "velocity_bias_source": self.velocity_bias_source,
                "acceleration_bias_source": self.acceleration_bias_source,
            },
            "limitations": [
                "Position closure uses caller-supplied scalar residual callbacks for every loop-closing edge.",
                "The constraint Jacobian is caller-supplied; normalized joint metadata does not yet generate geometric equations.",
                "Velocity bias and acceleration bias are caller-supplied time-derivative terms; they are not inferred from geometry.",
                "Velocity/acceleration uniqueness is not claimed when the Jacobian is rank-deficient.",
                "Branch identity is caller-supplied; continuity means the caller retained the same branch ID and the prior solved coordinates were reused as the seed.",
                "No dynamics, forces, torque, contact, collision, physical feasibility or certification.",
            ],
        }


def _validate_vector(
    label: str,
    values: tuple[float, ...],
    expected_count: int,
) -> None:
    if len(values) != expected_count:
        raise InvalidModelError(
            f"{label} length must match the Jacobian constraint count ({expected_count})"
        )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)
        for value in values
    ):
        raise InvalidModelError(f"{label} values must be finite numbers (not booleans)")


def _linear_constraint_equations(
    coordinate_ids: tuple[str, ...],
    jacobian: ConstraintJacobian,
    bias: tuple[float, ...],
    prefix: str,
) -> tuple[NonlinearConstraint, ...]:
    equations = []
    for row_index, (constraint_id, row, offset) in enumerate(
        zip(jacobian.constraint_ids, jacobian.values, bias)
    ):
        equations.append(NonlinearConstraint(
            f"{prefix}/{constraint_id}",
            lambda state, row=row, offset=float(offset), names=coordinate_ids: (
                sum(float(coefficient) * state[name]
                    for coefficient, name in zip(row, names)) + offset
            ),
        ))
    return tuple(equations)


def _derivative_result(
    quantity: str,
    solved: NonlinearSolveResult,
    mobility: MobilityAnalysisResult,
    source: str,
) -> DerivativeKinematicsResult:
    if solved.status is not NonlinearSolveStatus.CONVERGED:
        uniqueness = "NOT_ESTABLISHED"
    elif mobility.jacobian_rank.estimated_rank is None:
        uniqueness = "UNKNOWN"
    elif mobility.jacobian_rank.estimated_rank < mobility.jacobian_rank.column_count:
        uniqueness = "NON_UNIQUE"
    else:
        uniqueness = "UNIQUE"
    return DerivativeKinematicsResult(quantity, solved, uniqueness, source)


def solve_mechanism_kinematics(
    problem: MechanismKinematicsInput,
    *,
    previous_result: MechanismKinematicsResult | None = None,
    options: NonlinearSolverOptions | None = None,
) -> MechanismKinematicsResult:
    """Run position closure, local mobility, velocity and acceleration stages.

    If a previous result for the same model/configuration contract is supplied
    and branch_id is unchanged, its solved coordinates seed the new position
    solve. A changed branch ID uses the caller's fresh initial coordinates and
    is explicitly marked BRANCH_SWITCH.
    """
    if not isinstance(problem, MechanismKinematicsInput):
        raise InvalidModelError("problem must be MechanismKinematicsInput")
    for label, value in (
        ("ground_link_id", problem.ground_link_id),
        ("configuration_id", problem.configuration_id),
        ("branch_id", problem.branch_id),
        ("velocity_bias_source", problem.velocity_bias_source),
        ("acceleration_bias_source", problem.acceleration_bias_source),
    ):
        if not isinstance(value, str) or not value.strip():
            raise InvalidModelError(f"{label} must be a non-empty string")
    if not problem.coordinate_ids or any(
        not isinstance(item, str) or not item.strip() for item in problem.coordinate_ids
    ):
        raise InvalidModelError("coordinate_ids must contain non-empty stable IDs")
    if len(set(problem.coordinate_ids)) != len(problem.coordinate_ids):
        raise InvalidModelError("coordinate_ids must be unique")
    if tuple(problem.jacobian.coordinate_ids) != tuple(problem.coordinate_ids):
        raise InvalidModelError("Jacobian coordinate ordering must match coordinate_ids")
    if problem.jacobian.configuration_id != problem.configuration_id:
        raise InvalidModelError("Jacobian configuration_id must match the requested configuration")
    constraint_ids = tuple(item.constraint_id for item in problem.loop_constraints)
    if constraint_ids != tuple(problem.jacobian.constraint_ids):
        raise InvalidModelError(
            "Jacobian constraint ordering must match loop_constraints ordering"
        )
    if set(problem.initial_coordinates) != set(problem.coordinate_ids):
        raise InvalidModelError("initial_coordinates must define exactly coordinate_ids")
    if set(problem.initial_velocity) != set(problem.coordinate_ids):
        raise InvalidModelError("initial_velocity must define exactly coordinate_ids")
    if set(problem.initial_acceleration) != set(problem.coordinate_ids):
        raise InvalidModelError("initial_acceleration must define exactly coordinate_ids")
    _validate_vector("velocity_bias", problem.velocity_bias, len(constraint_ids))
    _validate_vector("acceleration_bias", problem.acceleration_bias, len(constraint_ids))
    if (
        isinstance(problem.rank_tolerance, bool)
        or not isfinite(problem.rank_tolerance)
        or problem.rank_tolerance <= 0.0
    ):
        raise InvalidModelError("rank_tolerance must be finite and positive")

    previous_configuration_id = None
    continuity = BranchContinuityStatus.INITIAL_CONFIGURATION
    initial_coordinates = dict(problem.initial_coordinates)
    if previous_result is not None:
        if (
            previous_result.model_id != problem.model.model_id
            or previous_result.model_revision != problem.model.revision
            or previous_result.ground_link_id != problem.ground_link_id
            or previous_result.formulation is not problem.formulation
            or previous_result.coordinate_ids != tuple(problem.coordinate_ids)
        ):
            raise InvalidModelError(
                "previous_result model, ground, formulation or coordinate contract mismatch"
            )
        if previous_result.position.solver_result.status is not NonlinearSolveStatus.CONVERGED:
            raise InvalidModelError("previous_result position stage is not converged")
        previous_configuration_id = previous_result.configuration_id
        if previous_result.branch_id == problem.branch_id:
            continuity = BranchContinuityStatus.CONTINUOUS
            initial_coordinates = previous_result.position.solver_result.values
        else:
            continuity = BranchContinuityStatus.BRANCH_SWITCH

    position = solve_mechanism_loops(
        problem.model,
        problem.coordinate_ids,
        initial_coordinates,
        problem.loop_constraints,
        options=options,
    )
    if position.status is not LoopClosureStatus.CONVERGED:
        return MechanismKinematicsResult(
            RESULT_SCHEMA_VERSION,
            problem.model.model_id,
            problem.model.revision,
            problem.ground_link_id,
            problem.formulation,
            problem.configuration_id,
            problem.branch_id,
            tuple(problem.coordinate_ids),
            previous_configuration_id,
            continuity,
            position,
            None,
            None,
            None,
            "POSITION_NOT_CONVERGED",
            ("mobility", "velocity", "acceleration"),
            problem.velocity_bias_source,
            problem.acceleration_bias_source,
        )

    mobility = analyze_mechanism_mobility(
        problem.model,
        problem.formulation,
        problem.jacobian,
        ground_link_id=problem.ground_link_id,
        reference_constraint_rank=problem.reference_constraint_rank,
        rank_tolerance=problem.rank_tolerance,
    )
    velocity_equations = _linear_constraint_equations(
        tuple(problem.coordinate_ids), problem.jacobian, problem.velocity_bias, "velocity"
    )
    acceleration_equations = _linear_constraint_equations(
        tuple(problem.coordinate_ids), problem.jacobian, problem.acceleration_bias, "acceleration"
    )
    velocity_solved = solve_nonlinear_constraints(
        tuple(problem.coordinate_ids),
        problem.initial_velocity,
        velocity_equations,
        options=options,
    )
    acceleration_solved = solve_nonlinear_constraints(
        tuple(problem.coordinate_ids),
        problem.initial_acceleration,
        acceleration_equations,
        options=options,
    )
    velocity = _derivative_result(
        "velocity", velocity_solved, mobility, problem.velocity_bias_source
    )
    acceleration = _derivative_result(
        "acceleration", acceleration_solved, mobility, problem.acceleration_bias_source
    )
    status = (
        "COMPLETE"
        if (
            velocity_solved.status is NonlinearSolveStatus.CONVERGED
            and acceleration_solved.status is NonlinearSolveStatus.CONVERGED
        )
        else "PARTIAL"
    )
    skipped = tuple(
        name for name, solved in (
            ("velocity", velocity_solved), ("acceleration", acceleration_solved)
        ) if solved.status is not NonlinearSolveStatus.CONVERGED
    )
    return MechanismKinematicsResult(
        RESULT_SCHEMA_VERSION,
        problem.model.model_id,
        problem.model.revision,
        problem.ground_link_id,
        problem.formulation,
        problem.configuration_id,
        problem.branch_id,
        tuple(problem.coordinate_ids),
        previous_configuration_id,
        continuity,
        position,
        mobility,
        velocity,
        acceleration,
        status,
        skipped,
        problem.velocity_bias_source,
        problem.acceleration_bias_source,
    )
