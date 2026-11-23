# WP-15 — Modern Unified Control Center UI

**Status:** PARTIAL — WP-15C shell, WP-15D workspace foundations are integrated; the first WP-15E module/function catalogue slice is proposed in the current change set; unified settings, jobs/diagnostics, workbench integration and owner acceptance remain open. WP-15A inventory is drafted in [WP15A_UI_INVENTORY.md](WP15A_UI_INVENTORY.md); WP-15B IA and journeys remain drafts pending owner review/acceptance.  
**Repository:** `phakphum12345/universal-platform`  
**Work package:** WP-15  
**Owner decision:** Use a unified, responsive Control Center as the primary human-facing surface, while keeping domain workbenches focused on their specialist workflows.

## Current implementation boundary — 2026-11-23

The /control-center shell remains hosted by the authenticated IPv4-loopback CAD API and preserves the canonical CAD workbench at /. Workspaces use the configured durable SQLite store. This change set proposes authenticated read-only module and function catalogue endpoints and Control Center rendering for registered metadata; it is not merged to main yet. The local launcher registers the validated built-in physics module manifest. Catalogue entries are metadata only: they do not load code, grant permissions, invoke operations or establish runtime readiness. The tools endpoint explicitly reports UNKNOWN because no separately governed tool registry is configured. Jobs, diagnostics, audit browsing, unified settings and cross-domain workbench integration remain open. WP-15B remains a draft pending owner review. Exact-head CI and owner browser acceptance are required.

## 1. Outcome

Deliver a modern, coherent Control Center through which an authorized user can discover, operate, configure and diagnose the real capabilities of Universal Platform. The experience must organize existing functions, tools, modules and settings without inventing capabilities or exposing unsafe operations.

This is a product and interaction redesign, not a decorative dashboard refresh. It includes information architecture, navigation, design system, interaction patterns, settings governance, accessibility, responsive behavior, API integration and end-to-end acceptance.

## 2. Product principles

1. **Capability truth:** every visible action maps to an implemented API/command/module and an authorization rule. Missing capabilities are labelled planned, unavailable or unsupported; never simulate success.
2. **One coherent shell:** shared navigation, identity/context, search, notifications, status and help across platform areas; specialist workbenches retain domain-specific controls.
3. **Progressive disclosure:** overview first, common tasks next, advanced engineering controls only when relevant.
4. **Local-first and cost-aware:** prefer local execution and existing dependencies. No paid hosted service, telemetry vendor or remote dependency without a documented need and approval.
5. **Security by default:** permission-aware visibility, server-side authorization, explicit confirmation for consequential actions, audit evidence and safe failure states.
6. **Accessible and responsive:** keyboard-first operation, visible focus, semantic structure, readable contrast, reduced motion and usable desktop/tablet/mobile layouts.
7. **User control:** settings are inspectable, validated, reversible where possible and never silently change security, connectivity, execution or data-sharing policy.
8. **Consistent engineering language:** consistent units, status semantics, error presentation, provenance and exact revision identity.

## 3. Information architecture

Proposed primary navigation:

- **Overview** — system health, recent activity, work in progress, alerts and next actions.
- **Workspace** — projects, files, revisions, tasks and recent work.
- **Modules** — module catalogue, contracts, versions, dependencies, permissions, lifecycle and health.
- **Tools** — available tools, inputs/outputs, required grants, execution mode, quotas and evidence.
- **Functions** — searchable capability/function directory grouped by domain (CAD, Mechanics, Physics, Hardware, Drivers, Simulation, System).
- **Workbenches** — focused CAD/3D, Mechanics, Physics, Schematic/Hardware and other validated engineering workspaces.
- **Automation & Jobs** — queued/running/completed/failed work, logs, cancellation and resource leases where implemented.
- **Diagnostics** — health, dependencies, connectivity, runtime status, test/evidence summaries and actionable failure details.
- **Activity & Audit** — user-visible event history, approvals, permission changes, execution provenance and exportable evidence.
- **Settings** — profile/preferences, appearance, workspace, modules/tools, execution/runtime, connectivity, security/privacy, storage and advanced configuration.
- **Help & Documentation** — contextual guides, contracts, supported capability matrix and troubleshooting.

