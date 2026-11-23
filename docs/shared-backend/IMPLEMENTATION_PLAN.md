# End-to-End Implementation Plan

## Phase 0 — Repository reconciliation
- [ ] Refresh main SHA, open PRs, branch protection, and workflow inventory in both repositories.
- [ ] Inventory Flutter API clients, Laravel routes/middleware/migrations, Python routes/stores/auth, and current deployment entrypoints.
- [ ] Classify each capability EXISTING / PARTIAL / MISSING / UNKNOWN with file and test evidence.
- [ ] Identify existing workflows and avoid duplicate automation.

## Phase 1 — Contract baseline
- [ ] Map existing request/response formats.
- [ ] Define only the minimum cross-domain schemas required by a real use case.
- [ ] Specify versioning, errors, correlation, timeout, and compatibility.
- [ ] Add schema/contract tests.

## Phase 2 — Python boundary
- [ ] Audit current HTTP server lifecycle, threading, concurrency, limits, and authentication.
- [ ] Preserve current CAD routes and loopback protections.
- [ ] Add only justified health/readiness and contract endpoints.
- [ ] Evaluate framework changes only with evidence.

## Phase 3 — Laravel boundary
- [ ] Audit existing API v1 and middleware.
- [ ] Preserve Google identity and organization authorization.
- [ ] Add adapters only for approved use cases.
- [ ] Verify regression and contract tests.

## Phase 4 — Flutter clients
- [ ] Inventory and reuse existing Dart clients.
- [ ] Define typed clients per domain.
- [ ] Support runtime endpoint configuration, timeout, and explicit error mapping.
- [ ] Keep secrets out of client binaries.

## Phase 5 — Integration and security
- [ ] Contract, unit, API, authorization, isolation, and failure-path tests.
- [ ] Verify no implicit token exchange.
- [ ] Verify service independence and recovery.
- [ ] Pin all evidence to exact head SHA.

## Phase 6 — Local operations
- [ ] Document start/stop and endpoint discovery.
- [ ] Test backup and restore.
- [ ] Verify loopback-only defaults.
- [ ] Audit workflows and external dependencies for unexpected costs.

## Gates
No implementation phase starts until Phase 0 evidence is reviewed. No production or destructive change without explicit approval. No merge based solely on documentation or skipped checks.
