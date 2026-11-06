# Geometric Loop Coordinate Solver Contract

**Status:** Implementation candidate in PR #36; fixed body poses, generalized-coordinate variables only.

## Purpose

Provide a bounded local solver adapter that fits explicit generalized-coordinate values to the geometry-aware joint pose-consistency equations. It composes the normalized schema v1.2, explicit joint placements, generated residuals, and the dependency-free nonlinear equality solver.

## Inputs

- A normalized mechanism with at least one graph loop.
- Explicit placement for every joint and complete generalized-coordinate parameterization for every non-fixed joint.
- One caller-supplied body-to-world pose per link, all targeting the same world frame.
- One finite initial value per generalized coordinate, within its declared limits.
- Positive translation and rotation tolerances in metres and radians.
- Optional nonlinear solver settings.

## Variables and equations

- Solver variables are generalized-coordinate IDs sorted deterministically.
- Body poses are fixed throughout the solve; they are not solver variables.
- Every generated six-component joint residual participates, including spanning-tree joints and loop-closing joints.
- Each residual is normalized by its declared tolerance for the least-squares objective; final acceptance remains in original residual units.
- Coordinate lower/upper limits and characteristic scales are forwarded to the solver.
- The final coordinate values are re-evaluated by the geometry-aware loop-closure evaluator.

## Status

- CONVERGED requires both the nonlinear solver's per-equation acceptance and a final geometric evaluation with all represented joint residuals within tolerance.
- NOT_CONVERGED preserves the solver's final values and residual evidence.
- A failed local solve is not classified as UNREACHABLE, SINGULAR, or physically infeasible.

## Limitations

- Body poses are fixed caller inputs; the adapter does not solve for link translations or rotations.
- No global search, branch discovery, continuation, uniqueness proof, or general 3D configuration solving.
- No dynamics, force/torque, collision/contact, friction, stability, physical validation, or certification.
- The solver remains local damped least squares; convergence depends on initialization, scaling, bounds, and model residuals.

## Acceptance criteria

- A closed four-bar reference with nonzero initial joint coordinates converges to a residual-valid coordinate state.
- Incompatible fixed body poses return NOT_CONVERGED with retained residual evidence.
- Coordinate bounds are enforced and characteristic scales are preserved.
- Missing loop topology or incomplete coordinate coverage fails closed.
- An analytic derivative mode is rejected because this adapter does not provide exact analytic derivatives.
- Existing regression suites remain unchanged and pass.
