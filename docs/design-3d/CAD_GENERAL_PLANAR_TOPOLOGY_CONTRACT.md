# General Planar Region and Boolean Topology Contract

**Status:** Design proposal for review. This document does not claim that general planar Boolean operations are implemented. The current production API remains convex-loop-only in `profile_boolean.py`.

## 1. Purpose and boundary

Define the next CAD-neutral 2D topology layer needed to move beyond convex-cell decompositions. The target is arbitrary valid simple polygon boundaries, disconnected components, and holes, with deterministic results and explicit numerical limitations. This contract is a prerequisite for implementation and kernel selection; it is not itself a geometry kernel.

Out of scope for this increment: circular arcs/splines, 3D B-rep, mesh Booleans, offsets, fillets, sketch solving, manufacturing validation, physical validation, certification, and machine actuation.

## 2. Coordinate and identity model

A planar region input must carry:

- A stable non-empty region ID and schema version.
- An explicit 2D coordinate frame ID and length unit; coordinates from different frames or units must not be combined implicitly.
- One outer boundary and zero or more hole boundaries.
- Finite coordinates and an explicit precision/tolerance policy identifier.
- Stable boundary/vertex IDs when the caller supplies them; generated IDs must be deterministic and derived from canonical input order, not runtime randomness.

The 2D frame must resolve to a declared plane in the platform frame graph before any 3D placement. This contract does not infer a plane or convert units silently.

## 3. Boundary invariants

- Every boundary is a closed simple polygon with at least three distinct vertices and non-zero signed area.
- The outer boundary is counter-clockwise; hole boundaries are clockwise after normalization.
- Consecutive duplicate vertices, zero-length edges, non-adjacent self-intersections, and ambiguous overlapping edges are rejected unless a later, explicitly versioned repair operation is approved.
- Every hole is strictly inside its outer boundary; hole boundaries may not touch, cross, overlap, or nest.
- Distinct region components may be disjoint. Shared-edge and point-touching relationships must be represented explicitly in topology results rather than silently merged.
- Collinear intermediate vertices may be preserved or removed only under a documented canonicalization rule that preserves boundary identity and topology.

Validation must report stable issue codes and affected region/boundary/edge IDs. Invalid input fails closed; the engine must not guess intended topology.

## 4. Boolean operation semantics

The future API may expose UNION, INTERSECTION, DIFFERENCE, and SYMMETRIC_DIFFERENCE over region sets.

- Output is a canonical set of connected planar regions, each with one outer boundary and zero or more holes.
- Empty, disjoint, contained, edge-touching, and point-touching cases have explicit semantics.
- Boundaries must not self-intersect; holes must remain strictly contained; distinct output components must not have overlapping interiors.
- Output area is the signed sum of outer and hole areas, with a separately reported numerical error bound or tolerance basis.
- The API must distinguish an empty-area contact (point/edge) from a positive-area region.
- Stable output ordering is independent of input winding and cyclic starting vertex. Input permutation behavior must be documented per operation.
- No output may claim exact arithmetic unless the selected implementation actually provides it.

The existing v1.0 convex-cell API remains backward compatible. General-region support must use a separately versioned schema/API rather than silently broadening the accepted input type of `ProfileLoop`.

## 5. Numerical policy and robustness tiers

The current convex implementation uses scale-relative floating-point tolerances and explicitly does not guarantee robust arbitrary near-coincident topology. The next implementation must not disguise this limitation.

The design must compare at least these strategies:

1. Floating-point predicates with a declared, scale-aware tolerance and fail-closed ambiguity band.
2. Integer-grid quantization with an explicit scale/origin, quantization error bound, overflow checks, and a documented minimum feature size.
3. Exact/adaptive predicates or a reviewed geometry kernel that provides documented robust predicates.

A precision policy must specify coordinate magnitude limits, minimum resolvable feature, orientation/intersection predicate behavior, snap/merge behavior (if any), area error bounds, and deterministic serialization. Silent snapping, epsilon-based topology repair, or coordinate rounding is prohibited.

Near-coincident, nearly collinear, very small/large scale, large translation, and overflow/underflow cases must be included in adversarial references. If an input is numerically ambiguous under the selected policy, return a typed UNKNOWN/invalid result rather than a fabricated topology.

## 6. Result and evidence contract

A result snapshot must include:

- Schema and algorithm/policy versions.
- Operation and ordered source region IDs plus canonical input digests.
- Canonical output region/component/boundary/vertex records.
- Coordinate frame and length unit.
- Area and perimeter summaries with explicit units and error/tolerance metadata.
- Stable diagnostics for contacts, discarded zero-area artifacts, and rejected ambiguities.
- Evidence/provenance references and explicit limitations.

Strict import rejects unknown fields, invalid topology, non-finite values, inconsistent counts, mismatched digests, and tampered metrics. Serialization must be deterministic across repeated runs and supported platforms.

## 7. Acceptance tests before implementation is called complete

- Outer boundaries, holes, multiple components, and winding normalization.
- Union/intersection/difference/symmetric-difference reference areas and topology for overlap, containment, disjointness, shared edges, and point contacts.
- Hole creation, hole elimination, and multiple-hole cases.
- Self-intersection, touching/nested holes, zero-length edges, duplicate vertices, and invalid frame/unit combinations fail closed.
- Adversarial scale/translation, near-collinear, near-coincident, tiny-feature, and overflow/underflow references.
- Independent area/perimeter and topology invariants; no overlapping output interiors.
- Deterministic snapshots, strict round trips, tamper rejection, and stable issue IDs.
- Cross-check a representative corpus against an independent implementation or analytically derived references. The independent implementation is test evidence only, not an automatically approved runtime dependency.

## 8. Kernel and adapter decision gate

No geometry library is selected by this contract. Before adoption, record exact version, official source, license and transitive-license posture, offline behavior, supported platforms, API coverage, precision model, deterministic behavior, memory/runtime cost, security/maintenance posture, and replacement path. Evaluate the same reference corpus against each candidate.

The selected kernel, if any, must sit behind a replaceable platform adapter. The public platform model and result schemas remain CAD-neutral. Owner approval is required before adding a third-party runtime dependency.

## 9. Explicit non-claims

This proposal is not implementation evidence and does not establish general CAD readiness. It does not provide 3D solids, B-rep validity, mesh generation, STEP/STL exchange, physical behavior, manufacturing suitability, standards compliance, or certification.