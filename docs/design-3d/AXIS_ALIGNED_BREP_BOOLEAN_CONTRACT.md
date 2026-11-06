# Axis-Aligned Faceted B-rep Boolean Contract v1.0

**Status:** Bounded first 3D Boolean implementation; PR candidate `feat/axis-aligned-brep-boolean-v1`.  
**Algorithm:** `exact-axis-aligned-brep-box-grid-v1`.

## 1. Supported inputs

- Two to sixteen validated `BRepSolid` inputs.
- Each input must be exactly an axis-aligned box shell represented by eight corner vertices and twelve triangular planar faces.
- All inputs must share the same frame and length unit.
- No implicit frame transform, unit conversion, tolerance welding, healing or snapping is performed.

## 2. Operations

- `UNION`: material occupied by any input.
- `INTERSECTION`: material occupied by every input.
- `DIFFERENCE`: first input minus the union of all remaining inputs.
- `SYMMETRIC_DIFFERENCE`: odd/even input membership.

The implementation partitions each axis at all exact input boundary coordinates, evaluates each resulting cell using exact rational comparisons over the represented binary64 coordinates, and extracts oriented boundary quads. Each quad is split deterministically into two triangles. Face-connected output cell components become independent closed `BRepSolid` records.

## 3. Validation and provenance

- Maximum 32,768 grid cells; inputs are limited to 16 solids.
- Output mesh must pass valid, watertight and consistently oriented mesh validation.
- Output B-rep must pass closed two-face edge incidence, opposite edge-use directions, connected shell, Euler/genus and positive signed-volume checks.
- Output component and result digests are deterministic; commutative operations canonicalize input ID/digest pairs.
- Point-only and edge-only contacts are kept as separate face-connected components rather than being silently welded. Face-only contacts merge into one face-connected component; multi-box face-connected branches must still produce a valid closed manifold shell.
- Empty intersection/difference results are represented by an empty component tuple.

Schema: `schemas/geometry/brep-boolean-result.schema.json`.

## 4. Explicit limitations

This is not a general 3D Boolean kernel. It does not accept arbitrary faceted solids, rotated boxes, cylinders, extrusions, curved surfaces, non-axis-aligned planes or general B-rep faces. It does not perform shell healing or geometric tolerance classification. The current single-shell BRepSolid profile cannot represent a solid with a fully enclosed internal cavity as multiple boundary shells; such results fail closed. Self-intersection and manufacturing validation are not implied.

## 5. Next gates

1. Extend planar face loops to n-gons and inner loops with exact containment/orientation.
2. Add multi-shell solid semantics to represent enclosed cavities.
3. Add exact triangle/plane splitting and 3D arrangement classification for arbitrary faceted solids.
4. Add independent reference corpus for coplanar overlap, tangency, edge/vertex contact, thin features and near-degenerate cases.
5. Add general B-rep surfaces/curves and STEP/AP242 interoperability only with explicit tolerances and provenance.


## 6.1 Contact-topology regression corpus

- Vertex-only contact: two boxes sharing one vertex remain two separate closed components.
- Edge-only contact: two boxes sharing one edge remain two separate closed components.
- Face-only contact: adjacent boxes sharing one full face merge into one closed component.
- Multi-box branch: three face-attached arms around a central box produce one valid genus-zero shell with deterministic output digest under input permutation.
- Every emitted component must pass B-rep closure, manifoldness, orientation, connectedness and positive-volume validation.
