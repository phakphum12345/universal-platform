import math

import pytest

from universal_platform.engineering.errors import SolverError
from universal_platform.engineering.inverse_kinematics import (
    solve_planar_two_link_inverse_kinematics,
)


def solve(x, y, **kwargs):
    return solve_planar_two_link_inverse_kinematics(2.0, 1.0, x, y, **kwargs)


def test_reaches_target_on_elbow_up_branch():
    result = solve(2.0, 1.0, elbow_branch="up")
    assert result.elbow_branch == "up"
    assert result.elbow_angle_rad > 0.0
    assert result.achieved_x == pytest.approx(2.0, abs=1e-9)
    assert result.achieved_y == pytest.approx(1.0, abs=1e-9)
    assert result.position_error <= 1e-9


def test_reaches_target_on_elbow_down_branch():
    result = solve(2.0, 1.0, elbow_branch="down")
    assert result.elbow_branch == "down"
    assert result.elbow_angle_rad < 0.0
    assert result.achieved_x == pytest.approx(2.0, abs=1e-9)
    assert result.achieved_y == pytest.approx(1.0, abs=1e-9)


def test_both_branches_reach_same_target_with_distinct_joint_solutions():
    up = solve(1.5, 0.75, elbow_branch="up")
    down = solve(1.5, 0.75, elbow_branch="down")
    assert up.shoulder_angle_rad != pytest.approx(down.shoulder_angle_rad)
    assert up.elbow_angle_rad == pytest.approx(-down.elbow_angle_rad)
    assert up.achieved_x == pytest.approx(down.achieved_x, abs=1e-9)
    assert up.achieved_y == pytest.approx(down.achieved_y, abs=1e-9)


def test_accepts_fully_extended_singular_boundary():
    result = solve(3.0, 0.0)
    assert result.shoulder_angle_rad == pytest.approx(0.0, abs=1e-9)
    assert result.elbow_angle_rad == pytest.approx(0.0, abs=1e-9)
    assert result.position_error <= 1e-9


def test_accepts_fully_folded_inner_boundary_for_equal_links():
    result = solve_planar_two_link_inverse_kinematics(1.0, 1.0, 0.0, 0.0)
    assert abs(result.elbow_angle_rad) == pytest.approx(math.pi)
    assert result.position_error <= 1e-9


@pytest.mark.parametrize("target", [(3.01, 0.0), (0.99, 0.0), (0.0, 0.0)])
def test_rejects_unreachable_target_for_unequal_links(target):
    with pytest.raises(SolverError, match="reachable workspace"):
        solve(*target)


def test_rejects_shoulder_limit_violation():
    with pytest.raises(SolverError, match="Shoulder angle"):
        solve(2.0, 1.0, shoulder_limits=(0.1, 0.2))


def test_rejects_elbow_limit_violation():
    with pytest.raises(SolverError, match="Elbow angle"):
        solve(2.0, 1.0, elbow_limits=(-0.1, 0.1))


def test_rejects_inverted_or_non_finite_limits():
    with pytest.raises(SolverError, match="inverted"):
        solve(2.0, 1.0, shoulder_limits=(1.0, -1.0))
    with pytest.raises(SolverError, match="must be finite"):
        solve(2.0, 1.0, elbow_limits=(float("-inf"), None))


@pytest.mark.parametrize("lengths", [(0.0, 1.0), (-1.0, 1.0)])
def test_rejects_non_positive_link_lengths(lengths):
    with pytest.raises(SolverError, match="positive"):
        solve_planar_two_link_inverse_kinematics(*lengths, 1.0, 0.0)


@pytest.mark.parametrize("target", [(float("nan"), 0.0), (0.0, float("inf"))])
def test_rejects_non_finite_target(target):
    with pytest.raises(SolverError, match="finite"):
        solve(*target)


def test_rejects_invalid_branch_and_tolerance():
    with pytest.raises(SolverError, match="elbow_branch"):
        solve(2.0, 1.0, elbow_branch="middle")
    with pytest.raises(SolverError, match="Tolerance"):
        solve(2.0, 1.0, tolerance=0.0)


@pytest.mark.parametrize(
    "x,y",
    [(2.8, 0.2), (1.5, 0.75), (0.5, 1.5), (-1.0, 1.0), (-2.5, -0.2)],
)
def test_reference_targets_reconstruct_with_small_residual(x, y):
    for branch in ("up", "down"):
        result = solve(x, y, elbow_branch=branch)
        assert result.position_error <= 1e-9
        assert result.achieved_x == pytest.approx(x, abs=1e-9)
        assert result.achieved_y == pytest.approx(y, abs=1e-9)
