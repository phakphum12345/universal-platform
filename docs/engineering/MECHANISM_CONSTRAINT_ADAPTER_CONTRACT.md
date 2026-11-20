# Mechanism Constraint Adapter Contract

**Status:** PROPOSED DESIGN CONTRACT — no general mechanism-to-solver adapter is implemented.
**Scope:** Offline model validation and numerical constraint preparation only.
**Related work:** Phase 2 WP-2.6; nonlinear solver contracts; assembly and kinematics primitives.

## 1. Purpose and boundary

Define a deterministic seam between a validated mechanism model and the generic nonlinear equality solver. The adapter translates a versioned model snapshot into an ordered numerical problem and maps the numerical result back to model identifiers.

The adapter does not replace assembly validation, coordinate-frame validation, dimensional analysis, or mechanism-specific physics. It must not infer missing topology, units, coordinate conventions, ground references, or joint semantics.

The existing `Assembly` contract records occurrences and nominal joint types/DOF. Tree forward kinematics supports FIXED, REVOLUTE and PRISMATIC joints only. The planar four-bar utility is a narrow analytic circle-intersection implementation. None of these is a general closed-loop or 3D mechanism constraint adapter.

## 2. Proposed input snapshot

A future adapter input must contain:

- Stable assembly/model identifier and immutable revision or content hash.
- Occurrence identifiers, part/revision identifiers and grounded/reference occurrence.
- Joint identifiers, endpoint occurrence identifiers, joint type, local frames, axes, limits and declared coordinate units.
- Link/occurrence geometry references needed by the selected constraint family.
- Coordinate-frame graph or explicit transforms with named source and target frames.
- Explicit length/angle units, handedness, axis conventions and transform composition convention.
- Initial joint coordinates and optional variable scales.
- Constraint selection, residual tolerances, residual scales and declared assumptions.
- Source references/provenance for model parameters and geometry.

No adapter may assume that an assembly is a tree. A closed loop is valid topology for an assembly constraint problem, although the existing tree forward-kinematics routine cannot solve it.

## 3. Proposed normalized problem

The adapter returns a `MechanismConstraintProblem` with:

| Field | Contract |
|---|---|
| `model_id`, `model_revision` | Stable identity and exact input revision |
| `variable_names` | Unique ordered variable IDs |
| `initial_values` | Exactly one finite value per variable |
| `constraints` | Ordered scalar equality residuals with stable IDs |
| `bounds` | Optional finite variable bounds, keyed by variable ID |
| `variable_scales` | Optional positive finite characteristic magnitudes |
| `residual_scales` | Positive normalization factors with declared units/meaning |
| `tolerances` | Per-residual acceptance thresholds in original units |
| `ground_reference` | Explicit fixed occurrence/frame and whether it is an assumption |
| `source_refs` | Parameter, geometry and model revision provenance |
| `adapter_id`, `adapter_version` | Reproducible adapter identity |

The adapter must produce deterministic variable and constraint ordering for the same model revision and options. Identifiers must not depend on dictionary iteration, display labels, or transient UI order.

## 4. Identifier and residual conventions

Recommended stable identifiers:

- `joint/<joint_id>/coordinate`
- `joint/<joint_id>/closure/translation_x`
- `joint/<joint_id>/closure/translation_y`
- `joint/<joint_id>/closure/translation_z`
- `loop/<loop_id>/closure/<component>`
- `anchor/<occurrence_id>/<component>`

Residuals are scalar equality functions; zero means satisfied. Each residual must document:

- Physical/geometric meaning and source entities.
- Coordinate frame in which it is evaluated.
- Original unit and positive normalization scale.
- Tolerance in original units.
- Smoothness/differentiability assumptions and any branch choices.

Examples of residual families include coincident joint origins, fixed-pose closure, revolute-axis alignment, prismatic-axis alignment, link-distance preservation and loop-closure components. Exact component counts and formulas are joint-family-specific and require independent reference cases; this contract does not prescribe unverified universal formulas.

## 5. Validation gates before solver invocation

The adapter must fail closed before numerical solving when any of these checks fail:

1. Duplicate or empty occurrence, joint, loop, variable or constraint IDs.
2. Unknown occurrence/joint/frame/geometry references.
3. Missing or contradictory parent/child endpoint definitions.
4. Missing coordinate frames, invalid transform paths, inconsistent handedness or unsupported transform conventions.
5. Missing, mixed or incompatible units; residual scales must not be used to conceal a unit mismatch.
6. Missing ground/reference occurrence or an unreported gauge freedom.
7. Unsupported joint type or constraint family.
8. Non-finite initial values, limits, geometry parameters, scales or tolerances.
9. Inverted bounds, duplicate variable mappings or unstable ordering.
10. Invalid loop topology or unsatisfied model-level preconditions.

A failed gate returns a typed model/adapter error or an explicit UNKNOWN result. It must not create a zero residual or silently omit an unsupported constraint.

## 6. Gauge, redundancy, branches and singularities

- The grounded occurrence/frame must be explicit. If grounding is an assumption, label it ASSUMPTION and preserve its source.
- Redundant constraints must remain identifiable by stable IDs; the adapter must not silently delete them to improve numerical behavior.
- Under-determined systems and free rigid-body modes must be reported, not arbitrarily fixed without a declared reference.
- Branch selection (e.g. open/crossed planar assembly) must be an explicit input and recorded in the result.
- Rank estimates and scale indicators are numerical diagnostics, not proof of uniqueness, mobility, physical feasibility or global convergence.
- Near-singular configurations require model-specific warning and validation; they must not be relabeled as a valid unique assembly.

## 7. Result mapping and evidence

A future adapter result maps solver variables and residual statuses back to the original joint, loop, occurrence and source IDs. It records:

- Exact model revision, adapter ID/version and solver version.
- Ordered input variable/constraint identifiers, scales, tolerances and bounds.
- Solver result snapshot and derivative/rank/scale diagnostics.
- Residual PASS/FAIL per constraint in original units.
- Validation gates that passed, failed, were skipped or remain unknown.
- Assumptions, branch choice, warnings and limitations.

Solver `CONVERGED` is not an assembly certification. Numerical residual PASS does not establish contact, collision freedom, material strength, manufacturability, safety, or physical feasibility.

## 8. Acceptance test plan for a future implementation

- Valid rooted-tree model with supported fixed/revolute/prismatic joints.
- Valid planar loop reference case with explicit branch selection.
- Multi-loop topology with deterministic variable and residual ordering.
- Duplicate IDs, unknown endpoints and disconnected components.
- Missing frame, invalid transform path and incompatible coordinate conventions.
- Inconsistent/missing units and invalid residual scales.
- Missing ground reference and gauge freedom.
- Redundant constraints and rank-deficient Jacobian.
- Unsatisfied loop closure and infeasible joint bounds.
- Unsupported joint family returns explicit unsupported/unknown status.
- Result maps every residual and variable back to the exact model IDs/revision.

## 9. Non-goals and safety

This document is a proposed interface contract, not an implementation claim. It does not deliver a general 3D mechanism solver, arbitrary multi-loop solving, collision/contact, dynamics, FEA, CAD generation, actuator control, firmware writes, fabrication, production release or engineering certification.

All future adapters remain offline and non-actuating. Hardware access and physical execution are outside this contract.
