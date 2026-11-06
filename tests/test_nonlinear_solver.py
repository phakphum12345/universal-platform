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