Navigation labels and groupings must be validated with task-based usability tests before being frozen. Hide or disable unavailable features with a clear reason and roadmap link.

## 4. Shared application shell and interaction model

- Responsive collapsible side navigation with clear active state and breadcrumbs.
- Global command/search palette for navigation and discoverable actions; results respect authorization.
- Persistent context selector for project/workspace and current environment, with explicit scope labels.
- Global status area for service health, job state, connection state and actionable notifications.
- Consistent page headers, primary/secondary actions, filters, tables/lists, detail panels and empty/loading/error states.
- Reusable confirmation, permission-request, progress, cancellation and result/evidence patterns.
- Deep links to resources and tasks, with graceful handling of expired or unauthorized targets.
- Keyboard shortcuts are discoverable, remappable where safe and never intercept normal text entry.
- Theme support (light/dark/system), density preference and reduced-motion behavior.

## 5. Design system

Create reusable design tokens and components before page-by-page restyling:

- Typography scale, spacing, layout grid, breakpoints, radii, elevation and icon conventions.
- Semantic colors for neutral, information, success, warning and failure; color is never the only status cue.
- Buttons, inputs, selects, tabs, menus, dialogs, tooltips, cards, tables, trees, code/log viewers, badges, alerts and toasts.
- Standard status vocabulary: PASS, FAIL, SKIPPED, UNKNOWN; distinguish running/pending states from evidence outcomes.
- Consistent units and precision formatting for engineering values; always show unit/context.
- Empty, loading, partial-data, stale-data, permission-denied, offline and error states.
- Avoid dense control panels; group advanced options and explain consequential settings.

## 6. Functions, tools and modules management

- Capability catalogue with search, domain/category filters, availability, maturity, version and source documentation.
- Function detail: purpose, input/output schema, examples, limitations, dependencies, permissions and evidence.
- Tool detail: execution environment, required grants, resource limits, timeout/cancellation support and audit trail.
- Module detail: manifest, operations, dependency graph, version compatibility, lifecycle and health.
- Clearly distinguish implemented, partial, planned, unavailable and unknown capabilities.
- Never expose a tool invocation as executable when its authorization or runtime enforcement is not available.
- No arbitrary plugin code execution or self-escalation through UI controls.

## 7. Settings architecture

Settings must be schema-backed, scoped and auditable:

- Profile and user preferences.
- Appearance, language, accessibility and layout density.
- Workspace/project defaults and storage locations.
- Module/tool enablement and host-granted permissions.
- Runtime/execution policy, quotas, timeouts and worker settings.
- Connectivity/provider configuration, with secrets masked and stored only through approved secret handling.
- Security, privacy, telemetry and data-retention controls.
- Advanced developer settings and diagnostics.

For every setting define owner/scope, type, default, validation, allowed values/ranges, persistence, migration behavior, security impact, restart requirement, audit event and rollback behavior. Show effective value and source (default/user/workspace/host policy). Host security policy must override user preference. Secrets must never be returned to the UI after write or logged. Dangerous changes require re-authentication or explicit confirmation when appropriate.

## 8. Diagnostics, activity and trust

- Display source-backed health checks with timestamp, exact component/version and evidence link.
- Separate unavailable checks from passing checks; missing data is UNKNOWN, not green.
- Show job lifecycle and structured logs with correlation IDs, redaction and copy/export controls.
- Show permission denials with the missing grant and a safe request path; do not reveal protected internals.
- Show audit records for settings changes, approvals, tool execution and module lifecycle.
- Do not expose secrets, tokens, private file content or unredacted sensitive logs.

## 9. Delivery sequence and dependencies

