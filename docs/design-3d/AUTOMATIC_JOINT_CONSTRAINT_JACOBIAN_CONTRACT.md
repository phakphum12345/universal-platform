# Automatic Joint Constraint Jacobian Contract

**Status:** Implemented candidate in PR #34; merge and exact-SHA CI evidence pending.

## Purpose

Construct a deterministic numerical Jacobian for the generated six-component joint pose-consistency residuals. The matrix differentiates residuals with respect to generalized-coordinate values and body-pose tangent variables. It is intended as a reusable local derivative estimate for downstream analysis and solver adapters.

## Rows and columns

- Rows preserve the generated joint constraint definition order and stable constraint IDs.
- Generalized-coordinate columns are ordered by coordinate ID.
- Body-pose columns follow sorted link ID, with translation_x/y/z then rotation_x/y/z.
- Body translation variables are world-frame metres.
- Body rotation variables are world-frame infinitesimal rotations applied on the left to the body-to-world rotation while holding the body origin fixed; units are radians.
- Matrix entries use residual-unit divided by variable-unit. Row units are preserved in the snapshot.

## Difference strategies

- CENTRAL_FINITE_DIFFERENCE is the default when both perturbation directions are feasible.
- FORWARD_FINITE_DIFFERENCE is supported.
- At coordinate limits, the implementation chooses a feasible one-sided direction and records FORWARD_FINITE_DIFFERENCE or BACKWARD_FINITE_DIFFERENCE per column.
- A coordinate fixed at both bounds has a zero column marked BOUND_LOCKED.
- Perturbation size is the configured relative step multiplied by the larger of the absolute variable value and the declared characteristic scale.

## Validation and determinism

- Reuses the generated constraint evaluator; pose, coordinate and frame validation is applied at every perturbed state.
- Rejects analytic mode (no exact analytic derivative is claimed), non-positive/non-finite steps and non-finite matrix entries.
- Returns stable row IDs, variable IDs, column metadata, steps, per-column strategy, raw matrix values and base residual values.
- Serialization is deterministic and JSON-compatible.

## Limitations

- Finite differences are step-sensitive approximations, not symbolic or exact derivatives.
- Body-pose rotational columns use the stated world-frame tangent convention; another solver parameterization would require a corresponding Jacobian mapping.
- No automatic nonlinear solve, convergence, uniqueness, rank proof, dynamics, contact/collision, physical feasibility or certification is implied.
