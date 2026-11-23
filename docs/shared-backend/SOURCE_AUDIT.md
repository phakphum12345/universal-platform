# Verified Source Audit — Laravel, Python and Flutter API Boundaries

**Audit date:** 2026-11-24  
**Purpose:** Record what exists in source code, distinguish it from the proposed architecture, and prevent accidental duplication or unsafe exposure.

## Repository baselines

These are the source snapshots inspected before the implementation changes in this workstream:

| Repository | Branch | SHA observed |
|---|---|---|
| `phakphum12345/universal-platform` | `main` | `2065b8a921dd5cdabbec007edf2af48f95d10761` |
| `phakphum12345/phakphum-calendar` | `main` | `dcb51b6ad7db3540eea7152949556465ea67256c` |

Calendar PR #176 and PR #177 have since merged to Calendar `main`; the current main SHA is `8be364f2a37dbfcd4e15bc7ea016cf4c67db4751`. Their resulting implementation is recorded below.

## 1. Laravel Calendar API

### Routing and ownership

The Laravel API is registered under `/api/v1` and remains the authoritative owner of Calendar, organization membership, shift-transaction, push-subscription and Calendar persistence behavior.

The inspected route surface includes:

- Public operational endpoints: `GET /api/v1/health` and `GET /api/v1/ready`.
- Client diagnostics: `POST /api/v1/diagnostics/client-errors`, throttled separately.
- Google-account authenticated endpoints: `/me`, organizations, join requests, organization members and membership audit, push subscriptions, shift policies, and shift transactions.
- The authenticated route group uses Google-account middleware and request throttling. It does not share the Python CAD bearer token.

### Authentication and request correlation

- `AuthenticateGoogleAccount` validates the Google ID-token bearer credential for protected routes.
- `AttachRequestId` is prepended to the Laravel API middleware group.
- The middleware accepts `X-Request-ID` only when it matches `[A-Za-z0-9._-]{8,128}`; otherwise it generates a UUID.
- The effective ID is stored on the request and returned in the `X-Request-ID` response header.
- Health and client-diagnostics responses also include `request_id` in their JSON body.
- Calendar PR #176 added regression coverage for valid correlation on auth failures and replacement of malformed IDs.

### Browser CORS

At the audited source SHA, allowed methods were `GET`, `POST`, `PUT`, and `OPTIONS`. The organization-admin gateway uses `PATCH` and `DELETE`, so those browser preflights were not covered by that baseline.

Calendar PR #176 is now merged and:

- Adds `PATCH` and `DELETE` to the CORS method allowlist.
- Keeps `X-Request-ID` in allowed request headers and exposed response headers.
- Adds tests for PATCH/DELETE preflight and browser access to the correlation response header.
- Preserves explicit origin allowlisting and bearer authentication; CORS does not grant authorization.

## 2. Python Engineering API

### What the existing service is

The inspected implementation is the **CAD Generator HTTP API**, not a general-purpose remote Engineering gateway.

Its local launcher:

- Binds to IPv4 loopback `127.0.0.1` only.
- Defaults to port `0`, allowing the operating system to select an available port.
- Generates a high-entropy bearer token when one is not supplied through `UP_CAD_BEARER_TOKEN`.
- Stores per-user SQLite data for feature history, feature artifacts, API audit records and workspaces.
- Does not start a socket merely by importing the launcher module.

The request handler validates the local origin and requires bearer authentication for non-static API routes. Static assets are served by the same local host.

### Existing route groups

The inspected route dispatcher includes:

- `GET /health`.
- Read-only capability catalogue routes: `GET /v1/modules`, `GET /v1/modules/{module_id}`, `GET /v1/functions`, and `GET /v1/tools`.
- `GET /v1/platform/status`, which reports unavailable or unwired components as `UNKNOWN` rather than claiming platform-wide readiness.
- Workspace collection and item routes under `/v1/workspaces`.
- Polygon extrusion template creation at `POST /v1/templates/polygon-extrusion`.
- Feature-history creation, revision navigation, branches and merge operations under `/v1/histories`.

