# Geometry-aware Mechanism Loop-Closure Evaluation Contract

**Status:** Implemented in PR #35; evaluates supplied configurations only.

## Purpose

Connect deterministic graph-cycle analysis (PR #28) with generated geometric joint pose-consistency residuals (PR #33) and normalized placement/coordinate contracts (PR #31/#32). This layer evaluates whether a caller-supplied configuration satisfies every represented joint relation and reports each fundamental loop's closing-joint residuals.

## Inputs

- A structurally valid normalized `MechanismModel` with explicit joint placements for every joint.
- Explicit generalized-coordinate parameterization for every non-fixed joint.
- Exactly one body-to-world `RigidTransform` per link, using each link's declared body frame and one common world frame.
- Exactly one finite in-limit value per generalized coordinate.
- Explicit positive translation and rotation tolerances (metres and radians).

## Evaluation

1. Analyze deterministic spanning-forest/fundamental-cycle topology.
2. Reject models without a graph loop.
3. Generate and evaluate all six-component pose-consistency residuals for every joint.
4. Group the six residuals for each loop-closing joint under its stable loop ID.
5. Retain all joint residuals, including spanning-tree joints, so a failed tree relation cannot be hidden by a passing closing edge.
6. Return PASS only when every represented joint residual and every loop-closing group is within tolerance; otherwise return FAIL with full residual evidence.

Each loop group preserves loop ID, closing joint ID, ordered joint path, closed link path, residual IDs, units, tolerances and values. Serialization is deterministic and JSON-compatible.

## Interpretation

PASS means only that the supplied poses and coordinate values satisfy represented joint pose-consistency equations within declared numerical tolerances. It is a configuration-consistency result, not proof that a configuration exists for arbitrary inputs and not a physical-feasibility statement.

## Limitations

- No configuration search or nonlinear solver integration; callers provide body poses and coordinate values.
- No branch discovery, continuation, singularity proof, global reachability or uniqueness.
- No automatic geometry inference from CAD, collision/contact, friction, dynamics, forces, structural analysis, manufacturing validation or certification.
- The six-component residual representation is not a count of independent constraints or DOF.

## Acceptance criteria

- A closed planar four-bar reference configuration returns PASS with six residuals on its closing edge.
- Perturbed body poses return FAIL and preserve all residuals.
- Multiple independent fundamental cycles are evaluated deterministically.
- Input reordering does not change serialized output.
- A model with no graph loop is rejected.
- Existing mechanism, solver, placement, mobility, kinematics and Jacobian regression tests remain unchanged and pass.
