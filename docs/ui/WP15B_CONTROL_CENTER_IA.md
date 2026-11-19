# WP-15B — Control Center Information Architecture and User Journeys

**Status:** PROPOSED DRAFT — requires product/owner review and acceptance before WP-15C shell implementation.  
**Repository:** `phakphum12345/universal-platform`  
**Work package:** WP-15B  
**Depends on:** WP-15A inventory; identity/permission contracts; capability metadata; unified API/CLI direction.  
**Source inventory:** [WP-15A Existing UI Inventory](WP15A_UI_INVENTORY.md)

---

## 1. Purpose and design constraints

Define a coherent information architecture and representative user journeys for the future Unified Control Center without replacing or duplicating existing specialist workbenches.

The WP-15A inventory found one browser UI: the local CAD Generator workbench. It did not find a shared application shell, platform overview, workspace manager, unified settings, global job centre, platform diagnostics or global audit UI. This draft therefore proposes a new shell around real capabilities; it does not claim those missing backends already exist.

Non-negotiable constraints:

- Capability truth: every executable action must map to a real API/command, permission, input/output schema and failure state.
- Backend authority: hiding/disabling a control is not authorization; every consequential operation must be checked by the host.
- Local-first: preserve loopback-only services and dynamic port selection. No fixed port, public listener or hosted dependency is introduced by this IA.
- Preserve CAD: do not replace `cad_generator.html/css/js` or break its current API, revision, branch and mesh workflows.
- Evidence truth: missing/stale checks are UNKNOWN; SKIPPED is never PASS.
- No fake dashboard metrics, simulated jobs, decorative launch buttons or invented module capabilities.
- No paid service, remote telemetry or external data transfer without a documented need and approval.

## 2. Proposed navigation model

Use a single shared shell with a small number of top-level areas. Group related capability catalogues under one navigation family to reduce sidebar density.

| Top-level area | Subsections | Purpose | Current maturity |
|---|---|---|---|
| Overview | System status, recent activity, attention needed, next actions | A source-backed summary of platform health and work | PLANNED; CAD `/health` is not platform health |
| Workspace | Projects, files, revisions, recent work | Organize user-owned work and provenance | PLANNED; CAD FeatureHistory is a specialist history store, not a workspace manager |
| Capabilities | Modules, Tools, Functions | Discover actual registered capabilities, contracts, versions, dependencies and grants | PLANNED UI; backend ModuleRegistry exists, no catalogue UI found |
| Workbenches | CAD/3D, Mechanics, Physics, Hardware/EDA | Launch and embed validated domain workflows | CAD workbench exists; other browser workbenches not found |
| Jobs | Queued, running, completed, failed, cancelled | Inspect supervised execution, progress, logs, cancellation and leases | PLANNED; no unified job API/centre found |
| Diagnostics | Health, dependencies, connectivity, runtime, evidence | Explain real health checks and actionable failures | PLANNED; only CAD service health exists |
| Activity & Audit | Events, approvals, permission changes, execution provenance | Inspect auditable events with safe redaction | PLANNED UI; CAD API audit store exists locally |
| Settings | Profile, appearance, workspace, modules, execution, connectivity, security | Typed, scoped and auditable preferences/policy views | PLANNED; no unified settings schema/UI found |
| Help | Guides, API contracts, capability limits, troubleshooting | Contextual learning and operator support | Documentation exists; contextual help UI is PLANNED |

The navigation grouping is a proposal, not a frozen product decision. Validate with task-based usability testing before finalizing labels.

## 3. Shared shell layout

### Desktop

- Persistent collapsible left navigation with active state and section labels.
- Compact top bar with current workspace/project context, global search/command palette, notifications and user/permission context.
- Main content region with page title, breadcrumbs, primary action and contextual help.
- Optional right-side detail/inspector panel for selected resource, job, module or evidence record.
- Status banners for offline, stale, partial-data, permission-denied and degraded states.

### Tablet

- Collapsible navigation drawer; main content remains primary.
- Tables may switch to stacked summary rows with a detail view.
- Inspector becomes a dismissible overlay or lower panel.

### Mobile

- Compact navigation drawer or bottom-level navigation for the highest-frequency areas, subject to usability validation.
- One primary column; details open as dedicated pages or sheets.
- No essential workflow depends on hover, pointer-only actions or wide tables.
- Preserve CAD's existing specialist responsive behavior; shell integration must not shrink its canvas below usable dimensions.

### Shared page patterns

