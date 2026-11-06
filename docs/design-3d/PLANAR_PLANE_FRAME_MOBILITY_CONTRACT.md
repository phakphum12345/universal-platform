# Planar Plane-Frame Mobility Contract

**Status:** Contract and acceptance criteria for the explicit 2D geometric-mobility adapter. The existing SPATIAL formulation remains unchanged.

## 1. Plane-frame definition

- The caller supplies a `RigidTransform` named `plane_frame` mapping a stable plane frame into the shared world frame.
- The plane frame's local +X/+Y axes define the analysis plane; local +Z is its normal.
- All link body poses map link frames into the same world frame and use metres (m), matching the generated translational residuals and `plane_tolerance_m`.
- Every body origin must lie on the plane within `plane_tolerance_m`.
- Every body frame's local +Z axis must align with the plane normal within `angular_tolerance_rad`; body motion is restricted to two in-plane translations and rotation about the plane normal.
- Every joint-frame origin must lie on the plane. Rotational generalized-coordinate axes must be parallel to the plane normal; translational axes must lie in the plane.

## 2. Supported joint families

The 2D mobility formulation supports FIXED, REVOLUTE, PRISMATIC and PLANAR joints only. CYLINDRICAL, HELICAL, SPHERICAL and UNIVERSAL are rejected rather than projected or silently approximated. A PLANAR joint kind is also valid in the SPATIAL formulation; that is distinct from selecting the PLANAR mobility formulation.

## 3. Variable construction and rank

- Use the existing generated six-component joint residuals and finite-difference Jacobian as the source of derivatives.
- Preserve every independent generalized-coordinate column.
- For each non-ground link, project the full world-frame body-pose columns into exactly three plane variables: translation along plane +X, translation along plane +Y, and left rotation about plane +Z.
- Exclude all three planar pose variables of the selected ground link.
- Keep deterministic ordering: generalized-coordinate IDs first, then sorted non-ground link IDs, each with plane translation X, plane translation Y and plane-normal rotation.
- The reduced column count is `3 * (link_count - 1) + generalized_coordinate_count`.
- The generated residual rows remain in stable joint/component order. Numerical rank and mobility are local estimates at the supplied configuration.

## 4. Acceptance criteria

1. Missing `plane_frame` is rejected for PLANAR analysis; existing SPATIAL calls remain backward compatible.
2. Single-joint references for FIXED, REVOLUTE, PRISMATIC and PLANAR return expected local mobility 0, 1, 1 and 3 respectively.
3. Regular single-joint references have the expected reduced variable count and constraint rank; reference-rank comparison is explicit.
4. Reversing the ground link preserves local mobility and removes the selected ground link's three plane-pose variables.
5. A translated and rotated plane frame produces the same local mobility as the canonical world-XY plane.
6. Out-of-plane body origins, tilted body frames, off-plane joint anchors and incompatible joint axes fail closed.
7. Unsupported joint families fail with a clear error; no projection is attempted.
8. Deterministic plane-variable IDs, column ordering, units, and JSON-compatible result snapshots are preserved.
9. Non-positive/non-finite tolerances, mismatched world frames and length units fail closed.

## 5. Limitations

This is a local planar mobility estimate for ideal lower-pair joints, not a general closed-loop configuration solver or proof of global mobility. It does not handle higher pairs, contact, friction, collision, dynamics, singularity-free branch discovery, physical feasibility, physical testing, certification or machine control. Numerical rank remains dependent on finite-difference step, scaling and tolerance.
