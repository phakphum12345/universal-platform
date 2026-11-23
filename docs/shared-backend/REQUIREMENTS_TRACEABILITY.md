# Requirements Traceability

Statuses are evidence-based. PASS is used only for the narrow behavior that was actually tested; a partial or unverified broader requirement remains UNKNOWN.

| Requirement | Design reference | Verification evidence | Status |
|---|---|---|---|
| FR-001a Flutter Shift Transaction client to Calendar | INTEGRATION/FLUTTER_INTEGRATION.md | Calendar PR #176 merged as `65321c02374b59fc588d8917c3b3c4ddc8d51b0f`; request-ID, HTTPS and client-error correlation tests passed | PASS |
| FR-001b Remaining Flutter Calendar clients | INTEGRATION/FLUTTER_INTEGRATION.md | Organization-admin gateway still requires reconciliation after its active PR is resolved | UNKNOWN |
| FR-002 Flutter to remote Engineering API | INTEGRATION/FLUTTER_INTEGRATION.md; SECURITY.md | Python CAD API remains loopback-only; no approved remote Flutter transport exists or was enabled | SKIPPED |
| FR-003 Health/readiness contract | API_CONTRACT.md | Laravel health/readiness and Python health endpoints exist, but no unified health contract or cross-service probe has been verified | UNKNOWN |
| FR-004 Domain API schemas | API_CONTRACT.md | Shared request-ID JSON Schema exists; domain OpenAPI/schema coverage remains incomplete | UNKNOWN |
| FR-005a Request correlation | API_CONTRACT.md | Python PR #289 merge commit `10b471a1e8a977d5257a3ea62b170301dfea62d6`, schema PR #290 merge commit `2065b8a921dd5cdabbec007edf2af48f95d10761`, and Calendar PR #176 merge commit `65321c02374b59fc588d8917c3b3c4ddc8d51b0f`; Python, Laravel and Flutter regression checks passed | PASS |
| FR-005b Shared error conventions | API_CONTRACT.md | No shared error schema yet; Laravel validation responses remain framework-specific | UNKNOWN |
| FR-006 Domain authorization | SECURITY.md | Google ID-token and local Python bearer boundaries are present; full route-by-route authorization inventory remains | UNKNOWN |
| FR-007 Data ownership/isolation | DATA_ARCHITECTURE.md | Laravel and Python persistence remain separate; full table-level ownership and isolation audit remains | UNKNOWN |
| FR-008 Local deployment | OPERATIONS/LOCAL_DEPLOYMENT.md | No local deployment exercise was run in this workstream | SKIPPED |
| FR-009 Backup/restore | OPERATIONS/BACKUP_RESTORE.md | No backup/restore exercise was run in this workstream | SKIPPED |
| FR-010a Request-correlation and CORS regression tests | TEST_STRATEGY.md | Calendar PR #176 and Python PRs #289/#290 passed their exact-head tests and gates at the recorded merge SHAs | PASS |
| FR-010b Cross-service end-to-end workflow | TEST_STRATEGY.md | No direct Laravel-to-Python call path is part of the approved architecture; no cross-service E2E was executed | SKIPPED |
| NFR-001 No new unapproved paid services | ZERO_COST_POLICY.md | No paid service or cloud infrastructure was added in the reviewed PRs; a full account-level cost audit remains | UNKNOWN |
| NFR-002 Dynamic endpoint configuration | ARCHITECTURE.md | Python launcher uses port 0; legacy Research OS bridge contract still declares default port 8765 and requires separate reconciliation | UNKNOWN |
| NFR-003 Python loopback default | SECURITY.md | Python launcher binds to 127.0.0.1 and does not expose a public listener | PASS |
| NFR-004 Identity boundary | SECURITY.md | Google ID tokens remain Laravel-only; Python uses a separate local bearer token; no credential forwarding was introduced | PASS |

## Status definitions

- PASS: verified by evidence tied to an exact source SHA.
- FAIL: verified failure.
- SKIPPED: intentionally not executed or outside the approved current scope.
- UNKNOWN: insufficient, stale, queued, or missing evidence.

Documentation alone never proves implementation status.
