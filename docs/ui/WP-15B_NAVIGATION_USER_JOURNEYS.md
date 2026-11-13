# WP-15B — Navigation & User Journeys

**Status:** DRAFT — pending user review and acceptance.  
**Work package:** WP-15B  
**Parent:** WP-15 Modern Unified Control Center UI  
**Repository:** `phakphum12345/universal-platform`  
**Target branch:** `docs/reconcile-2026-11-12-pr240`  
**Scope:** Information architecture, navigation, representative user journeys, shared UI state and integration boundaries.  
**Non-goal:** This document does not implement UI, add API endpoints, change runtime behavior or authorize a merge.

## 1. Purpose and design constraints

WP-15B turns the WP-15 product requirements into a reviewable navigation and interaction specification. It must build on the WP-15A inventory and the existing domain workbenches rather than create duplicate implementations.

The design follows these constraints:

1. **Reuse before replacement.** Keep the existing CAD Generator Workbench and its specialist workflow. Integrate it through a shared shell only when the shell exists; do not recreate its feature tree, revision, branch, merge or modeling controls.
2. **Capability truth.** Every actionable control must map to a verified UI route and an existing API/command, authorization check, result and failure behavior. If one is missing, present an explicitly non-executable state.
3. **No inferred health.** Missing, stale, inaccessible or unexecuted evidence is UNKNOWN or unavailable, never PASS or healthy.
4. **Security boundary.** UI visibility is not authorization. Host-side permission enforcement remains authoritative. Do not expose arbitrary plugin execution, self-escalation or untrusted code loading.
5. **Local-first and cost-aware.** Prefer existing local capabilities and dependencies. No new paid service, telemetry vendor or external data transfer without documented need and approval.
6. **No false affordances.** No decorative controls, fake success, placeholder metrics or buttons that cannot complete their stated action.
7. **Traceable operations.** Consequential actions show scope, revision, permission context, confirmation requirements and resulting evidence.

## 2. Proposed navigation model

The following is a proposed information architecture, not a claim that these routes already exist.

| Primary area | Purpose | Initial content | WP-15 status |
|---|---|---|---|
| Overview | Orient the user to the platform | Source-backed health, recent activity, work in progress, alerts and evidence | Planned |
| Workspaces | Organize domain work | CAD, Mechanics, Physics, Hardware/Electronics and project context | Existing domain capability varies; unified workspace planned |
| Modules | Discover module metadata and lifecycle | Manifest, version, dependencies, declared operations, grants and health | Registry/runtime foundations exist; unified UI planned |
| Tools | Discover supported tools and execution contracts | Inputs/outputs, execution mode, limits, permissions and evidence | Inventory/API coverage incomplete |
| Functions | Search platform capabilities by domain | CAD, Mechanics, Physics, Hardware, Drivers, Simulation and System | Central UI catalogue not verified |
| Jobs & Activity | Inspect work execution and history | Job state, logs, cancellation where supported, resource/lease context and audit events | Runtime foundations exist; unified UI planned |
| Evidence | Inspect provenance and verification | Exact revision, test/check result, timestamp, source and limitations | Unified evidence UI not verified |
| Diagnostics | Diagnose system and dependency failures | Health checks, connectivity, component status and actionable failures | Existing health components; unified UI planned |
| Settings | Manage validated configuration | Appearance, workspace, module/tool preferences, runtime and connectivity settings | Unified settings UI not verified |
| Permissions & Security | Understand and request authorized access | Effective grants, scope, policy owner, approval and audit trail | Host permission foundations exist; unified UI planned |
| Help & Documentation | Explain supported behavior | User guides, API contracts, capability maturity and troubleshooting | Documentation exists; contextual UI planned |

### 2.1 Navigation behavior

- Use a responsive, collapsible primary navigation with a clear active item and breadcrumbs.
- Keep the current workspace/project and environment scope visible.
- Provide global search/command discovery only for destinations and actions that actually exist and are authorized.
- Deep links must resolve to a clear not-found, expired, unavailable or unauthorized state; never silently redirect to a misleading success page.
- Preserve specialist workbench navigation and state when entering or leaving the shared shell.
- Hide or disable an unavailable action only with an explanatory reason and, where appropriate, a roadmap/documentation link.
- Do not freeze labels or grouping until representative task-based review is complete.

## 3. Representative user journeys

### Journey A — Inspect platform status

1. User opens Overview.
2. UI loads status from identified health/evidence sources and displays source, timestamp and component identity.
3. User distinguishes PASS, FAIL, SKIPPED and UNKNOWN; running/pending states remain separate from completed evidence outcomes.
4. User opens a failed or unknown component to view diagnostic detail and the next supported action.
5. If no authoritative status source exists, UI says unavailable/UNKNOWN rather than synthesizing a green state.

**Acceptance:** Every displayed status has provenance. Missing or stale data cannot appear as PASS.

### Journey B — Create or continue a CAD task

