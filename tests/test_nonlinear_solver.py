import json
import math

import pytest

from universal_platform.engineering.errors import SolverError
from universal_platform.engineering.nonlinear_solver import (
    NonlinearConstraint,
    NonlinearSolveStatus,
    NonlinearSolverOptions,
    VariableBound,
    solve_nonlinear_constraints,
)


def test_solves_single_nonlinear_square_equation():
    result = solve_nonlinear_constraints(
        ["x"], {"x": 1.0},
        [NonlinearConstraint("square", lambda v: v["x"] ** 2 - 4.0)],
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.values["x"] == pytest.approx(2.0, abs=1e-7)
    assert result.all_constraints_satisfied


def test_solves_overdetermined_consistent_system():
    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.2, "y": 0.2},
        [
            NonlinearConstraint("sum", lambda v: v["x"] + v["y"] - 3.0),
            NonlinearConstraint("difference", lambda v: v["x"] - v["y"] - 1.0),
            NonlinearConstraint("scaled", lambda v: 10.0 * (v["x"] - 2.0), scale=10.0),
        ],
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.values["x"] == pytest.approx(2.0, abs=1e-7)
    assert result.values["y"] == pytest.approx(1.0, abs=1e-7)


def test_solves_coupled_nonlinear_system():
    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.8, "y": 2.2},
        [
            NonlinearConstraint("circle", lambda v: v["x"] ** 2 + v["y"] ** 2 - 5.0),
            NonlinearConstraint("line", lambda v: v["x"] + v["y"] - 3.0),
        ],
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.values["x"] == pytest.approx(1.0, abs=1e-6)
    assert result.values["y"] == pytest.approx(2.0, abs=1e-6)


def test_projects_trial_steps_to_variable_bounds():
    result = solve_nonlinear_constraints(
        ["x"], {"x": 0.0},
        [NonlinearConstraint("target", lambda v: v["x"] - 3.0)],
        bounds={"x": VariableBound(lower=0.0, upper=2.0)},
    )
    assert result.status is NonlinearSolveStatus.NOT_CONVERGED
    assert result.values["x"] <= 2.0
    assert result.residuals[0].status == "FAIL"


def test_unsatisfied_stationary_point_is_not_pass():
    result = solve_nonlinear_constraints(
        ["x"], {"x": 0.0},
        [NonlinearConstraint("impossible", lambda v: v["x"] ** 2 + 1.0)],
    )
    assert result.status is NonlinearSolveStatus.NOT_CONVERGED
    assert not result.all_constraints_satisfied
    assert result.residuals[0].status == "FAIL"


def test_initial_point_can_satisfy_all_constraints_without_iteration():
    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 1.0, "y": 2.0},
        [NonlinearConstraint("sum", lambda v: v["x"] + v["y"] - 3.0)],
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.iterations == 0
    assert result.termination_reason == "initial_point_satisfies_all_constraints"


def test_missing_variables_and_duplicate_ids_are_rejected():
    with pytest.raises(SolverError, match="exactly"):
        solve_nonlinear_constraints(
            ["x", "y"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"])],
        )
    with pytest.raises(SolverError, match="unique"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [
                NonlinearConstraint("same", lambda v: v["x"]),
                NonlinearConstraint("same", lambda v: v["x"] - 1.0),
            ],
        )


def test_non_finite_residual_is_rejected():
    with pytest.raises(SolverError, match="non-finite"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("bad", lambda v: math.nan)],
        )


def test_invalid_bounds_and_unknown_bound_variables_are_rejected():
    with pytest.raises(SolverError, match="unknown variable"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"])],
            bounds={"y": VariableBound(0.0, 1.0)},
        )
    with pytest.raises(SolverError, match="inverted"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"])],
            bounds={"x": VariableBound(2.0, 1.0)},
        )


def test_invalid_options_and_constraint_scales_are_rejected():
    with pytest.raises(SolverError, match="max_iterations"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"])],
            options=NonlinearSolverOptions(max_iterations=0),
        )
    with pytest.raises(SolverError, match="scale"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"], scale=0.0)],
        )


