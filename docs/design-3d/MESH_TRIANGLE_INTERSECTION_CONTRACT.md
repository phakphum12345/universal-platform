# Triangle-Mesh Self-Intersection Contract

**Status:** IMPLEMENTED / INTEGRATED — separate exact-rational `analyze_mesh_intersections` API and `MeshIntersectionAnalysis` v1.0 implemented by PR #80 (`cb91c7c49406fd02324be6b30d5570e821b4d503`). Exact PR head `009ab1b24578579c0f6c6bbf3d4f8e3ee42fc181` passed workflow-sanity and Python tests (550 passed); post-merge CI on the exact merge SHA was not returned and remains UNKNOWN. `MeshTopologyAnalysis.self_intersection_status` in schema v1.0 intentionally remains UNKNOWN for backward compatibility.

## 1. Purpose and API boundary

Define deterministic detection of geometric intersections between distinct triangles in one indexed TriangleMesh. The API is additive and separate from validate_triangle_mesh (structural edge/winding checks) and analyze_mesh_topology (components/vertex-link/duplicate-coordinate diagnostics).

The first implementation must be offline-capable and dependency-free. It must not mutate vertices, weld, snap, repair, reorder or simplify the source mesh.

## 2. Result and provenance

The versioned MeshIntersectionAnalysis result must bind:
- Solid ID, frame ID and length unit.
- Source geometry SHA-256 and canonical mesh snapshot SHA-256.
- Algorithm and predicate-policy versions.
- Broad-phase candidate pair count, narrow-phase checked pair count and configured pair limit.
- Ordered intersection pair records with stable source triangle indices and a classification code.
- Unresolved pair records/reasons when the result is UNKNOWN.
- Overall status: NO_INTERSECTIONS_FOUND, INTERSECTIONS_FOUND or UNKNOWN.

A NO_INTERSECTIONS_FOUND result is permitted only when every broad-phase candidate pair has been resolved by the narrow phase. Resource exhaustion, unsupported degeneracy or numerical uncertainty must never be reported as no intersections.

## 3. Geometric semantics

The narrow phase must distinguish:
- PROPER_INTERSECTION: non-coplanar triangle interiors cross.
- COPLANAR_OVERLAP: coplanar triangle interiors overlap with positive area.
- UNSHARED_CONTACT: triangles touch at a point/edge not represented by shared indexed topology.
- DUPLICATE_FACET: geometrically duplicate triangles with distinct face indices.
- ADJACENT_FOLDOVER: triangles share an indexed edge but overlap beyond that expected shared edge.
- ADJACENT_VERTEX_CROSSING: triangles share one indexed vertex but intersect beyond that expected vertex.

Expected adjacency is not itself a self-intersection:
- Two triangles sharing an indexed edge may meet along that edge. If their planes are distinct, that shared edge is the expected intersection. If coplanar, their interiors must lie on opposite sides of the shared edge; same-side overlap is a foldover.
- Two triangles sharing one indexed vertex may meet at that vertex only; any additional contact is reported.
- Faces sharing all three indices are duplicate/invalid topology and must be reported or rejected by the structural precondition.

The API must not silently suppress a pair merely because it shares an index.

## 4. Broad-phase candidate generation

- Use deterministic sweep-and-prune over triangle AABBs (or an equivalently justified deterministic spatial index).
- Candidate ordering is stable by the ordered pair of source triangle indices.
- AABBs are conservative: the broad phase may over-report but must never omit a possible intersection.
- Exclude a face paired with itself; all distinct candidate pairs are counted.
- Enforce a configurable upper bound with a documented hard ceiling (initial default target: 5,000,000 pairs).
- If the candidate count exceeds the configured limit, return UNKNOWN with RESOURCE_LIMIT_EXCEEDED; never return a partial no-intersection result.

## 5. Predicate and numerical policy

- Source coordinates are finite IEEE-754 binary64 values in the mesh's declared frame/unit.
- Topology decisions use exact signs for the represented binary64 inputs, not a global epsilon. A dependency-free implementation may use Fraction.from_float or a reviewed adaptive exact-predicate strategy.
- Coplanarity, orientation, segment/triangle and point-in-triangle decisions must be consistent under exact represented-input semantics.
- The algorithm must not silently snap near-coplanar or near-coincident coordinates.
- If a future fast floating-point filter is added, it must fall back to exact predicates whenever the sign is not safely separated from its error bound.
- Degenerate triangles are a structural precondition failure; they must not be interpreted as clean geometry.

## 6. Determinism, performance and failure behavior

- Pair records and issue ordering are stable and sorted by source triangle indices/classification.
- The result includes exact source mesh identity and algorithm/predicate versions.
- No timestamps, random IDs, host paths or runtime-dependent ordering are serialized.
- Pair-count and memory limits are explicit. Resource exhaustion produces UNKNOWN, not a timeout-dependent PASS.
- Input meshes that fail structural validation are rejected before geometric analysis.
- The implementation must document worst-case broad-phase behavior and provide bounded adversarial stress tests.

## 7. Acceptance reference corpus

- Closed Box and Cylinder meshes: shared indexed edges are ignored as expected adjacency; no other intersections are reported.
- Two disjoint closed shells: no intersections, while topology analysis separately reports multiple components.
- Non-coplanar crossing triangles with no shared indices: PROPER_INTERSECTION.
- Coplanar positive-area overlap: COPLANAR_OVERLAP.
- Point and edge contacts without shared indices: UNSHARED_CONTACT.
- Duplicate geometric facets with distinct indices: DUPLICATE_FACET.
- Shared-edge coplanar same-side overlap: ADJACENT_FOLDOVER; opposite-side adjacency is accepted.
- Shared-vertex pair intersecting beyond the shared vertex: ADJACENT_VERTEX_CROSSING.
- Large translations, very small/large scales, near-coplanar pairs and nearly degenerate but structurally valid triangles.
- Independent exact-rational test oracle for a compact reference corpus; broad-phase output must contain every oracle-positive pair.
- Deterministic snapshots, strict round trips, resource-limit UNKNOWN behavior and no input mutation.

## 8. Integration with topology analysis

PR #77's `MeshTopologyAnalysis.self_intersection_status` remains UNKNOWN for backward-compatible schema v1.0. PR #80 implements the separate `MeshIntersectionAnalysis` API; callers must explicitly invoke it and retain its result alongside structural/topology evidence. Do not silently reinterpret the v1.0 field or infer overall model validity from either result alone.

## 9. Explicit non-claims

This API implements bounded self-intersection diagnostics only. It does not repair, weld, snap, mutate or simplify meshes; perform Boolean operations; certify general B-rep validity; simulate collision/contact; validate manufacturing; or establish physical safety/certification.