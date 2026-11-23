# WP-15E — Modules, Tools and Functions Catalogue

**Status:** PARTIAL — first authenticated metadata-only module/function slice implemented in this change set; tool registry and owner acceptance remain open.  
**Work package:** WP-15E  
**Parent:** WP-15 Modern Unified Control Center UI  
**Repository:** `phakphum12345/universal-platform`  
**Target branch:** `main`

## 1. Scope

Provide a truthful, searchable foundation for discovering registered modules, declared operations and governed tools in the local-first Control Center. This slice intentionally exposes metadata only. It does not create a general plugin loader, invoke arbitrary code, grant permissions or provide a tool-execution surface.

## 2. Implemented in this slice

- The local launcher creates the existing built-in Physics Module Bridge and supplies its validated `ModuleRegistry` to the loopback HTTP host.
- The bridge exposes its metadata registry as a typed field while retaining the existing host-controlled runtime grant/revoke boundary.
- Authenticated read-only endpoints:
  - `GET /v1/modules` — deterministic manifest list, registration state, dependency-order evidence and explicit limitations.
  - `GET /v1/modules/{module_id}` — one validated manifest.
  - `GET /v1/functions` — declared module operations with schema versions, execution kind, domain, maturity and required permissions.
  - `GET /v1/tools` — explicitly reports `UNKNOWN` and an empty list because no separately governed tool registry is configured.
- The Control Center renders module, function and tool catalogue states using DOM text nodes; it does not use HTML injection or expose invocation buttons.
- Catalogue requests reuse the existing bearer-authenticated same-origin API. The bearer token remains in page memory only and is not persisted.

## 3. Current source-backed inventory

The local launcher currently registers one validated module:

- Module ID: `org.universal.physics`
- Version: `1.0.0`
- Domain: `physics`
- Maturity: `VALIDATED`
- Declared operation: `physics.solve`
- Required permission: `engineering.physics.solve`
- Execution kind: `CALCULATION`

The physics adapter currently contains bounded built-in analytical solvers for axial stress, Ohm's law and linear thermal expansion. These are not separate module operations in the current manifest and are not independently invokable through the catalogue API.

No separately governed tool registry is configured. The tools catalogue must remain UNKNOWN rather than imply that tools are available.

## 4. Security and capability boundaries

- Every catalogue endpoint is protected by the existing bearer authentication, loopback peer, Host and Origin checks, strict request handling and append-only audit lifecycle.
- Catalogue routes are GET-only and reject unsupported query parameters.
- Module registration is metadata; it is not a permission grant or runtime readiness signal.
- `execution_status=NOT_ENABLED_BY_CATALOGUE` is deliberately conservative. The catalogue does not reveal or modify host grants.
- No module code is loaded from user-controlled paths or metadata.
- No arbitrary tool execution, remote access, physical device I/O or privilege escalation is introduced.

## 5. Validation required

- API tests for list/detail/function/tool responses, authentication, unknown module IDs and read-only behavior.
- Browser E2E for rendered module/function metadata, truthful UNKNOWN tools state and absence of execution controls.
- Existing CAD Generator, workspace, runtime, cross-shell and browser regression suites must remain green.
- Exact PR-head CI and post-merge CI must be checked separately.
- A failed, skipped, missing or unexecuted check is not PASS.

## 6. Remaining WP-15E work

- Add a separately governed tool registry only after its ownership, schema, permission and execution contracts are implemented.
- Expand catalogue coverage from the built-in Physics module to other modules only when their manifests are validated and registered by trusted host code.
- Add capability search and domain/category filters after catalogue data volume justifies them.
- Add dependency and compatibility detail views without claiming runtime health.
- Add lifecycle/authorization views only when backed by host-side read APIs that do not leak grants or secrets.
- Record owner acceptance for representative discovery journeys.

## 7. Dependencies and next work packages

- WP-15F — Unified Settings: typed, scoped, validated and auditable settings with secure secret handling and migration/rollback.
- WP-15G — Diagnostics and Activity: jobs, logs, status provenance, approvals and audit browsing.
- WP-15H — Workbench integration.
- WP-15I — Accessibility, responsive and usability acceptance.
- WP-15J — Release hardening.

WP-15 remains PARTIAL until all applicable work packages and end-to-end acceptance gates pass.