The built-in physics module bridge provides registry metadata. The platform status response explicitly reports that the ModuleRuntime, jobs service, diagnostics aggregator and audit browser are not wired into this HTTP host. Catalogue registration does not imply executable remote functions.

### Request correlation

The Python API accepts bounded request IDs matching `[A-Za-z0-9._-]{8,128}`, generates a UUID for missing or malformed values, writes the ID into audit events and JSON bodies, and returns it in the response header. This runtime behavior was merged in Universal Platform PR #289. The canonical schema is `schemas/shared/request-id.schema.json`.

### Boundary decision

Do not bind this service to `0.0.0.0`, a LAN address, a Tailscale address, or a public host as part of shared-backend work. Remote access requires a separately reviewed transport, identity, authorization and threat model. No such bridge is implied by the current API.

## 3. Flutter clients and adjacent integrations

### Calendar API clients

- `ShiftTransactionApiClient` uses `ORGANIZATION_API_BASE_URL` and a Google ID-token provider for Calendar API calls.
- Calendar PR #176 is merged: the shift-transaction client generates a distinct opaque ID per request, sends `X-Request-ID`, and retains the response correlation ID on API exceptions.
- The same client requires HTTPS for non-loopback API origins. HTTP is allowed only for `localhost`, `127.0.0.1`, and `::1` local development.
- `HttpOrganizationAdminGateway` uses the same configured API origin and Google ID-token authentication. Its membership operations include `PATCH` and `DELETE`; reconcile its request-correlation behavior after the separate active PR that changes this gateway is resolved.
- The Calendar API CORS configuration now permits the correlation header and membership write preflights, while authorization remains enforced by Laravel.

### Other HTTP integrations

- `GoogleApiClient` is a transport wrapper for external Google APIs, not a Calendar or Engineering backend client.
- `ResearchOsCalendarBridgeContract` is a contract-only helper with no network I/O or server implementation. It declares loopback host `127.0.0.1` and a default port of `8765`. Treat that as a legacy contract detail, not as the shared backend port or a fixed-port requirement. Any future bridge must use explicit runtime discovery and a separately approved security boundary.

## 4. Confirmed architecture boundaries

| Concern | Calendar / Laravel | Engineering / Python |
|---|---|---|
| Domain ownership | Calendar, organizations, shift transactions | CAD generation, feature history, workspaces, engineering modules |
| Authentication | Google ID-token bearer | Local CAD bearer token |
| Persistence | Laravel-owned database and migrations | Per-user SQLite stores |
| Network default | Configured HTTPS API origin; local development may use loopback | Loopback-only local host |
| Port policy | Configured origin; no shared fixed port | OS-selected port by default |
| Correlation | `X-Request-ID` middleware and Flutter client | `X-Request-ID` validation and response echo |

Do not merge these databases, credentials, migrations, or authorization systems. The shared layer is limited to agreed metadata, schemas, error conventions and integration documentation.

## 5. Verified gaps and next implementation order

1. Reconcile request-correlation behavior in the organization-admin gateway after its active PR is resolved.
2. Define a shared error schema for new integrations while preserving Laravel's existing validation response format.
3. Inventory and document domain-owned OpenAPI contracts; do not claim a generated specification is authoritative until checked against route behavior and tests.
4. Add client-level contract tests for both APIs using local/mock transports. Do not create a new cloud gateway or shared database.
5. Keep cross-service end-to-end tests limited to actual approved call paths; the current architecture does not require Laravel to call Python.
6. Complete operational evidence for backup, restore, local startup, shutdown, port discovery and audit retention before any production-readiness claim.

## 6. Non-goals for this audit

- No public exposure or deployment.
- No new paid service, managed database, queue, monitoring platform or API gateway.
- No shared database or shared credential.
- No FastAPI migration solely for framework uniformity.
- No deletion or replacement of existing domain APIs.
