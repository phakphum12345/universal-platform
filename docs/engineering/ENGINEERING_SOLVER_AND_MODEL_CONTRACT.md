# Engineering Solver and Model Contract

**Status:** PROPOSED

## 1. Purpose

Standardize how UEIC invokes analytical, symbolic, numerical, optimization and simulation engines without coupling the platform to a single vendor or solver.

## 2. Solver declaration

A solver adapter declares identifier/version, vendor/project, license, supported model types, input schema, output schema, units, coordinate conventions, supported precision, compute requirements, determinism, timeout, cancellation, resource limits, supported platforms, security boundary and evidence output.

## 3. Model declaration

A model declares physical/domain meaning, variables, parameters, equations or governing rules, constraints, initial/boundary conditions, validity range, assumptions, source references, calibration data, uncertainty and expected outputs.

## 4. Invocation lifecycle

VALIDATE_INPUT -> RESOLVE_DEPENDENCIES -> CHECK_UNITS -> CHECK_VALIDITY -> ESTIMATE_RESOURCES -> AUTHORIZE -> EXECUTE_IN_ISOLATION -> VALIDATE_OUTPUT -> CROSS_CHECK -> RECORD_EVIDENCE.

A skipped or unavailable stage must be visible. Solver output is untrusted until schema, units, numerical health and domain checks pass.

## 5. Error classes

INVALID_INPUT, DIMENSION_MISMATCH, OUT_OF_VALIDITY_RANGE, UNSUPPORTED_MODEL, MISSING_PARAMETER, RESOURCE_LIMIT, TIMEOUT, CANCELLED, NON_CONVERGENCE, NUMERICAL_INSTABILITY, SOLVER_FAILURE, OUTPUT_VALIDATION_FAILURE, CONFLICTING_RESULT, UNKNOWN.

## 6. Reproducibility

Record exact input snapshot, model and solver versions, configuration, random seed where relevant, environment, hardware/compute profile, logs, outputs and validation steps. If exact determinism is not available, state the reproducibility limits.

## 7. Security

Run untrusted or third-party solvers in least-privilege isolation. No solver may obtain hardware-control privileges through this interface. External network access and file writes require explicit adapter policy and scoped approval.

## 8. Acceptance criteria

- [ ] Solver adapters are replaceable.
- [ ] Input/output schemas are versioned.
- [ ] Units and coordinate frames are checked.
- [ ] Resource limits, timeout and cancellation are enforced.
- [ ] Non-convergence and invalid outputs cannot be reported as PASS.
- [ ] Reproduction metadata is emitted.