def test_constraint_function_exception_is_reported_as_solver_error():
    def broken(_values):
        raise RuntimeError("bad model")
    with pytest.raises(SolverError, match="evaluation failed"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", broken)],
        )



def test_forward_difference_remains_the_default_and_reports_evaluations():
    result = solve_nonlinear_constraints(
        ["x"], {"x": 1.0},
        [NonlinearConstraint("square", lambda v: v["x"] ** 2 - 4.0)],
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.jacobian_method == "forward_finite_difference"
    assert result.jacobian_evaluations > 0
    assert result.residual_evaluations > 1
    assert result.analytic_jacobian_evaluations == 0


def test_central_difference_solves_coupled_system_and_reports_method():
    from universal_platform.engineering.nonlinear_solver import JacobianMethod

    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.8, "y": 2.2},
        [
            NonlinearConstraint("circle", lambda v: v["x"] ** 2 + v["y"] ** 2 - 5.0),
            NonlinearConstraint("line", lambda v: v["x"] + v["y"] - 3.0),
        ],
        options=NonlinearSolverOptions(jacobian_method=JacobianMethod.CENTRAL_FINITE_DIFFERENCE),
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.values["x"] == pytest.approx(1.0, abs=1e-6)
    assert result.values["y"] == pytest.approx(2.0, abs=1e-6)
    assert result.jacobian_method == "central_finite_difference"


def test_analytic_jacobian_matches_numeric_solution_and_counts_callback():
    from universal_platform.engineering.nonlinear_solver import JacobianMethod

    calls = []
    def analytic(values):
        calls.append(dict(values))
        return [[2.0 * values["x"], 2.0 * values["y"]], [1.0, 1.0]]

    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.8, "y": 2.2},
        [
            NonlinearConstraint("circle", lambda v: v["x"] ** 2 + v["y"] ** 2 - 5.0),
            NonlinearConstraint("line", lambda v: v["x"] + v["y"] - 3.0),
        ],
        options=NonlinearSolverOptions(jacobian_method=JacobianMethod.ANALYTIC),
        jacobian=analytic,
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.values["x"] == pytest.approx(1.0, abs=1e-6)
    assert result.values["y"] == pytest.approx(2.0, abs=1e-6)
    assert result.jacobian_method == "analytic"
    assert result.analytic_jacobian_evaluations == len(calls)
    assert result.analytic_jacobian_evaluations == result.jacobian_evaluations


def test_analytic_jacobian_respects_residual_scaling():
    from universal_platform.engineering.nonlinear_solver import JacobianMethod

    result = solve_nonlinear_constraints(
        ["x"], {"x": 1.0},
        [NonlinearConstraint("scaled", lambda v: 10.0 * (v["x"] - 2.0), scale=10.0)],
        options=NonlinearSolverOptions(jacobian_method=JacobianMethod.ANALYTIC),
        jacobian=lambda _v: [[10.0]],
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.values["x"] == pytest.approx(2.0, abs=1e-7)


def test_analytic_jacobian_rejects_wrong_shape_and_non_finite_values():
    from universal_platform.engineering.nonlinear_solver import JacobianMethod

    options = NonlinearSolverOptions(jacobian_method=JacobianMethod.ANALYTIC)
    constraints = [NonlinearConstraint("eq", lambda v: v["x"] - 2.0)]
    with pytest.raises(SolverError, match="shape"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0}, constraints, options=options,
            jacobian=lambda _v: [[1.0, 2.0]],
        )
    with pytest.raises(SolverError, match="non-finite"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0}, constraints, options=options,
            jacobian=lambda _v: [[math.nan]],
        )


def test_analytic_jacobian_callback_failures_are_typed_solver_errors():
    from universal_platform.engineering.nonlinear_solver import JacobianMethod

    with pytest.raises(SolverError, match="Analytic Jacobian evaluation failed"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"] - 2.0)],
            options=NonlinearSolverOptions(jacobian_method=JacobianMethod.ANALYTIC),
            jacobian=lambda _v: (_ for _ in ()).throw(RuntimeError("bad derivative")),
        )


