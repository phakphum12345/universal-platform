# General Mechanism Loop-Closure Contract

**Status:** Graph-topology analysis and an explicit residual-to-solver bridge are implemented. Automatic geometric joint equations remain out of scope.

## Purpose

Extend the normalized stable-ID mechanism model beyond the single analytic planar 4R utility. Discover closed graph loops reproducibly and separate topology, geometric equations and numerical solving.

## Topology model

- Links are graph vertices; joints are undirected edges between parent and child links.
- Joint IDs are processed lexicographically for a deterministic spanning forest and fundamental cycle basis.
- An edge joining vertices already connected in the forest is a loop-closing edge.
- Each fundamental cycle contains its tree-path joint IDs followed by its closing joint ID, and an explicitly closed link path.
- Disconnected components, isolated links and parallel joints are retained.
- For V vertices, E edges and C connected components, independent cycle count is E - V + C.

## Residual and solver boundary

solve_mechanism_loops requires at least one caller-supplied LoopClosureConstraint for every loop-closing joint. Each record identifies the closing joint, a unique constraint ID, scalar residual callback, tolerance and positive scale. The existing nonlinear equality solver evaluates these residuals and retains per-equation PASS/FAIL and Jacobian diagnostics.

The normalized schema does not yet contain complete joint placements, coordinate parameterizations or geometric primitives to synthesize general joint equations. The API does not infer equations from JointKind.

## Status interpretation

- CONVERGED: every supplied equality residual is within its declared tolerance.
- UNDERCONSTRAINED: the solver reports an underdetermined Jacobian shape and estimated rank below the variable count.
- UNKNOWN: local solve did not converge and diagnostics do not justify a stronger conclusion.
- SINGULAR and UNREACHABLE are reserved; this implementation does not infer either from local solver failure.

A graph cycle is not proof of a geometrically feasible mechanism. Convergence of caller-provided residuals does not prove physical feasibility, uniqueness, stability or safety.

## Acceptance coverage

- Planar 4R: one cycle, three tree edges, one closing edge.
- Planar six-link cycle: one fundamental cycle.
- Multi-loop graph: deterministic independent cycles under input reordering.
- Disconnected components, isolated links and parallel edges.
- Invalid models and missing loop residuals fail closed.
- Existing nonlinear solver is reused; local failure remains UNKNOWN.

## Explicit non-goals

Automatic joint equation generation; spatial loop closure; pose graph optimization; arbitrary CAD geometry solving; mobility proof; singularity classification; branch continuation; global reachability; collision/contact; friction; dynamics; physical feasibility; safety certification.
