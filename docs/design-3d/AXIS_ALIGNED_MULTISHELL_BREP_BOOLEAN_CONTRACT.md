# Axis-Aligned Multi-Shell B-rep Boolean Contract v1.0

**Status:** Implementation candidate in PR #191; exact-head CI is the acceptance gate.  
**Algorithm:** `exact-axis-aligned-multishell-brep-box-grid-v1`.

## 1. Supported inputs

- Two to sixteen immutable `BRepMultiShellSolid` inputs.
- Each aggregate has one validated outer `BRepSolid` shell and zero or more validated cavity `BRepSolid` shells.
- Every outer/cavity component must be exactly an axis-aligned box shell represented by eight corner vertices and twelve triangular planar faces.
- All input aggregates share one frame and length unit.
- No implicit frame transform, unit conversion, tolerance welding, healing or snapping is performed.

## 2. Operations and material membership

The input aggregate membership at each exact-grid cell center is:

`inside(outer) AND NOT inside(any cavity)`.

The existing operations are then evaluated cellwise:
- `UNION`: material occupied by any input aggregate.
- `INTERSECTION`: material occupied by every input aggregate.
- `DIFFERENCE`: first input aggregate minus the union of all remaining inputs.
- `SYMMETRIC_DIFFERENCE`: odd/even input aggregate membership.

The grid is partitioned at every outer and cavity box boundary coordinate. Exact rational comparisons over represented binary64 coordinates classify each cell. Maximum grid size remains 32,768 cells.

## 3. Output shell composition

- Face-connected occupied-cell components are emitted as separate result solids.
- Each component boundary mesh is split into connected shells by shared edges.
- Positive-oriented shells become outer material boundaries.
- Negative-oriented shells are cavity boundaries; each is normalized to a positive-volume standalone `BRepSolid` snapshot before being attached to the aggregate. The aggregate reverses cavity triangle winding when converted to a mesh.
- Every cavity must be strictly contained by exactly one outer shell; unresolved or ambiguous assignment fails closed.
- Each output is a `BRepMultiShellSolid`: one outer shell plus zero or more cavity shells.
- Source inputs are immutable. No shell is healed, welded or mutated.

## 4. Validation and provenance

- Output boundary mesh must pass valid, watertight, consistently-oriented mesh validation.
- Every extracted shell must independently pass closed manifold B-rep validation after orientation normalization.
- The aggregate must pass strict cavity containment, complete shell-intersection analysis and positive net signed volume.
- Result digest includes algorithm version, operation, canonicalized input IDs/digests for commutative operations, grid-cell count and ordered component digests.
- Schema: `schemas/geometry/brep-multishell-boolean-result.schema.json`.

## 5. Explicit limitations

This is still an axis-aligned box-grid Boolean adapter, not a general 3D Boolean kernel. Arbitrary faceted/rotated/non-axis-aligned inputs, cylinders, extrusions, curved surfaces, NURBS, nested material islands, shell healing, tolerance classification, STEP/AP242 multi-shell exchange and manufacturing certification remain unsupported. The grid budget is fail-closed; exceeding it is an error.

## 6. Acceptance tests

- Difference of a solid box by one box emits one cavity shell and correct net volume.
- Difference by two disjoint boxes emits two cavity shells and deterministic net volume.
- Intersection preserves an existing cavity where it remains inside the clipped material region.
- Union preserves disconnected material components and deterministic result digests.
- Empty intersection and strict snapshot/digest round-trip.
- Frame/unit mismatch and non-axis-aligned component rejection.
- Input-count and grid-cell resource limits.
