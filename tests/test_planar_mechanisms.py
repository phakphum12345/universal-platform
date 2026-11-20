import math

import pytest

from universal_platform.engineering.errors import SolverError
from universal_platform.engineering.planar_mechanisms import (
    estimate_planar_mobility,
    solve_planar_four_bar_loop,
)


def four_bar(branch="left", angle=math.pi / 2, **kwargs):
    return solve_planar_four_bar_loop(4.0, 1.0, 3.0, 3.0, angle, branch=branch, **kwargs)


def test_four_bar_loop_closes_on_left_and_right_branches():
    left = four_bar("left")
    right = four_bar("right")
    assert left.branch == "left"
    assert right.branch == "right"
    assert left.input_joint_x == pytest.approx(right.input_joint_x)
    assert left.input_joint_y == pytest.approx(right.input_joint_y)
    assert left.coupler_joint_x != pytest.approx(right.coupler_joint_x)
    assert left.coupler_joint_y != pytest.approx(right.coupler_joint_y)
    assert left.closure_error <= 1e-9
    assert right.closure_error <= 1e-9


def test_four_bar_reports_angles_and_reconstructable_joint_positions():
    result = four_bar()
    assert math.isfinite(result.coupler_angle_rad)
    assert math.isfinite(result.output_angle_rad)
    assert math.hypot(result.coupler_joint_x - result.input_joint_x,
                      result.coupler_joint_y - result.input_joint_y) == pytest.approx(3.0)
    assert math.hypot(result.coupler_joint_x - 4.0,
                      result.coupler_joint_y) == pytest.approx(3.0)


def test_four_bar_accepts_tangent_outer_workspace_boundary():
    result = solve_planar_four_bar_loop(1.0, 2.0, 1.5, 1.5, math.pi)
    assert result.coupler_joint_x == pytest.approx(-0.5, abs=1e-9)
    assert result.coupler_joint_y == pytest.approx(0.0, abs=1e-9)
    assert result.closure_error <= 1e-9


def test_four_bar_rejects_unreachable_outer_configuration():
    with pytest.raises(SolverError, match="cannot close"):
        solve_planar_four_bar_loop(4.0, 1.0, 1.0, 1.0, 0.0)


def test_four_bar_rejects_unreachable_inner_configuration():
    with pytest.raises(SolverError, match="cannot close"):
        solve_planar_four_bar_loop(0.5, 1.0, 3.0, 1.0, 0.0)


def test_four_bar_rejects_coincident_circle_centers():
    with pytest.raises(SolverError, match="centers coincide"):
        solve_planar_four_bar_loop(1.0, 1.0, 2.0, 2.0, 0.0)


def test_four_bar_rejects_invalid_branch_and_tolerance():
    with pytest.raises(SolverError, match="branch must"):
        four_bar("middle")
    with pytest.raises(SolverError, match="Tolerance"):
        four_bar(tolerance=0.0)


@pytest.mark.parametrize("lengths", [(0.0, 1.0, 1.0, 1.0), (1.0, -1.0, 1.0, 1.0)])
def test_four_bar_rejects_non_positive_lengths(lengths):
    with pytest.raises(SolverError, match="positive"):
        solve_planar_four_bar_loop(*lengths, 0.2)


def test_four_bar_rejects_non_finite_inputs():
    with pytest.raises(SolverError, match="finite"):
        solve_planar_four_bar_loop(4.0, 1.0, 3.0, 3.0, float("nan"))


def test_planar_mobility_estimates_four_bar_as_one_dof():
    result = estimate_planar_mobility(link_count=4, lower_pair_count=4)
    assert result.estimated_degrees_of_freedom == 1
    assert result.interpretation == "positive_nominal_mobility"


def test_planar_mobility_estimates_triangle_as_zero_dof():
    result = estimate_planar_mobility(link_count=3, lower_pair_count=3)
    assert result.estimated_degrees_of_freedom == 0
    assert result.interpretation == "zero_nominal_mobility"


def test_planar_mobility_flags_negative_count_for_review():
    result = estimate_planar_mobility(link_count=3, lower_pair_count=4)
    assert result.estimated_degrees_of_freedom == -2
    assert result.interpretation == "negative_nominal_mobility_requires_review"


@pytest.mark.parametrize(
    "counts",
    [(1, 0, 0), (4, -1, 0), (4, 0, -1), (4.0, 4, 0), (True, 4, 0)],
)
def test_planar_mobility_rejects_invalid_counts(counts):
    with pytest.raises(SolverError):
        estimate_planar_mobility(*counts)
