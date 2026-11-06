# Engineering Test Strategy

**Status:** PROPOSED test plan; implemented coverage is tracked separately in IMPLEMENTATION_STATUS.md.

## Test levels
1. Unit: deterministic functions, dimensions, validation and error behavior.
2. Contract: module manifests, request/response schemas, version compatibility, JSON-safe serialization, immutable nested payloads, resource-limit validation and permission declarations.
3. Reference: analytical cases with independently derived expected values and justified tolerances.
4. Property/fuzz: invariants, boundary values, malformed input and non-finite values.
5. Adapter integration: supported CAD/solver/data tools, pinned versions and isolated environments.
6. Interchange: export, independent reopen, unit/scale/orientation and metadata checks.
7. Security/governance: least privilege, path/network controls, secret handling, cancellation and prohibited physical actions.
8. End-to-end: one owner-approved vertical slice from requirements through evidence package.

## Test record
Record test ID/version, source SHA, fixture hash, command, environment, dependency/tool versions, expected criterion, actual output, exit code, log/artifact references, duration, reviewer and status.

## Evidence semantics
PASS only when the required test ran and met its criterion. FAIL when it ran and did not. SKIPPED only with an explicit reason. UNKNOWN when the evidence is missing or inconclusive. A workflow/job can succeed while individual steps are skipped; report both accurately.

## CI requirements
- Pin supported Python/tool versions and dependency constraints.
- Run lint/type/security checks only after tools and rules are selected; do not imply unconfigured scans ran.
- Keep unit and reference tests deterministic.
- Upload logs/artifacts for failures without exposing secrets.
- Separate optional adapter tests from required core tests and show unavailable adapters as SKIPPED/UNKNOWN.
- Run pull_request checks on the target base branch and bind results to the exact tested SHA.

## Release criteria
No critical FAIL or UNKNOWN; skipped tests have approved rationale; supported-platform matrix is explicit; test fixtures and expected values are reviewed; rollback and limitations are documented. Engineering correctness requires domain review beyond software CI.


## Implemented contract coverage

PR #39 tests metadata manifest/registry validation, dependency ordering and deterministic snapshots. PR #41 adds request/response envelope validation for identifiers, schema versions, finite numeric values, JSON compatibility, immutable nested payloads, resource limits, operational status semantics and error-code consistency. Runtime invocation and permission enforcement remain unimplemented.


## Evidence/provenance validation coverage

PR #42 adds source metadata and SHA-256 checks, timezone validation, immutable evidence metadata, JSON/non-finite rejection, duplicate source/record detection, deterministic serialization and aggregate evidence-gate precedence. Empty evidence must remain UNKNOWN; a gate can PASS only when every supplied required record passes.


## Coordinate-frame exchange validation

PR #43 adds JSON round-trip and deterministic-order tests for RigidTransform/FrameGraph, explicit length-unit checks, schema-version/field validation, graph topology validation, cycle and duplicate detection, and rejection of mixed-unit composition.


## Quantity interchange validation

PR #44 adds Quantity v1.0 JSON round-trip, SI-value/dimension/source-unit preservation, malformed schema/version rejection, non-finite numeric rejection, immutable dimension checks and JSON Schema shape validation.


## Frame-bound spatial value validation

PR #45 tests strict v1.0 serialization, POINT/VECTOR distinction, frame identity, explicit units, correct translation-versus-rotation behavior, unknown/disconnected frames and unit mismatch rejection.


## Hardware schematic model validation

PR #46 tests strict SchematicModel v1.0 JSON round-trip, deterministic component/net/pin ordering, stable IDs and reference designators, duplicate detection, dangling terminal rejection, one-net-per-pin, NO_CONNECT enforcement, schema version and unknown-field rejection. These are connectivity-model checks, not electrical rule checking.


## Hardware driver binding validation

PR #47 adds tests for driver/protocol/signal schema round-trip, module/operation identity, known schematic pin and driver signal resolution, duplicate bindings, NO_CONNECT rejection, pin/signal direction compatibility and optional ModuleRegistry operation lookup. These checks do not load driver code or communicate with hardware.


