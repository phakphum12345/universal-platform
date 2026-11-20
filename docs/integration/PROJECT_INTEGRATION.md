# Existing Project Integration Policy

**Status:** CONFIRMED: no automatic merge or integration. Assessment required first.

## Integration levels
0. Reference only: link and describe an independent project.
1. Read-only discovery: inspect public/authorized docs, source, issues, and tests.
2. Data exchange: explicit schemas and export/import contracts.
3. Adapter/plugin: isolated capability with versioned interface.
4. Workflow integration: coordinated tasks with scoped permissions.
5. Shared library/service: explicit ownership, compatibility, security, and release policy.
6. Fork/merge/consolidation: exceptional decision requiring owner approval and migration plan.

## Assessment checklist
Purpose and ownership; current status and exact SHA; license; security posture; dependencies; architecture; API/data contracts; tests and CI evidence; deployment/runtime assumptions; costs; secrets and personal data; maintenance burden; overlap; risks; rollback; and exit strategy.

## Candidate projects (not approved integrations)
### Development Control Platform (DCP)
Potential fit: repository inspection, PR review, evidence, gates, checkpoints, and audit workflows. Its existing read-only/public-API boundary and PASS/FAIL/SKIPPED/UNKNOWN evidence model should be preserved unless separately reviewed and approved.

### Research OS / Drive-letter
Potential fit: research and knowledge workflows. The owner clarified that the `v3` directory is the current main UI; do not assume the `research-os` directory is the main UI. Inspect the current repository state and exact SHA before any integration proposal.

## Adapter contract
Adapter identity/version; capability declarations; input/output schemas; permissions; data classification; network behavior; resource limits; failure modes; evidence format; health status; compatibility; tests; and deactivation procedure.

## Acceptance criteria
- Integration level is explicit.
- Source project remains unchanged during assessment.
- License/security/ownership are reviewed.
- Data flow and permission boundaries are documented.
- Integration is reversible and has an owner-approved plan.
