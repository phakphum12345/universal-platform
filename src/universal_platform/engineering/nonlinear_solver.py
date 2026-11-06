"""Bounded, dependency-free nonlinear equality-constraint solving.

The implementation is a local least-squares solver using finite-difference
Jacobians and a damped Levenberg–Marquardt step. It is intended for small,
offline engineering models. It provides no global-optimum, uniqueness,
conditioning, or physical-feasibility guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Callable, Mapping, Sequence

from .errors import SolverError
from .linear_solver import solve_linear

ResidualFunction = Callable[[Mapping[str, float]], float]
JacobianFunction = Callable[[Mapping[str, float]], Sequence[Sequence[float]]]


class NonlinearSolveStatus(str, Enum):
    CONVERGED = "CONVERGED"
    NOT_CONVERGED = "NOT_CONVERGED"


class JacobianMethod(str, Enum):
    FORWARD_FINITE_DIFFERENCE = "forward_finite_difference"
    CENTRAL_FINITE_DIFFERENCE = "central_finite_difference"
    ANALYTIC = "analytic"


@dataclass(frozen=True, slots=True)
class NonlinearConstraint:
    """One scalar equality residual; zero means the equation is satisfied."""

    constraint_id: str
    residual: ResidualFunction
    tolerance: float = 1e-8
    scale: float = 1.0


@dataclass(frozen=True, slots=True)
class VariableBound:
    lower: float | None = None
    upper: float | None = None


@dataclass(frozen=True, slots=True)
class NonlinearSolverOptions:
    max_iterations: int = 100
    finite_difference_step: float = 1e-6
    step_tolerance: float = 1e-10
    initial_damping: float = 1e-3
    maximum_damping: float = 1e12
    jacobian_method: JacobianMethod = JacobianMethod.FORWARD_FINITE_DIFFERENCE


@dataclass(frozen=True, slots=True)
class NonlinearConstraintResidual:
    constraint_id: str
    value: float
    tolerance: float
    status: str


@dataclass(frozen=True, slots=True)
class NonlinearSolveResult:
    status: NonlinearSolveStatus
    variables: tuple[tuple[str, float], ...]
    residuals: tuple[NonlinearConstraintResidual, ...]
    iterations: int
    objective: float
    termination_reason: str
    method: str = "finite-difference-levenberg-marquardt"
    jacobian_method: str = "forward_finite_difference"
    residual_evaluations: int = 0
    jacobian_evaluations: int = 0
    analytic_jacobian_evaluations: int = 0
    limitations: tuple[str, ...] = (
        "Local solver; no global convergence or uniqueness guarantee",
        "Finite-difference Jacobian; scaling and smoothness affect accuracy",
        "No automatic inequality/contact/complementarity or symbolic constraints",
        "Does not establish physical feasibility or engineering certification",
    )

    @property
    def values(self) -> dict[str, float]:
        """Return a fresh mapping of the solved variable values."""
        return dict(self.variables)

    @property
    def all_constraints_satisfied(self) -> bool:
        return self.status is NonlinearSolveStatus.CONVERGED and all(
            item.status == "PASS" for item in self.residuals
        )


@dataclass(slots=True)
class _EvaluationStats:
    residual_evaluations: int = 0
    jacobian_evaluations: int = 0
    analytic_jacobian_evaluations: int = 0


def _evaluate(
    constraints: tuple[NonlinearConstraint, ...],
    variable_names: tuple[str, ...],
    values: tuple[float, ...],
    stats: _EvaluationStats,
) -> tuple[float, ...]:
    state = dict(zip(variable_names, values))
    residuals: list[float] = []
    for item in constraints:
        stats.residual_evaluations += 1
        try:
            value = float(item.residual(state))
        except Exception as exc:
            raise SolverError(
                f"Constraint {item.constraint_id!r} evaluation failed: {exc}"
            ) from exc
        if not isfinite(value):
            raise SolverError(
                f"Constraint {item.constraint_id!r} returned a non-finite residual"
            )
        residuals.append(value / item.scale)
    return tuple(residuals)


def _objective(residuals: tuple[float, ...]) -> float:
    value = 0.5 * sum(item * item for item in residuals)
    if not isfinite(value):
        raise SolverError("Nonlinear objective became non-finite")
    return value


def _all_pass(
    scaled_residuals: tuple[float, ...],
    constraints: tuple[NonlinearConstraint, ...],
) -> bool:
    return all(
        abs(value * item.scale) <= item.tolerance
        for value, item in zip(scaled_residuals, constraints)
    )


def _jacobian(
    constraints: tuple[NonlinearConstraint, ...],
    variable_names: tuple[str, ...],
    values: tuple[float, ...],
    base_residuals: tuple[float, ...],
    step_size: float,
    method: JacobianMethod,
    analytic_jacobian: JacobianFunction | None,
    stats: _EvaluationStats,
) -> list[list[float]]:
    row_count = len(constraints)
    column_count = len(variable_names)
    stats.jacobian_evaluations += 1
    matrix = [[0.0] * column_count for _ in range(row_count)]

    if method is JacobianMethod.ANALYTIC:
        if analytic_jacobian is None:
            raise SolverError("Analytic Jacobian method requires a jacobian callback")
        stats.analytic_jacobian_evaluations += 1
        try:
            raw = analytic_jacobian(dict(zip(variable_names, values)))
        except Exception as exc:
            raise SolverError(f"Analytic Jacobian evaluation failed: {exc}") from exc
        try:
            if len(raw) != row_count or any(len(row) != column_count for row in raw):
                raise SolverError(
                    f"Analytic Jacobian must have shape ({row_count}, {column_count})"
                )
            for row, constraint in enumerate(constraints):
                for column in range(column_count):
                    value = float(raw[row][column])
                    if not isfinite(value):
                        raise SolverError("Analytic Jacobian contains a non-finite value")
                    matrix[row][column] = value / constraint.scale
        except (TypeError, ValueError, OverflowError) as exc:
            raise SolverError(f"Analytic Jacobian must be a finite numeric matrix: {exc}") from exc
        return matrix

    for column in range(column_count):
        step = step_size * max(1.0, abs(values[column]))
        plus = list(values)
        plus[column] += step
        plus_residuals = _evaluate(
            constraints, variable_names, tuple(plus), stats
        )
        if method is JacobianMethod.FORWARD_FINITE_DIFFERENCE:
            for row in range(row_count):
                matrix[row][column] = (
                    plus_residuals[row] - base_residuals[row]
                ) / step
        else:
            minus = list(values)
            minus[column] -= step
            minus_residuals = _evaluate(
                constraints, variable_names, tuple(minus), stats
            )
            for row in range(row_count):
                matrix[row][column] = (
                    plus_residuals[row] - minus_residuals[row]
                ) / (2.0 * step)
    return matrix


def _project_bounds(
    values: tuple[float, ...],
    variable_names: tuple[str, ...],
    bounds: Mapping[str, VariableBound],
) -> tuple[float, ...]:
    projected: list[float] = []
    for name, value in zip(variable_names, values):
        bound = bounds.get(name, VariableBound())
        lower, upper = bound.lower, bound.upper
        if lower is not None and upper is not None and lower > upper:
            raise SolverError(f"Variable {name!r} has inverted bounds")
        if lower is not None and value < lower:
            value = lower
        if upper is not None and value > upper:
            value = upper
        projected.append(value)
    return tuple(projected)


def _build_result(
    status: NonlinearSolveStatus,
    variable_names: tuple[str, ...],
    values: tuple[float, ...],
    constraints: tuple[NonlinearConstraint, ...],
    scaled_residuals: tuple[float, ...],
    iterations: int,
    reason: str,
    stats: _EvaluationStats,
    jacobian_method: JacobianMethod,
) -> NonlinearSolveResult:
    residual_items = tuple(
        NonlinearConstraintResidual(
            constraint_id=item.constraint_id,
            value=scaled * item.scale,
            tolerance=item.tolerance,
            status="PASS" if abs(scaled * item.scale) <= item.tolerance else "FAIL",
        )
        for item, scaled in zip(constraints, scaled_residuals)
    )
    final_status = (
        NonlinearSolveStatus.CONVERGED
        if status is NonlinearSolveStatus.CONVERGED
        and all(item.status == "PASS" for item in residual_items)
        else NonlinearSolveStatus.NOT_CONVERGED
    )
    return NonlinearSolveResult(
        status=final_status,
        variables=tuple(zip(variable_names, values)),
        residuals=residual_items,
        iterations=iterations,
        objective=_objective(scaled_residuals),
        termination_reason=reason,
        jacobian_method=jacobian_method.value,
        residual_evaluations=stats.residual_evaluations,
        jacobian_evaluations=stats.jacobian_evaluations,
        analytic_jacobian_evaluations=stats.analytic_jacobian_evaluations,
    )


def solve_nonlinear_constraints(
    variable_names: tuple[str, ...] | list[str],
    initial_values: Mapping[str, float],
    constraints: tuple[NonlinearConstraint, ...] | list[NonlinearConstraint],
    *,
    bounds: Mapping[str, VariableBound] | None = None,
    options: NonlinearSolverOptions | None = None,
    jacobian: JacobianFunction | None = None,
) -> NonlinearSolveResult:
    """Solve scalar equality residuals with bounded damped least squares.

    Convergence requires every original (unscaled) residual to be within its
    own tolerance. A stationary point that does not satisfy all equations is
    returned as NOT_CONVERGED, never PASS.
    """
    names = tuple(variable_names)
    equations = tuple(constraints)
    settings = options or NonlinearSolverOptions()
    bound_map = bounds or {}

    if not names or any(not isinstance(name, str) or not name.strip() for name in names):
        raise SolverError("At least one non-empty variable name is required")
    if len(names) != len(set(names)):
        raise SolverError("Variable names must be unique")
    if not equations:
        raise SolverError("At least one nonlinear constraint is required")
    if len({item.constraint_id for item in equations}) != len(equations):
        raise SolverError("Constraint identifiers must be unique")
    if any(not isinstance(item.constraint_id, str) or not item.constraint_id.strip()
           for item in equations):
        raise SolverError("Constraint identifiers must be non-empty")
    if set(initial_values) != set(names):
        raise SolverError("Initial values must define exactly the declared variables")
    for item in equations:
        if not callable(item.residual):
            raise SolverError(f"Constraint {item.constraint_id!r} residual must be callable")
        if not isfinite(item.tolerance) or item.tolerance <= 0.0:
            raise SolverError(f"Constraint {item.constraint_id!r} tolerance must be finite and positive")
        if not isfinite(item.scale) or item.scale <= 0.0:
            raise SolverError(f"Constraint {item.constraint_id!r} scale must be finite and positive")
    if settings.max_iterations < 1:
        raise SolverError("max_iterations must be at least one")
    if (not isfinite(settings.finite_difference_step)
            or settings.finite_difference_step <= 0.0
            or not isfinite(settings.step_tolerance)
            or settings.step_tolerance <= 0.0
            or not isfinite(settings.initial_damping)
            or settings.initial_damping <= 0.0
            or not isfinite(settings.maximum_damping)
            or settings.maximum_damping <= settings.initial_damping):
        raise SolverError("Solver step, tolerance and damping options must be finite and positive")

    for key, bound in bound_map.items():
        if key not in names:
            raise SolverError(f"Bounds supplied for unknown variable {key!r}")
        if not isinstance(bound, VariableBound):
            raise SolverError(f"Bounds for variable {key!r} must be VariableBound")
        for endpoint in (bound.lower, bound.upper):
            if endpoint is not None and not isfinite(endpoint):
                raise SolverError(f"Variable {key!r} bounds must be finite")
        if bound.lower is not None and bound.upper is not None and bound.lower > bound.upper:
            raise SolverError(f"Variable {key!r} has inverted bounds")

    try:
        initial = tuple(float(initial_values[name]) for name in names)
    except (TypeError, ValueError, OverflowError) as exc:
        raise SolverError("Initial variable values must be numeric") from exc
    if not all(isfinite(value) for value in initial):
        raise SolverError("Initial variable values must be finite")
    if not isinstance(settings.jacobian_method, JacobianMethod):
        raise SolverError("jacobian_method must be a JacobianMethod")
    if settings.jacobian_method is JacobianMethod.ANALYTIC and jacobian is None:
        raise SolverError("Analytic Jacobian method requires a jacobian callback")
    if settings.jacobian_method is not JacobianMethod.ANALYTIC and jacobian is not None:
        raise SolverError("A jacobian callback requires jacobian_method=ANALYTIC")
    if jacobian is not None and not callable(jacobian):
        raise SolverError("jacobian must be callable")

    stats = _EvaluationStats()
    current = _project_bounds(initial, names, bound_map)
    residuals = _evaluate(equations, names, current, stats)
    objective = _objective(residuals)
    if _all_pass(residuals, equations):
        return _build_result(
            NonlinearSolveStatus.CONVERGED, names, current, equations,
            residuals, 0, "initial_point_satisfies_all_constraints",
            stats, settings.jacobian_method,
        )

    damping = settings.initial_damping
    reason = "maximum_iterations_reached"
    iterations = 0

    for iteration in range(1, settings.max_iterations + 1):
        iterations = iteration
        jacobian = _jacobian(
            equations, names, current, residuals,
            settings.finite_difference_step,
            settings.jacobian_method, jacobian, stats,
        )
        row_count, column_count = len(equations), len(names)
        gradient = [
            sum(jacobian[row][col] * residuals[row] for row in range(row_count))
            for col in range(column_count)
        ]
        if max(abs(value) for value in gradient) <= settings.step_tolerance:
            reason = "stationary_point_without_constraint_convergence"
            break

        normal = [[0.0] * column_count for _ in range(column_count)]
        for i in range(column_count):
            for j in range(column_count):
                normal[i][j] = sum(
                    jacobian[row][i] * jacobian[row][j]
                    for row in range(row_count)
                )
            normal[i][i] += damping * max(normal[i][i], 1.0)

        try:
            delta = solve_linear(normal, [-value for value in gradient]).solution
        except SolverError:
            damping *= 10.0
            if damping > settings.maximum_damping:
                reason = "damping_limit_reached_after_singular_step"
                break
            continue

        candidate = _project_bounds(
            tuple(value + change for value, change in zip(current, delta)),
            names,
            bound_map,
        )
        actual_step = max(abs(new - old) for new, old in zip(candidate, current))
        if actual_step <= settings.step_tolerance * (
            1.0 + max(abs(value) for value in current)
        ):
            reason = "step_tolerance_reached_without_constraint_convergence"
            break

        candidate_residuals = _evaluate(equations, names, candidate, stats)
        candidate_objective = _objective(candidate_residuals)
        if candidate_objective < objective:
            current = candidate
            residuals = candidate_residuals
            objective = candidate_objective
            damping = max(damping / 3.0, 1e-15)
            if _all_pass(residuals, equations):
                return _build_result(
                    NonlinearSolveStatus.CONVERGED, names, current, equations,
                    residuals, iterations,
                    "all_constraint_residuals_within_tolerance",
                    stats, settings.jacobian_method,
                )
        else:
            damping *= 10.0
            if damping > settings.maximum_damping:
                reason = "damping_limit_reached_without_improvement"
                break

    return _build_result(
        NonlinearSolveStatus.NOT_CONVERGED, names, current, equations,
        residuals, iterations, reason, stats, settings.jacobian_method
    )
