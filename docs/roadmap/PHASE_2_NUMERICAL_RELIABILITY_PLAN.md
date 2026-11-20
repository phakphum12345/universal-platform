# Phase 2 — Numerical Reliability and Mechanism Integration Plan

**Status:** PROPOSED IMPLEMENTATION PLAN  
**Planning baseline:** `docs/phase-0-complete-requirements` at `3fc73791f8b954a4965c96856a6e59ed45b52667`  
**Delivery branch:** `docs/phase-2-numerical-reliability-plan`  
**Scope:** Offline numerical analysis and engineering-model validation only  
**Authority:** This plan does not authorize physical actuation, fabrication, production release, or engineering certification.

## 1. Purpose

Phase 2 hardens the existing bounded nonlinear equality-constraint solver before it is reused by broader mechanism, geometry, and multidisciplinary engineering modules. The immediate objective is trustworthy numerical diagnostics and reproducible evidence—not a claim of a general-purpose solver.

The current implementation is a small dense, local Levenberg–Marquardt least-squares method. It estimates a forward finite-difference Jacobian, forms damped normal equations, and uses the existing partial-pivoting linear solver. It supports scalar equality residuals, residual scales and tolerances, optional projected variable bounds, and explicit `CONVERGED` / `NOT_CONVERGED` outcomes.

## 2. Baseline facts and constraints

At the planning baseline:

- The nonlinear solver is implemented in `src/universal_platform/engineering/nonlinear_solver.py`.
- The linear solver is implemented in `src/universal_platform/engineering/linear_solver.py`.
- The public engineering package exports the nonlinear solver contracts.
- Existing tests are in `tests/test_nonlinear_solver.py`.
- The nonlinear solver contract is documented in `docs/engineering/NONLINEAR_CONSTRAINT_SOLVER_CONTRACT.md`.
- The solver/model adapter contract is documented in `docs/engineering/ENGINEERING_SOLVER_AND_MODEL_CONTRACT.md`.
- PR #16 implemented the initial nonlinear equality solver; PR #17 reconciled implementation status and traceability evidence.
- Current limitations include no robust rank or conditioning diagnostics, no exact/analytic Jacobian callback, no sparse solver, no inequality/contact/complementarity, no continuation or branch enumeration, and no global convergence or uniqueness guarantee.

The current integration branch head is recorded above. Any implementation PR must record its actual base SHA and tested head SHA; the planning SHA must not be reused as evidence for later commits.

## 3. Design principles

1. **Evidence before claims:** every PASS is tied to an exact commit SHA, reproducible command, and actual test result.
2. **Fail closed:** malformed, non-finite, singular, rank-deficient, or diagnostically indeterminate inputs must never silently become PASS.
3. **Preserve compatibility:** additive API changes where practical; existing result semantics remain stable unless a separately reviewed breaking change is required.
4. **Separate diagnosis from proof:** rank and condition estimates are numerical indicators, not proof of physical feasibility or uniqueness.
5. **Scaling is explicit:** variable and residual scaling must be represented in the API and reports; no hidden unit inference.
6. **Deterministic core:** dependency-light dense algorithms first; external numerical packages require a separate technology decision.
7. **Adapter boundary:** mechanism-specific equations and physical interpretation remain outside the generic solver.
8. **Offline and non-actuating:** no hardware access, machine control, firmware writes, fabrication, deployment, or autonomous release.

## 4. Phase 2 work packages

### WP-2.1 — Jacobian strategy and validation

**Goal:** Make derivative estimation explicit, testable, and replaceable.

Deliverables:
- Define a Jacobian representation and validation contract (dimensions, finite values, row/column ordering).
- Support the existing forward finite-difference method as the compatibility default.
- Evaluate central finite differences as an opt-in method with a documented extra evaluation cost.
- Add an optional analytic Jacobian callback at the solver boundary; validate shape and finite values before use.
- Keep derivative method and evaluation counts in result diagnostics.
- Document nonsmooth/discontinuous residual limitations and finite-difference step sensitivity.

