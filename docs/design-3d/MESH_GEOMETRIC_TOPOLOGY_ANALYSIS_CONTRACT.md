# Mesh Geometric Topology Analysis Contract

**Status:** Implemented by PR #77; exact PR-head and post-merge CI passed 533 tests. The existing `validate_triangle_mesh` remains the structural edge-incidence/winding validator. This analysis does not claim general triangle-triangle self-intersection detection.

## 1. Purpose and separation of concerns

Triangle meshes require validation beyond indexed edge counts. A mesh can be edge-watertight and consistently oriented yet contain disconnected shells, a pinched vertex fan, unused vertices, or distinct vertex IDs at identical/near-identical coordinates.

The next analysis layer is additive and must not silently change the existing `MeshValidationResult` or the behavior of `validate_triangle_mesh`. It reports topology diagnostics separately and preserves the source mesh.

## 2. Analysis record

The versioned `MeshTopologyAnalysis` v1.0 result must contain:
- Stable schema version, solid/frame identity, length unit, source geometry digest and canonical mesh snapshot SHA-256.
- Vertex and triangle counts so every reported index is range-checkable during strict snapshot import.
- Ordered face-connected components, represented by sorted source face indices.
- Exact duplicate-coordinate vertex groups.
- Optional near-coincident vertex groups, using a caller-supplied positive tolerance in the mesh's declared length unit.
- Non-manifold vertex indices, derived from each vertex's incident-face link graph.
- Unused vertex indices.
- Stable, sorted diagnostic issue codes.
- `self_intersection_status = UNKNOWN` until a geometric triangle-triangle algorithm is implemented and independently validated.

This result is diagnostic evidence, not an overall geometry/engineering PASS. The base structural result and topology analysis must remain separate.

## 3. Connected shell semantics

Face components are edge-connected: two faces are adjacent only when they share an undirected indexed edge. Components are deterministic and sorted by their smallest face index.

- A supported primitive mesh is expected to contain exactly one edge-connected shell.
- Multiple components are reported, not silently joined or welded.
- A future assembly/compound-mesh contract may explicitly permit multiple shells; v1 analysis does not infer that intent.
- Faces with invalid indices are excluded from component traversal and remain the responsibility of the structural validator.

## 4. Vertex manifoldness

For each used vertex, construct its link graph: every incident triangle contributes an undirected link edge between that triangle's other two vertex indices.

- A manifold interior vertex has one connected cycle in its link graph.
- A manifold boundary vertex has one connected path (exactly two degree-1 link nodes; all others degree 2).
- A disconnected link graph, degree greater than 2, or any other degree pattern is reported as a non-manifold vertex.
- This detects pinched/bow-tie vertex fans that edge-incidence checks alone may miss.
- Unused vertices are reported independently.

The analysis must not repair or reindex a vertex fan.

## 5. Duplicate and near-coincident coordinates

Exact duplicate groups use exact numeric coordinate equality; signed zero compares equal. The optional `coincident_tolerance` is an absolute Euclidean distance in the mesh's declared length unit.

- Tolerance defaults to zero (exact duplicates only); no global epsilon is inferred.
- Near-coincident groups are the deterministic connected components of the pairwise-within-tolerance relation.
- A spatial bucket or equivalent bounded-neighbor strategy should avoid unconditional all-pairs comparison for large meshes.
- The analysis reports source vertex indices and does not weld, snap, average or delete coordinates.
- A non-zero tolerance must be finite, positive and recorded in the result.
- A tolerance larger than the model's minimum feature size can over-report; callers remain responsible for selecting a meaningful threshold.

## 6. Determinism, units and resource limits

- Input mesh is immutable and is never modified.
- Component, group and issue ordering is stable and independent of hash-map iteration.
- Coordinates remain in the mesh's local frame and length unit; no transform or unit conversion occurs.
- Result serialization is strict, versioned and deterministic.
- Near-coincident search uses a deterministic 3D spatial bucket and a hard default ceiling of 5,000,000 neighbor comparisons; exceeding the ceiling fails closed.
- Analysis must expose or document resource limits for vertex/face counts and neighbor comparisons.
- Invalid face indices do not crash the analyzer; they are reported by the structural validator and excluded from topology traversal.

## 7. Acceptance references

- A valid Box mesh reports one component, no duplicate groups, no unused vertices and no non-manifold vertex.
- Two disjoint closed boxes combined into one TriangleMesh report two edge-connected components.
- Two otherwise closed shells sharing one indexed vertex report a non-manifold vertex fan even though their edges remain individually two-manifold.
- An unused vertex is reported.
- Exact duplicate coordinates with distinct indices are reported.
- Caller-supplied positive tolerance reports near-coincident coordinates; zero/default tolerance does not infer near matches.
- Repeated analysis and strict result round trips produce identical snapshots.
- The input mesh snapshot is unchanged by analysis.
- The result explicitly leaves self-intersection status UNKNOWN.

## 8. Follow-up geometric intersection gate

Triangle-triangle self-intersection requires a separate contract and implementation covering:
- Non-coplanar and coplanar intersections, touching and overlap semantics.
- Adjacent-face shared-edge/shared-vertex exclusions without hiding additional intersections.
- Deterministic broad-phase candidate generation and robust narrow-phase predicates.
- Scale/translation/near-coplanar adversarial references and numerical ambiguity behavior.
- Independent reference corpus and bounded runtime/memory behavior.

Until that gate passes, no mesh topology analysis may claim that a mesh is free of geometric self-intersections.

## 9. Explicit non-claims

This contract does not implement geometric self-intersection detection, mesh repair, welding, snapping, decimation, normals smoothing, mesh Booleans, collision/contact, B-rep validity, manufacturing checks, physical validation or certification.