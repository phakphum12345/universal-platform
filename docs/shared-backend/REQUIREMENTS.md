# Requirements

## Functional
- FR-001: Flutter can call the existing Calendar API.
- FR-002: Flutter can call the existing Engineering API.
- FR-003: Each backend exposes a non-secret health/readiness contract.
- FR-004: Cross-service payloads have versioned schemas.
- FR-005: Errors and request correlation follow documented conventions.
- FR-006: Every operation enforces the owning domain's authorization.
- FR-007: Each backend owns its data and migrations.
- FR-008: Services can run locally without a newly purchased cloud host.
- FR-009: Backup and restore procedures are documented and tested.
- FR-010: Integration and failure-path tests cover the supported flows.

## Non-functional
- NFR-001: No new paid service or billable resource without approval.
- NFR-002: No fixed-port dependency.
- NFR-003: Local APIs remain loopback-only by default.
- NFR-004: Credentials and tokens are not shared across domains implicitly.
- NFR-005: Logs include correlation metadata but exclude secrets.
- NFR-006: One backend being unavailable does not corrupt the other domain.
- NFR-007: Existing API compatibility is preserved unless a migration is approved.
- NFR-008: All release claims are backed by SHA-pinned evidence.

## Acceptance
A requirement is PASS only when implementation and test evidence are linked to the exact tested commit. SKIPPED, UNKNOWN, missing, queued, or stale evidence is not PASS.