Acceptance:
- Forward-difference legacy cases remain green.
- Analytic Jacobian and finite-difference results agree on smooth reference systems within declared tolerances.
- Wrong-shaped and non-finite Jacobians fail with a typed solver error.
- Tests include nonlinear scalar, coupled, badly scaled, and near-stationary examples.

### WP-2.2 — Rank and singularity diagnostics

**Goal:** Report whether the local constraint Jacobian appears full rank, deficient, or numerically indeterminate.

Deliverables:
- Introduce a documented rank-estimation method suitable for the dependency-light dense core.
- Prefer a numerically defensible factorization/thresholding approach; do not label a heuristic pivot count as an exact mathematical rank.
- Report matrix dimensions, estimated rank, rank threshold, and diagnostic status.
- Distinguish underdetermined, overdetermined, redundant, and locally rank-deficient cases where the available evidence supports that classification.
- Keep solver convergence status separate from diagnostic status.

Acceptance:
- Full-rank, duplicate-row, zero-column, underdetermined, and nearly dependent Jacobian fixtures are covered.
- Threshold sensitivity is tested and documented.
- A rank warning does not silently convert an otherwise residual-valid solution into a physical PASS.
- Uncertain classification is reported as UNKNOWN/INDETERMINATE rather than overstated.

### WP-2.3 — Conditioning and scaling

**Goal:** Expose numerical sensitivity and make normalization reproducible.

Deliverables:
- Add explicit variable scales, retaining current residual scales.
- Define how scaled variables and residuals map to original coordinates and units.
- Add a condition estimate or clearly labelled condition indicator with method and limitations.
- Define warnings for extreme scale disparity and near-singularity.
- Ensure residual acceptance continues to use original, unscaled residual values and per-equation tolerances.
- Include scale metadata and diagnostics in the result object.

Acceptance:
- Equivalent problems expressed at different magnitudes are tested.
- Tests demonstrate that scaling metadata does not alter the original-unit acceptance rule.
- Near-singular cases produce warnings or indeterminate diagnostics rather than false precision.
- Zero, negative, non-finite, missing, and mismatched scales are rejected.

### WP-2.4 — Solver reliability and regression suite

**Goal:** Build a durable test matrix around numerical failure modes.

Required test families:
- Baseline scalar and coupled nonlinear reference systems.
- Consistent overdetermined and underdetermined systems.
- Duplicate/redundant constraints and rank-deficient Jacobians.
- Ill-scaled variables and residuals.
- Near-singular and singular local systems.
- Bounds active at lower/upper limits and infeasible bounded targets.
- Initial point already satisfying all constraints.
- Stationary points with unsatisfied residuals.
- Non-finite residual/Jacobian, callback exception, and malformed dimensions.
- Finite-difference step sensitivity and analytic-vs-numeric derivative agreement.
- Regression tests preserving existing public API and result semantics.

Acceptance:
- Tests are deterministic and do not rely on network access or hardware.
- Every expected failure asserts the correct typed error/status.
- Tests distinguish residual convergence from rank/conditioning diagnostics.
- No flaky timing-based assertions.

### WP-2.5 — Diagnostics and evidence reporting

**Goal:** Make solver results inspectable and traceable.

Deliverables:
- Add structured diagnostic fields without removing existing result fields.
- Record derivative method, function/Jacobian evaluation counts, estimated rank, condition indicator, scale information, and diagnostic warnings when available.
- Keep `CONVERGED` / `NOT_CONVERGED` and per-residual `PASS` / `FAIL` semantics.
- Define a stable serialization/reporting contract only after inspecting the existing data model and API conventions.
- Update solver contract and implementation status only after code and tests support the statements.

Acceptance:
- A result can be reproduced from declared inputs/options and recorded solver version.
- Missing diagnostics are explicit (UNKNOWN/NOT_COMPUTED), never fabricated.
- Documentation does not claim a field is implemented before it exists.

### WP-2.6 — Mechanism constraint adapter design

**Goal:** Define the seam between generic numerical solving and mechanism-specific residual construction.

