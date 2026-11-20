# Engineering Failure Modes and Error Taxonomy

**Status:** PROPOSED cross-cutting contract.

## Purpose
Provide consistent failure reporting across UEIC, domain modules, solvers, CAD adapters, simulation and evidence services. An error must not be converted into a plausible-looking result or a PASS.

## Failure classes
| Class | Examples | Required response |
|---|---|---|
| INPUT_INVALID | Missing field, malformed value, non-finite number | Reject before execution; identify field |
| UNIT_DIMENSION | Incompatible dimensions, unknown unit | Reject; preserve original units and context |
| FRAME_MISMATCH | Unrelated coordinate frames, invalid transform | Block composition; request transform/source |
| PROVENANCE_GAP | Missing source, revision, or lineage | UNKNOWN or blocked according to criticality |
| MODEL_INVALID | Contradictory constraints, invalid geometry, unsupported topology | FAIL if executed criterion fails; otherwise UNKNOWN |
| OUT_OF_DOMAIN | Inputs outside model validity range | Reject or mark CONDITIONAL/UNKNOWN; do not extrapolate silently |
| SOLVER_NUMERICAL | Singular matrix, instability, overflow, non-convergence | FAIL for executed solve; retain diagnostics |
| SOLVER_OPERATIONAL | Timeout, cancellation, resource exhaustion, unavailable binary | ERROR/CANCELLED/UNKNOWN operational state; evidence step not PASS |
| ADAPTER_CONTRACT | Schema mismatch, incompatible version, malformed output | Reject output and record adapter/version |
| EVIDENCE_INTEGRITY | Hash mismatch, missing artifact, stale result | Invalidate dependent evidence |
| GOVERNANCE | Permission denied, approval missing, prohibited action | REJECTED; do not retry with broader privileges |
| EXPORT_INTERCHANGE | Unit/scale loss, unsupported entity, corrupt export | FAIL export validation; retain source model |
| INTEGRATION | API unavailable, incompatible dependency, partial response | PARTIAL/UNKNOWN; preserve completed outputs |
| HUMAN_REVIEW | Required qualified reviewer unavailable | BLOCKED/UNKNOWN; no automatic approval |

## Status separation
- Evidence: PASS, FAIL, SKIPPED, UNKNOWN.
- Operation: ACCEPTED, REJECTED, RUNNING, COMPLETED, CANCELLED, ERROR, PARTIAL.
- A completed operation is not necessarily a passing verification.
- SKIPPED requires a reason and remains non-PASS.
- CONDITIONAL may describe a conclusion dependent on explicit assumptions; it must not be collapsed into PASS.

## Required error envelope
error_code, class, message, affected object/input, source/model/solver/adapter version, retryability, safe remediation, diagnostics/log references, partial outputs, evidence status, and whether downstream evidence was invalidated.

## Recovery
Retry only when the failure is transient and the operation is safe/idempotent. Never retry authorization failures with expanded permissions. Re-run dependent checks after inputs, models, tools or source revisions change. Preserve the original failure record.

## Acceptance
Contract tests cover each class; logs avoid secrets; user-facing messages identify the failed stage; rollback/invalidation is deterministic; no missing evidence is silently promoted.
