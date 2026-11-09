# CAD Exact Boolean Kernel — Resource and Acceptance Plan

**Status:** Engineering plan; not an implementation or passing test report.  
**Baseline:** `RATIONAL_FACETED_SOLID_V1` at commit `f11f41e301e9e0a10213fbf07d2c3eb17317892f`.  
**Scope:** Harden exact-rational input handling and define independent acceptance evidence for the Boolean pipeline.

## Current verified boundary

The current rational faceted solid profile:
- accepts one closed, edge-connected, outward-oriented outer shell;
- validates positive exact signed volume and rejects degenerate triangles;
- bounds vertex and triangle counts and pairwise triangle checks;
- checks each coordinate numerator and denominator against `max_coordinate_bits`;
- rejects cavities and unsupported contact configurations;
- is not yet the end-to-end Boolean Kernel acceptance proof and is not shown here as integrated with `CADGeneratorService`.

## Findings requiring implementation and regression tests

1. **Pre-conversion integer bound.** `_parse_integer_string` currently calls `int(value)` after canonical-string validation. Enforce a conservative decimal digit bound derived from the configured bit ceiling before conversion. Convert conversion failures to the documented `InvalidModelError` contract. Test oversized positive and negative numerator strings and oversized denominator strings.
2. **Validate limits before parsing.** Validate `max_coordinate_bits` and `max_pairwise_checks` at the start of `from_dict`, before parsing any coordinate. Reject booleans, non-integers, non-positive values, and values above hard ceilings consistently with direct construction.
3. **Aggregate rational budget.** Add a documented aggregate budget over all parsed coordinate numerators and denominators (using integer bit lengths, not floating-point estimates). Check incrementally while parsing so the budget is enforced before retaining the full geometry. The chosen ceiling must be justified against supported geometry sizes and CI resource constraints.
4. **Metadata/provenance bounds.** Define and enforce maximum lengths for `solid_id`, `frame_id`, `length_unit`, and `source_id`, plus a maximum provenance record count. Preserve canonical ordering and digest validation.
5. **Adversarial compatibility.** Add tests proving ordinary canonical v1 fixtures round-trip unchanged and boundary values at each configured limit remain accepted. Do not silently alter the serialized schema or digest contract.

## Independent exact coverage oracle

The oracle must be independently implemented from the fragment-generation path. For every source face partition, prove:
- every expected region is covered exactly once;
- no positive-area gaps exist;
- no positive-area overlaps exist;
- no duplicate fragments exist;
- shared boundaries are handled by an explicit zero-area/touching policy.

Use exact rational predicates/area accounting. Include adversarial fixtures for point-touching, edge-touching, shared vertices, coplanar overlap, slivers, duplicate fragments, and disconnected regions. A generator's own bookkeeping is not independent oracle evidence.

### Current implementation audit — PR #221

The repository already contains an independent module, `engineering.triangle_coverage_oracle`, and `global_triangle_arrangement.arrange_triangle_mesh_globally` invokes `certify_triangle_partition` on the final conforming fragments for each source triangle. The oracle uses exact `Fraction` arithmetic, dominant-axis projection, exact convex clipping, exact area sums, and pairwise positive-area intersection checks. It does not call the fragment generator; it imports only the shared exact point/triangle type aliases and validation error.

Existing tests in `tests/test_triangle_coverage_oracle.py` cover:
- an exact partition with shared internal boundaries;
- duplicate and positive-area overlapping fragments;
- a positive-area gap where all fragments remain individually inside the source;
- a fragment outside the source;
- projected coverage translated off the source plane;
- degenerate/non-exact inputs and coordinate/pairwise budget rejection;
- a coplanar contact-closure helper.

The global arrangement tests also verify that the final conforming fragments are passed through the oracle and that a coverage failure rejects the arrangement.

**Status: PARTIAL, not PASS.** This establishes an independent exact area-coverage implementation and current integration at the per-source-face arrangement layer. It does not yet establish the full adversarial matrix or prove coverage for the complete Boolean output. Remaining oracle work:
1. Add explicit point-touching, edge-touching, shared-vertex, narrow-sliver, and disconnected-region adversarial fixtures, with a documented policy distinguishing zero-area boundary contact from positive-area overlap.
2. Add direct API resource preflight before fragment materialization/validation: a hard fragment-count ceiling, a hard pair-check ceiling, and an aggregate rational-bit budget. The current oracle accepts caller-provided positive limits but does not impose a maximum fragment count or aggregate coordinate-bit budget itself; it materializes and validates the supplied fragment sequence before computing the pair-check charge.
3. Verify that the oracle's pair-check counter and configured budget are charged consistently across every source face in global arrangement, including the zero-remaining-budget case.
4. Keep oracle assertions independent of the generator's own area-conservation counters; the latter are supplementary checks, not oracle evidence.