- Page header: title, short purpose, breadcrumbs and one primary action.
- Data states: loading, empty, partial, stale, offline, unauthorized, error and success.
- Tables/lists: search, filters, sort, pagination/virtualization where required, keyboard focus and empty state.
- Details: source/version, permissions, dependencies, limitations and evidence.
- Confirmations: required for consequential or irreversible actions.
- Long-running operations: explicit state, progress when available, cancellation when supported, correlation ID and result/evidence link.

## 4. Capability and permission presentation

Each catalogue entry must be generated from a trusted backend record, not a hard-coded UI list.

Minimum capability card/detail fields:

- Stable capability/module/function ID and display name.
- Domain and purpose.
- Maturity: IMPLEMENTED, VERIFIED, INTEGRATED, ACCEPTED or PLANNED/PARTIAL.
- Availability: available, unavailable, disabled, blocked or unknown.
- Version and compatibility.
- Input/output schema links.
- Dependencies and execution mode.
- Required permissions and current host grant state.
- Resource/timeout/cancellation support only where enforced.
- Evidence links and known limitations.

UI behavior:

- Viewer without a grant can inspect safe metadata but cannot execute.
- An ungranted operation shows the exact missing permission and a safe approval path; it never self-grants.
- Unsupported operations are labelled unavailable/planned and have no executable button.
- A missing registry/API response is UNKNOWN, not an empty catalogue that implies no capabilities.
- A successful calculation is not automatically an engineering PASS or safety certification.

## 5. Representative end-to-end user journeys

### Journey A — Inspect platform health

1. User opens Overview.
2. Shell requests platform health from a future host-owned health API.
3. Overview shows component identity/version, timestamp, evidence status and source link.
4. User selects a failed/unknown component and opens Diagnostics.
5. Diagnostics shows actionable cause and safe remediation guidance.

**Current gap:** only CAD Generator `GET /health` exists. It must not be displayed as global platform health.

### Journey B — Discover a validated function

1. User opens Capabilities → Functions.
2. User searches/filter by domain (CAD, Mechanics, Physics, Hardware, Runtime).
3. Function detail shows real operation schema, dependencies, permissions and limitations.
4. User can inspect examples and reference evidence.
5. Execute action is enabled only if backend reports the operation available and host authorization is satisfied.

**Current gap:** ModuleRegistry and operation contracts exist, but no unified catalogue API/UI was found.

### Journey C — Run a validated engineering calculation

1. User opens Physics workbench or a function detail.
2. User selects a registered solver and enters schema-validated inputs with units.
3. UI displays assumptions, validity range and limitations before execution.
4. Host checks grant, input schema and resource reservation.
5. If asynchronous execution exists, user sees a real job record; otherwise UI shows a synchronous operation result without inventing a job.
6. Result includes quantities, units, provenance, evidence status and limitations.

**Current boundary:** the three existing built-in analytical solvers are exposed through trusted in-process ModuleRuntime adapters. They are not a general simulation service, OS sandbox or unified job centre.

### Journey D — Author a CAD model

1. User opens Workbenches → CAD.
2. Existing CAD Generator workbench is reused, not rewritten.
3. User connects to its local service, creates a bounded polygon/extrusion, saves a FeatureHistory revision and regenerates.
4. User edits features, uses undo/redo or forks/merges a branch with revision checks.
5. User inspects the source-linked mesh preview and result metadata.

**Current status:** this journey is already implemented in the specialist CAD workbench. Preserve its same-origin, loopback-only and bearer-authenticated API boundary.

### Journey E — Inspect or cancel a job

1. User opens Jobs and filters by status, owner, module and time.
2. User opens a job detail to inspect lifecycle, correlation ID, logs and resource lease.
3. Cancel is offered only when host runtime supports cancellation and the job is cancellable.
4. UI waits for host-confirmed terminal state and process-tree cleanup before reporting cancellation complete.

**Current gap:** no unified job record/API or ModuleRuntime-to-supervised-worker integration is established. Do not create fake jobs from synchronous CAD results.

### Journey F — Change a safe preference

1. User opens Settings and selects an owned preference (e.g. appearance).
2. UI shows effective value, scope and source (default/user/workspace/host policy).
3. User edits a schema-valid value and previews the change.
4. Host validates and persists the change, then emits an audit event.
5. UI displays the new effective value and rollback path.

**Current gap:** no schema-backed settings registry or settings UI was found. Security, permissions, execution policy and data-sharing settings must remain host-owned and cannot be weakened by user preference.

### Journey G — Inspect activity and audit evidence

