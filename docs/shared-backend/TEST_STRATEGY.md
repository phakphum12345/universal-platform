# Test Strategy

## Test layers
1. Unit: domain services, validators, serializers, repositories.
2. Contract: JSON Schema/OpenAPI compatibility and error envelopes.
3. API: status codes, auth, validation, pagination, request limits.
4. Authorization: organization/workspace isolation and cross-domain denial.
5. Integration: Flutter-to-Laravel and Flutter-to-Python supported flows.
6. Resilience: timeout, unavailable dependency, retry safety, restart.
7. Data: migrations, transaction behavior, backup and restore.
8. Security: token handling, secret leakage, injection, network binding.

## Shared error-envelope acceptance

- Validate the canonical schema at `schemas/shared/error-envelope.schema.json` against the JSON Schema 2020-12 dialect.
- For each adopted endpoint, assert the HTTP status, stable `error.code`, safe `error.message`, and correlation ID/header agreement.
- Preserve domain-specific error extensions only when they are safe, bounded and documented.
- Keep legacy Laravel validation responses unchanged until a separately versioned migration is approved and tested.
- The Universal Platform Python API regression currently covers 401 unauthorized and 404 missing-route responses. It does not establish Laravel adoption or full cross-service conformance.

## Evidence rules

Record repository, commit SHA, workflow/run ID, job, test command, and conclusion. PASS requires a completed successful check on the exact PR head or a documented equivalent. FAIL means a completed failing check. SKIPPED means not run. UNKNOWN means evidence is absent, queued, stale, or inconclusive. Never promote SKIPPED/UNKNOWN to PASS.
