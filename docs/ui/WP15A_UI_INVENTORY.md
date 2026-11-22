# WP-15A — Existing UI Inventory and Route Map

**Status:** INVENTORY BASELINE WITH WP-15C FOLLOW-UP — canonical CAD workbench and API inventory retained; a provisional shared-shell foundation is now added on the WP-15C feature branch. This is not owner-accepted IA or a completed Control Center.  
**Repository:** `phakphum12345/universal-platform`  
**Inspected ref:** `docs/phase-0-complete-requirements`  
**Reference integration base observed in current PRs:** `a0bf54e5ccc0de4ee9682de4395391d1fa9a67e8`  
**Work package:** WP-15A — UI inventory and user journeys  
**Purpose:** Record the canonical existing UI, its APIs, authorization boundary, tests and gaps before designing or building a shared shell.

---

## 1. Executive inventory

The inspected repository has one implemented specialist browser workbench plus a provisional shared-shell entry point:

- **Control Center shell (WP-15C foundation):** `src/universal_platform/engineering/static/control_center.html`, served at `/control-center` on the existing loopback CAD host; this is a navigation foundation, not a complete platform dashboard.\n- **CAD Generator workbench:** `src/universal_platform/engineering/static/cad_generator.html`
- **Styles:** `src/universal_platform/engineering/static/cad_generator.css`
- **Browser behavior:** `src/universal_platform/engineering/static/cad_generator.js`
- **Loopback HTTP API and static asset host:** `src/universal_platform/engineering/cad_generator_http_api.py`
- **Service layer:** `src/universal_platform/engineering/cad_generator_service.py`
- **Browser E2E:** `e2e/test_cad_generator_browser.py`
- **HTTP/API tests:** `tests/test_cad_generator_http_api.py`

The canonical specialist UI remains the CAD/FeatureHistory workbench. WP-15C adds a provisional shared shell at `/control-center`; global workspace/project manager, module/tool/function catalogue, unified settings, job centre, diagnostics centre and platform-wide activity/audit screen are still not implemented.

Do not create a second CAD workbench. WP-15 should reuse this workbench and progressively host it inside a shared shell after the shell/API contracts are designed and accepted.

## 2. Canonical application surface

| Surface | Source | Current behavior | Evidence boundary |
|---|---|---|---|
| Control Center shell | `engineering/static/control_center.html/css/js` | Provisional responsive navigation shell, planned-area labels, CAD service health check and link to existing CAD workbench | WP-15C foundation; exact-head CI and owner acceptance pending |\n| CAD workbench document | `engineering/static/cad_generator.html` | Single-page specialist UI with connection, sketch, history, revision, branch, mesh and result panels | Implemented; preserve as canonical specialist workbench |
| CAD styles | `engineering/static/cad_generator.css` | Dark visual theme, responsive two-column layouts, mobile breakpoint at 650px, focus/disabled states, sketch/mesh/feature-tree styles | Responsive CSS exists; accessibility acceptance is not established |
| CAD browser controller | `engineering/static/cad_generator.js` | Bearer-token API client, sketch authoring, history/revision navigation, feature editing, branching/merge, mesh preview/measurement | Implemented for the bounded workflows listed below |
| HTTP adapter | `engineering/cad_generator_http_api.py` | Loopback-only HTTP server, static assets, API routing, strict JSON request handling and audit logging | Local-only service; not a general platform API |
| CAD domain service | `engineering/cad_generator_service.py` | FeatureHistory persistence, editing, revision operations, branch/fork/merge and regeneration orchestration | Existing service; preserve its revision and validation semantics |
| Browser E2E | `e2e/test_cad_generator_browser.py` | Chromium browser workflows for editing, conflicts, safe text rendering, suppression, undo/redo, reorder and branch merge | Chromium only in the inspected E2E file |
| HTTP/API tests | `tests/test_cad_generator_http_api.py` | API auth/origin/body-size/audit, templates, history, revision conflicts, editing, navigation and branches | Backend API tests; not a full platform UI E2E suite |

## 3. Existing user journeys and UI panels

### 3.1 Connection

- User supplies a bearer token in the password input.
- Connect action gates protected API controls.
- Token is held in page memory; no persistent browser storage is used by the inspected controller.
- Static page assets are same-origin; API calls add an Authorization Bearer header.

### 3.2 Sketch and extrusion

- Bounded straight-edge polygon profile authoring with numeric X/Y inputs.
- Add point, undo point, clear profile and set extrusion height.
- Generate action calls the fixed polygon-extrusion template endpoint.
- API contract limits the template to at most 64 vertices and explicitly states that it is not a general sketcher or CAD kernel.

### 3.3 FeatureHistory authoring and inspection

- Paste/edit a FeatureHistory JSON snapshot and identify history/revision.
- Preview a bounded dependency tree and inspect selected feature metadata.
- Add, replace, remove, suppress and unsuppress allow-listed feature nodes.
- Cascade removal/suppression is explicit.
- Reorder is presentation-only; execution order remains dependency-derived.
- Backend validation remains authoritative; the browser tree is not a replacement for server validation.

