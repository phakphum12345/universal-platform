"""Analytic inverse kinematics for a planar two-link revolute arm.

This deliberately narrow solver is a reference vertical slice, not a general
assembly, closed-loop, redundant, or 3D inverse-kinematics engine. Lengths and
target coordinates must use one consistent model length unit; angles are radians.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, atan2, cos, hypot, isfinite, sin, sqrt
from typing import Literal

from .errors import SolverError

ElbowBranch = Literal["up", "down"]
JointLimits = tuple[float | None, float | None] | None


@dataclass(frozen=True, slots=True)
class PlanarIKResult:
    """A two-joint solution and its independently recomputed end-effector pose."""

    shoulder_angle_rad: float
    elbow_angle_rad: float
    achieved_x: float
    achieved_y: float
    position_error: float
    elbow_branch: ElbowBranch


def _validate_limits(name: str, limits: JointLimits) -> None:
    if limits is None:
        return
    if not isinstance(limits, tuple) or len(limits) != 2:
        raise SolverError(f"{name} limits must be a (lower, upper) tuple or None")
    lower, upper = limits
    if lower is not None and not isfinite(lower):
        raise SolverError(f"{name} lower limit must be finite")
    if upper is not None and not isfinite(upper):
        raise SolverError(f"{name} upper limit must be finite")
    if lower is not None and upper is not None and lower > upper:
        raise SolverError(f"{name} limits are inverted")


def _check_limit(name: str, angle: float, limits: JointLimits) -> None:
    if limits is None:
        return
    lower, upper = limits
    if lower is not None and angle < lower:
        raise SolverError(f"{name} angle is below its lower limit")
    if upper is not None and angle > upper:
        raise SolverError(f"{name} angle is above its upper limit")


def solve_planar_two_link_inverse_kinematics(
    link1_length: float,
    link2_length: float,
    target_x: float,
    target_y: float,
    *,
    elbow_branch: ElbowBranch = "up",
    shoulder_limits: JointLimits = None,
    elbow_limits: JointLimits = None,
    tolerance: float = 1e-9,
) -> PlanarIKResult:
    """Solve a planar 2R arm using the law of cosines.

    The shoulder angle is measured from +X. The elbow angle is relative to
    link 1; positive values select the up branch and negative values the
    down branch. The result is rejected if the target is unreachable,
    either joint limit is violated, or the recomputed pose misses tolerance.
    No angle wrapping is applied to user limits: limits are checked against
    the canonical atan2 result in [-pi, pi] and elbow solution in [-pi, pi].
    """
    values = (link1_length, link2_length, target_x, target_y, tolerance)
    if not all(isfinite(value) for value in values):
        raise SolverError("Lengths, target coordinates and tolerance must be finite")
    if link1_length <= 0.0 or link2_length <= 0.0:
        raise SolverError("Link lengths must be positive")
    if tolerance <= 0.0:
        raise SolverError("Tolerance must be positive")
    if elbow_branch not in ("up", "down"):
        raise SolverError("elbow_branch must be 'up' or 'down'")
    _validate_limits("Shoulder", shoulder_limits)
    _validate_limits("Elbow", elbow_limits)

    radius = hypot(target_x, target_y)
    outer_reach = link1_length + link2_length
    inner_reach = abs(link1_length - link2_length)
    if radius > outer_reach + tolerance or radius < inner_reach - tolerance:
        raise SolverError("Target is outside the two-link reachable workspace")

    denominator = 2.0 * link1_length * link2_length
    cosine_elbow = (
        radius * radius - link1_length * link1_length - link2_length * link2_length
    ) / denominator
    cosine_elbow = max(-1.0, min(1.0, cosine_elbow))
    magnitude = acos(cosine_elbow)
    elbow = magnitude if elbow_branch == "up" else -magnitude
    shoulder = atan2(target_y, target_x) - atan2(
        link2_length * sin(elbow),
        link1_length + link2_length * cos(elbow),
    )
    shoulder = atan2(sin(shoulder), cos(shoulder))

    _check_limit("Shoulder", shoulder, shoulder_limits)
    _check_limit("Elbow", elbow, elbow_limits)

    achieved_x = link1_length * cos(shoulder) + link2_length * cos(shoulder + elbow)
    achieved_y = link1_length * sin(shoulder) + link2_length * sin(shoulder + elbow)
    error = sqrt((achieved_x - target_x) ** 2 + (achieved_y - target_y) ** 2)
    if not isfinite(error) or error > tolerance:
        raise SolverError(
            f"Inverse-kinematics residual {error!r} exceeds tolerance {tolerance!r}"
        )
    return PlanarIKResult(
        shoulder_angle_rad=shoulder,
        elbow_angle_rad=elbow,
        achieved_x=achieved_x,
        achieved_y=achieved_y,
        position_error=error,
        elbow_branch=elbow_branch,
    )