1. **WP-15A — UI inventory and user journeys:** source-backed inventory drafted in [WP15A_UI_INVENTORY.md](WP15A_UI_INVENTORY.md); review/accept the canonical CAD workbench, API route map, security boundaries, tests and capability gaps before building a shared shell. No duplicate shell.
2. **WP-15B — IA and interaction specification:** proposed in [WP-15B_NAVIGATION_USER_JOURNEYS.md](WP-15B_NAVIGATION_USER_JOURNEYS.md); this remains a draft until the owner accepts navigation, personas, entrypoint, responsive behavior, accessibility target and representative user journeys before WP-15C.
3. **WP-15C — Design system and application shell:** tokens, accessible primitives, responsive shell, navigation, command palette and global status.
4. **WP-15D — Overview and workspace:** health, recent activity, projects/tasks and evidence links.
5. **WP-15E — Functions/tools/modules catalogue:** first metadata-only slice is proposed for the validated built-in physics module and its declared operation, pending exact-head CI and merge; separate tool registry, richer discovery, lifecycle/authorization views and owner acceptance remain open.
6. **WP-15F — Unified settings:** next work package; typed schemas, effective values, validation, secure secret handling, audit and migration/rollback.
7. **WP-15G — Diagnostics and activity:** jobs, logs, status provenance, approvals and audit.
8. **WP-15H — Workbench integration:** connect existing CAD/Mechanics/Physics/Hardware workbenches using shared shell and consistent contracts; preserve specialist functionality.
9. **WP-15I — Accessibility, responsive and usability acceptance:** automated accessibility checks, keyboard-only tests, screen-reader review and task-based usability testing across supported viewports.
10. **WP-15J — Release hardening:** performance, error recovery, security review, browser matrix, regression tests and operator documentation.

Dependencies: API/CLI contracts, identity and authorization, module/function metadata, runtime/job status, audit/evidence contracts and the actual UI inventory. UI may present unavailable capability states before the backend is complete, but must not imply execution support.

## 10. Acceptance criteria

- [ ] Canonical UI inventory and route/component map exists; existing UI is reused or replacement is justified.
- [ ] Every screen/action is mapped to an API/command, permission, evidence and failure behavior.
- [ ] No decorative/inert controls, fake success, placeholder metrics or unsupported operations.
- [ ] Navigation and common tasks are consistent; search and deep links work with authorization.
- [ ] Functions/tools/modules expose truthful maturity, schemas, dependencies, permissions and limitations.
- [ ] Settings are typed, validated, scoped, auditable, secret-safe and have documented migration/rollback behavior.
- [ ] PASS/FAIL/SKIPPED/UNKNOWN semantics are consistent; missing checks never appear as PASS.
- [ ] Loading, empty, partial, stale, offline, unauthorized and error states are tested.
- [ ] Keyboard-only and screen-reader journeys pass; focus, contrast, semantics and reduced motion are verified.
- [ ] Desktop, tablet and mobile layouts pass defined viewport tests without horizontal overflow in primary workflows.
- [ ] No new paid dependency or external data transfer without documented approval.
- [ ] Browser E2E, API contract, component, accessibility and security checks pass on exact PR head and post-merge integration SHA.
- [ ] User acceptance is recorded for representative end-to-end workflows.

## 11. Evidence and status rules

Current state: **PLANNED**. WP-15A inventory and WP-15B IA are drafted; owner review/acceptance is pending. These documents are planning/evidence artifacts, not evidence of an implemented Control Center. WP-15 must remain PARTIAL until each delivery slice has source, tests, exact-SHA CI, security review and user acceptance. SKIPPED, missing and UNKNOWN checks are never PASS.

## 12. Open decisions

- Confirm primary supported browsers and minimum viewport sizes.
- Confirm whether the existing canonical UI is a web application, desktop shell or both after inventory.
- Confirm initial user roles and permission profiles.
- Select initial high-value journeys (suggested: inspect system health, run a validated calculation, manage a CAD task, inspect a job, update a safe preference).
- Confirm language/localization priority and accessibility target (recommend WCAG 2.2 AA).
- Confirm which settings are user-, workspace-, host- or administrator-owned.