### 3.4 Revision and navigation

- Save a snapshot with expected revision.
- List revisions and load an exact revision.
- Regenerate a selected revision.
- Undo and redo append immutable revisions; historical revisions are read-only.
- Stale writes return a conflict and the UI asks the user to refresh/load the current head before retrying.

### 3.5 Branch, fork and merge

- List branches for a history.
- Fork an immutable selected revision into a new history/branch.
- Merge a selected source branch into the current target head with expected source and target revisions.
- Structured merge conflicts are surfaced in the workbench.
- The UI requires the current target head to be loaded before merge.

### 3.6 Mesh preview and measurement

- Render a static isometric SVG preview from the exact generated mesh artifact.
- Bounded client-side zoom, pan/orbit and reset controls.
- Triangle selection by pointer and keyboard activation; report selected facet area and centroid.
- Clear selection and inspect mesh metadata/validation flags.
- Preview limits and malformed-geometry handling are enforced in the browser; backend mesh validation remains authoritative.
- This is a bounded triangle-mesh viewer, not a full interactive B-rep viewport.

### 3.7 Result and evidence

- Structured operation result and status message.
- Mesh state/validation details, source revision and artifact metadata.
- No general platform job history or global audit browser is present in this workbench.

## 4. Existing HTTP route map

The route implementation is in `_CADGeneratorRequestHandler._dispatch` in `engineering/cad_generator_http_api.py`.

| Method | Route | Purpose | Authorization |
|---|---|---|---|
| GET | `/` | Serve CAD workbench HTML | Local-origin checks; static asset route does not require bearer token |\n| GET | `/control-center` | Serve provisional Control Center shell | Same loopback and restrictive static-asset security boundary |\n| GET | `/static/control_center.css` | Serve Control Center stylesheet | Same loopback and restrictive static-asset security boundary |\n| GET | `/static/control_center.js` | Serve Control Center browser controller | Same loopback and restrictive static-asset security boundary |
| GET | `/static/cad_generator.css` | Serve workbench CSS | Local-origin checks; static asset route does not require bearer token |
| GET | `/static/cad_generator.js` | Serve workbench JavaScript | Local-origin checks; static asset route does not require bearer token |
| GET | `/health` | CAD Generator readiness/version | Bearer token required |
| POST | `/v1/templates/polygon-extrusion` | Build bounded polygon extrusion FeatureHistory template | Bearer token required |
| POST | `/v1/histories` | Save a new snapshot using expected revision | Bearer token required |
| GET | `/v1/histories/{history_id}` | Read latest or selected revision (`?revision=N`) | Bearer token required |
| GET | `/v1/histories/{history_id}/revisions` | List revision numbers | Bearer token required |
| GET | `/v1/histories/{history_id}/navigation` | Read undo/redo navigation state | Bearer token required |
| POST | `/v1/histories/{history_id}/undo` | Append an undo revision using expected revision | Bearer token required |
| POST | `/v1/histories/{history_id}/redo` | Append a redo revision using expected revision | Bearer token required |
| POST | `/v1/histories/{history_id}/edit` | Add/replace/remove/reorder/suppress/unsuppress feature | Bearer token required |
| GET | `/v1/histories/{history_id}/branches` | List branches | Bearer token required |
| POST | `/v1/histories/{history_id}/branches` | Fork a branch from a saved revision | Bearer token required |
| POST | `/v1/histories/{history_id}/merge` | Merge source branch into target history | Bearer token required |
| POST | `/v1/histories/{history_id}/regenerate` | Regenerate a saved history/revision | Bearer token required |

The handler defines methods for PUT/PATCH/DELETE for uniform dispatch, but `_dispatch` accepts only GET and POST and returns 405 for unsupported methods. Do not document those methods as implemented API routes.

## 5. HTTP security and operational boundary

Source-backed behavior in `cad_generator_http_api.py`:

- Server binds only to `127.0.0.1`; non-loopback host values are rejected.
- Port defaults to `0`, allowing the operating system to select an available port.
- Requests must originate from the configured loopback peer and exact Host header.
- If Origin is present, it must equal the same loopback origin; no CORS permission is granted.
- Transfer-Encoding requests are rejected; JSON requests require Content-Length and strict UTF-8 JSON.
- Duplicate JSON object keys and non-finite JSON constants are rejected.
- Request body limit is configurable from 1 byte through 16 MiB; request timeout is greater than zero and at most 30 seconds.
- Bearer token must contain at least 32 UTF-8 bytes; comparison uses constant-time `hmac.compare_digest`.
- API requests are audited on receipt and completion. Audit unavailability fails closed with 503.
- Responses use no-store and nosniff headers. Static assets also set frame denial, no-referrer, same-origin resource policy, restrictive permissions policy and a restrictive Content Security Policy.
- The static page is available only through the local server; protected API calls require the bearer token.

This is a local CAD API security boundary. It is not an identity provider, multi-user authorization service, remote API gateway or general platform security model.

