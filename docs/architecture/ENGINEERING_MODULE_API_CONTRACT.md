# Engineering Module API Contract

**Status:** PROPOSED logical contract; no implementation implied

## 1. Purpose

Define the stable boundary between UEIC, domain modules, CAD/design tools, solvers, simulation adapters and evidence services.

## 2. Required operations

- describe_module
- validate_inputs
- estimate_resources
- prepare_model
- solve_or_simulate
- validate_outputs
- explain_result
- emit_evidence
- cancel_operation

The actual transport and serialization format remain OPEN until a vertical slice is tested.

## 3. Request envelope

Include request_id, task_id, module_id/version, operation, schema_version, inputs, units, coordinate_frames, assumptions, constraints, source_refs, requested_precision, resource_limits, permissions and cancellation context.

## 4. Response envelope

Include request_id, status, outputs, units, model/solver versions, warnings, assumptions, uncertainty, limitations, source_lineage, execution_metadata, evidence_refs and error details.

## 5. Status semantics

Use PASS / FAIL / SKIPPED / UNKNOWN for evidence checks. Operational responses may use ACCEPTED / REJECTED / RUNNING / COMPLETED / CANCELLED / ERROR. Never equate COMPLETED with engineering PASS.

## 6. Security and authority

Modules receive least privilege. A calculation module cannot acquire hardware-control permissions. External network, file modification, procurement, fabrication and deployment are separate permission scopes.

## 7. Compatibility

Contracts are versioned. Breaking changes require a new major schema version, migration notes and compatibility tests. Unknown fields must not silently change safety-critical meaning.

## 8. Acceptance criteria

- [ ] Module operations and schemas are versioned.
- [ ] Permissions are operation-specific.
- [ ] Errors and cancellation are explicit.
- [ ] Result lineage is preserved.
- [ ] Completion and verification are separate.


## 6. Implemented metadata registry subset (PR #39)

The implementation adds immutable `ModuleManifest` and `ModuleOperation` records plus an in-memory `ModuleRegistry`. It validates stable IDs, semantic module versions, MAJOR.MINOR operation schema versions, explicit license/maturity, operation permission subsets and a restricted execution classification. Dependency ordering is deterministic and fails closed for missing dependencies or cycles. Snapshots are JSON-compatible and sorted.

This is a metadata registry only. It does not load or invoke code, enforce permissions, isolate processes, or provide a runtime plugin system.
