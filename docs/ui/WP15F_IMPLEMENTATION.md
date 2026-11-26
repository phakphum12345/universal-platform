# WP-15F — Unified Settings (first implementation slice)

**Status:** PARTIAL — authenticated local user-preference API and durable SQLite storage are proposed in this PR. This is not the complete WP-15F settings system and does not establish owner acceptance.

## Scope delivered by this slice

- A fixed, typed allowlist for non-secret user preferences: theme, density and reduced motion.
- Effective values expose whether each value comes from the default or the user scope.
- SQLite persistence uses schema versioning, WAL, full synchronous writes and compare-and-swap revisions.
- Each changed revision stores an immutable snapshot and an append-only hash-chained audit event containing changed key names only; values are not copied into the settings audit event.
- Authenticated GET /v1/settings and revision-checked PUT /v1/settings are hosted by the existing loopback-only CAD API.
- The local launcher creates the settings database in the existing per-user data directory.
- Unknown keys, other scopes and secret-like keys are rejected. Validation errors do not echo rejected values.

## Explicit exclusions

- No credentials, tokens, passwords, provider secrets or secret retrieval API. A dedicated OS-backed secret store and threat model are required before those settings can be supported.
- No workspace, project, host-policy or organization scope.
- No multi-user identity or authorization model beyond the existing local bearer-token boundary.
- No settings migration framework beyond SQLite user_version schema guard.
- No explicit restore/rollback endpoint or UI in this slice; a later WP-15F increment must design and test history restoration.
- No UI wiring or owner acceptance is claimed by this backend-only increment.

## API contract

GET /v1/settings returns scope, revision, effective values, per-key sources, and updated_at.

PUT /v1/settings accepts exactly expected_revision and a non-empty values object. Writes merge supplied allowlisted keys into the current user settings. A stale revision returns HTTP 409. Repeating an identical value is a no-op and does not create a new revision.

All routes inherit the existing loopback peer/Host/Origin checks, bearer authentication, request correlation and request audit lifecycle. The settings-specific audit chain records changed key names and revision metadata, never setting values.

## Validation required

- Store tests: defaults, type/range validation, scope rejection, persistence, stale writer rejection, audit integrity, secret rejection and newer-schema fail-closed behavior.
- HTTP tests: authenticated read/write, request-ID agreement, stale revision conflict, unsupported methods/query parameters, and no secret-value reflection.
- Exact PR-head CI and post-merge integration CI remain separate gates.
- WP-15F remains PARTIAL until settings UI, owner/scope governance, secret management, migration/rollback, accessibility and owner acceptance are implemented and verified.
