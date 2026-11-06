"""Deterministic regression matrix for nonlinear solver reliability boundaries."""

import pytest

from universal_platform.engineering.nonlinear_solver import (
    JacobianMethod,
    JacobianRankStatus,
    NonlinearConstraint,
    NonlinearSolveStatus,
    NonlinearSolverOptions,
    VariableBound,
    solve_nonlinear_constraints,
)


def test_consistent_overdetermined_system_reports_full_rank():
    result = solve_nonlinear_constraints(
        ["x", "y"], {"x": 0.2, "y": 0.2},
        [
            NonlinearConstraint("sum", lambda v: v["x"] + v["y"] - 3.0),
            NonlinearConstraint("difference", lambda v: v["x"] - v["y"] - 1.0),
            NonlinearConstraint("redundant_scale", lambda v: 10.0 * (v["x"] - 2.0), scale=10.0),
        ],
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.values["x"] == pytest.approx(2.0, abs=1e-7)
    assert result.values["y"] == pytest.approx(1.0, abs=1e-7)
    assert result.jacobian_rank is not None
    assert result.jacobian_rank.status is JacobianRankStatus.FULL_RANK
    assert result.jacobian_rank.system_shape == "OVERDETERMINED"


def test_inconsistent_overdetermined_system_never_reports_pass():
    result = solve_nonlinear_constraints(
        ["x"], {"x": 0.0},
        [
            NonlinearConstraint("target_a", lambda v: v["x"] - 1.0),
            NonlinearConstraint("target_b", lambda v: v["x"] - 2.0),
        ],
    )
    assert result.status is NonlinearSolveStatus.NOT_CONVERGED
    assert not result.all_constraints_satisfied
    assert all(item.status == "FAIL" for item in result.residuals)


@pytest.mark.parametrize(
    ("target", "bound"),
    [
        (-3.0, VariableBound(lower=0.0, upper=2.0)),
        (4.0, VariableBound(lower=0.0, upper=2.0)),
    ],
)
def test_active_lower_and_upper_bounds_remain_fail_closed(target, bound):
    result = solve_nonlinear_constraints(
        ["x"], {"x": 1.0},
        [NonlinearConstraint("target", lambda v: v["x"] - target)],
        bounds={"x": bound},
    )
    assert result.status is NonlinearSolveStatus.NOT_CONVERGED
    assert bound.lower <= result.values["x"] <= bound.upper
    assert result.residuals[0].status == "FAIL"


@pytest.mark.parametrize("step", [1e-4, 1e-6, 1e-8])
def test_finite_difference_step_regression_for_smooth_scalar_equation(step):
    result = solve_nonlinear_constraints(
        ["x"], {"x": 1.5},
        [NonlinearConstraint("square", lambda v: v["x"] ** 2 - 9.0)],
        options=NonlinearSolverOptions(finite_difference_step=step),
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert result.values["x"] == pytest.approx(3.0, abs=1e-6)


def test_analytic_and_central_difference_strategies_agree_on_reference_system():
    constraints = [
        NonlinearConstraint("circle", lambda v: v["x"] ** 2 + v["y"] ** 2 - 5.0),
        NonlinearConstraint("line", lambda v: v["x"] + v["y"] - 3.0),
    ]
    initial = {"x": 0.8, "y": 2.2}
    central = solve_nonlinear_constraints(
        ["x", "y"], initial, constraints,
        options=NonlinearSolverOptions(jacobian_method=JacobianMethod.CENTRAL_FINITE_DIFFERENCE),
    )
    analytic = solve_nonlinear_constraints(
        ["x", "y"], initial, constraints,
        options=NonlinearSolverOptions(jacobian_method=JacobianMethod.ANALYTIC),
        jacobian=lambda v: [[2.0 * v["x"], 2.0 * v["y"]], [1.0, 1.0]],
    )
    assert central.status is NonlinearSolveStatus.CONVERGED
    assert analytic.status is NonlinearSolveStatus.CONVERGED
    assert analytic.values["x"] == pytest.approx(central.values["x"], abs=1e-7)
    assert analytic.values["y"] == pytest.approx(central.values["y"], abs=1e-7)


def test_original_unit_tolerances_remain_authoritative_after_residual_scaling():
    result = solve_nonlinear_constraints(
        ["x"], {"x": 0.25},
        [NonlinearConstraint(
            "large_unit_residual",
            lambda v: 1e6 * (v["x"] - 1.0),
            tolerance=1e-6,
            scale=1e6,
        )],
        options=NonlinearSolverOptions(step_tolerance=1e-14),
    )
    assert result.status is NonlinearSolveStatus.CONVERGED
    assert abs(result.residuals[0].value) <= 1e-6
    assert result.residuals[0].status == "PASS"
