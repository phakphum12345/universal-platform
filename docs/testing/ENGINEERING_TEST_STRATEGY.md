# Engineering Test Strategy

**Status:** PROPOSED test plan; implemented coverage is tracked separately in IMPLEMENTATION_STATUS.md.

## Test levels
1. Unit: deterministic functions, dimensions, validation and error behavior.
2. Contract: module manifests, request/response schemas, version compatibility and permissions.
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