1. User opens Workspaces → CAD.
2. UI opens or embeds/links the existing CAD Generator Workbench instead of duplicating its modeling UI.
3. User selects a supported polygon-extrusion template or an existing history.
4. UI communicates the selected history/revision and the relevant operation result.
5. User edits, regenerates, undoes/redoes or branches only through the existing supported CAD API operations.
6. Conflicts and validation failures are displayed as failures with actionable context; the UI does not claim a model update unless the API confirms it.

**Known existing CAD API surface from WP-15A inventory:**
- `GET /health`
- `POST /v1/templates/polygon-extrusion`
- `POST /v1/histories`
- `GET /v1/histories/{id}`
- `GET /v1/histories/{id}/revisions`
- `POST /v1/histories/{id}/regenerate`
- `POST /v1/histories/{id}/edit`
- `POST /v1/histories/{id}/undo`
- `POST /v1/histories/{id}/redo`
- `GET /v1/histories/{id}/navigation`
- `GET/POST /v1/histories/{id}/branches`
- `POST /v1/histories/{id}/merge`

The API was observed as loopback-bound, bearer-token protected and dynamically port-configured during WP-15A. Do not hard-code a port or expose it publicly as part of this UI work.

### Journey C — Discover a module and inspect its execution boundary

1. User opens Modules and searches/filter modules by domain or capability.
2. User opens a module detail view to inspect manifest metadata, version, dependencies and declared operations.
3. UI shows whether the module is metadata-only, backed by a trusted in-process handler, or otherwise unavailable; it must not imply that a manifest is an executable plugin.
4. User reviews required permissions and host-granted permissions.
5. If a supported operation is available, UI submits only through the authorized host/runtime path and displays the returned result/evidence.
6. If runtime enforcement or a required contract is absent, execution is disabled with a clear reason.

**Boundary:** WP-15A found ModuleRegistry/ModuleManifest/ModuleRuntime foundations. The registry is metadata, and the runtime uses trusted in-process handlers; this is not an OS sandbox or permission to execute arbitrary untrusted plugin code.

### Journey D — Find and use a tool or function

1. User opens Tools or Functions and searches by name, domain or supported capability.
2. Detail view presents purpose, input/output contract, dependencies, execution mode, resource bounds, required grants and limitations.
3. UI distinguishes implemented, partial, planned, unavailable and unknown maturity.
4. User invokes only a verified operation with a validated input schema and sufficient host authorization.
5. UI displays structured result, failure, cancellation or timeout only when the backend contract supports that outcome.

**Acceptance:** No invocation control is enabled based solely on a label, manifest claim or user-supplied permission.

### Journey E — Inspect a job and diagnose a failure

1. User opens Jobs & Activity and selects a job or recent operation.
2. UI shows the strongest available identity: job/correlation ID, component, operation, revision, state and timestamps.
3. User inspects structured logs and linked evidence with sensitive values redacted.
4. Cancellation is offered only if the actual execution contract supports it.
5. User opens Diagnostics for related health/dependency information.
6. Missing job, log or health data is shown as UNKNOWN/unavailable, not successful completion.

**Boundary:** WP-15A found runtime resource registry, health monitor and worker supervisor foundations. The inventory did not establish a complete unified job API or prove all cancellation/lease lifecycle semantics. Do not invent endpoints or claim OS-level containment.

### Journey F — Review settings and permissions

1. User opens Settings and selects a clearly scoped setting group.
2. UI displays effective value, source (default/user/workspace/host policy), validation rules and security impact.
3. User edits a supported setting; invalid values are rejected before submission and backend validation remains authoritative.
4. Sensitive changes require confirmation or re-authentication when policy requires it.
5. UI never returns or logs secret values after write.
6. User opens Permissions & Security to inspect effective grants and the policy owner.
7. A permission request is a request only; it does not grant itself. Host policy and approval remain authoritative.

**Acceptance:** Settings are typed, scoped, validated and auditable. Host policy cannot be overridden by a user preference.

## 4. Shared application state

The shell should share only state needed for consistent navigation and context. Suggested state domains:

| State domain | Meaning | Safety/consistency rule |
|---|---|---|
| platform_status | Aggregated component status and provenance | Preserve UNKNOWN and source timestamps |
| selected_workspace | Current project/domain workspace | Do not silently change execution scope |
| selected_resource | Selected file, history, module or resource | Bind to stable identity and revision |
| selected_module | Module detail and declared capabilities | Metadata does not imply executable authority |
| selected_operation | Operation and validated input context | Revalidate against current contract and grants |
| active_job | Current/recent job identity and state | Do not infer completion from missing polling data |
| permission_context | Effective host grants and policy scope | Read-only from UI perspective; no self-escalation |
| diagnostic_filters | User-selected diagnostic filters | Filters must not alter underlying evidence |
| evidence_context | Exact commit/revision, checks and provenance | Never mix evidence from different SHAs |

### 4.1 Standard view states

Every data-driven screen/component must define the states it can actually encounter:

