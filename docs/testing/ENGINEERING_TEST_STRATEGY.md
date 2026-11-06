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
