# Arbitrary Faceted B-rep Boolean Contract

**Status:** PLANNED — architecture and acceptance contract only; no general 3D Boolean implementation is claimed.  
**Target profile:** `FACETED_BREP_BOOLEAN_V1`.  
**Predecessor:** axis-aligned single-shell and multi-shell box-grid adapters in PR #191.  
**Design baseline:** integration SHA `20e03675ec1000bd2bbcfaf251df4790305f2c0c`.

## 1. Purpose and non-goals

Define a separate bounded Boolean kernel for validated polygonal faceted solids whose planar faces are not restricted to axis-aligned boxes. The kernel must not broaden or alter `boolean_axis_aligned_multishell_solids`; existing APIs and serialized result profiles remain backward compatible.

The first implementation is a staged, fail-closed vertical slice. It is not a promise of unrestricted CAD-kernel behavior, curved-surface support, manufacturing validity, or STEP/AP242 fidelity.

## 2. Input contract

- Accept immutable, validated polygonal B-rep snapshots with planar polygon faces and explicit face inner loops.
- Accept a multi-shell aggregate only when its outer shell and cavity shells pass the existing multi-shell validator.
- Require a common frame and length unit. No implicit transform, unit conversion, snapping, tolerance welding, shell healing, or source mutation.
- Reject open, non-manifold, inconsistently oriented, degenerate, self-intersecting, or unresolved input topology.
- Require completed mesh intersection analysis for every tessellated input boundary. `UNKNOWN` is rejection, never evidence of a clean input.
- Apply explicit limits for input solids, faces, triangles, candidate pairs, generated fragments, exact-rational bit growth, memory and output triangles. Limits are configurable only within documented hard ceilings.

## 3. Boolean semantics

Operations are `UNION`, `INTERSECTION`, first-input-minus-the-union-of-the-rest `DIFFERENCE`, and odd/even `SYMMETRIC_DIFFERENCE`.

Material membership is defined from the validated oriented boundary and shell nesting, not from an axis-aligned occupancy grid. A point on a boundary is not assigned an arbitrary inside/outside value: boundary classification must be explicit and deterministic.

Each output component must represent a closed material region with one outer shell and zero or more strictly-contained cavity shells. Nested material islands are a separate future profile until containment and shell-parent semantics are explicitly implemented.

## 4. Numerical and topological policy

- Interpret each finite binary64 input coordinate as its exact represented rational value for topological predicates.
- Use exact signs for plane-side, orientation, segment/triangle, coplanarity and point-in-region decisions. A reviewed adaptive filter may accelerate predicates only when it falls back to exact arithmetic whenever a sign is uncertain.
- Construct intersection points as exact rational coordinates internally. Any conversion back to binary64 must be deterministic, documented, and followed by a validation pass; distinct exact points must not be silently merged by rounding.
- Never use a global epsilon to decide topology. No tolerance-based vertex welding is permitted in v1.
- Preserve stable source face/triangle provenance through split fragments and output boundary assembly.
- The output must pass closed edge incidence, opposite directed edge use, connected-shell, orientation, Euler/genus, positive net-volume, watertight mesh and complete self-intersection checks.

## 5. Staged implementation gates

### Gate A — pairwise intersection arrangement (first code slice)

- Reuse the existing exact-rational triangle-pair predicates and conservative sweep-and-prune candidate generator where their contracts apply.
- Produce deterministic intersection events and exact segment/point/overlap records for a source triangle pair.
- Split source triangles into non-overlapping planar fragments while preserving winding and source-face provenance.
- Initially accept only transverse, non-degenerate intersection configurations for fragment generation. Coplanar positive-area overlap, coincident faces, tangential contact and branching events return typed unsupported/ambiguous results until a dedicated implementation gate covers them.
- Prove candidate completeness against an independent exact-rational oracle on a compact reference corpus.

### Gate B — fragment classification

- Classify each fragment as inside, outside or boundary-ambiguous relative to the other solid using a deterministic point classification strategy.
- Use multiple deterministic interior witnesses or an equivalently justified method; a single centroid heuristic is insufficient for concave or thin geometry.
- Boundary-ambiguous, inconsistent or resource-limited classification returns `UNKNOWN`/typed failure and produces no partial solid.

### Gate C — boundary selection and assembly

- Select and orient fragments according to the requested Boolean operation.
- Pair split edges with exact canonical identities; reject unmatched, multiply-used or orientation-conflicting edges.
- Assemble connected shells and cavity containment without tolerance welding.
- Do not heal or silently discard sliver/degenerate fragments.

### Gate D — degeneracies and multi-shell topology

Add separate reference-backed support for coplanar overlap, tangency, point/edge/vertex contact, coincident boundaries, thin features and branching arrangements. Each case needs explicit material-set semantics and manifold output proof. Until its gate passes, the affected input returns a typed unsupported/ambiguous result.

### Gate E — public API and interoperability

Only after Gates A–D pass: add a versioned result envelope, strict schema, deterministic digest, public exports, independent fixtures and optional CAD workbench/API exposure. STEP/AP242 and 3MF exchange remain separate work packages.

## 6. Result and failure semantics

The result envelope must record schema/algorithm/predicate versions, operation, ordered input IDs and source digests, frame/unit, resource counters, output components, source-fragment provenance, warnings and deterministic result digest.

- A successful empty result is distinct from failure.
- Unsupported geometry, unresolved predicates, ambiguous boundary classification, exceeded budgets, invalid topology or failed output validation must return a typed failure or `UNKNOWN`; never return a partial result as success.
- Inputs remain immutable and no source revision is overwritten.
- Deterministic output must be invariant to irrelevant input enumeration for commutative operations after canonical input ordering.

## 7. Independent acceptance corpus

At minimum include:
- Transverse intersection of two rotated convex polyhedra.
- Concave polygonal prism intersection and difference.
- Multiple disjoint intersection segments on one face pair.
- A solid with an existing cavity intersected by a non-axis-aligned solid.
- Disconnected output material components.
- Exact edge/vertex contact, tangency and coplanar overlap as explicit unsupported cases in the first gate, then positive acceptance fixtures in Gate D.
- Large translations, very small/large scales, nearly coplanar faces and thin features.
- Independent exact-rational pairwise intersection oracle and expected material-volume/bounds checks where analytically available.
- Deterministic serialization, input immutability, malformed snapshots, schema round trips, resource-limit failures and injected `UNKNOWN` paths.
- Every successful output passes B-rep validation and complete mesh self-intersection analysis.

Tests must not use the implementation under test as its own oracle. A skipped or untriggered test suite is not a pass.

## 8. Compatibility and security

- Keep the existing axis-aligned Boolean functions and schemas unchanged.
- Do not add third-party geometry dependencies without a separate license, maintenance, offline and reproducibility review.
- No external service or paid geometry kernel is required for the first implementation.
- Bound CPU, memory, pair counts, fragment counts and rational arithmetic growth.
- Never execute imported model content or treat geometry metadata as instructions.

## 9. Exit criteria

The arbitrary-faceted Boolean capability is not PASS until all applicable gates have implementation, independent reference tests, exact-head CI and post-merge CI on the integration branch. The repository remains INCOMPLETE while other required domains or platform-wide acceptance gates remain open.