No new adversarial tests are claimed by this document, and no local test execution is claimed here.

## Boolean material and boundary acceptance

For UNION, INTERSECTION, DIFFERENCE, and XOR:
- classify each fragment on both sides as INSIDE, OUTSIDE, or BOUNDARY;
- reject unresolved BOUNDARY/ambiguous witnesses unless a documented exact tie-break rule applies;
- select only fragments that separate result material from non-material;
- orient selected faces outward from result material;
- verify operation truth tables against independent exact point witnesses.

## Shell assembly acceptance

For every output component:
- each undirected edge has exactly two incident faces with opposite directed use;
- face adjacency produces the expected connected shells;
- shell orientation and exact signed/net volume agree with material classification;
- cavity ownership is unique and strictly contained;
- non-manifold edges, self-intersections, unsupported tangencies, nested ambiguous shells, and zero/non-positive material volume fail closed.

## CAD Generator integration

The service-level acceptance test must exercise the complete path from typed source meshes and operation through arrangement, independent coverage oracle, material classification, boundary selection, shell assembly, and serialized result. Verify deterministic output digests, resource counters, failure modes, and that unsupported configurations fail closed. A lower-level unit test or caller-supplied pre-arranged fragments does not prove this integration.

## Exit gates and evidence labels

| Gate | Required evidence | Passing condition |
|---|---|---|
| Input/resource preflight | unit tests for malformed, oversized, and boundary inputs | all expected accepts/rejections verified |
| Independent coverage | exact oracle tests against adversarial partitions | no gaps, overlaps, or duplicates in supported cases |
| Material classification | exact inside/outside/boundary witness tests | ambiguity is explicit and fail-closed |
| Boundary selection | truth-table tests for all four operations | selected faces and orientation match independent witnesses |
| Shell assembly | topology, orientation, containment, volume, and intersection tests | all invariants hold |
| Generator E2E | service-level tests from source meshes to serialized result | complete supported workflow passes |
| CI | checks on the exact PR head SHA | all required checks succeed |

Use only `PASS`, `FAIL`, `SKIPPED`, or `UNKNOWN`. Missing tests, missing CI, and skipped checks are never PASS. Do not claim the Boolean Kernel is complete until every required gate has evidence on the exact reviewed commit.

## Explicit non-goals for this work unit

- No merge to `main` without explicit approval.
- No deletion of repository content.
- No rounding exact rational coordinates to binary64.
- No claim of support for cavities, branching, point/edge tangencies, or arbitrary degeneracies without dedicated exact proofs and tests.
- No paid external service dependency.


## Input and resource validation — implementation slice

The rational solid input path now has an initial hardening implementation on the resource-preflight branch:

- Decimal integer strings are length-bounded from `max_coordinate_bits` before conversion; bounded 9-digit chunks avoid Python's process-wide large-decimal conversion cap while preserving the configured 16,384-bit ceiling. Conversion errors are normalized to `InvalidModelError`.
- `from_dict` validates the caller-supplied coordinate-bit and pair-check limits, including boolean/type/positive-value checks and hard ceilings, before parsing coordinate arrays.
- Geometry counts and the derived triangle-pair work count are checked against supported ceilings before coordinate parsing; a request that exceeds the pair budget is rejected before rational coordinate construction.
- Shell envelope, provenance record count, identifier lengths, provenance identifier/digest shape, and aggregate metadata character count are preflighted before rational coordinate parsing.
- Numerator and denominator bit lengths are charged incrementally to a 64,000,000-bit aggregate budget before each `Fraction` is retained. Direct immutable construction also checks the aggregate total.
- Solid/frame/unit identifiers, source identifiers, and provenance record counts have explicit hard limits.

The current constants are implementation policy, not a claim that every maximum-size geometry is affordable. The aggregate rational ceiling bounds integer payload size independently of the per-coordinate ceiling; vertex, triangle, pairwise-check, metadata, and provenance ceilings remain separate controls. Any future adjustment must preserve fail-closed behavior and be justified by supported workloads and CI resource measurements.

Regression coverage added for oversized positive/negative numerator and denominator strings, the per-integer bit boundary, invalid resource limits rejected before parsing, aggregate-budget exhaustion, metadata/provenance ceilings, and invalid geometry counts rejected before parsing. These tests have been committed but are **not yet reported PASS** until the workflow on the exact latest branch head completes successfully.

**Status: IMPLEMENTED / CI UNKNOWN** for this resource-hardening slice. No local test run is claimed. This does not certify the Boolean Kernel or the independent oracle's outstanding adversarial matrix.


## Follow-on audit — coverage adversarial matrix and existing downstream stages

### Coverage oracle hardening
The first adversarial extension is now implemented:

