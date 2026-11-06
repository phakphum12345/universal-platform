# Planar Two-Link Inverse-Kinematics Contract

**Status:** Initial analytic adapter implemented; narrow reference capability only.

## Scope

This contract defines inverse kinematics for a planar serial arm with exactly two rigid links and two revolute joints (2R). It is not a general assembly solver, 3D solver, closed-loop constraint solver, redundant-arm optimizer or physical controller.

## Inputs and conventions

- Positive finite link lengths, expressed in one consistent model length unit.
- Finite target point (x, y) in the same planar coordinate frame and length unit.
- elbow_branch is up or down.
- Optional shoulder and elbow limits are canonical angle bounds in radians.
- Positive finite absolute Cartesian residual tolerance.
- Shoulder angle is measured from +X; elbow angle is relative to link 1.
- Positive elbow angle selects the up branch; negative selects the down branch.

## Method

Use the law of cosines:

    cos(q2) = (x² + y² - L1² - L2²) / (2 L1 L2)
    q2 = ±acos(clamp(cos(q2), -1, 1))
    q1 = atan2(y, x) - atan2(L2 sin(q2), L1 + L2 cos(q2))

The candidate is independently reconstructed with the forward equations. A result is returned only when its Cartesian residual is no greater than the requested tolerance.

## Reachability and failure behavior

The reachable radial interval is abs(L1-L2) <= hypot(x,y) <= L1+L2. Targets outside the interval, beyond tolerance, fail with SolverError. Small floating-point excursions at a boundary are clamped only after the reachability test. Non-finite values, non-positive lengths, invalid branch names, invalid limits, joint-limit violations and residual failures are rejected.

Fully extended and fully folded boundary configurations are accepted when numerically reconstructable. At singular configurations, the two branches may coincide; the returned branch records the requested branch, not a claim of distinct physical postures.

## API

solve_planar_two_link_inverse_kinematics(link1_length, link2_length, target_x, target_y, *, elbow_branch="up", shoulder_limits=None, elbow_limits=None, tolerance=1e-9)

Returns PlanarIKResult with shoulder/elbow angles in radians, reconstructed end-effector coordinates, Cartesian position error and requested branch.

## Explicit exclusions

No 3D inverse kinematics, arbitrary joint chains, joint offsets, non-planar axes, closed-loop closure, redundancy resolution, collision avoidance, singularity conditioning analysis, dynamics, actuator sizing, friction, backlash, compliance, uncertainty propagation, physical device control or safety certification.

## Acceptance evidence

Tests cover both branches, reconstruction residuals, fully extended/folded boundaries, inner/outer unreachable targets, non-finite values, invalid lengths/limits/branch/tolerance and joint-limit violations. Passing these tests validates only this analytic 2R adapter at the tested commit SHA.
