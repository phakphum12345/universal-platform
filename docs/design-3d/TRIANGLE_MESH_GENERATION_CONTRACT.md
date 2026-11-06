# Deterministic Primitive Triangle Mesh Contract

**Status:** Implemented by PR #64 for BoxSolid/CylinderSolid, PR #66 for straight-edged profiles, PR #68 for polygonal through-holes; PR #70 adds circular-arc profile sampling under explicit chordal tolerance. This is a triangle-surface tessellator and structural mesh checker, not a B-rep CAD kernel.

## 1. Scope

The v1.0 adapter converts one validated analytic `BoxSolid`, `CylinderSolid` or straight-edged `ExtrudedProfileSolid` with polygonal through-holes into an immutable triangle mesh. Mesh coordinates are expressed in the source solid's local `frame_id` and retain its explicit `length_unit`. Source solids are never mutated.

- Box: exact planar boundary represented by 8 vertices and 12 outward-oriented triangles.
- Cylinder: local +Z axis, deterministic regular polygon rings and triangle-fan caps. The caller supplies a positive maximum radial chordal error in the same length unit as the source solid.
- Straight/arc extruded profile: deterministic ear-clipped caps and boundary side walls for validated simple concave/convex polygon loops with optional strictly-contained polygonal holes. Circular arcs are subdivided to a caller-supplied maximum radial chordal error; the same tolerance applies to outer and hole arcs.
- Unsupported source geometry fails closed. Non-circular curves, splines, assemblies and 3D Boolean results are not tessellated by v1.0.

## 2. Mesh identity and serialization

Every mesh records schema version, source solid ID, source frame ID, length unit, source primitive kind, SHA-256 of canonical source geometry, optional chordal tolerance, ordered vertices and indexed triangles. Vertex and face order is deterministic for identical source inputs and tolerance.

The schema is `schemas/geometry/triangle-mesh.schema.json`. Import rejects missing/unknown fields, unsupported versions, malformed vertices/faces, invalid units and malformed provenance digests. A successful round trip preserves the complete ordered snapshot.

## 3. Cylinder chordal tolerance

For radius `r` and requested maximum radial chord error `e`, the circumferential segment count is:

`n = max(3, ceil(pi / acos(1 - min(e/r, 1))))`

The implementation rejects a tolerance below floating-point resolution and limits the ring to 100,000 segments to bound resource use. The actual maximum radial deviation is `r * (1 - cos(pi/n))`; this is a geometric tessellation bound, not a global mesh accuracy or manufacturing tolerance.

## 4. Curved profile chordal tolerance

For each circular arc with radius `r`, absolute sweep `|θ|` and requested maximum radial chord error `e`, choose `n = max(1, ceil(|θ| / (2 acos(1 - min(e/r, 1)))))` equal angular segments. The actual maximum radial deviation is `r * (1 - cos(|θ|/(2n)))`. Curved input requires a positive tolerance in the source length unit; a 100,000-segment per-arc resource ceiling applies. The cap-area difference is bounded conservatively by perimeter × chordal tolerance. The resulting mesh is an approximation, not an exact analytic surface.

## 5. Structural validation

`validate_triangle_mesh` reports:
- face-index range errors and repeated/degenerate triangles;
- boundary edges and edges incident to more than two faces;
- inconsistent directed edge use between adjacent faces;
- signed volume and triangle surface area.

A mesh is valid only when no structural issues are found and signed volume is positive above the scale-relative threshold. This validates a closed, consistently oriented two-manifold edge structure for the supported single-shell primitive output. It does not detect all triangle-triangle self-intersections, duplicate coincident vertices with different indices, geometric gaps hidden by duplicated seams, or invalid source geometry beyond the analytic primitive constructors.

## 6. Determinism and units

The mesh remains in its source-local frame; frame transformation is an explicit downstream operation. Coordinates and chordal tolerance use the source solid's declared length unit. No unit conversion, frame inference, welding, vertex snapping or topology repair occurs. Source provenance is a SHA-256 digest of the canonical primitive snapshot.

## 7. Acceptance references

- Box `2 x 3 x 4 m`: 8 vertices, 12 triangles, closed oriented edges, volume 24 m³, surface area 52 m².
- Cylinder: requested chordal tolerance bounds radial polygon deviation; output is closed and outward-oriented, with positive volume and surface area.
- Concave L-profile: deterministic ear clipping produces a closed outward-oriented mesh with volume 12 m³ and surface area 38 m² for the 6-vertex 2×2 L section extruded 4 m.
- Clockwise/counter-clockwise and collinear-boundary profile references preserve positive volume and watertight edge incidence.
- Single-hole and multiple-disjoint-hole fixtures preserve net volume/surface area and produce closed, consistently-oriented meshes.
- Invalid face indices, open boundaries, repeated triangle indices, inconsistent winding, invalid tolerance and strict snapshot tampering are rejected or reported.
- Repeated tessellation and strict serialization round trips produce identical snapshots.

## 8. Explicit non-claims and next increments

This module does not tessellate non-circular curves/splines, arbitrary planar regions or assemblies. It does not perform B-rep validity, general mesh self-intersection, repair, decimation, normals smoothing, Boolean operations, STEP/STL/3MF import/export, independent interchange reopen, collision/contact, finite-element meshing, structural analysis, manufacturing checks, physical validation or certification. Passing these tests proves only the implemented software invariants for the exact tested SHA.
