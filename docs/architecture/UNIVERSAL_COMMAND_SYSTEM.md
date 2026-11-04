# Universal Command System

**Status:** PROPOSED architecture contract; command syntax OPEN.

## Purpose
Provide one consistent way to express goals and coordinate platform capabilities across Web, Desktop, Mobile, CLI, API, and automation without binding the platform to one interface.

## Canonical task envelope
A task record should carry:
- task_id and schema_version
- original_request and normalized_intent
- requester / acting identity and authorization context
- scope, target resources, and exclusions
- inputs, attachments, source references, and provenance
- constraints: time, budget, compute, network, privacy, platform
- plan and dependency graph
- risk classification and required approvals
- expected outputs and acceptance criteria
- execution records, tool versions, logs, evidence, and final status

## Lifecycle
1. Capture request without losing original wording.
2. Parse intent and entities; identify ambiguity.
3. Ask only essential clarifying questions.
4. Normalize into a typed task.
5. Discover capabilities and prerequisites.
6. Draft a plan with alternatives, costs, risks, and boundaries.
7. Validate permissions, policy, resources, and dependencies.
8. Preview the exact actions and expected effects.
9. Obtain scoped human authorization when required.
10. Execute in an isolated, observable environment.
11. Verify outputs against acceptance criteria.
12. Report results, evidence, limitations, and rollback options.
13. Record reusable learning without retaining secrets or unauthorized data.

## State model
PROPOSED → NEEDS_INPUT → READY → AWAITING_APPROVAL → RUNNING → VERIFYING → SUCCEEDED / FAILED / PARTIAL / CANCELLED. SKIPPED and UNKNOWN apply to individual steps/evidence. State transitions must be recorded and validated.

## Plan-step contract
Each step includes step_id, capability_id/version, purpose, inputs, outputs, dependencies, read/write scope, permission requirement, risk, timeout/resource budget, retry policy, idempotency, verification, and compensation/rollback strategy.

## Command surfaces
The same task model may be exposed through natural language, structured forms, CLI, API, SDK, and automation. Exact syntax, aliases, localization, and voice interaction are OPEN decisions.

## Authority model
- Default to read-only.
- Separate planning from execution.
- No implicit permission inheritance across unrelated targets.
- Approval must identify the action, target, scope, duration, and expected side effects.
- Revocation and cancellation must be available where technically possible.
- High-impact actions require stronger approval and independent verification.

## Failure handling
Classify invalid input, ambiguity, missing capability, permission denial, unavailable dependency, resource exhaustion, timeout, tool failure, partial completion, and verification failure. Preserve logs and partial outputs; never convert missing evidence into success.

## Acceptance criteria
- A single task can be represented independent of UI.
- A plan is inspectable before execution.
- Unauthorized writes are blocked.
- Cancellation and failure are recorded.
- Every terminal result includes evidence and unresolved items.
- Replay/reproduction is possible when inputs and environment permit.
