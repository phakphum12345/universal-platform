# Faceted B-rep Polygonal Mesh Triangulation Contract

**Status:** Implemented candidate; pending exact-head CI and review.  
**Input profile:** `FACETED_POLYGONAL_PLANAR_SHELL_V2`.  
**Output:** Validated `TriangleMesh` with `source_kind=IMPORTED_BREP`.

## 1. Purpose

Define the bounded conversion from a validated single-shell polygonal B-rep v2.0 into a triangle mesh. The adapter triangulates each planar polygonal face, including faces with one or more strictly-contained inner loops, without changing the B-rep or inventing geometric vertices.

This is a mesh-conversion adapter, not a general CAD kernel, surface tessellator or Boolean engine.

## 2. Input preconditions

- The source must pass `validate_brep_solid`.
- The source is one connected, closed, orientable shell.
- Every face has one simple outer loop and zero or more simple, strictly-contained, mutually disjoint inner loops.
- Face loops are planar and their edge-use orientation is consistent with the shell.
- All referenced vertices, edges, loops and faces must resolve.

## 3. Triangulation algorithm

1. Read each face's directed outer and inner loop vertex IDs from its edge uses.
2. Derive a non-zero face normal using exact represented-binary64 rational arithmetic.
3. Project the planar face to the two coordinates orthogonal to the dominant normal axis.
4. Reuse the deterministic profile-region bridge-and-ear-clipping implementation for the outer loop and all inner loops.
5. Restore the source outer-loop orientation to every emitted triangle.
6. Map triangulation indices back to the original B-rep vertex IDs and then to the unchanged mesh vertex array.
7. Validate the complete mesh using `validate_triangle_mesh`; return only if it is valid, watertight and consistently oriented.

The bridge used to represent a hole in the temporary 2D polygon is topological only. It does not add a geometric vertex or alter the source B-rep. Triangulation uses the existing bounded floating-point ear-clipping predicates; the B-rep's topology and planarity checks remain exact-rational. Near-degenerate triangulation cases may fail closed.

## 4. Identity and determinism

- Preserve solid ID, frame ID, length unit, source geometry SHA-256 and the exact ordered source vertex positions.
- Generate triangles in source face order and deterministic ear/bridge order.
- Preserve each face's outer-loop orientation.
- Do not weld vertices, repair geometry, change source loops or mutate the B-rep.
- Repeated conversion of the same immutable snapshot must produce the same triangle sequence.

## 5. Resource limits

- Maximum 10,000 boundary vertices per face.
- Maximum 200,000 output triangles per solid.
- Exceeding either limit fails closed with an explicit validation error.
- No external geometry dependency is introduced.

## 6. Acceptance criteria

- Convex and concave planar n-gon faces triangulate.
- Faces with one or multiple inner loops triangulate without filling the holes.
- Resulting meshes are valid, watertight and consistently oriented.
- Round-trip mesh-to-B-rep validation preserves the expected shell genus and signed volume for reference cases.
- Source vertex identity, frame, unit and digest are preserved.
- Deterministic output is verified across repeated conversions.
- Invalid B-rep input and triangulation failures are rejected; no partial mesh is returned.

## 7. Explicit limits

- One connected shell only; multiple shells and disconnected solids remain unsupported.
- No general 3D Boolean operations, curved surfaces, NURBS, trims, shell healing or tolerance-based vertex welding.
- No guarantee of geometric non-self-intersection beyond the existing mesh validator and separate intersection analysis.
- STEP/AP242 and 3MF assembly interoperability remain separate requirements.
- A valid mesh is not a manufacturing, physical or engineering certification.

## 8. Implementation evidence

PR #182 implements this adapter in `triangle_mesh_from_brep`, reusing the existing deterministic polygon-with-holes triangulation helper. The exact PR-head Python/workflow results and post-merge evidence must be recorded here after CI completes. A skipped browser test is not counted as a pass when the change has no UI surface.