## CAD-neutral primitive geometry validation

PR #48 adds reference-value tests for Box/Cylinder SI volume and surface area, local and transformed bounding boxes, exact rotated-cylinder extents, unit/frame consistency, strict v1.0 snapshots and malformed primitive rejection. No mesh/B-rep or physical validation is implied.


## Profile extrusion validation

PR #49 adds simple polygon validation (duplicate vertices, self-intersections and degenerate area), SI volume/surface area references, concave profile coverage, strict JSON round-trip and transformed extrusion bounds.


## Through-hole profile geometry regression (PR #52 — merged; exact head and post-merge CI PASS, 425 tests each)

- Reference values cover a rectangular plate with one through-hole and a profile with multiple disjoint holes.
- Verify net area, total boundary perimeter, SI volume and surface area including inner hole walls.
- Reject holes touching or crossing the outer boundary, outside holes, intersecting/overlapping holes and nested holes.
- Verify optional-field compatibility: snapshots without `holes` remain valid and empty-hole serialization omits the field.
- Verify `Vec2` and `ExtrudedProfileSolid` are importable from the public engineering package, not only their implementation module.
- Preserve the existing Box/Cylinder, transformed-bound and mechanism regression suite.


Evidence: PR #52 head `bf093db34c7a7900d3d0924bccadfb40c33a30f0`, run #384 (`42191597715`) passed both jobs with 425 tests in 0.78s; merge `1d1628175dafca3f5d4d3d6b5cf01e241ec75afa`, post-merge run #385 (`42191666816`) passed both jobs with 425 tests in 0.87s.


## Spatial joint reference validation (PR #54 — merged; exact head and post-merge CI PASS, 452 tests each)

- A versioned JSON fixture enumerates all eight declared joint families and their independent coordinates, units, axes, nominal local DOF and expected zero-configuration Jacobian entries.
- Verify six deterministic residual rows and units for every family.
- Verify finite-difference Jacobian reference entries for cylindrical, spherical, planar and universal joints in addition to existing fixed/revolute/prismatic/helical coverage.
- Verify single-joint spatial local mobility and rank references for all eight families, including ground-link reversal.
- Verify nontrivial parent-to-joint and joint-to-child transforms with translation and rotation.
- Validate explicit 2D PLANAR mobility independently from the SPATIAL formulation; a PLANAR joint kind remains valid in SPATIAL without selecting the PLANAR analysis formulation.
- Acceptance contract: docs/design-3d/SPATIAL_JOINT_REFERENCE_VALIDATION_CONTRACT.md. Exact-head CI pending.


Evidence: PR #54 head `3da8c733895baab939548e0ba2e81670ca0c6359`, run #404 (`42193562931`): 452 passed in 1.35s; merge `22bbf1714224095cfd652d6887130d26facef087`, post-merge run #405 (`42193654653`): 452 passed in 1.33s. Initial run #403 failed due a test expectation that confused full and reduced Jacobian widths; the assertion was corrected and the latest head passed.


## Explicit planar plane-frame mobility (PR #56 — merged; exact head and post-merge CI PASS, 462 tests each)

- Require a plane-to-world RigidTransform and shared world frame; reject missing/mismatched plane frames.
- Validate every body origin lies in the plane and every body local +Z aligns with the plane normal.
- Validate joint-frame origins and rotational/translational coordinate axes against the declared plane.
- Verify FIXED, REVOLUTE, PRISMATIC and PLANAR single-joint mobility references; reject CYLINDRICAL, HELICAL, SPHERICAL and UNIVERSAL in the 2D formulation.
- Project the generated world-frame Jacobian to two in-plane translations and one plane-normal rotation per non-ground link; preserve generalized-coordinate columns and deterministic IDs.
- Test rotated/translated plane frames, ground-link reversal, off-plane body origins, tilted bodies, off-plane anchors, incompatible axes, unsupported joints and invalid tolerances.
- Acceptance contract: docs/design-3d/PLANAR_PLANE_FRAME_MOBILITY_CONTRACT.md. PR #56 merged at `8335515b31a89efc4cacb70cf9c2e3aeb4ae16d4`. Exact PR head `8b76f89687c4685c66fee5f8bc9cd045bd589abe`; run #459 (`42197011073`) passed `workflow-sanity` and `python-tests` with 462 tests. Exact post-merge run #461 (`42197156442`) on the merge SHA passed both jobs with 462 tests.


