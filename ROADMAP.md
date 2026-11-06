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

PRs #32–#38 are complete and merged on `docs/phase-0-complete-requirements`: generalized coordinates (#32), generated joint constraints (#33), numerical constraint Jacobian (#34), geometry-aware loop evaluation (#35), fixed-body-pose coordinate fitting (#36), spatial local mobility (#37), and cross-discipline reference validation (#38). Their exact merge commits and post-merge check runs are recorded in the engineering phase plan and traceability ledger. PR #39 was used for the offline module metadata registry, not a spatial-joint implementation. The spatial-joint reference/foundation gap is closed by PR #54 at `22bbf1714224095cfd652d6887130d26facef087`. Exact PR-head run #404 (`42193562931`) passed both jobs with 452 tests; post-merge run #405 (`42193654653`) on the exact merge SHA passed both jobs with 452 tests. The suite covers all eight declared joint kinds, generated six-component residuals, finite-difference Jacobian references, local spatial mobility/rank, ground-link reversal and nontrivial joint-frame placement composition. The separate 2D PLANAR mobility formulation remains deferred until an explicit plane-frame/coplanarity contract exists.

PR #49 (profile extrusion) is integrated at `bfc3e6585106c73b29297cbda2ab9ec9d50340db`. PR #52 integrated the through-hole extension and public exports at `1d1628175dafca3f5d4d3d6b5cf01e241ec75afa`. Exact PR-head run #384 (`42191597715`) passed both jobs with 425 tests; post-merge run #385 (`42191666816`) on the exact merge SHA passed both jobs with 425 tests. The PR #50 implementation was ported because its original stacked feature branch was not an ancestor of the integration branch. PR #51's documentation index was restored to the integration line by PR #53 at `1db066915c4993e544b386c0311e332874ef4aed`; PR #53 exact head run #401 (`42192288446`) and post-merge run #402 (`42192465566`) both passed 425 tests.

Next repository-wide work is driven by the capability audit: planar plane-frame mobility; curved CAD profiles and Boolean topology; mesh generation and independent STL/STEP interchange; sketch constraints/feature history; schematic rendering/ERC/circuit simulation; validated solver adapters for additional physics domains; and module runtime/isolation only after separate security and permission contracts. Each item remains PLANNED/PARTIAL until implemented and reference-tested.


PR #35 — Geometry-aware loop-closure evaluation — merged at `223740381b81fc06a292eb90ba0653b27cbe8e7a`; exact PR-head run #283 and post-merge run #284 passed 253 tests each. This validates supplied configurations only and does not imply nonlinear configuration search or physical feasibility.


PR #36 — Geometric loop coordinate fitting — adds local bounded generalized-coordinate fitting for caller-supplied fixed body poses using all generated joint residuals. Body-pose solving and global reachability remain outside this increment.


PR #36 — Geometric loop coordinate fitting — merged at `d7b740fc98d396c130f1c17b3c6487b30b599c2c`; exact PR-head runs #288/#289 and post-merge run #290 passed 258 tests. This is a fixed-body-pose coordinate solver, not a general mechanism configuration solver.


PR #37 — Generated spatial Jacobian mobility — automatically derives local spatial mobility from joint residuals and finite-difference Jacobians, using body-pose tangent variables plus independent joint coordinates with ground pose elimination. PLANAR automatic mobility remains deferred pending a plane-frame contract.


PR #37 — Generated spatial Jacobian mobility — merged at `41d81818385dd82497840ce93ce5aac60e3216da`; exact PR-head runs #293/#294 and post-merge run #295 passed 265 tests each. The generated adapter is SPATIAL-only; PLANAR remains deferred pending explicit plane-frame validation.


PR #38 — Cross-discipline engineering reference validation — add versioned reference data and executable checks for dimensional, mechanics, electrical, thermal, geometry, transform, linear solver, static algebraic simulation, kinematics, material record, assembly, constraint and safety-boundary behavior.


PR #38 — Cross-discipline reference validation pack — merged at `587bd503dad3f6d4f66c99fe08e39e20a65c5265`; exact PR-head run #297 and post-merge run #298 passed 285 tests.
