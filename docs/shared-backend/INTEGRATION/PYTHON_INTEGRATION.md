# Python Integration

## Ownership
Python remains the Engineering domain backend.

## Preserve
- Existing CAD Generator API and contracts.
- Existing bearer-token and workspace boundaries.
- SQLite persistence, artifacts, and audit behavior.
- Dynamic port behavior and loopback-only defaults.

## Assessment before changes
Inspect server lifecycle, request parsing, threading/concurrency, request limits, authentication, persistence, and existing tests. Do not replace the HTTP framework solely for architectural uniformity.

## Verification
CAD API regression, authentication/authorization, workspace isolation, SQLite concurrency, malformed input, health/readiness, and contract tests.