- Preflight fragment count and the full containment-plus-pairwise work estimate before validating/materializing fragment geometry.
- Add an aggregate rational bit budget to the oracle call, charged across source and fragment coordinates.
- Add exact point-touch and edge-touch relation cases, an 80-bit-denominator narrow-sliver overlap, contiguous overlay-contact coverage, a gap in overlay-contact coverage, and resource-preflight ordering tests.
- Correct the prior CI failure in `_parse_integer_string`: decimal digit preflight is intentionally conservative, but the exact `bit_length()` must also be enforced after bounded chunk conversion. The 8-bit boundary test now distinguishes 255 from 256.

PR #222 run 2389 exposed the missing post-conversion bit check (991 passed, 1 failed). The fix is in commit `8b4bc1f7be9b037a271524a4af9e1eb20639622c`. A subsequent exact-head run is required before this parser slice can be marked PASS.

### Existing stages found — do not rebuild
The branch already contains distinct implementations and tests for:
- `material_classification.py`: exact INSIDE / OUTSIDE / BOUNDARY / UNKNOWN classification with fail-closed ray witnesses.
- `boolean_boundary_selection.py`: two-sided material witnesses and operation-specific selection/orientation for UNION, INTERSECTION, DIFFERENCE and XOR.
- `boolean_shell_assembly.py`: shell/component assembly, cavities, exact net volume and topology validation.
- `cad_generator_service.py`: `execute_faceted_boolean` orchestration, with E2E tests for intersecting boxes and coplanar overlap.

These are existing bounded paths, not yet proof of complete Boolean Kernel support. PR #225 now adds the separate exact-rational multi-shell result path through shell assembly and deterministic serialization. The legacy binary64 B-rep result path remains separate and rejects non-lossless rational coordinates; it is not the exact-output contract.

### Still open
- Complete aggregate rational budget accounting across global arrangement, classification, selection, and shell assembly (the new oracle budget is one layer, not proof of end-to-end aggregate accounting).
- Adversarial coverage matrix for shared vertices, multi-fragment point/edge contacts, disconnected overlays, and malformed/resource-exhaustion paths.
- Verify all four operations across disjoint, nested, coplanar, intersecting, and degeneracy fixtures.
- Extend service-level E2E and operation coverage across the rational multi-shell path; keep exact rational serialization distinct from the legacy binary64 B-rep adapter.


### Cross-stage resource accounting extension

The rational bit budget and early-work preflight now extend beyond the standalone oracle:

- Global arrangement validates aggregate exact-coordinate bits across source triangles and cutter planes before fragment generation, and separately charges each source-face coverage partition against a shared aggregate coverage budget.
- Material classifier checks ray-triangle work before allocating exact triangle tuples, validates mesh topology before rational conversion, and enforces an aggregate rational-coordinate budget.
- Boundary selection preflights total mesh input rational bits, shares the coverage pair-check counter across source faces, explicitly rejects exhausted remaining pair budget, and charges source/fragment rational bits against one operation-level aggregate budget.
- Regression tests cover classifier allocation preflight, classifier and selection aggregate-budget rejection, and global-arrangement aggregate-budget rejection.

These are stage-scoped budgets with conservative charging, not yet one shared accounting object spanning the entire `CADGeneratorService` invocation. Shell assembly still needs its own aggregate budget and exact-rational output contract. The Boolean pipeline therefore remains PARTIAL until those integration gates and current-head CI are complete.


## Rational multi-shell output — implementation candidate

A separate `RATIONAL_BOOLEAN_SOLID_V1` result contract now composes individually
validated `RATIONAL_FACETED_SOLID_V1` shells into material components. Each
component has one OUTER shell and zero or more CAVITY shells, with explicit
parent-shell identity and exact net volume. Disconnected outer components are
preserved rather than rejected or silently discarded.

The rational generator path now:
- keeps every coordinate as an exact `Fraction` through shell assembly;
- normalizes each shell's own orientation while retaining its OUTER/CAVITY role;
- validates each shell with the existing exact rational faceted-solid validator;
- preflights inter-shell triangle-pair work and aggregate rational coordinate bits;
- rejects inter-shell intersection/contact, ambiguous containment, nested positive
  shells, and nested cavities rather than approximating them;
- uses exact rational ray witnesses for cavity-to-outer containment;
- serializes child shells, component parentage, exact net volume, counters and a
  deterministic SHA-256 result digest; and
- exposes a CADGeneratorService method returning the multi-shell artifact.

Regression coverage targets non-binary rational round-trip, disconnected outer
components, cavity role/parentage/net volume, touching-shell rejection,
invalid cavity containment, and service-level Boolean serialization.

**Status: IMPLEMENTED IN PR CANDIDATE / CI PENDING.** This does not certify
branching, arbitrary tangencies, nested material islands, all degeneracies, or
unrestricted exact Boolean geometry. Do not mark the stage PASS until all
required checks succeed on the exact latest head SHA.