1. User opens Activity & Audit.
2. User filters by event type, time, resource and actor.
3. User opens an event to inspect timestamp, correlation ID, source component, outcome and evidence links.
4. Export produces a redacted record set and never exposes secrets or private file content.

**Current gap:** CAD API writes a local hash-chained audit log, but there is no global query/export UI or platform audit contract.

## 6. Conceptual user roles — not an implemented identity model

| Conceptual role | Intended access | Explicit boundary |
|---|---|---|
| Viewer | Read approved metadata, results and documentation | No execution or settings mutation |
| Engineer/Author | Create/edit own workspace artifacts and invoke granted engineering functions | Host grants remain authoritative |
| Operator | Inspect jobs, diagnostics and perform approved operational actions | No permission self-escalation or policy weakening |
| Administrator/Owner | Manage host policy, grants and protected settings | High-impact actions require explicit confirmation and audit |

These are design personas only. The repository inventory does not establish a complete user identity provider, multi-user account model or role-management UI. Do not implement role controls until identity and permission contracts are agreed.

## 7. Status and evidence vocabulary

Keep capability maturity separate from operation lifecycle and evidence outcomes.

- Maturity: IMPLEMENTED, VERIFIED, INTEGRATED, ACCEPTED; use PARTIAL/PLANNED where appropriate.
- Evidence: PASS, FAIL, SKIPPED, UNKNOWN.
- Job lifecycle (future API): QUEUED, RUNNING, CANCELLING, COMPLETED, FAILED, CANCELLED, TIMED_OUT, RECOVERY_REQUIRED.
- Health: READY, DEGRADED, UNAVAILABLE, UNKNOWN.

Rules:
- A job's COMPLETED lifecycle does not automatically mean its engineering evidence is PASS.
- SKIPPED and UNKNOWN never render as green success.
- Missing timestamps, stale source data and missing evidence are explicit.
- Never infer a terminal job state from a browser timeout or a closed tab.

## 8. Entry point and routing decision — intentionally open

The existing CAD service serves its workbench at `/` and static assets under `/static/*`. It is a specialist local service, not the platform host.

Do not commandeer the CAD service root or bind a fixed port to host the Control Center. Before WP-15C, choose one architecture:

1. A separate local Control Center host that binds loopback and selects a dynamic port, backed by approved platform APIs; or
2. A future unified application/API host that serves the Control Center and mounts the CAD workbench under a dedicated workbench route while preserving its API contract.

The decision must include startup/discovery, authentication, token handling, same-origin policy, port discovery, shutdown, API compatibility and E2E coverage. No route or port is frozen by this draft.

## 9. Responsive and accessibility target

Proposed acceptance targets (pending owner confirmation):

- Desktop baseline: 1280×800 and 1440×900.
- Tablet baseline: 768×1024.
- Mobile baseline: 390×844 and 360×800.
- No horizontal overflow in primary workflows at supported viewports.
- Keyboard-only completion of navigation, search, forms, dialogs, CAD launch and safe settings flows.
- Visible focus, semantic landmarks/headings, accessible names, status announcements and error association.
- Reduced-motion support and no color-only status communication.
- Screen-reader review on at least one supported desktop/mobile reader combination.
- WCAG 2.2 AA as the proposed target; formal target requires owner acceptance.

## 10. WP-15B acceptance gates

- [ ] Owner accepts top-level navigation and grouping.
- [ ] Representative user journeys are reviewed and prioritized.
- [ ] Role/permission personas are confirmed or replaced with an approved identity model.
- [ ] Capability truth, maturity, availability and evidence presentation rules are accepted.
- [ ] Control Center host/entrypoint architecture is selected without a fixed-port assumption.
- [ ] Responsive viewport and browser matrix is approved.
- [ ] Accessibility target and test strategy are approved.
- [ ] API dependencies and unavailable states are recorded before UI implementation.

WP-15B remains DRAFT until these decisions are accepted. Do not mark WP-15B COMPLETE or start WP-15C as if the product decisions were approved.

## 11. Open owner decisions

1. Confirm top-level navigation labels and whether Capabilities groups Modules, Tools and Functions.
2. Confirm initial user personas and whether the first release is single-user/local-only.
3. Confirm primary browser matrix and whether a desktop wrapper is in scope.
4. Confirm language/localization priority.
5. Confirm WCAG 2.2 AA target.
6. Choose the Control Center host/entrypoint architecture after unified API review.
7. Confirm initial high-value journeys for first release.
