# Nonlinear Constraint Solver Contract

**Status:** Implemented narrow numerical core; general mechanism solving remains open.

## Purpose

Provide a small, dependency-free local nonlinear equality solver that can be reused by mechanism, geometry and multidisciplinary model adapters. The first implementation is a finite-difference Levenberg–Marquardt least-squares solver.

## Input contract

- Variables have unique non-empty string identifiers and finite initial scalar values.
- Each constraint has a unique identifier and a callable scalar residual. A satisfied equality has residual zero.
- Each constraint defines a positive residual tolerance in original units and a positive scale used only to normalize the optimization objective.
- Optional variable bounds are finite lower/upper endpoints; trial values are projected into the declared interval.
- Solver options define iteration, finite-difference, step and damping limits, plus a Jacobian strategy. Forward finite differences remain the default; central differences and an analytic callback are opt-in.
- An analytic Jacobian callback returns an `m × n` matrix in constraint order and variable order, containing derivatives of the original (unscaled) residuals. The solver validates its shape and finite values, then applies each residual scale internally.
- A positive relative rank tolerance controls a dependency-free modified Gram–Schmidt estimate with column pivoting. The estimate is computed from the scaled Jacobian used by the solver; it is a numerical diagnostic, not a proof of mathematical rank. Its threshold sensitivity is tested using nearly dependent columns.
- The caller owns units, coordinate frames and physical interpretation. Residuals from unlike dimensions must be normalized deliberately using documented scales.

## Algorithm

1. Evaluate and validate all residuals at the initial point.
2. Estimate the Jacobian with the selected strategy: forward finite differences (default), central finite differences, or a validated analytic callback.
3. Form damped normal equations: (JᵀJ + λD) Δ = −Jᵀr.
4. Solve the small dense linear system using the existing partial-pivoting solver.
5. Project the trial variables into optional bounds.
6. Accept an improving step and reduce damping; otherwise increase damping.
7. Converge only when every original, unscaled residual is within its own tolerance.

## Result semantics

- CONVERGED means every supplied equality residual passed its declared tolerance at the returned point.
- NOT_CONVERGED includes stationary points, damping limits, iteration limits and bound-limited unsatisfied systems.
- Individual residuals are always returned as PASS or FAIL.
- Input/model evaluation errors raise SolverError; no missing/non-finite residual is silently treated as zero.
- The result includes the iteration count, objective, termination reason, method and limitations.
- Derivative strategy and residual/Jacobian/analytic-Jacobian evaluation counts are reported separately. Residual evaluation counts are scalar residual callback invocations.
- When a Jacobian has been evaluated, the result reports estimated rank, threshold, matrix shape and whether the estimate is full rank, rank deficient or indeterminate. The matrix shape separately identifies underdetermined, square and overdetermined systems. If no Jacobian was needed, diagnostics are `None` (not computed).

## Explicit limitations

This is a local numerical least-squares method, not a general symbolic or global solver. It does not currently implement inequality constraints, complementarity/contact, sparse matrices, automatic dimensional analysis, condition estimates, continuation, branch enumeration, topology changes or automatic gauge fixing. Redundant or underdetermined systems may have non-unique solutions. Initial guesses, residual scaling, smoothness and bounds materially affect convergence.

It does not by itself solve arbitrary CAD constraints, multi-loop assemblies, 3D mechanisms, dynamics or physical feasibility. Such integrations require adapter-specific residual definitions, independent reference cases and validation.

## Acceptance tests

The test suite covers scalar and coupled nonlinear equations, a consistent overdetermined system, variable bounds, stationary unsatisfied equations, already-satisfied initial points, malformed contracts, non-finite residuals and callback failures. It also covers default forward differences, central differences, analytic Jacobian agreement, residual scaling, shape/finiteness validation, derivative callback failures, evaluation diagnostics, full-rank/duplicate-row/underdetermined rank fixtures, threshold validation and indeterminate rank handling.

## Safety boundary

Offline calculation only. The solver cannot actuate hardware, issue fabrication instructions, approve a design, certify a result or release a production artifact.
