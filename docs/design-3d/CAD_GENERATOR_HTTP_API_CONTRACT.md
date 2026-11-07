# CAD Generator Loopback HTTP API Contract v1.0

**Status:** Implemented local transport adapter; exact-head CI pending.  
**Implementation:** `engineering/cad_generator_http_api.py`.  
**Dependency:** `CADGeneratorService`, explicit `SQLiteCADAPIAuditLog`, caller-supplied bearer token.  
**Transport:** HTTP over IPv4 loopback only; no public listener, TLS endpoint, CORS permission or remote access.

## 1. Startup and authority

Importing the module opens no socket. A caller must explicitly create the server and call `serve_forever()`. The only accepted bind host is exactly `127.0.0.1`; wildcard, LAN, IPv6-any and public binds are rejected. Port 0 is the default and asks the OS for a dynamic available port. A caller may select a fixed port only when explicitly requested.

The server is single-threaded and handles one request at a time. It does not launch subprocesses, run user code, load plugins, call external networks, operate hardware, flash firmware, release manufacturing or deploy software.

The local API is not a remote service. Do not use port forwarding, SSH tunnels, reverse proxies, container publishing or firewall rules to expose it. A future remote transport requires a separate security review and explicit authorization.

## 2. Construction

```python
from secrets import token_urlsafe
from universal_platform.engineering import (
    CADGeneratorService,
    SQLiteCADAPIAuditLog,
    create_cad_generator_http_server,
)

token = token_urlsafe(32)  # keep secret; do not log or persist in source control
audit = SQLiteCADAPIAuditLog("data/cad-api-audit.sqlite3")
server = create_cad_generator_http_server(
    generator_service,
    audit_log=audit,
    bearer_token=token,
    host="127.0.0.1",
    port=0,
)
print(server.server_port)  # OS-selected local port
server.serve_forever()     # explicit start; no implicit listener
```

The history store, artifact cache and audit database paths are separate explicit filesystem inputs. No default global data path or port is created by the API.

The bearer token must contain at least 32 UTF-8 bytes. Send it only in `Authorization: Bearer <token>`; query-string tokens, cookies and Basic authentication are not accepted. Keep it out of logs and client-visible URLs.

## 3. Common request controls

- IPv4 loopback peer address must be exactly `127.0.0.1`.
- `Host` must match `127.0.0.1:<bound-port>`.
- If `Origin` is present, it must match the same local origin; no CORS headers are emitted.
- Every route requires a valid bearer token, including health.
- JSON requests require `Content-Type: application/json`, a valid `Content-Length`, strict UTF-8 JSON, unique object keys and finite numbers.
- Default body limit is 1 MiB; configurable maximum is 16 MiB.
- Per-connection socket timeout defaults to 5 seconds and is bounded to 30 seconds.
- Only GET and POST are supported. Responses set `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` and `Connection: close`.
- Errors use a structured `error.code` / `error.message` response and a generated `request_id`.

No rate limiting, TLS, browser session management or remote authentication is claimed in this local-only version. A local process with access to the bearer token and database files remains inside the local trust boundary.

## 4. Routes

All routes require authorization.

### `GET /health`

Returns service readiness and API version. It does not expose file paths, database content or secrets.

### `POST /v1/histories`

Request fields are exactly:

```json
{
  "expected_revision": 0,
  "history": {
    "history_id": "history.example"
  }
}
```

The complete `history` object must satisfy `FeatureHistory.from_dict`. The API identifier subset is lowercase letters, digits, dot, underscore and hyphen. `expected_revision=0` creates a new history; subsequent writes must supply the current revision number. This is append-only optimistic concurrency, not overwrite.

Returns HTTP 201 with history ID, revision number, parent digest, content digest and creation timestamp.

### `GET /v1/histories/{history_id}/revisions`

Returns the ordered immutable revision numbers.

### `GET /v1/histories/{history_id}?revision={n}`

Returns the exact revision envelope and source FeatureHistory snapshot. Omitting `revision` selects the current head.

### `POST /v1/histories/{history_id}/regenerate`

Request body is an empty JSON object or `{"revision": 1}`. Omission selects the current head. An explicit revision never falls back to a different revision.

Returns the `CADGeneratorRun` provenance envelope. HTTP 200 means regeneration succeeded; HTTP 422 means the selected revision failed regeneration and the body contains its bounded failure result.

There are no DELETE, PUT, PATCH, arbitrary file, shell, plugin, firmware or physical-device routes.

## 5. Error mapping

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `INVALID_REQUEST`, `INVALID_JSON`, `INVALID_FIELDS`, `INVALID_REVISION` | Invalid input or model |
| 401 | `UNAUTHORIZED` | Missing or invalid bearer token |
| 403 | `LOCAL_ONLY` | Peer, Host or Origin is outside the local origin |
| 404 | `NOT_FOUND` | Unknown route/history/revision |
| 405 | `METHOD_NOT_ALLOWED` | Method is not GET or POST |
| 409 | `REVISION_CONFLICT` | Expected revision is stale |
| 411 / 413 / 415 | `LENGTH_REQUIRED` / `REQUEST_TOO_LARGE` / `UNSUPPORTED_MEDIA_TYPE` | Request transport validation failed |
| 422 | Regeneration result | Engineering regeneration did not succeed |
| 500 | `STORAGE_INTEGRITY_ERROR` / `INTERNAL_ERROR` | Stored data integrity or unexpected internal failure |
| 503 | `AUDIT_UNAVAILABLE` | Audit could not be recorded; request is not dispatched if the start record fails |

Unexpected exceptions are not returned with stack traces or internal file paths.

## 6. Audit evidence

Every handled request appends a `REQUEST_RECEIVED` record before dispatch and a `REQUEST_COMPLETED` record after dispatch. If the initial record cannot be written, the operation is not executed. Completion-record failure returns 503 and leaves the received event as evidence that the operation may have started.

Audit rows contain request ID, timestamp, method, path without query, peer address, event type, status and outcome. They never contain request bodies, Authorization headers, bearer tokens or model payloads. The local SQLite audit log uses an append-only sequence and SHA-256 previous-event chain; `verify()` checks the chain.

This hash chain detects accidental/tampered records when the attacker cannot rewrite the entire database consistently. It is not a keyed signature, remote witness, tamper-proof ledger or protection against a local attacker who can rewrite the complete file.

## 7. Acceptance criteria

- [x] Explicit startup only; import has no network side effects.
- [x] Reject every non-loopback bind and enforce loopback peer/Host/Origin.
- [x] Require a high-entropy bearer token for all routes.
- [x] Dynamic port by default; bounded body size and request timeout.
- [x] Strict JSON parsing, route allow-list and structured errors.
- [x] Append-only local audit chain with integrity verification.
- [x] Save, read, list and regenerate an exact FeatureHistory revision.
- [ ] Exact PR-head CI and post-merge CI pass before promotion.
- [ ] Production-grade rate limiting, TLS, remote authentication, browser session controls and external audit witness remain out of scope.
