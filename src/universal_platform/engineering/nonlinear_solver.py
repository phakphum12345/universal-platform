"""Bounded, dependency-free nonlinear equality-constraint solving.

The implementation is a local least-squares solver using finite-difference
Jacobians and a damped Levenberg–Marquardt step. It is intended for small,
offline engineering models. It provides no global-optimum, uniqueness,
conditioning, or physical-feasibility guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import hypot, isfinite
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


class JacobianScaleStatus(str, Enum):
    BALANCED = "BALANCED"
    SCALE_DISPARITY = "SCALE_DISPARITY"
    INDETERMINATE = "INDETERMINATE"


class JacobianRankStatus(str, Enum):
    FULL_RANK = "FULL_RANK"
    RANK_DEFICIENT = "RANK_DEFICIENT"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True, slots=True)
class JacobianScaleDiagnostics:
    column_norm_ratio: float | None
    threshold: float
    status: JacobianScaleStatus
    method: str = "scaled-jacobian-column-norm-ratio"


@dataclass(frozen=True, slots=True)
class JacobianRankDiagnostics:
    estimated_rank: int | None
    maximum_rank: int
    row_count: int
    column_count: int
    threshold: float
    status: JacobianRankStatus
    system_shape: str
    method: str = "modified-gram-schmidt-column-pivoting"


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
    rank_tolerance: float = 1e-10
    column_scale_disparity_threshold: float = 1e8


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
    jacobian_rank: JacobianRankDiagnostics | None = None
    jacobian_scale: JacobianScaleDiagnostics | None = None
    variable_scales: tuple[tuple[str, float], ...] = ()
    limitations: tuple[str, ...] = (
        "Local solver; no global convergence or uniqueness guarantee",
        "Derivative accuracy depends on the selected strategy; finite differences are step-sensitive",
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


def _estimate_jacobian_rank(
    matrix: list[list[float]],
    relative_tolerance: float,
) -> JacobianRankDiagnostics:
    row_count = len(matrix)
    column_count = len(matrix[0]) if row_count else 0
    maximum_rank = min(row_count, column_count)
    if any(len(row) != column_count for row in matrix):
        return JacobianRankDiagnostics(
            None, maximum_rank, row_count, column_count, 0.0,
            JacobianRankStatus.INDETERMINATE, "UNKNOWN",
        )
    if not all(isfinite(value) for row in matrix for value in row):
        return JacobianRankDiagnostics(
            None, maximum_rank, row_count, column_count, 0.0,
            JacobianRankStatus.INDETERMINATE, _system_shape(row_count, column_count),
        )

    columns = [
        [matrix[row][column] for row in range(row_count)]
        for column in range(column_count)
    ]
    norms = [hypot(*column) for column in columns]
    reference_norm = max(norms, default=0.0)
    threshold = relative_tolerance * reference_norm
    rank = 0

    while columns and rank < maximum_rank:
        pivot = max(range(len(columns)), key=lambda index: sum(
            value * value for value in columns[index]
        ))
        vector = columns.pop(pivot)
        norm = hypot(*vector)
        if norm <= threshold:
            break
        basis = [value / norm for value in vector]
        rank += 1

        # Re-orthogonalize once to reduce loss of orthogonality for nearly
        # dependent columns while keeping the implementation dependency-free.
        for candidate in columns:
            for _ in range(2):
                projection = sum(a * b for a, b in zip(basis, candidate))
                for index in range(row_count):
                    candidate[index] -= projection * basis[index]

    status = (
        JacobianRankStatus.FULL_RANK
        if rank == maximum_rank
        else JacobianRankStatus.RANK_DEFICIENT
    )
    return JacobianRankDiagnostics(
        rank, maximum_rank, row_count, column_count, threshold, status,
        _system_shape(row_count, column_count),
    )


def _estimate_jacobian_scale(
    matrix: list[list[float]],
    disparity_threshold: float,
) -> JacobianScaleDiagnostics:
    if not matrix or not matrix[0] or any(
        len(row) != len(matrix[0]) for row in matrix
    ) or not all(isfinite(value) for row in matrix for value in row):
        return JacobianScaleDiagnostics(
            None, disparity_threshold, JacobianScaleStatus.INDETERMINATE
        )
    norms = [
        hypot(*(matrix[row][column] for row in range(len(matrix))))
        for column in range(len(matrix[0]))
    ]
    if not norms or min(norms) <= 0.0 or not all(isfinite(value) for value in norms):
        return JacobianScaleDiagnostics(
            None, disparity_threshold, JacobianScaleStatus.INDETERMINATE
        )
    ratio = max(norms) / min(norms)
    return JacobianScaleDiagnostics(
        ratio,
        disparity_threshold,
        JacobianScaleStatus.SCALE_DISPARITY
        if ratio > disparity_threshold else JacobianScaleStatus.BALANCED,
    )


def _system_shape(row_count: int, column_count: int) -> str:
    if row_count < column_count:
        return "UNDERDETERMINED"
    if row_count > column_count:
        return "OVERDETERMINED"
    return "SQUARE"


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
    jacobian_rank: JacobianRankDiagnostics | None,
    jacobian_scale: JacobianScaleDiagnostics | None,
    variable_scales: tuple[tuple[str, float], ...],
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
        jacobian_rank=jacobian_rank,
        jacobian_scale=jacobian_scale,
        variable_scales=variable_scales,
    )


def solve_nonlinear_constraints(
    variable_names: tuple[str, ...] | list[str],
    initial_values: Mapping[str, float],
    constraints: tuple[NonlinearConstraint, ...] | list[NonlinearConstraint],
    *,
    bounds: Mapping[str, VariableBound] | None = None,
    options: NonlinearSolverOptions | None = None,
    jacobian: JacobianFunction | None = None,
    variable_scales: Mapping[str, float] | None = None,
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
    variable_scale_map = variable_scales or {}

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
            or settings.maximum_damping <= settings.initial_damping
            or not isfinite(settings.rank_tolerance)
            or settings.rank_tolerance <= 0.0
            or not isfinite(settings.column_scale_disparity_threshold)
            or settings.column_scale_disparity_threshold <= 1.0):
        raise SolverError("Solver step, tolerance and damping options must be finite and positive")

    for key, scale in variable_scale_map.items():
        if key not in names:
            raise SolverError(f"Variable scales supplied for unknown variable {key!r}")
        if not isfinite(scale) or scale <= 0.0:
            raise SolverError(f"Variable scale for {key!r} must be finite and positive")

    scales = tuple(float(variable_scale_map.get(name, 1.0)) for name in names)

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
            stats, settings.jacobian_method, None, None,
            tuple(zip(names, scales)),
        )

    damping = settings.initial_damping
    reason = "maximum_iterations_reached"
    iterations = 0
    rank_diagnostics: JacobianRankDiagnostics | None = None
    scale_diagnostics: JacobianScaleDiagnostics | None = None

    for iteration in range(1, settings.max_iterations + 1):
        iterations = iteration
        jacobian_matrix = _jacobian(
            equations, names, current, residuals,
            settings.finite_difference_step,
            settings.jacobian_method, jacobian, stats,
        )
        scaled_jacobian = [
            [jacobian_matrix[row][col] * scales[col] for col in range(len(names))]
            for row in range(len(equations))
        ]
        rank_diagnostics = _estimate_jacobian_rank(
            scaled_jacobian, settings.rank_tolerance
        )
        scale_diagnostics = _estimate_jacobian_scale(
            scaled_jacobian, settings.column_scale_disparity_threshold
        )
        row_count, column_count = len(equations), len(names)
        gradient = [
            sum(scaled_jacobian[row][col] * residuals[row] for row in range(row_count))
            for col in range(column_count)
        ]
        if max(abs(value) for value in gradient) <= settings.step_tolerance:
            reason = "stationary_point_without_constraint_convergence"
            break

        normal = [[0.0] * column_count for _ in range(column_count)]
        for i in range(column_count):
            for j in range(column_count):
                normal[i][j] = sum(
                    scaled_jacobian[row][i] * scaled_jacobian[row][j]
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
            tuple(value + change * scale for value, change, scale in zip(current, delta, scales)),
            names,
            bound_map,
        )
        actual_step = max(
            abs(new - old) / scale
            for new, old, scale in zip(candidate, current, scales)
        )
        if actual_step <= settings.step_tolerance * (
            1.0 + max(abs(value) / scale for value, scale in zip(current, scales))
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
                    stats, settings.jacobian_method, rank_diagnostics,
                    scale_diagnostics, tuple(zip(names, scales)),
                )
        else:
            damping *= 10.0
            if damping > settings.maximum_damping:
                reason = "damping_limit_reached_without_improvement"
                break

    return _build_result(
        NonlinearSolveStatus.NOT_CONVERGED, names, current, equations,
        residuals, iterations, reason, stats, settings.jacobian_method,
        rank_diagnostics, scale_diagnostics, tuple(zip(names, scales)),
    )