- **LOADING** — request is in progress.
- **READY** — required data was retrieved and validated.
- **EMPTY** — authoritative response confirms there are no records.
- **PARTIAL** — some expected data is available, but one or more sources failed or are unavailable.
- **FAILED** — the operation/request failed.
- **UNKNOWN** — no reliable status can be established.
- **UNAUTHORIZED** — access is denied by the authoritative service.

Do not convert timeout, missing endpoint, parse failure, stale response or authorization failure into EMPTY or READY.

## 5. Existing integration map and gaps

| Domain | Existing source identified in WP-15A | UI integration rule | Open gap / verification |
|---|---|---|---|
| CAD | `engineering/static/cad_generator.html`, `cad_generator.js`, `cad_generator.css`; `engineering/cad_generator_http_api.py` | Reuse the existing workbench and API contracts | Shared-shell embedding/routing and API lifecycle need implementation tests |
| Modules | `engineering/module_registry.py`, `module_runtime.py` | Present metadata separately from trusted handler execution | No arbitrary plugin loader or OS sandbox claim |
| Physics | `engineering/physics.py`, `PhysicsSolverRegistry` | Discover registered solvers and supported adapters | Unified UI/API contract and maturity map need verification |
| Resources | `runtime/resources/registry.py`, `runtime/health/monitor.py` | Display source-backed resource/health information | Unified resource/job endpoints and freshness contract need verification |
| Workers | `runtime/supervisor.py` | Display only lifecycle events actually exposed by the supervisor | ModuleRuntime integration, Windows Job Objects and durable lease recovery remain separate engineering gaps |
| Evidence/tests | Existing tests and GitHub Actions workflows | Link evidence to exact source revision and workflow result | Browser E2E must be verified as actually executed on the relevant code SHA |

This table is an integration map, not an API promise. WP-15C and later implementation work must inspect the current source and tests again before binding UI components to contracts.

## 6. Roles, permissions and consequential actions

Initial role names are intentionally not fixed in this document because WP-15A did not establish a complete role catalogue. WP-15C+ must derive roles from actual identity/authorization contracts.

For each actionable operation, document:

- operation identifier and owning component;
- required host grant and scope;
- whether the action is read-only or mutating;
- input validation and resource limits;
- confirmation/re-authentication requirements;
- timeout/cancellation behavior, if supported;
- result, audit and evidence contract;
- failure, retry and recovery behavior.

The UI must not treat hidden navigation, disabled buttons or client-side checks as a security boundary.

## 7. Responsive and accessibility behavior

- Desktop: support efficient navigation between overview, domain workbenches and detail panels.
- Tablet: collapse secondary navigation and preserve readable tables/details without losing context.
- Mobile: prioritize status, task inspection and safe read-only workflows; complex engineering editing must be explicitly tested before being claimed as supported.
- All navigation and core flows must be keyboard operable with visible focus and logical focus order.
- Use semantic headings, labels and controls; communicate status with text/icons as well as color.
- Respect reduced-motion preferences and maintain usable contrast.
- Accessibility target recommendation: WCAG 2.2 AA, subject to formal acceptance in WP-15I.

## 8. WP-15B deliverables and acceptance gate

Deliverables:
1. Proposed primary navigation and grouping.
2. Representative end-to-end user journeys.
3. Shared state and standard view-state model.
4. Existing subsystem integration map and explicit unknowns.
5. Permission and security interaction boundaries.
6. Responsive/accessibility behavior and implementation dependencies.

Acceptance checklist:
- [ ] User reviews and accepts navigation labels and grouping.
- [ ] User reviews and accepts the six representative journeys.
- [ ] Every proposed action is mapped to an existing contract or explicitly marked as a future dependency.
- [ ] Existing CAD Workbench is reused; no duplicate CAD UI is proposed.
- [ ] Module metadata is not misrepresented as executable code.
- [ ] Host-side authorization remains authoritative.
- [ ] UNKNOWN, PARTIAL, FAILED and UNAUTHORIZED states are not collapsed into success.
- [ ] No unsupported endpoint, cancellation behavior, sandbox guarantee or paid dependency is invented.
- [ ] WP-15A findings are revalidated before implementation if source/API contracts change.

**Exit condition:** WP-15B may move from DRAFT to ACCEPTED only after review of this document. WP-15C (Design System & Control Center Shell) must not be considered started merely because this specification is committed.

## 9. Explicit exclusions

This work package does not:
- implement or restyle the Control Center;
- modify CAD, Mechanics, Physics, Hardware, module runtime or worker supervisor code;
- add or change API endpoints;
- introduce authentication, authorization or OS sandbox guarantees;
- claim browser E2E, accessibility or release acceptance has passed;
- authorize merging PR #242 or PR #241;
- authorize changes to `main`, deployment or paid services.

## 10. Current status

**WP-15B: DRAFT — recorded for review; acceptance pending.**  
**WP-15C–WP-15J: PLANNED — implementation not started.**

This document is a specification artifact only. Its presence in a pull request is not evidence that the UI or its integrations have been implemented or tested.
