# Universal Platform — Roadmap

Status: Proposed sequence. No phase is declared complete.

## Phase 0 — Requirements consolidation
- Consolidate goals, constraints, terminology, and command expectations.
- Separate confirmed requirements, proposals, assumptions, and open questions.
- Select the first end-to-end use case.
- Gate: reviewed vision, blueprint, and decision register.

## Phase 1 — Architecture and governance
- Define module boundaries and contracts.
- Define identity, authorization, audit, evidence, error, and version models.
- Create threat model and data-handling policy.
- Gate: architecture review, contract tests, threat-model review.

## Phase 2 — Minimal foundation
- Configuration, logging, diagnostics, versioning, test harness, extension contract.
- Prefer a modular core until evidence justifies distributed services.
- Gate: reproducible local setup, automated tests, documented resource use.

## Phase 3 — Discovery and knowledge
- Authorized repository/document ingestion.
- Parse metadata, code structure, dependencies, and documentation.
- Store provenance and versioned knowledge.
- Gate: source-linked explanations and repeatable indexing tests.

## Phase 4 — System understanding and adaptation
- Map architecture and interfaces.
- Produce impact analysis and change proposals.
- Modify only in isolated workspaces.
- Gate: reproducible build/test evidence, license review, human approval.

## Phase 5 — Runtime and execution
- Permissioned local runners and isolated execution.
- Evaluate containers, VMs, and platform-specific runners.
- Add quotas, timeouts, cancellation, and artifact capture.
- Gate: isolation tests and resource controls.

## Phase 6 — Calculation and engineering labs
- Calculation contracts, units, assumptions, uncertainty.
- Add software, electronics, network, and scientific simulation adapters incrementally.
- Gate: validated reference cases and simulation/measurement distinction.

## Phase 7 — Cross-platform interfaces
- Deliver interfaces for validated workflows.
- Add CLI/API, then Web/Desktop/Mobile as justified.
- Gate: platform test matrix and usability review.

## Phase 8 — Governed capability evolution
- Detect capability gaps and propose tools/modules.
- Prototype in sandbox.
- Human approval for integration, permissions, and deployment.
- Gate: rollback, audit, policy enforcement, no self-escalation.

## Phase 9 — Expand domains
- Add specialist adapters based on demand and validated tools.
- Expand hardware intelligence, digital twins, science, and manufacturing.
- Gate: reviewed scope, specialist validation, provenance, tests.

## Release gates
Every phase requires acceptance criteria, reproducible tests, exact revision identity, PASS/FAIL/SKIPPED/UNKNOWN evidence, applicable security/license review, known limitations, rollback, and human approval.

## Cost policy
Prefer existing hardware, local execution, free/open-source tools, and portable environments. Use hosted infrastructure only when a documented need justifies its cost and operational burden.

## Engineering-core delivery ledger — 2026-11-06

PRs #32–#34 are merged on `docs/phase-0-complete-requirements` with exact-SHA CI evidence. PR #35 adds geometry-aware loop-closure evaluation for caller-supplied configurations; it does not imply a general spatial solver.

Next dependency sequence: PR #36 nonlinear configuration/solver integration; PR #37 integrated mobility and kinematics validation; PR #38 engineering regression and reference validation; PR #39 spatial-joint foundation. Subsequent repository-wide work remains governed by the capability inventory, requirement traceability, explicit owner decisions and per-module reference tests. A roadmap item is not complete merely because it is documented.


PR #35 — Geometry-aware loop-closure evaluation — merged at `223740381b81fc06a292eb90ba0653b27cbe8e7a`; exact PR-head run #283 and post-merge run #284 passed 253 tests each. This validates supplied configurations only and does not imply nonlinear configuration search or physical feasibility.


PR #36 — Geometric loop coordinate fitting — adds local bounded generalized-coordinate fitting for caller-supplied fixed body poses using all generated joint residuals. Body-pose solving and global reachability remain outside this increment.


PR #36 — Geometric loop coordinate fitting — merged at `d7b740fc98d396c130f1c17b3c6487b30b599c2c`; exact PR-head runs #288/#289 and post-merge run #290 passed 258 tests. This is a fixed-body-pose coordinate solver, not a general mechanism configuration solver.


PR #37 — Generated spatial Jacobian mobility — automatically derives local spatial mobility from joint residuals and finite-difference Jacobians, using body-pose tangent variables plus independent joint coordinates with ground pose elimination. PLANAR automatic mobility remains deferred pending a plane-frame contract.
