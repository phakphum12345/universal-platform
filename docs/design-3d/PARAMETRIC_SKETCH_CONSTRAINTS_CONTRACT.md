# Parametric Sketch Constraint Contract v1.2

**Status:** Bounded implementation — PR #90 baseline; relational constraints added in this feature PR.  
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

Every scalar residual has its own positive tolerance. Distance is non-negative; signed horizontal and vertical distances are allowed. Relational constraints identify two segments using four distinct point IDs; zero-length segment vectors are rejected before solving and after convergence. Parallel includes same- and opposite-direction vectors. Unsupported kinds and invalid arity/value combinations are rejected.

## 4. Solver contract

- Variables are ordered deterministically by sketch point order, x then y.
- Residuals are ordered by sketch constraint order; COINCIDENT expands to x then y. Relational constraints contribute one scalar cross-product, dot-product or length-difference residual.
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

Not yet supported: splines, construction geometry, symmetry, midpoint, point-on-object, block/fix-whole-entity, inequality/contact constraints, symbolic solving, interactive dragging, automatic constraint inference, sketch import/export and persistent document editing.

The first slice does not yet create a closed PlanarRegion automatically. A later, separately tested adapter must validate closed boundary topology, winding, self-intersection, holes and frame/unit before creating a region.

## 7. Acceptance evidence

- Dimensioned rectangle solved from an intentionally perturbed initial guess.
- Coincident points generate and satisfy two scalar equations.
- Euclidean distance constraint solves to the requested length.
- Invalid references, duplicate IDs, invalid arity, negative distance and invalid tolerance fail closed.
- Deterministic JSON-compatible result snapshot and strict input schema.
- Full repository Python suite: 618 passed on exact PR head and post-merge integration SHA.


## 8. Relational constraint increment

The follow-on relational increment adds `PARALLEL`, `PERPENDICULAR` and `EQUAL_LENGTH` for two non-degenerate segments identified by four distinct point IDs. These are scalar nonlinear equalities and inherit the solver's local-convergence and rank limitations. Angle, tangent, radius/diameter, shared-endpoint segment references and richer segment-ID constraint binding remain out of scope; no symbolic or globally unique solution is claimed.


## 9. Schema v1.1 — directed angle between segments

- `ParametricSketch` schema v1.1 adds the `ANGLE` constraint and an optional
  `segment_ids` reference array on constraints. Existing v1.0 snapshots remain
  readable; newly serialized snapshots use v1.1.
- `ANGLE` references exactly two distinct existing segment IDs and no point
  IDs. The target is a signed directed angle in radians in the inclusive range
  [-π, π]. Segment direction is from each segment's start point to its end point.
- The residual is `atan2(cross(u, v), dot(u, v)) - target`. Both segment
  vectors must be non-degenerate before solving and remain non-degenerate after
  convergence. This is a local nonlinear equality, not a symbolic or global
  angular solver.
- The implementation remains straight-segment-only. Arc geometry is not
  introduced by this increment, so tangent and radius/diameter constraints
  remain unsupported and must wait for an explicit circular-arc model.


## 10. Schema v1.2 — circular arcs, radius and tangent

- `SketchArc` references one center point, a start point and an end point,
  plus an explicit `clockwise` direction flag. The three point IDs must be
  distinct, all references must resolve, and both radial vectors and the
  endpoint chord must be non-degenerate.
- Each arc must have exactly one `RADIUS` constraint. The positive radius
  target creates two scalar residuals: center-to-start and center-to-end
  distance minus the requested radius. This keeps both endpoints on the same
  circle during solving.
- `TANGENT` references one existing straight segment, one circular arc and
  their shared endpoint. It contributes the normalized dot product between
  the line direction and the center-to-contact radial vector; the residual
  must be zero. Contact must be a segment endpoint and an arc endpoint.
- Arc IDs, segment IDs and point IDs are explicit references. Unknown,
  duplicate, malformed and degenerate references fail closed.
- Schema v1.0 and v1.1 snapshots remain readable. v1.0 cannot contain segment
  references or new constraints; v1.1 supports ANGLE only; v1.2 carries the
  arc collection and arc-aware constraints.
- The solver remains the existing bounded local nonlinear equality solver.
  It does not infer arcs, prove global uniqueness, or certify manufacturing
  geometry.
- `sketch_to_planar_regions` explicitly rejects sketches containing arcs.
  Curved-loop topology, arc tessellation, Boolean operations over curved
  profiles and CAD-kernel B-rep conversion remain OPEN.
