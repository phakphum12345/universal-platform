# Technical Debt Register — 2026-11-20

**Repository:** `phakphum12345/universal-platform`  
**Current main baseline:** `main` at `84cc7fa88161818f240619393dd1482e170fec2e` (PR #286 merge). Historical Development-branch findings below must be reconciled before reuse.  
**Related live audit:** [Repository Audit 2026-11-20](../audit/REPOSITORY_AUDIT_2026-11-20.md)  
**Status:** OPEN — this register records verified gaps and evidence debt; it is not a claim that all possible debt has been discovered.

## Live reconciliation — 2026-11-23

- WP-15E authenticated read-only module/function catalogue is integrated by PR #286. Its tools endpoint truthfully returns UNKNOWN because a separate governed tool registry does not exist.
- PR #286 exact-head CI passed Repository Quality, Engineering Core, CAD Generator Browser E2E and all four Cross-Shell jobs. Post-merge CI on `84cc7fa...` is still queued/in progress.
- PR #280 remains open and is based on an older main; documentation must be reconciled before merge.
- Main branch protection was last observed disabled; required checks are not enforced by GitHub. Verify the live settings before closing GOV-001.
- Current major debt remains: platform-wide Control Center WP-15F–J, WP-09G identity/security acceptance and OS isolation, cross-domain orchestration, general CAD/Mechanics/Physics/Hardware capability gaps, and full release acceptance.

## Severity and state

- **P0 — Governance / safety blocker:** must be resolved before the affected operation or acceptance claim.
- **P1 — Critical integration gap:** blocks the corresponding work package's acceptance.
- **P2 — Major capability gap:** blocks broad domain or platform acceptance.
- **P3 — Maintainability / completeness:** should be addressed in the relevant implementation slice.
- **UNKNOWN:** available evidence is insufficient; do not infer PASS.

## P0 — Governance and safety

| ID | Finding | Evidence | Required action | State |
|---|---|---|---|---|
| GOV-001 | Documentation describes `main` as protected, but GitHub reports both `main.protected=false` and `docs/phase-0-complete-requirements.protected=false`; required status-check enforcement is off and no repository rulesets exist | Live branch and ruleset API snapshot in the 2026-11-20 audit | Owner/admin must configure and verify branch protection or rulesets (required reviews, status checks, stale approval dismissal, restrictions appropriate to the workflow); update docs only after the live settings are verified | FAIL / OPEN |
| GOV-002 | Product source is on a non-default development branch while `main` contains only the small blueprint/docs tree | `main` HEAD `96e7501...`; development HEAD `2eff621...`; tree counts 10 vs 450 | Define an explicit promotion/release policy, validate full release gates and obtain separate authorization before any promotion to `main`; the live compare currently reports development ahead by 878 commits and main behind by 0 | OPEN |
| SEC-001 | Process supervision and Windows Job Objects are not a general security sandbox | Runtime contracts and source docstrings explicitly disclaim privilege, filesystem/network and OS resource isolation | Threat-model and implement least-privilege worker identity, filesystem/network controls and platform-specific enforcement before executing untrusted plugins/code | OPEN |

## P1 — Runtime durability and recovery

| ID | Finding | Evidence | Required action | State |
|---|---|---|---|---|
| RT-001 | Durable allocator and ModuleRuntime integration are verified on PR heads but not integrated on the development branch | PR #258 exact-head CI PASS (1,160 passed / 4 skipped); PR #260 exact-head CI PASS (1,166 passed / 4 skipped) with subprocess capacity-race and Windows integration coverage | Complete review, integrate #258 before #260 after explicit authorization, then require exact merge-SHA and post-merge regression evidence | OPEN / VERIFIED ON PR HEAD |
| RT-002 | Durable allocator PR #258 has no formal review submission | PR #258 review API returned no review submissions | Complete code review and resolve blocking comments before merge | OPEN |
| RT-003 | Cross-process allocator admission must remain covered on every supported OS | PR #260 adds a subprocess capacity-race regression; exact-head Windows durable allocator/ModuleRuntime job passes and the full Python suite passes | Keep subprocess race and crash/restart tests required on Linux and Windows after integration | VERIFIED ON PR HEAD / OPEN UNTIL INTEGRATED |
| RT-004 | OS process identity hand-off is implemented in a candidate PR chain but not integrated | #261 identity snapshots, #262 durable `LEASE_PROCESS_BOUND`, #263 Linux/Windows start gate, #264 WorkerIPC/ModuleRuntime callback; #264 exact-head CI PASS (Python 1,185 passed / 5 skipped; Windows WorkerIPC/ModuleRuntime integration 70 passed) | Review and integrate the dependency chain in order; retain callback-failure, cancellation, PID-reuse and pre-payload persistence tests | IN PROGRESS / VERIFIED ON PR HEAD |
| RT-005 | Startup process-tree liveness and durable lease reconciliation are in progress but not integrated | #265 adds Linux procfs and Windows Job Object PRESENT/ABSENT/UNKNOWN inspection (Python 1,194 passed / 6 skipped; Windows and workflow checks PASS); #266 adds startup gating/recovered-release evidence (CI QUEUED) | Complete exact-head CI, fault-injection and restart tests; only exact ABSENT evidence may release; UNKNOWN and unsafe PRESENT remain quarantined | IN PROGRESS |
| RT-006 | Audited operator force release is unavailable | PR #258 intentionally rejects ordinary release of quarantined leases | Implement WP-09G-E with authenticated authorization, durable audit event, reason, operator identity and fail-closed behavior if audit persistence fails | NOT IMPLEMENTED |
| RT-007 | Durable journal lifecycle/rotation and checkpoint anchoring are not delivered by PR #258 | WP-09G contract calls for active-segment limits, checkpoint/rotation and trusted anchors | Design and test bounded rotation/checkpoint semantics without losing active or quarantined leases; distinguish unkeyed integrity from authenticated integrity | OPEN |
| RT-008 | Four tests are skipped on PR #258's Linux Python run; they are the four Windows-only supervisor cases in `tests/test_runtime_process_supervisor.py`, and the Windows job executes them | Exact-head run #44618695050: Python 1,160 passed / 4 skipped; Windows process supervisor 21 passed / 2 POSIX-only skipped; journal 20 passed / 1 Windows-only skipped | Keep platform-specific skips explicit and verify the opposite-platform CI job runs the applicable cases | SKIPPED |
| RT-009 | CI does not yet enforce repository-wide formatting/lint, type checking, dependency vulnerability scanning or source security analysis | Current workflows run Python tests, Windows process-supervisor/journal/runtime integration and workflow sanity; no repository-wide lint/type/dependency-security job was observed | Add low-cost reproducible lint/type/dependency-security gates in a dedicated PR; resolve findings without suppressing checks or adding blanket skips | OPEN |

## P2 — Engineering domain capability gaps

| ID | Domain | Finding | Required action | State |
|---|---|---|---|---|
| CAD-001 | CAD / Geometry | General arbitrary topology, branching/tangencies, non-manifold policy, curved surfaces and broad Boolean degeneracies remain outside the verified narrow kernel | Add independent geometric reference corpus, exact/fail-closed predicates, adversarial tests and resource-bound proofs per topology slice | PARTIAL |
| CAD-002 | CAD Generator | FeatureHistory recompute propagation and broader parametric feature generation remain incomplete | Define dependency invalidation/recompute semantics and verify revision-safe regeneration through service/API/browser E2E | PARTIAL |
| CAD-003 | Interchange | STL, STEP AP214 and 3MF Core support is bounded; full neutral-format fidelity is not established | Add explicit versioned profiles, loss reports, unit/coordinate/topology checks and independent round-trip fixtures | PARTIAL |
| MEC-001 | Mechanics | General multi-loop and 3D mechanism configuration solving, singularity/redundancy analysis and dynamics remain incomplete | Implement separate validated solver increments with independent mechanism references; keep nominal DOF distinct from Jacobian rank/local mobility | PARTIAL |
| PHY-001 | Physics | Central registry exists, but built-in reference-checked solvers cover only narrow analytical families | Add independently validated thermal/fluid/electromagnetic/structural models; separate model assumptions, numerical method, convergence, uncertainty and results | PARTIAL |
| HW-001 | Hardware / EDA | Schematic/netlist, rendering and static ERC foundations do not constitute a complete EDA/PCB or circuit-simulation system | Add datasheet-backed component constraints, library/import/export, power domains, BOM/footprint checks and reference-validated circuit simulation | PARTIAL |
| DRV-001 | Drivers | Driver interfaces exist, but hardware integration and generated-driver lifecycle are not a complete device-control plane | Reuse the existing driver architecture; add safe simulation/diagnostic paths and explicit capability boundaries; do not enable physical I/O by implication | PARTIAL |

## P2 — Platform integration and UI

| ID | Finding | Evidence | Required action | State |
|---|---|---|---|---|
| UI-001 | WP-15B navigation/user journeys remain a draft awaiting owner acceptance | `docs/ui/WP-15B_NAVIGATION_USER_JOURNEYS.md`; PR #251 is Draft | Obtain owner review/acceptance before starting WP-15C | BLOCKED |
| UI-002 | Shared Control Center shell and cross-domain workspaces are not implemented | WP-15A inventory reports CAD as the existing browser workbench; no shared shell or Mechanics/Physics/Hardware workbenches found | Implement an accepted thin shared shell, then connect real backend capabilities and unavailable/UNKNOWN states | PLANNED |
| API-001 | Unified platform API/CLI and cross-domain orchestration are incomplete | Current completion matrix and source inventory | Define stable versioned contracts and one end-to-end user journey before expanding UI surface | PARTIAL |
| E2E-001 | Repository-wide user journey and supported-platform release matrix are not established | Current workflows cover engineering core, Windows process supervisor and CAD browser E2E, not a complete platform journey | Add source-backed integration/E2E tests and explicit platform coverage tied to release requirements | UNKNOWN / OPEN |

## P3 — Documentation and maintainability

| ID | Finding | Evidence | Required action | State |
|---|---|---|---|---|
| DOC-001 | Implementation Status and Work Package Status carry older PR #240 / 2026-11-12 baselines | Existing headers and rows | Reconcile live SHA, PR #254–#258, and separate PR-head vs merge-SHA evidence; preserve historical sections |
| DOC-002 | Completion Matrix, Roadmap and Documentation Index do not consistently record PR #256–#258 | Existing 2026-11-19 / PR #254 snapshots | Keep one dated live snapshot and cross-link the audit and debt register |
| DOC-003 | Requirements Traceability Matrix is dated 2026-11-12 and row-level claims are not fully revalidated against current source | Existing header | Revalidate requirement-by-requirement with source path, test path, exact SHA, maturity and limitations |
| DOC-004 | Several historical PRs were closed without merge and replaced through later consolidated/rebased PRs | PR inventory #1–#258 | Keep supersession mapping; never equate a closed PR with an accepted implementation; retain branches/history |

## Acceptance policy for this register

A debt item closes only when its required code or governance change is present on the intended integration branch, applicable tests pass on the exact SHA, post-merge checks pass on the exact merge SHA, documentation/traceability is synchronized, and review/owner acceptance is recorded where required.

A design document, green partial workflow, skipped platform test, closed PR, or unmerged PR does not close a debt item. The repository remains INCOMPLETE while any P0/P1 or in-scope P2 item remains open.
