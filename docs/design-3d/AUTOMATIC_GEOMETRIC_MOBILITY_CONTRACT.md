# Automatic Geometric Mobility Analysis Contract

**Status:** SPATIAL geometric mobility implemented in PR #37; explicit PLANAR plane-frame projection implemented in PR #56. Exact-head and post-merge CI both pass.

## Purpose

Build local mobility diagnostics from geometric joint residuals and the finite-difference Jacobian introduced in PRs #33 and #34. Unlike nominal Kutzbach/Gruebler counting, this evaluates numerical constraint rank at one supplied configuration.

## Inputs

- A valid normalized mechanism with explicit joint placements and complete generalized-coordinate parameterization.
- One body-to-world rigid pose per link in a shared world frame.
- One finite value per generalized coordinate.
- A stable ground-link ID and configuration ID.
- A finite-difference method and positive step.
- Optional reference constraint rank for comparison with a regular configuration.

## Variable construction

- Include six body-pose tangent variables for each non-ground link: world-frame translations in metres and left-perturbed world-frame rotations in radians.
- Exclude all six ground-link pose variables to remove the global rigid-body gauge.
- Include every independent generalized joint coordinate with the units and characteristic scale declared by the model.
- Preserve deterministic variable ordering from the generated Jacobian.
- The resulting local variable count is 6 * (link_count - 1) + generalized_coordinate_count.

## Mobility and rank

- Evaluate every generated six-component joint residual row.
- Estimate rank with the existing threshold-dependent numerical rank routine.
- Local mobility is combined variable count minus estimated rank.
- Keep nominal spatial joint-count mobility separate from local Jacobian mobility.
- Report redundant residual rows separately; row redundancy alone is not proof of physical overconstraint.
- Singularity is UNKNOWN unless a regular-configuration reference rank is explicitly supplied. A lower rank indicates POSSIBLE_SINGULARITY only.

## Formulation boundary

SPATIAL uses six pose-tangent variables per non-ground link. PLANAR requires an explicit plane-to-world RigidTransform, verifies body origins and local +Z axes, validates joint anchors and coordinate axes, then projects the full world-frame Jacobian to two in-plane translations and one plane-normal rotation per non-ground link. It does not silently project an arbitrary 3D snapshot. PR #56 sets the geometric-mobility default finite-difference step to 1e-5 to reduce round-off amplification from composed frames; explicit caller overrides remain supported.

## Limitations

- Finite-difference rank depends on perturbation step, coordinate scaling, residual units and rank tolerance.
- Rank estimates are numerical, not exact mathematical proofs.
- No global mobility proof, branch discovery, reachability, nonlinear pose solving, dynamics, contact/collision, physical feasibility or certification.

## Acceptance criteria

- A fixed two-link joint reports zero local spatial mobility.
- Revolute and prismatic two-link references each report one local mobility.
- Ground-link reversal preserves local mobility and removes the selected ground pose columns.
- Combined body-pose and joint-coordinate variables are declared explicitly.
- Legacy caller-supplied ConstraintJacobian usage remains compatible.
- PLANAR requests fail closed without an explicit plane_frame and coplanarity validation. PR #56 implements this contract and passes exact-head and post-merge CI.
