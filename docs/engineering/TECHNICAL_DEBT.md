# Technical Debt Register — 2026-11-25

**Repository:** `phakphum12345/universal-platform`  
**Current main baseline:** `main` at `24dbf3851cb64e7827234675a832e5abf1876b38` (PR #291 merge). Historical Development-branch findings below are retained as historical evidence and must not be treated as current branch state.  
**Related live audit:** [Repository Audit 2026-11-20](../audit/REPOSITORY_AUDIT_2026-11-20.md)  
**Status:** OPEN — this register records verified gaps and evidence debt; it is not a claim that all possible debt has been discovered.

## Live reconciliation — 2026-11-25

- Main is `24dbf3851cb64e7827234675a832e5abf1876b38` after PR #291. PR #280 and #287–#291 are merged; PR #258–#266 are also merged. Pre-PR-#292 inventory snapshot: 273 merged PRs, 18 closed without merge, 0 open PRs; current documentation reconciliation PR #292 is OPEN / Draft and not merged.
- PR #286 integrated the WP-15E authenticated read-only module/function catalogue. Its tools endpoint remains UNKNOWN because a separate governed tool registry does not exist.
- PRs #258–#266 integrated the durable allocator, identity/process-binding, worker start-gate, liveness and startup-recovery slices. This does not close WP-09G-E: authenticated/audited operator recovery, end-to-end acceptance and OS isolation/resource enforcement remain open.
- PR #288–#291 integrated shared-backend architecture, request correlation, Request ID schema and Laravel/Python source audit/documentation reconciliation.
- Exact-SHA post-merge CI on current Main `24dbf3851cb64e7827234675a832e5abf1876b38` is UNKNOWN in this register; do not infer PASS from merged PR state. The last recorded branch-protection observation is disabled; re-check live settings before closing GOV-001.
- Current major debt remains: WP-15F–J, WP-09G identity/security acceptance, cross-domain orchestration, general CAD/Mechanics/Physics/Hardware capability gaps, and full release acceptance.

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
| GOV-002 | Historical finding: product source was on a non-default development branch while `main` contained only the blueprint/docs tree | Historical `main` HEAD `96e7501...`; development HEAD `2eff621...`; tree counts 10 vs 450 (2026-11-20 snapshot) | Superseded as a current branch-state claim by subsequent Main integrations through PR #291. Retain this row only as historical audit evidence; do not reuse its old branch comparison as current state. | SUPERSEDED / HISTORICAL |
| SEC-001 | Process supervision and Windows Job Objects are not a general security sandbox | Runtime contracts and source docstrings explicitly disclaim privilege, filesystem/network and OS resource isolation | Threat-model and implement least-privilege worker identity, filesystem/network controls and platform-specific enforcement before executing untrusted plugins/code | OPEN |

## P1 — Runtime durability and recovery

> **Historical candidate-state note (superseded):** The RT-001–RT-005 rows below were written before PRs #258–#266 merged on 2026-11-20. Those PRs are now integrated. The historical exact-head evidence is retained, but their old “not integrated” states are not current. WP-09G acceptance remains partial because authenticated operator recovery, durable operational acceptance and OS enforcement are separate requirements.


| ID | Finding | Evidence | Required action | State |
|---|---|---|---|---|
| RT-001 | Durable allocator and ModuleRuntime integration | PRs #258 and #260 merged 2026-11-20; their PR-head evidence is retained in the historical audit | Preserve cross-process admission, restart and Windows integration regression coverage; verify current Main SHA and post-merge CI before claiming acceptance | INTEGRATED / ACCEPTANCE PARTIAL |
| RT-002 | PR #258 was merged without a formal review submission | PR #258 review API returned no review submissions; PR #258 merged 2026-11-20 | Record this as a historical governance gap; perform retrospective review if risk warrants and enforce required review policy on future changes | OPEN / HISTORICAL GOVERNANCE GAP |
| RT-003 | Cross-process allocator admission must remain covered on every supported OS | PR #260 merged 2026-11-20 with subprocess capacity-race regression and Windows integration coverage | Keep subprocess race and crash/restart tests required on Linux and Windows; current Main exact-SHA regression status is tracked separately | INTEGRATED / REGRESSION GATE |
| RT-004 | OS process identity hand-off and start-gate dependency chain | PRs #261–#264 merged 2026-11-20; identity snapshots, durable `LEASE_PROCESS_BOUND`, Linux/Windows start gate and WorkerIPC/ModuleRuntime callback are integrated | Retain callback-failure, cancellation, PID-reuse and pre-payload persistence tests; complete WP-09G host identity/authorization acceptance separately | INTEGRATED / ACCEPTANCE PARTIAL |
| RT-005 | Startup process-tree liveness and durable lease reconciliation | PRs #265–#266 merged 2026-11-20; Linux procfs and Windows Job Object PRESENT/ABSENT/UNKNOWN inspection plus startup gating/recovered-release evidence are integrated | Preserve fault-injection and restart tests; only exact ABSENT evidence may release; UNKNOWN and unsafe PRESENT remain quarantined. WP-09G operational acceptance remains open | INTEGRATED / ACCEPTANCE PARTIAL |
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
| UI-001 | WP-15B navigation/user journeys remain a draft awaiting owner acceptance | `docs/ui/WP-15B_NAVIGATION_USER_JOURNEYS.md`; PR #251 merged 2026-11-19, but merge of the draft document is not owner acceptance | Obtain owner review/acceptance and freeze the information architecture before treating navigation as accepted | BLOCKED / OWNER ACCEPTANCE |
| UI-002 | Shared Control Center shell exists, but cross-domain workspaces and platform-wide integrations are incomplete | PR #286 integrated WP-15C shell, WP-15D workspace foundations and the first WP-15E authenticated read-only module/function catalogue slice; no complete Mechanics/Physics/Hardware workbenches are established | Continue WP-15F–J against real backend contracts; preserve unavailable/UNKNOWN states and obtain owner/browser acceptance | PARTIAL |
| API-001 | Unified platform API/CLI and cross-domain orchestration are incomplete | Current completion matrix and source inventory | Define stable versioned contracts and one end-to-end user journey before expanding UI surface | PARTIAL |
| E2E-001 | Repository-wide user journey and supported-platform release matrix are not established | Current workflows cover engineering core, Windows process supervisor and CAD browser E2E, not a complete platform journey | Add source-backed integration/E2E tests and explicit platform coverage tied to release requirements | UNKNOWN / OPEN |

## P3 — Documentation and maintainability

| ID | Finding | Evidence | Required action | State |
|---|---|---|---|---|
| DOC-001 | Implementation Status and Work Package Status previously carried older PR #240 / 2026-11-12 live headers | Live headers reconciled to Main `24dbf3851cb64e7827234675a832e5abf1876b38`; historical dated sections intentionally retained | Keep live headers current and label dated snapshots as historical | SUPERSEDED / HISTORICAL |
| DOC-002 | Completion Matrix, Roadmap and Documentation Index had inconsistent live baselines and PR references | Completion Matrix and Roadmap now reflect PR #291 baseline; Documentation Index header and index-description correction are included in this reconciliation | Keep one dated live snapshot and cross-link the audit and debt register | IN PROGRESS |
| DOC-003 | Requirements Traceability Matrix row-level claims are not fully revalidated against current source | Live header reconciled to Main `24dbf3851cb64e7827234675a832e5abf1876b38`; several detailed rows still require source/test SHA revalidation | Revalidate requirement-by-requirement with source path, test path, exact SHA, maturity and limitations | OPEN |
| DOC-004 | Several historical PRs were closed without merge and replaced through later consolidated/rebased PRs | PR inventory #1–#258 | Keep supersession mapping; never equate a closed PR with an accepted implementation; retain branches/history |

## Acceptance policy for this register

A debt item closes only when its required code or governance change is present on the intended integration branch, applicable tests pass on the exact SHA, post-merge checks pass on the exact merge SHA, documentation/traceability is synchronized, and review/owner acceptance is recorded where required.

A design document, green partial workflow, skipped platform test, closed PR, or unmerged PR does not close a debt item. The repository remains INCOMPLETE while any P0/P1 or in-scope P2 item remains open.