def test_jacobian_callback_and_strategy_must_be_consistent():
    from universal_platform.engineering.nonlinear_solver import JacobianMethod

    with pytest.raises(SolverError, match="requires a jacobian callback"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"] - 2.0)],
            options=NonlinearSolverOptions(jacobian_method=JacobianMethod.ANALYTIC),
        )
    with pytest.raises(SolverError, match="requires jacobian_method"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"] - 2.0)],
            jacobian=lambda _v: [[1.0]],
        )



def test_jacobian_rank_diagnostic_reports_full_rank_and_square_shape():
    from universal_platform.engineering.nonlinear_solver import JacobianRankStatus

    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.8, "y": 2.2},
        [
            NonlinearConstraint("sum", lambda v: v["x"] + v["y"] - 3.0),
            NonlinearConstraint("difference", lambda v: v["x"] - v["y"] + 1.0),
        ],
    )
    assert result.jacobian_rank is not None
    assert result.jacobian_rank.status is JacobianRankStatus.FULL_RANK
    assert result.jacobian_rank.estimated_rank == 2
    assert result.jacobian_rank.system_shape == "SQUARE"


def test_jacobian_rank_diagnostic_detects_duplicate_constraint_rows():
    from universal_platform.engineering.nonlinear_solver import JacobianRankStatus

    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.0, "y": 0.0},
        [
            NonlinearConstraint("first", lambda v: v["x"] + v["y"] - 2.0),
            NonlinearConstraint("duplicate", lambda v: 2.0 * (v["x"] + v["y"] - 2.0)),
        ],
    )
    assert result.jacobian_rank is not None
    assert result.jacobian_rank.status is JacobianRankStatus.RANK_DEFICIENT
    assert result.jacobian_rank.estimated_rank == 1


def test_jacobian_rank_diagnostic_labels_underdetermined_full_row_rank():
    from universal_platform.engineering.nonlinear_solver import JacobianRankStatus

    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.0, "y": 0.0},
        [NonlinearConstraint("sum", lambda v: v["x"] + v["y"] - 2.0)],
    )
    assert result.jacobian_rank is not None
    assert result.jacobian_rank.status is JacobianRankStatus.FULL_RANK
    assert result.jacobian_rank.system_shape == "UNDERDETERMINED"
    assert result.jacobian_rank.maximum_rank == 1


def test_jacobian_rank_tolerance_is_validated_and_diagnostics_can_be_uncomputed():
    from universal_platform.engineering.nonlinear_solver import JacobianRankDiagnostics

    with pytest.raises(SolverError, match="step, tolerance and damping"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"] - 1.0)],
            options=NonlinearSolverOptions(rank_tolerance=0.0),
        )
    result = solve_nonlinear_constraints(
        ["x"], {"x": 1.0},
        [NonlinearConstraint("eq", lambda v: v["x"] - 1.0)],
    )
    assert result.jacobian_rank is None


def test_rank_estimator_reports_indeterminate_for_non_finite_matrix():
    from universal_platform.engineering.nonlinear_solver import (
        JacobianRankStatus,
        _estimate_jacobian_rank,
    )

    diagnostic = _estimate_jacobian_rank([[math.inf, 0.0]], 1e-10)
    assert diagnostic.status is JacobianRankStatus.INDETERMINATE
    assert diagnostic.estimated_rank is None


def test_rank_estimator_threshold_sensitivity_is_explicit():
    from universal_platform.engineering.nonlinear_solver import (
        JacobianRankStatus,
        _estimate_jacobian_rank,
    )

    nearly_dependent = [[1.0, 1.0], [0.0, 1e-8]]
    loose = _estimate_jacobian_rank(nearly_dependent, 1e-6)
    tight = _estimate_jacobian_rank(nearly_dependent, 1e-10)
    assert loose.status is JacobianRankStatus.RANK_DEFICIENT
    assert tight.status is JacobianRankStatus.FULL_RANK
    assert tight.threshold < loose.threshold


