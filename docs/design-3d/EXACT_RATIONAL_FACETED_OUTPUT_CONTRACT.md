# Exact Rational Faceted Output Contract

**Status:** PARTIAL — PR #221 adds the bounded single-outer-shell exact-rational artifact profile. Boolean shell-assembly integration, cavity semantics and universal degeneracy certification remain incomplete.  
**Target profile:** `RATIONAL_FACETED_SOLID_V1`.  
**Compatibility:** additive profile; existing binary64 `TriangleMesh`, `BRepSolid` and `BRepMultiShellSolid` formats remain unchanged.

## 1. Problem statement

The faceted Boolean pipeline constructs exact rational intersection coordinates. The current public B-rep and mesh models store binary64 coordinates. Shell assembly therefore rejects any rational coordinate that cannot round-trip exactly through binary64.

This fail-closed behavior is intentional. Rounding, snapping or tolerance-welding would make the serialized output differ from the geometry used by exact predicates and exact-volume checks.

A separate exact output profile is required before general Boolean results containing non-binary rational coordinates can be represented.

## 2. Data model

The proposed `RATIONAL_FACETED_SOLID_V1` envelope contains:

- `schema_version`: fixed version identifier.
- `solid_id`, `frame_id`, `length_unit`: validated stable identity and unit metadata.
- `vertices`: canonical exact 3D rational coordinate tuples.
- `triangles`: oriented index triples into `vertices`.
- `shells`: explicit shell records with stable ID, role (`OUTER` or `CAVITY`), triangle indices and optional parent outer-shell ID.
- `exact_signed_volume`: canonical rational value derived from oriented triangles; never trusted as an input assertion.
- `source_provenance`: ordered input IDs/digests and source-face/fragment references.
- `algorithm_version`, `predicate_version`, resource counters and deterministic content digest.

A rational scalar is serialized as a pair of decimal integer strings `[numerator, denominator]`. The denominator must be positive; numerator and denominator must be coprime; zero is exactly `["0","1"]`. JSON floating-point values are forbidden in exact coordinate fields.

Vertices are deduplicated only by exact normalized rational equality. No tolerance or rounded identity is permitted.

## 3. Exact validation gates

A rational output is not valid merely because it serializes. Validation must independently prove:

1. All vertex coordinates are canonical and within numerator/denominator bit limits.
2. All triangle indices are in range and each triangle is non-degenerate.
3. Every undirected shell edge has exactly two incident directed uses with opposite orientation.
4. Each shell is edge-connected and has non-zero exact signed volume.
5. Outer/cavity shell ownership is explicit, unique and strictly contained; ambiguous or nested positive material islands fail closed until parent semantics are implemented.
6. Exact triangle self-intersection analysis returns a supported clean result; `UNKNOWN` is rejection.
7. Resource limits cover vertices, triangles, candidate pairs, rational growth and aggregate predicate work.
8. Recomputed exact volume and canonical digest match the serialized envelope.

No partial solid may be returned when any gate fails.

## 4. Binary64 interoperability

Conversion to the existing binary64 profile is optional and lossless-only:

- Every coordinate must convert to a finite binary64 value and convert back to the identical `Fraction`.
- If any coordinate fails that test, no legacy mesh/B-rep is emitted for that component.
- An explicitly separate display-only approximation may be considered later, but it must be labelled approximate, must not be used for topology or volume, and must never replace the exact artifact.
- STEP, 3MF and other exporters must declare whether they preserve the exact rational profile. An exporter that cannot do so must reject or require an explicit, separately versioned approximation policy.

## 5. Result envelope and API compatibility

The existing result shape remains supported for components that are losslessly representable as binary64. A future versioned Boolean result may add:

- `exact_rational_solid`: the authoritative exact artifact.
- `legacy_binary64_solid`: present only when exact round-trip conversion succeeds.
- `display_mesh`: optional and explicitly approximate, never authoritative.

Consumers must not infer exactness from the presence of a display mesh. Result status must distinguish success, successful empty result, unsupported geometry, resource exhaustion and validation failure.

## 6. Security and resource policy

- No third-party geometry kernel or paid service is required.
- All exact integer/rational parsing is bounded before expensive arithmetic.
- Enforce hard ceilings for coordinate bit length, vertices, triangles, shell count, pairwise checks and aggregate classification work.
- Reject booleans where integers are expected; reject malformed, non-canonical or oversized rational encodings.
- Do not execute imported geometry metadata or treat it as instructions.
- Inputs remain immutable; no automatic healing, snapping or silent face deletion.

## 7. Implementation sequence

1. Add canonical rational scalar/point codecs and strict schema tests.
2. Add immutable rational faceted solid/shell models and exact edge-incidence/orientation/volume validation.
3. Add exact self-intersection validation and bounded candidate generation.
4. Adapt Boolean shell assembly to emit the rational profile as the authoritative result.
5. Preserve legacy binary64 output only when every coordinate is losslessly representable.
6. Add deterministic serialization, tamper, round-trip, resource-exhaustion and adversarial geometry tests.
7. Integrate the versioned envelope with CADGeneratorService and document exporter capability boundaries.

## 8. Acceptance criteria

The profile is not PASS until:
- non-binary rational intersections survive serialization and reload without change;
- exact topology, shell validity and volume are independently recomputed;
- no rounded or tolerance-welded vertices are introduced;
- supported Boolean fixtures pass all operations with exact expected volumes;
- unsupported contact, branching, nested-shell and resource-limit cases fail closed;
- exact-head and post-merge required CI checks pass.

Until those criteria are met, the existing binary64 rejection is the correct behavior and general arbitrary-faceted Boolean remains **PARTIAL / INCOMPLETE**.


## 9. Bounded implementation evidence — PR #221

The additive `RATIONAL_FACETED_SOLID_V1` profile is implemented by
`engineering.rational_faceted_solid.RationalFacetedSolid` with a strict JSON
Schema and public engineering-package export.

Implemented in this slice:

- Exact coordinates are immutable `Fraction` triples; serialization uses
  reduced decimal-string numerator/positive-denominator pairs.
- Vertices must be lexicographically canonical and unique by exact equality.
- Triangle indices, degeneracy, two-face edge incidence, opposite directed
  edge use, edge connectivity and outward positive exact signed volume are
  validated independently of binary64 B-rep conversion.
- A bounded exact-rational SAT pair scan rejects detected non-adjacent
  intersections and unsupported contacts; coplanar adjacent faces are checked
  for same-side overlap.
- Exact volume and deterministic SHA-256 content digest are recomputed during
  deserialization. Resource counters are checked against geometry.
- Legacy binary64 schemas and exporters are unchanged.

The v1 implementation deliberately accepts exactly one connected OUTER shell.
Cavities, nested positive material islands, branching, some vertex-contact
configurations, and arbitrary degeneracy semantics are not certified. The
pairwise SAT scan is a bounded conservative check, not a universal proof for
all possible faceted shell configurations. The artifact is not yet consumed
by `assemble_boolean_shells` or `CADGeneratorService`; those integrations
remain required before rational Boolean results can be emitted end-to-end.

PR #221 acceptance requires exact-head CI and post-merge CI. A passing
tetrahedral rational round-trip fixture establishes only the implemented
single-shell profile, not unrestricted arbitrary-faceted Boolean support.