## 6. Existing test and validation coverage

### HTTP/API tests

`tests/test_cad_generator_http_api.py` currently includes tests for:

- Same-origin workbench assets and absence of permissive CORS.
- Health, polygon template generation and invalid profile rejection.
- History save/read/regenerate.
- Missing/invalid bearer token, bad origin, unsupported method and unsafe bind rejection.
- Request body size, strict JSON and revision conflicts.
- Audit chain integrity and tamper detection.
- FeatureHistory edit, suppression/restoration, undo/redo, reorder and branch/fork/merge.
- Structured branch merge conflict handling.
- JavaScript syntax validation without external dependencies.

### Browser E2E tests

`e2e/test_cad_generator_browser.py` includes nine named Chromium journeys:

1. Workbench startup, no runtime errors and edit-control gating.
2. Parameter edit/add/remove and explicit cascade.
3. Stale writer conflict without overwrite.
4. Feature parameter rendering as text rather than HTML.
5. Suppression cascade confirmation and dependency-order restore.
6. Undo/redo persistence across reload and redo clearing after a new edit.
7. Dependency-safe presentation reorder.
8. FeatureHistory branch fork and merge.
9. Branch merge conflict presentation.

The E2E file installs/launches Playwright Chromium. This inventory does not establish Firefox/WebKit, mobile-device, screen-reader or WCAG 2.2 AA acceptance.

## 7. Control Center capability gap map

| Proposed Control Center area | Existing implementation found | WP-15 implication |
|---|---|---|
| Shared application shell/navigation | None in inspected source tree | Build once after route/API inventory and IA acceptance |
| Overview/system health | CAD `/health` only | Needs platform health aggregation; do not reuse CAD health as platform health |
| Workspace/projects | CAD history/revision/branch persistence only | Needs platform-level workspace/project contract |
| Modules catalogue | ModuleRegistry exists in backend; no UI catalogue found | Needs read-only, permission-aware catalogue API and UI |
| Tools catalogue | No unified UI found | Must map to real registered tools and authorization |
| Functions catalogue | Backend operation declarations exist; no UI found | Derive from actual module/function metadata, not static invented entries |
| Unified settings | No settings UI/schema registry found | Requires typed settings ownership, effective values, validation, audit and rollback contracts |
| Jobs/execution centre | CAD regenerate action/result only | Requires runtime job lifecycle API and cancellation evidence |
| Diagnostics | CAD health and local result/error display only | Requires platform diagnostic source aggregation |
| Activity/audit | CAD API audit log exists; no global audit UI found | Needs safe, redacted, user-visible platform audit query contract |
| CAD workbench | Implemented | Reuse through route/client navigation under the shell; do not iframe because the existing host sends `X-Frame-Options: DENY` and CSP `frame-ancestors 'none'`. Preserve current API and user journeys. |
| Mechanics workbench | No browser workbench found in inspected source | Planned until actual UI/API inventory identifies one |
| Physics workbench | No browser workbench found in inspected source | Planned until actual UI/API inventory identifies one |
| Hardware workbench | No browser workbench found in inspected source | Planned until actual UI/API inventory identifies one |
| Accessibility/responsive shell | CAD has responsive CSS and some keyboard interactions | Shared shell still needs keyboard, screen-reader, contrast, reduced-motion and viewport acceptance |

## 8. Canonical reuse decisions

1. Keep `cad_generator.html/css/js` as the specialist CAD workbench; do not rewrite it as a second independent CAD UI.
2. Preserve the loopback-only, dynamic-port API model. Do not introduce a fixed port or public bind to support the Control Center.
3. Reuse existing FeatureHistory revision, conflict, branch and merge service contracts; do not invent a second project/history store.
4. Keep backend validation authoritative; browser previews and status labels are not engineering certification.
5. Reuse existing API audit records only after defining a safe query/export contract and redaction policy; do not expose the SQLite store directly to the browser.
6. Treat Modules/Tools/Functions as source-backed catalogues with real availability, maturity, permissions and evidence. No decorative/inert launch controls.

## 9. Remaining WP-15A evidence and limitations

- The inventory covers the canonical UI and its known API/tests in the inspected branch. It is not a complete inventory of every possible local developer tool or future desktop client.
- The source ref's live commit SHA should be refreshed from GitHub before implementation work is based on this document.
- No user-journey usability study or IA acceptance is claimed.
- No shared Control Center implementation is claimed.
- No platform-wide API, settings or job centre is claimed.
- No completion percentage is assigned; there is no approved UI requirement denominator yet.

## 10. Next dependency-ready work

1. Review and accept this source-backed inventory.
2. WP-15B: validate navigation and representative user journeys against actual API/permission contracts.
3. In parallel, define missing read-only platform APIs for capability catalogue, system health, jobs and audit, with explicit unavailable/UNKNOWN states.
4. WP-15C: implement shared shell and design tokens as a thin host for existing workbenches; keep CAD specialist UI functional and preserve its loopback security model.
5. Add shell-level browser E2E and accessibility tests before adding more feature panels.
