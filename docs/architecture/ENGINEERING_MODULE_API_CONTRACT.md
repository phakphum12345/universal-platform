# Engineering Module API Contract

**Status:** PROPOSED invocation contract; metadata registry subset implemented in PR #39.

## 1. Purpose

Define the stable boundary between UEIC, domain modules, CAD/design tools, solvers, simulation adapters and evidence services. The first implementation deliberately separates module discovery metadata from any future code execution.

## 2. Required operations

The proposed full adapter lifecycle includes:
- describe_module
- validate_inputs
- estimate_resources
- prepare_model
- solve_or_simulate
- validate_outputs
- explain_result
- emit_evidence
- cancel_operation

These invocation operations are not implemented by the metadata registry. Transport and runtime execution remain OPEN pending a reviewed vertical slice.

## 3. Request envelope

The existing Python ModuleRequest envelope includes module_id, operation, inputs, schema_version, request_id, assumptions, source_refs, resource_limits and permissions. It does not yet validate schemas, units, coordinate frames, task identity or cancellation.

## 4. Response envelope

The existing Python ModuleResponse envelope includes request_id, status, outputs, warnings, assumptions, limitations, evidence_refs and error_code. Completion remains distinct from engineering verification. Model/solver versions, uncertainty and execution metadata require a later versioned contract.

## 5. Metadata manifest v1.0

The offline ModuleManifest contract declares:
- Stable module ID, semantic version, domain, license identifier and maturity.
- Operation IDs, input/output MAJOR.MINOR schema versions and execution classification.
- Module dependencies and permission declarations.
- Operation permissions, which must be a subset of module-declared permissions.

Allowed execution classifications in this registry are ANALYSIS, CALCULATION, SIMULATION and EXTERNAL_READ. Physical control, firmware writes and external writes are not accepted classifications.

The ModuleRegistry provides duplicate-ID rejection, operation lookup, deterministic listing/snapshots and dependency ordering. Missing dependencies and dependency cycles fail closed.

## 6. Security and authority

The registry stores metadata only. It does not import, load, invoke or grant permissions to module code. Declared permissions are descriptive metadata, not authorization. No hardware-control, firmware-write, physical-actuation, deployment or external-write operation is enabled.

## 7. Compatibility

Manifest schema version is 1.0. Module versions use MAJOR.MINOR.PATCH semantic version syntax. Operation input/output schema versions use MAJOR.MINOR. Breaking changes require a new major schema version, migration notes and compatibility tests. Unknown fields must not silently change safety-critical meaning.

## 8. Acceptance criteria

- [x] Stable module and operation identifiers and explicit versions.
- [x] License and maturity are explicit.
- [x] Duplicate IDs, duplicate operations and undeclared permissions are rejected.
- [x] Unsupported execution classifications fail closed.
- [x] Missing dependencies and cycles fail closed.
- [x] Registry snapshots are deterministic and JSON-compatible.
- [ ] Runtime loading, invocation, isolation, cancellation and evidence emission remain future work.
