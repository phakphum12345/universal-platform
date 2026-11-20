"""Narrow planar four-bar loop-closure and mobility-estimate utilities.

This module solves one rigid planar 4R loop by circle intersection. It is not
a general nonlinear constraint solver or a proof of mechanism mobility.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, isfinite, sin, sqrt
from typing import Literal

from .errors import SolverError

AssemblyBranch = Literal["left", "right"]


@dataclass(frozen=True, slots=True)
class PlanarFourBarResult:
    """Closed planar 4R geometry with closure residuals in model length units."""

    input_joint_x: float
    input_joint_y: float
    coupler_joint_x: float
    coupler_joint_y: float
    coupler_angle_rad: float
    output_angle_rad: float
    branch: AssemblyBranch
    closure_error: float


@dataclass(frozen=True, slots=True)
class PlanarMobilityEstimate:
    """Kutzbach/Gruebler planar mobility count, not a singularity proof."""

    link_count: int
    lower_pair_count: int
    higher_pair_count: int
    estimated_degrees_of_freedom: int
    interpretation: str


def solve_planar_four_bar_loop(
    ground_length: float,
    input_crank_length: float,
    coupler_length: float,
    output_rocker_length: float,
    input_angle_rad: float,
    *,
    branch: AssemblyBranch = "left",
    tolerance: float = 1e-9,
) -> PlanarFourBarResult:
    """Close a planar 4R loop using the intersection of two circles.

    The ground pivots are A=(0, 0) and D=(ground_length, 0). The input
    crank endpoint B is fixed by input_angle_rad. The coupler endpoint C is
    selected from a circle around B (coupler radius) and a circle around D
    (rocker radius). Branch is left/right of directed B→D. All lengths and
    tolerance use one consistent model length unit; angles are radians.
    Tangent configurations are accepted even though both branches then coincide.
    """
    values = (
        ground_length,
        input_crank_length,
        coupler_length,
        output_rocker_length,
        input_angle_rad,
        tolerance,
    )
    if not all(isfinite(value) for value in values):
        raise SolverError("Four-bar lengths, input angle and tolerance must be finite")
    if min(
        ground_length, input_crank_length, coupler_length, output_rocker_length
    ) <= 0.0:
        raise SolverError("Four-bar link lengths must be positive")
    if tolerance <= 0.0:
        raise SolverError("Tolerance must be positive")
    if branch not in ("left", "right"):
        raise SolverError("branch must be 'left' or 'right'")

    bx = input_crank_length * cos(input_angle_rad)
    by = input_crank_length * sin(input_angle_rad)
    dx, dy = ground_length - bx, -by
    center_distance = hypot(dx, dy)
    if center_distance <= tolerance:
        raise SolverError("Four-bar circle centers coincide; loop is degenerate")

    outer_reach = coupler_length + output_rocker_length
    inner_reach = abs(coupler_length - output_rocker_length)
    if (
        center_distance > outer_reach + tolerance
        or center_distance < inner_reach - tolerance
    ):
        raise SolverError("Four-bar loop cannot close for this input angle")

    along = (
        coupler_length * coupler_length
        - output_rocker_length * output_rocker_length
        + center_distance * center_distance
    ) / (2.0 * center_distance)
    height_squared = coupler_length * coupler_length - along * along
    if height_squared < -(tolerance * tolerance):
        raise SolverError("Four-bar circle intersection is numerically invalid")
    height = sqrt(max(0.0, height_squared))

    ux, uy = dx / center_distance, dy / center_distance
    perpendicular_x, perpendicular_y = -uy, ux
    side = 1.0 if branch == "left" else -1.0
    cx = bx + along * ux + side * height * perpendicular_x
    cy = by + along * uy + side * height * perpendicular_y

    coupler_angle = atan2(cy - by, cx - bx)
    output_angle = atan2(cy, cx - ground_length)
    input_residual = abs(hypot(bx, by) - input_crank_length)
    coupler_residual = abs(hypot(cx - bx, cy - by) - coupler_length)
    output_residual = abs(hypot(cx - ground_length, cy) - output_rocker_length)
    closure_error = max(input_residual, coupler_residual, output_residual)
    if not isfinite(closure_error) or closure_error > tolerance:
        raise SolverError(
            f"Four-bar closure residual {closure_error!r} exceeds tolerance {tolerance!r}"
        )

    return PlanarFourBarResult(
        input_joint_x=bx,
        input_joint_y=by,
        coupler_joint_x=cx,
        coupler_joint_y=cy,
        coupler_angle_rad=coupler_angle,
        output_angle_rad=output_angle,
        branch=branch,
        closure_error=closure_error,
    )


def estimate_planar_mobility(
    link_count: int,
    lower_pair_count: int,
    higher_pair_count: int = 0,
) -> PlanarMobilityEstimate:
    """Return the planar Kutzbach/Gruebler mobility estimate.

    M = 3 * (N - 1) - 2 * J1 - J2, where N includes the ground link,
    J1 counts one-DOF lower pairs, and J2 counts higher pairs. Negative values
    indicate a nominally over-constrained count and require model-specific
    review; special geometry, redundant constraints and singularities can make
    the formula differ from actual mobility.
    """
    values = (link_count, lower_pair_count, higher_pair_count)
    if any(type(value) is not int for value in values):
        raise SolverError("Mobility counts must be integers")
    if link_count < 2:
        raise SolverError("A planar mechanism must include at least two links")
    if lower_pair_count < 0 or higher_pair_count < 0:
        raise SolverError("Joint-pair counts cannot be negative")

    dof = 3 * (link_count - 1) - 2 * lower_pair_count - higher_pair_count
    if dof > 0:
        interpretation = "positive_nominal_mobility"
    elif dof == 0:
        interpretation = "zero_nominal_mobility"
    else:
        interpretation = "negative_nominal_mobility_requires_review"
    return PlanarMobilityEstimate(
        link_count=link_count,
        lower_pair_count=lower_pair_count,
        higher_pair_count=higher_pair_count,
        estimated_degrees_of_freedom=dof,
        interpretation=interpretation,
    )
