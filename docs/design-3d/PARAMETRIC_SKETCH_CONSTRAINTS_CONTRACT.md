# Parametric Sketch Constraint Contract v1.0

**Status:** Bounded implementation — PR #90 merged to the integration branch.  
**Merge SHA:** `e2d631b49910e3d7f05fea6337742fd87385fb81`.  
**Exact PR-head CI:** run #42260796531 — `workflow-sanity` PASS; `python-tests` PASS, 618 tests.  
**Post-merge CI:** run #42260977543 — both required jobs PASS, 618 tests.  
**Main branch:** unchanged at `96e75010716226037893155b9fd4b13410fb0d6f`.

## 1. Purpose and boundary

Provide a CAD-neutral, versioned 2D parametric sketch model that can express a bounded first set of geometric and dimensional equality constraints and delegate solving to the existing local nonlinear equality solver.

This is not a full interactive sketcher, symbolic constraint engine, CAD kernel, or proof of unique geometry.

## 2. Model

- `ParametricSketch` contains a stable sketch ID, explicit frame ID, explicit length unit, immutable points, straight segments and constraints.
- `SketchPoint` has a stable point ID and finite 2D coordinates.
- `SketchSegment` references two distinct existing points.
- Point, segment and constraint identifiers are unique within their respective collections.
- All references must resolve; dangling IDs are rejected.
- The sketch unit must resolve to a registered length dimension. No implicit conversion is performed.
- Schema: `schemas/geometry/parametric-sketch.schema.json`.

## 3. Supported constraints

| Kind | Equation / meaning |
|---|---|
| HORIZONTAL | (y_b-y_a=0) |
| VERTICAL | (x_b-x_a=0) |
| COINCIDENT | (x_b-x_a=0) and (y_b-y_a=0) |
| DISTANCE | (sqrt{(x_b-x_a)^2+(y_b-y_a)^2}=d) |
| HORIZONTAL_DISTANCE | (x_b-x_a=d_x) |
| VERTICAL_DISTANCE | (y_b-y_a=d_y) |
| FIX_X | (x_a=x) |
| FIX_Y | (y_a=y) |

Every scalar residual has its own positive tolerance. Distance is non-negative; signed horizontal and vertical distances are allowed. Unsupported kinds and invalid arity/value combinations are rejected.

## 4. Solver contract

- Variables are ordered deterministically by sketch point order, x then y.
- Residuals are ordered by sketch constraint order; COINCIDENT expands to x then y.
- The adapter calls `solve_nonlinear_constraints`; it does not fork or silently alter the solver.
- Convergence is true only when the underlying solver reports CONVERGED and every original residual passes its own tolerance.
- Solver rank and scale diagnostics are propagated in the nested result snapshot when computed.
- A converged but underdetermined system may have infinitely many valid configurations. Rank estimates are threshold-dependent, not proof of uniqueness.
- An inconsistent or locally unsolved system returns NOT_CONVERGED; the caller must not treat its coordinates as a valid design.

## 5. Determinism and safety

- Immutable data records, stable IDs and deterministic variable/residual order.
- JSON-compatible schema-versioned input and result snapshots.
- Non-finite coordinates, values or tolerances are rejected.
- No implicit frame transform, unit conversion, geometry repair or auto-constraint inference.
- This module performs offline calculations only; it has no physical device or actuator interface.

## 6. Explicit limitations / future increments

Not yet supported: arcs, splines, construction geometry, angle, tangent, parallel, perpendicular, equal-length, radius/diameter, symmetry, midpoint, point-on-object, block/fix-whole-entity, inequality/contact constraints, symbolic solving, interactive dragging, automatic constraint inference, sketch import/export and persistent document editing.

The first slice does not yet create a closed PlanarRegion automatically. A later, separately tested adapter must validate closed boundary topology, winding, self-intersection, holes and frame/unit before creating a region.

## 7. Acceptance evidence

- Dimensioned rectangle solved from an intentionally perturbed initial guess.
- Coincident points generate and satisfy two scalar equations.
- Euclidean distance constraint solves to the requested length.
- Invalid references, duplicate IDs, invalid arity, negative distance and invalid tolerance fail closed.
- Deterministic JSON-compatible result snapshot and strict input schema.
- Full repository Python suite: 618 passed on exact PR head and post-merge integration SHA.