Deliverables:
- Specify an adapter contract that maps a mechanism model snapshot into ordered variables, scalar residuals, units/scales, tolerances, bounds, and source references. A proposed contract is documented in `docs/engineering/MECHANISM_CONSTRAINT_ADAPTER_CONTRACT.md` (PR #24); it is not an implementation.
- Define stable variable/constraint identifiers and deterministic ordering.
- Define how joint, link, frame, loop-closure, and fixed-reference constraints are translated to residuals.
- Define validation of model topology and coordinate-frame consistency before numerical solving.
- Define a result mapping back to mechanism variables and residual evidence.
- Keep planar four-bar implementation as a narrow reference case; do not generalize its assumptions silently.

Acceptance:
- Adapter contract includes invalid topology, missing frame, inconsistent units, duplicate IDs, and unsatisfied-loop cases.
- A reference planar mechanism can be represented without changing generic solver semantics.
- Multi-loop and 3D mechanisms remain explicitly out of scope until separately specified and tested.

## 5. Proposed delivery sequence

Each item below is a proposed PR/work package, not an existing PR number or an assertion that work has started.

| Sequence | Proposed change | Primary gate |
|---|---|---|
| 1 | Jacobian contract, forward/central strategy and analytic callback | Shape, finiteness, derivative agreement, compatibility |
| 2 | Rank and singularity diagnostics | Rank fixtures, threshold behavior, honest indeterminate state |
| 3 | Variable scaling and conditioning indicators | Scale invariance checks and original-unit residual acceptance |
| 4 | Reliability and regression matrix | Full deterministic test suite |
| 5 | Result diagnostics and documentation reconciliation | Schema/API compatibility and exact-SHA evidence |
| 6 | Mechanism constraint adapter contract | Reference planar mechanism mapping and invalid-model tests |

Do not bundle unrelated 3D CAD kernel, physics, dynamics, hardware schematic, or driver-generation work into these PRs. Those domains have their own architecture and validation gates.

## 5.1 Delivery status and evidence (2026-11-06)

| Work package | Delivery | Exact evidence | Current interpretation |
|---|---|---|---|
| WP-2.1 Jacobian strategies | PR #19 merged at `9676bdb00f3ffb1c8a2b0929fd27481b47368d43` | Tested head `db18dc115a55a2ba2aa648e7665e2d111a52e572`; run #118; 120 tests passed; workflow-sanity PASS | Implemented; post-merge CI lookup UNKNOWN |
| WP-2.2 Rank diagnostics | PR #20 merged at `6651b5985391679daba15abb6bdf2f78b9ff894b` | Tested head `43dbe1cb76eff112b6c4ea4bd348cd72f596da69`; run #131; 127 tests passed; workflow-sanity PASS | Implemented as a threshold-dependent estimate; post-merge CI lookup UNKNOWN |
| WP-2.3 Scaling indicators | PR #21 merged at `0ce6774aac48d822ef4a0d373ada36af6e3e2d3c` | Tested head `8f5c1ad54e42dd40f585c7860e37a6ac37b9dc78`; run #142; 130 tests passed; workflow-sanity PASS | Variable scaling and column-norm disparity indicator implemented; not a formal condition number; post-merge CI lookup UNKNOWN |
| WP-2.4 Reliability regression matrix | PR #22 merged at `1a3f05b5f99fa330cf0fd79e64f7ff3934211265` | Corrected tested head `265a7420edbb21da977dd357affaec61fa63f701`; run #147; 139 tests passed; workflow-sanity PASS | Implemented; first run #146 failed due a test fixture tolerance; corrected in run #147; post-merge CI lookup UNKNOWN |
| WP-2.5 Structured diagnostics/evidence | PR #23 merged at `870a3f634d7a7fbd47e838f85aff4dc2f1b76162` | Tested head `207d38d9959764756c703625e13d4122b82e0151`; run #159; 141 tests passed; workflow-sanity PASS | Versioned Python solver-result snapshot implemented; full provenance/evidence ledger and signing remain open; post-merge CI lookup UNKNOWN |
| WP-2.6 Mechanism constraint adapter | PR #24 design contract merged at `7aead53ac5af9dd3a82999c823a413db0e2f4ead` | Tested head `ef4330d1e7aa424df8cd58f4ff46ba572beaf975`; run #170; 141 tests passed; workflow-sanity PASS | Design contract delivered; actual adapter implementation, reference mechanism mapping and adapter-specific tests remain NOT IMPLEMENTED; post-merge CI lookup UNKNOWN |

For PR #19–#21, the documentation-only marker was SKIPPED and is not counted as PASS. The post-merge workflow/status lookup interface returned no entries for the three merge SHAs; those post-merge CI states remain UNKNOWN. PR-head CI evidence is not substituted for post-merge evidence.

## 6. Dependencies and sequencing constraints

- WP-2.1 precedes robust rank/conditioning work because diagnostics depend on a validated Jacobian representation.
- WP-2.2 and WP-2.3 may share internal matrix utilities, but public diagnostics should remain separately interpretable.
- WP-2.4 runs continuously and is expanded with every work package.
- WP-2.5 follows implementation so evidence fields describe actual emitted data.
- WP-2.6 follows stable solver inputs/results; the adapter must not conceal numerical uncertainty.
- Any external dependency, alternate solver backend, or CAD kernel requires a separate documented evaluation and decision record.

## 7. Verification and merge gates

For every implementation PR:

1. Record base branch and exact base SHA.
2. Review diff for scope, compatibility, security, and claims.
3. Run focused tests and the complete repository test suite.
4. Run workflow sanity and all required CI checks on the exact PR head SHA.
5. Inspect failed jobs and relevant logs; fix and rerun against the new exact head SHA.
6. Treat skipped jobs as SKIPPED, not PASS; unavailable evidence as UNKNOWN.
7. Merge only when required checks are successful and mergeability is confirmed.
8. Record merge commit SHA and run post-merge checks on that exact merge SHA.
9. Update implementation status and traceability with evidence links and explicit limitations.

A green status on an earlier SHA does not validate a later commit. A documentation-only marker being skipped is not evidence that a code test passed.

## 8. Risk register

| Risk | Consequence | Mitigation |
|---|---|---|
| Normal-equation conditioning | Loss of precision near rank deficiency | Diagnostics, thresholds, scaling, reference tests; evaluate QR/SVD separately |
| Misleading rank/condition estimates | False confidence in model identifiability | Label estimates and methods; include thresholds and UNKNOWN states |
| Bad scaling | Convergence distortion or unit confusion | Explicit scales, original-unit residual checks, dimensional adapter validation |
| Nonsmooth residuals | Derivative estimates become unreliable | Document smoothness assumptions; targeted tests and adapter validation |
| Overfitting to planar mechanisms | Incorrect claims for 3D/multi-loop systems | Keep adapter scope narrow and explicit |
| API churn | Downstream modules break | Additive evolution and compatibility tests |
| False engineering PASS | Unsafe downstream decisions | Separate numerical convergence, residual checks, physical validation, and human approval |

## 9. Explicit non-goals and safety boundary

Phase 2 does not deliver:
- A global optimizer, symbolic solver, sparse large-scale solver, or proof of uniqueness.
- Inequality/contact/complementarity solving, continuation, branch enumeration, or automatic gauge fixing.
- A general 3D or arbitrary multi-loop mechanism solver.
- Dynamics, FEA, CFD, multiphysics, collision, manufacturing, or structural certification.
- A CAD/B-rep kernel, geometry Boolean engine, mesh generator, or file interchange implementation.
- Any hardware actuation, firmware modification, fabrication command, machine operation, or production release.

A numerical result is not proof of physical feasibility, safety, regulatory compliance, or engineering certification. Any later high-impact use requires separate model validation, independent review, and explicit human authorization.

## 10. Exit criteria

Phase 2 is complete only when:
- All approved work packages have implementation and tests merged.
- Public contracts and documentation match the actual code.
- Reliability cases cover the stated numerical edge conditions.
- Exact PR-head and post-merge evidence is recorded for each implementation PR.
- Traceability entries identify what is implemented, what remains open, and the limits of each claim.
- No skipped or unknown check is represented as PASS.

Until these criteria are met, Phase 2 status remains **IN PROGRESS / NOT VERIFIED**.