## Deterministic primitive triangle mesh validation (PR #64)

- Box reference: exact 8 vertices / 12 triangles, watertight two-face edge incidence, consistent outward winding, signed volume 24 m³ and surface area 52 m² for the 2×3×4 m fixture.
- Cylinder reference: explicit maximum radial chordal error, closed edge incidence, consistent winding, positive signed volume and surface area.
- Adversarial structural cases: out-of-range indices, open boundary, repeated triangle indices, inconsistent winding, invalid/under-resolution tolerance, and non-length units.
- Verify strict schema/version/unknown-field rejection and deterministic round-trip snapshots.
- This test level does not establish triangle-triangle self-intersection freedom, profile-with-hole meshing, B-rep validity or independent interchange fidelity.


## Straight extruded-profile mesh references (PR #66 candidate)

- Concave L-section with six vertices: validate ear-clipped caps, side-wall closure, positive signed volume (12 m³) and surface area (38 m²) at 4 m extrusion height.
- Verify clockwise and counter-clockwise input, collinear boundary vertices, deterministic serialization and source provenance.
- Fail closed for through-hole and curved-edge profiles in this increment.
- Continue Box/Cylinder regression tests and malformed index/open-boundary/degenerate/winding/tolerance/unit cases.


## Polygonal through-hole profile mesh references (PR #68 candidate)

- One rectangular hole in a 4×4 m outer profile, 2 m extrusion: net volume 30 m³, surface area 70 m².
- Two disjoint rectangular holes in a 10×10 m outer profile, 1 m extrusion: net volume 95 m³, surface area 242 m².
- Verify closed edge incidence, consistent outward/void-facing winding, positive signed volume, deterministic bridge/ear order and strict mesh round trips.
- Hole and outer loops with reversed winding must normalize without changing geometric validity.
- Curved outer/hole boundaries remain rejected; touching, crossing and nested invalid holes remain rejected by source profile validation.


## Circular-arc profile mesh references (PR #70 merged; PR #71 reference coverage)

- Require an explicit positive chordal tolerance for every profile with circular arcs; reject missing, zero, negative, under-resolution and resource-excessive tolerances.
- Verify the maximum radial chord deviation formula for each subdivided arc and preserve exact source endpoints.
- Verify closed two-manifold edge incidence, consistent winding, positive signed volume, deterministic snapshots and source provenance.
- Exercise both outer-boundary arcs and hole-boundary arcs; retain straight-only, single-hole and multiple-hole references.
- This remains a tessellated approximation; it does not establish exact curved B-rep geometry or manufacturing tolerance.


- PR #70 exact PR-head runs #42223197118/#42223188816 passed both jobs with 515 tests; post-merge run #42223460020 passed with 515 tests in 2.01s.
- PR #71 adds a curved polygonal-hole fixture. Exact PR-head run #42225768304 passed with 516 tests in 1.74s; post-merge run #42225830931 passed with 516 tests in 1.45s.
- The curved-hole reference checks closed/manifold topology, consistent winding, positive volume, a conservative chordal-area error bound, exact source endpoint retention, deterministic output and strict snapshot round trip.


## Binary STL export references (PR #74 implementation candidate)

- Require a valid source TriangleMesh and reject non-finite/overflowing float32 coordinates, quantized degenerate facets and facet counts above the documented resource limit.
- Verify deterministic 80-byte header, little-endian facet count, 50-byte facet records, zero attribute bytes and exact payload length.
- Use an independent test-only parser that does not reuse production packing helpers; verify order, winding, bounds, signed volume and the coordinate-error bound.
- Bind the payload SHA-256 to a strict sidecar carrying frame, length unit, source identity, source digest, chordal tolerance and facet count.
- External CAD application reopen remains UNKNOWN until TECH-002 selects and validates an independent tool.