def test_rank_estimator_detects_zero_jacobian_column():
    from universal_platform.engineering.nonlinear_solver import (
        JacobianRankStatus,
        _estimate_jacobian_rank,
    )

    diagnostic = _estimate_jacobian_rank([[1.0, 0.0], [2.0, 0.0]], 1e-10)
    assert diagnostic.status is JacobianRankStatus.RANK_DEFICIENT
    assert diagnostic.estimated_rank == 1


def test_variable_scaling_balances_jacobian_columns_and_solves_mixed_scales():
    from universal_platform.engineering.nonlinear_solver import JacobianScaleStatus

    constraints = [
        NonlinearConstraint("sum", lambda v: v["x"] * 1e-6 + v["y"] * 1e6 - 2.0),
        NonlinearConstraint("difference", lambda v: v["x"] * 1e-6 - v["y"] * 1e6),
    ]
    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.8e6, "y": 0.8e-6}, constraints,
        variable_scales={"x": 1e6, "y": 1e-6},
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.values["x"] == pytest.approx(1e6, rel=1e-7)
    assert result.values["y"] == pytest.approx(1e-6, rel=1e-7)
    assert result.variable_scales == (("x", 1e6), ("y", 1e-6))
    assert result.jacobian_scale is not None
    assert result.jacobian_scale.status is JacobianScaleStatus.BALANCED
    assert result.jacobian_scale.column_norm_ratio == pytest.approx(1.0, rel=1e-4)


def test_unscaled_mixed_magnitude_columns_report_scale_disparity():
    from universal_platform.engineering.nonlinear_solver import JacobianScaleStatus

    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.8e6, "y": 0.8e-6},
        [
            NonlinearConstraint("sum", lambda v: v["x"] * 1e-6 + v["y"] * 1e6 - 2.0),
            NonlinearConstraint("difference", lambda v: v["x"] * 1e-6 - v["y"] * 1e6),
        ],
    )
    assert result.jacobian_scale is not None
    assert result.jacobian_scale.status is JacobianScaleStatus.SCALE_DISPARITY
    assert result.jacobian_scale.column_norm_ratio > 1e8


def test_variable_scales_reject_unknown_names_and_invalid_values():
    with pytest.raises(SolverError, match="unknown variable"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"] - 2.0)],
            variable_scales={"y": 1.0},
        )
    with pytest.raises(SolverError, match="finite and positive"):
        solve_nonlinear_constraints(
            ["x"], {"x": 1.0},
            [NonlinearConstraint("eq", lambda v: v["x"] - 2.0)],
            variable_scales={"x": 0.0},
        )



def test_result_serialization_is_versioned_deterministic_and_json_compatible():
    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.8, "y": 2.2},
        [
            NonlinearConstraint("circle", lambda v: v["x"] ** 2 + v["y"] ** 2 - 5.0),
            NonlinearConstraint("line", lambda v: v["x"] + v["y"] - 3.0),
        ],
        variable_scales={"x": 1.0, "y": 1.0},
    )
    snapshot = result.to_dict()
    encoded = json.dumps(snapshot, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded["schema_version"] == "1.0"
    assert decoded["status"] == "CONVERGED"
    assert decoded["all_constraints_satisfied"] is True
    assert decoded["jacobian_rank"]["status"] == "FULL_RANK"
    assert decoded["jacobian_scale"]["status"] == "BALANCED"
    assert decoded["variable_scales"] == {"x": 1.0, "y": 1.0}
    assert json.dumps(result.to_dict(), sort_keys=True) == encoded


def test_result_serialization_preserves_not_computed_diagnostics_as_null():
    result = solve_nonlinear_constraints(
        ["x"], {"x": 1.0},
        [NonlinearConstraint("already_satisfied", lambda v: v["x"] - 1.0)],
    )
    snapshot = result.to_dict()
    assert snapshot["jacobian_rank"] is None
    assert snapshot["jacobian_scale"] is None
    assert snapshot["jacobian_evaluations"] == 0
