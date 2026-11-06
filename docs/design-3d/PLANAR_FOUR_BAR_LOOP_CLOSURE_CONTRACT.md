# Planar Four-Bar Loop-Closure and Mobility Contract

**Status:** Initial planar 4R loop-closure adapter and Kutzbach mobility estimate implemented on a feature branch; exact-SHA CI pending.

## Scope

This contract covers one planar four-link mechanism with four revolute joints (4R): a ground link, input crank, coupler and output rocker. It closes the loop analytically by intersecting the coupler and rocker endpoint circles. It also exposes the planar Kutzbach/Gruebler mobility count.

This is not a general nonlinear constraint solver, arbitrary closed-loop assembly solver, 3D mechanism solver or physical controller.

## Geometry and conventions

- Ground pivot A is (0, 0); output ground pivot D is (ground_length, 0).
- Input joint B is set by input_crank_length and input_angle_rad.
- Coupler length is the radius of the circle centered at B.
- Output rocker length is the radius of the circle centered at D.
- All lengths use one consistent model length unit; angles are radians.
- The selected assembly branch is left or right of the directed line B→D.
- The requested tolerance is an absolute closure residual in the model length unit.

## Loop-closure method

Find C as the intersection of two circles:

- Center B, radius coupler_length.
- Center D, radius output_rocker_length.

The center distance must lie in the inclusive interval between the absolute radius difference and the sum of radii. The along-axis distance follows the circle-intersection equation; the perpendicular offset selects left or right branch. Tangent intersections are accepted and both branches coincide.

The returned closure_error is the maximum absolute residual among the input crank, coupler and output rocker lengths. A result is returned only when this residual is finite and no greater than tolerance.

## Mobility estimate

The planar Kutzbach/Gruebler estimate is:

    M = 3 * (N - 1) - 2 * J1 - J2

N includes the ground link; J1 is the number of one-DOF lower pairs; J2 is the number of higher pairs. Negative estimates require model-specific review. The formula is a count, not a proof: special geometry, redundant constraints and singular configurations can make actual mobility differ.

## API

- solve_planar_four_bar_loop(ground_length, input_crank_length, coupler_length, output_rocker_length, input_angle_rad, *, branch="left", tolerance=1e-9)
- estimate_planar_mobility(link_count, lower_pair_count, higher_pair_count=0)

## Failure behavior

Reject non-finite values, non-positive link lengths, invalid branch names, non-positive tolerance, coincident circle centers, unreachable circle configurations, invalid mobility counts and closure residuals above tolerance. No silent constraint relaxation or branch inference is performed.

## Explicit exclusions

No arbitrary topology, more than one loop, multi-loop coupling, 3D constraints, non-revolute pairs, generic nonlinear iteration, redundancy resolution, automatic singularity classification, dynamic simulation, collision/contact, friction, backlash, compliance, uncertainty propagation, physical device control or safety certification.

## Acceptance evidence

Tests cover both branches, independent link-length closure, tangent boundary, unreachable outer/inner configurations, degenerate centers, invalid inputs and Kutzbach mobility examples for a four-bar, a triangle and a negative count requiring review. Passing tests validates only this planar 4R adapter and mobility estimate at the tested commit SHA.
