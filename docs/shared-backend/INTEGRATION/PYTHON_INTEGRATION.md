# Python Integration

## Ownership

Python remains the Engineering domain backend.

## Preserve

- Existing CAD Generator API and contracts.
- Existing local bearer-token and workspace boundaries.
- SQLite persistence, artifacts, and audit behavior.
- Dynamic port behavior and loopback-only defaults.

## Request correlation

- Accept `X-Request-ID` only when it matches the shared schema at `schemas/shared/request-id.schema.json`.
- Generate a UUID for missing or malformed IDs.
- Return the effective ID in the response header and existing JSON diagnostic field.
- Do not treat a request ID as an authentication token or authorization claim.

## Assessment before changes

Inspect server lifecycle, request parsing, threading/concurrency, request limits, authentication, persistence, and existing tests. Do not replace the HTTP framework solely for architectural uniformity.

The current CAD Generator API is a local host service, not a remotely reachable Engineering gateway. Do not widen its bind address or forward Calendar credentials to it. Any remote bridge requires an independently reviewed threat model and explicit runtime endpoint discovery.

## Verification

CAD API regression, authentication/authorization, workspace isolation, SQLite concurrency, malformed input, health/readiness, correlation behavior, and contract tests.
