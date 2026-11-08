# Arbitrary Faceted B-rep Boolean Contract

**Status:** PARTIAL — PRs #195–#212 implement bounded exact intersection/fragment primitives, global multi-mesh arrangement, independent coverage certification, fail-closed material classification, Boolean boundary selection, shell assembly and CAD Generator execution for supported faceted cases. General arbitrary-topology Boolean remains incomplete.  
**Target profile:** `FACETED_BREP_BOOLEAN_V1`.  
**Predecessor:** axis-aligned single-shell and multi-shell box-grid adapters in PR #191.  
**Design baseline:** integration SHA `2e436b34150b9e068d0a1b38a8841d5c6c0e6eec` (post-PR #192 documentation reconciliation).

## 1. Purpose and non-goals

Define a separate bounded Boolean kernel for validated polygonal faceted solids whose planar faces are not restricted to axis-aligned boxes. The kernel must not broaden or alter `boolean_axis_aligned_multishell_solids`; existing APIs and serialized result profiles remain backward compatible.

The first implementation is a staged, fail-closed vertical slice. It is not unrestricted CAD-kernel behavior, curved-surface support, manufacturing validity, or STEP/AP242 fidelity.

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
- Use exact signs for plane-side, orientation, segment/triangle, coplanarity and point-in-region decisions. An adaptive filter may accelerate predicates only when it falls back to exact arithmetic whenever a sign is uncertain.
- Construct intersection points as exact rational coordinates internally. Conversion back to binary64 must be deterministic and followed by validation; distinct exact points must not be silently merged by rounding.
- Never use a global epsilon to decide topology. No tolerance-based vertex welding is permitted in v1.
- Preserve stable source face/triangle provenance through split fragments and output boundary assembly.
- Output must pass closed edge incidence, opposite directed edge use, connected-shell, orientation, Euler/genus, positive net-volume, watertight mesh and complete self-intersection checks.

## 5. Staged implementation gates

### Gate A — pairwise intersection arrangement (first code slice)

- **Implemented sub-step:** PR candidate adds `TriangleIntersectionSegment` and `extract_transverse_triangle_intersection` for exact-rational endpoints of a proper transverse triangle-pair crossing. It canonicalizes source triangle order and endpoint order, validates the exact segment, serializes rational coordinates strictly, and rejects coplanar/contact/degenerate cases. This primitive does not split triangles and does not implement Boolean operations.
- Implemented bounded sub-step: PR #197 splits one source triangle by one properly intersecting cutter plane with exact clipping, deterministic triangulation, source-winding preservation and exact area conservation.
- Implemented bounded sub-step: PR #199 applies ordered exact-rational planes to each source triangle without float round-tripping, records per-plane side provenance, preserves winding, checks exact area conservation and enforces per-call fragment/rational-bit ceilings.
- Gate A bounded implementation: PRs #200–#203 add global exact vertex/edge topology, T-junction diagnostics, independent exact coverage certification and aggregate arrangement budgets. PR #209 converts registered T-junctions into conforming facets; PR #210 orchestrates all-source supporting-plane arrangement for multiple meshes. PR #212 hardens the coverage oracle against non-coplanar fragments that could otherwise look identical after projection.
- Reuse existing exact-rational triangle-pair predicates and conservative sweep-and-prune candidate generation where their contracts apply.
- Produce deterministic intersection events and exact segment/point/overlap records for a source triangle pair.
- Split source triangles into non-overlapping planar fragments while preserving winding and source-face provenance.
- Initially accept only transverse, non-degenerate intersection configurations for fragment generation. Coplanar positive-area overlap, coincident faces, tangential contact and branching events return typed unsupported/ambiguous results until a dedicated implementation gate covers them.
- Prove candidate completeness against an independent exact-rational oracle on a compact reference corpus.

### Gate B — fragment classification

- Classify each fragment as inside, outside or boundary-ambiguous relative to the other solid using a deterministic point-classification strategy.
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

- Keep existing axis-aligned Boolean functions and schemas unchanged.
- Do not add third-party geometry dependencies without separate license, maintenance, offline and reproducibility review.
- No external service or paid geometry kernel is required for the first implementation.
- Bound CPU, memory, pair counts, fragment counts and rational arithmetic growth.
- Never execute imported model content or treat geometry metadata as instructions.

## 9. Exit criteria

The arbitrary-faceted Boolean capability is not PASS until all applicable gates have implementation, independent reference tests, exact-head CI and post-merge CI on the integration branch. The repository remains INCOMPLETE while other required domains or platform-wide acceptance gates remain open.


## 10. Implementation evidence update — 2026-11-08

The following bounded slices are merged to `docs/phase-0-complete-requirements`:

- PR #200: global exact-rational vertex identity, face/edge incidence and adjacency.
- PR #201: exact global T-junction diagnostics with a fail-closed topology scan budget.
- PR #202: canonical subedge incidence at every registered exact vertex on a face edge.
- PR #203: independent exact 2D coverage oracle for source-triangle containment, pairwise overlap, duplicate fragments and area conservation; plane type/index and rational-bit validation.
- PR #204: exact point-vs-mesh classification with INSIDE / OUTSIDE / BOUNDARY / UNKNOWN outcomes and multiple deterministic ray witnesses.
- PR #205: Boolean boundary selection for UNION, INTERSECTION, DIFFERENCE and SYMMETRIC_DIFFERENCE on caller-supplied complete face partitions.
- PR #206: exact edge-connected shell grouping, orientation and exact-volume checks, cavity assignment, and BRepSolid/BRepMultiShellSolid validation.
- PR #207: public package exports and CADGeneratorService orchestration for the pre-arranged Boolean pipeline.

Latest integration SHA at this reconciliation: `f77e3cf7ba413c97d32c3a800e07938d50bd7ce8`.

### Remaining restrictions

- Cross-solid triangle intersection discovery and automatic global face splitting are not complete. The boundary-selection service requires complete caller-supplied per-source-face partitions.
- Coplanar overlap, tangency, point/edge/vertex contact, branching and other degeneracies remain unsupported unless a dedicated exact gate proves them.
- The current B-rep schema uses binary64. Shell assembly rejects rational coordinates that cannot round-trip exactly; it never rounds or tolerance-welds them.
- Nested positive material islands and generalized shell-parent semantics remain unsupported.
- PR #207 integration is service-level. It does not expose an unrestricted Boolean HTTP/browser endpoint and does not establish arbitrary faceted Boolean E2E.

**Gate status:** The global arrangement, material classification, boundary selection and shell assembly slices have bounded implementations. The general arbitrary-faceted Boolean kernel remains **PARTIAL / INCOMPLETE** until automatic arrangement completeness, degeneracy semantics, rational-coordinate output, generator E2E and independent acceptance fixtures all pass.


## 11. Current implementation evidence — 2026-11-08, post-PR #212

The following PRs are merged to `docs/phase-0-complete-requirements`:

| PR | Bounded capability | Merge SHA | Post-merge required checks |
|---|---|---|---|
| #200 | Global exact-rational vertex identity, face/edge incidence, adjacency and coverage accounting | `ee4c7420d230616270be3513f9ef2b4e530761a6` | PASS on available post-merge runs |
| #201 | Exact global T-junction diagnostics with bounded scan | `504dc12e6e6bbfcb2a4932a0b5ec3a6af5eefd9b` | PASS |
| #202 | Exact subedge incidence for long-edge / short-edge facet conformity | `17406635f623011dfff51e24fbfa9ed16ef3ce69` | PASS |
| #203 | Independent exact 2D coverage oracle for containment, overlap, duplicates and area | `5670d17ee7dc059c11d44ada0a7e9da2b3bbd9d1` | PASS |
| #204 | Fail-closed exact mesh material classification | `29f41a2be5c2c9699c8a18e17732edf63bd2dbc6` | PASS |
| #205 | Boolean boundary selection for UNION / INTERSECTION / DIFFERENCE / SYMMETRIC_DIFFERENCE | `6238085aebebba2199ac5170061c0cec0f4aed85` | PASS |
| #206 | Connected shell assembly, orientation, volume and B-rep validation | `9c1834ee79b90d559fd5075560c0677124e18290` | PASS |
| #207 | Public exports and CADGeneratorService Boolean orchestration | `f77e3cf7ba413c97d32c3a800e07938d50bd7ce8` | PASS; Chromium E2E PASS |
| #208 | Repository audit reconciliation | `60919a663e7a81f0105d5aebf477400479c5f4e6` | PASS |
| #209 | Conforming facet triangulation across global T-junctions | `5da14bcbaa4265fcb6b965462c0ceeeb3a266cf7` | PASS |
| #210 | Automatic bounded multi-mesh Boolean arrangement and non-coplanar intersecting-box workflow | `954f17b6add03e294a8707be03ff37b03827e57a` | PASS; Chromium E2E PASS |
| #211 | Coplanar positive-area overlay and two-sided Boolean material classification; overlapping-box UNION exact volume 12 | `bde93ccf2a3fe3bec90ec36afe724df40ed9c505` | Exact PR-head Python/workflow-sanity PASS |
| #212 | Exact 3D coplanarity gate in coverage oracle; rejects projected-but-off-plane partitions | `7fd78fa40886694bd46cfb6a61f60c3f716033f2` | Exact PR-head and post-merge Python/workflow-sanity PASS |

The exact post-merge workflow for #212 completed with workflow-sanity PASS and Python tests PASS. These checks establish the bounded code/test behavior on that merge SHA; they do not certify unrestricted geometry classes.

### Current bounded end-to-end examples

- Non-coplanar intersecting box UNION through `CADGeneratorService.execute_faceted_boolean`: exact expected volume `15`.
- Coplanar-overlapping box UNION through the same service: exact expected volume `12`.
- Input mesh validation, exact supporting-plane splitting, conforming facet generation, independent per-source coverage, material classification, boundary selection and closed-shell/B-rep validation are connected for these bounded fixtures.

### Remaining restrictions and gaps

- Point/edge-only coplanar contact, arbitrary tangencies, branching, vertex/edge degeneracy and other unsupported arrangements remain fail-closed.
- The output B-rep coordinate model remains binary64. Exact rational intersection coordinates that cannot round-trip losslessly are rejected; no rounding or tolerance welding is allowed.
- Nested positive material islands and generalized shell-parent semantics remain unsupported.
- The exact coverage oracle certifies coplanar per-source triangle partitions; it is not by itself a global proof of all possible multi-solid arrangement completeness.
- The service integration is in-process/offline. The current HTTP/browser workbench does not expose an unrestricted Boolean authoring endpoint.
- The CAD browser E2E workflow is path-filtered to browser/API/service assets. Kernel-only PRs do not trigger it; an untriggered browser workflow is not recorded as PASS.

**Current gate verdict:** bounded multi-mesh faceted Boolean execution is implemented and tested for the listed reference cases. The general arbitrary-faceted B-rep Boolean requirement remains **PARTIAL / INCOMPLETE** until broader independent adversarial coverage, degeneracy semantics and rational-coordinate B-rep output are implemented and validated.


### PR #213 — rational input resource ceilings

PR #213 merged at `d1289efdb71a1172beb88665baf09b4620f0cdc5` (exact head `093db080ebbb2a04431bd6254c889ceb53d8afed`). Direct `arrange_triangles_by_planes` calls now validate plane object types and apply the configured rational numerator/denominator bit ceiling to cutter-plane coordinates. The standalone coverage oracle also applies a coordinate bit ceiling before projection/clipping. Exact-head workflow-sanity and Python tests PASS. Post-merge workflow #42485255693 on the exact merge SHA passed workflow-sanity and Python tests.


### PR #215 — exact isolation of coplanar contact

PR #215 merged at `1ce59cab30ccfa18d8a8d72022706ffd9d9cec0b` (exact head `171583c852994aba3f61f712d48deabd0aab7cca`). For every coplanar triangle-pair contact, the arrangement now retains its exact projected point/segment and verifies that the entire contact is covered by the union of positive-area overlap polygons on the same supporting plane. A separate overlap elsewhere on that plane no longer masks an unrelated edge/point contact. Exact-head and post-merge workflow-sanity and Python tests PASS on the exact merge SHA `1ce59cab30ccfa18d8a8d72022706ffd9d9cec0b`.
