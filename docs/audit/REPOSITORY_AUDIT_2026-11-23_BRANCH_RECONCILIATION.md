# Repository Branch Reconciliation Audit — 2026-11-23

**Repository:** `phakphum12345/universal-platform`  
**Audited branch:** `main`  
**Audited Main SHA:** `84cc7fa88161818f240619393dd1482e170fec2e` (PR #286 squash merge)  
**Audit type:** GitHub branch/PR inventory, ancestry comparison, source/test/documentation counterpart inspection  
**Overall repository status:** **INCOMPLETE**

## Executive result

**No — not every branch has been merged into `main`.** The pre-audit-PR inventory snapshot had 306 branches including `main`. This snapshot was taken before creating the dedicated audit branch for PR #287. Branches must not be equated with PRs: squash merges preserve the feature changes but do not make the original feature-branch head commit an ancestor of `main`.

At the time of this audit, the PR inventory was:

| PR state | Count | Interpretation |
|---|---:|---|
| Merged | 267 | GitHub records a merge commit; verify integration and post-merge evidence separately |
| Closed without merge | 18 | Do not merge automatically; inspect for superseding PRs and unique content |
| Open | 1 | PR #280, documentation reconciliation |
| **Total PRs** | **286** | All PRs returned by the repository's paginated PR API |

The branch inventory at the pre-audit-PR snapshot was:

| Branch group | Count |
|---|---:|
| All branches including `main` | 306 |
| Branches with at least one associated PR | 285 |
| Branches without an associated PR, excluding `main` | 20 |
| **Total** | **306** |

After the inventory snapshot, this audit created branch `docs/reconcile-main-branch-audit-2026-11-23` and opened PR #287. Therefore the live repository now has 307 branches and 287 PRs: 267 merged, 18 closed without merge, and 2 open (#280 and #287). The baseline counts above intentionally exclude this audit PR. The PR and branch counts are not one-to-one: more than one PR can reference a branch, and a branch can remain after its PR has merged or closed.

## Main and current PRs

- `main` HEAD is `84cc7fa88161818f240619393dd1482e170fec2e`.
- PR #286 — [Authenticated module and function catalogue](https://github.com/phakphum12345/universal-platform/pull/286) — **MERGED** at `84cc7fa88161818f240619393dd1482e170fec2e`.
- PR #280 — [Live repository status reconciliation](https://github.com/phakphum12345/universal-platform/pull/280) — **OPEN**. Its head `074757f95d302f87967b4ef6c6563a224e4e98a7` was authored against an older main baseline. The compare against current main `84cc7fa88161818f240619393dd1482e170fec2e` reports 30 commits ahead and 4 behind. Its changes must be refreshed before merge.
- No branch or file was deleted, no history was rewritten, and no force push was used in this audit.

## PR #286 evidence

Exact PR-head SHA: `dcc14c36117c60e6a3fd104cd614ad1577f46502`.

| Workflow | Exact PR-head result |
|---|---|
| Repository Quality and Dependency Security | PASS |
| Engineering Core Tests | PASS |
| CAD Generator Browser E2E | PASS |
| Cross-Shell Runtime Validation | PASS — Windows cmd, Windows PowerShell, Ubuntu sh and Ubuntu bash (4/4) |

Reviews: none returned. Inline review threads: none returned. PR was mergeable and open at the final pre-merge check. It was squash-merged using the expected head SHA.

Post-merge workflows on `84cc7fa88161818f240619393dd1482e170fec2e` were queued/in progress at the audit snapshot. **Post-merge CI is UNKNOWN until all applicable runs complete successfully.** The successful PR-head workflows are not a substitute for post-merge evidence.

## Closed-without-merge PR reconciliation

The following 18 PRs were closed without a merge commit:

`#100, #101, #102, #103, #104, #105, #106, #108, #109, #111, #112, #114, #193, #229, #249, #250, #253, #255`.

### Findings

| PR(s) | Observed disposition | Required caution |
|---|---|---|
| #100–#106, #109, #111–#112 | The corresponding runtime adapter, recovery, log, resource, health and evidence source files and tests are present on current `main` | Their branch tips are not ancestors because the integration history was later rebased/squashed. This confirms current file counterparts, not byte-for-byte equivalence of every historical branch revision |
| #108 | Central physics registry source and reference tests are present on current `main` | Broader physics domains remain incomplete; registry presence is not broad solver acceptance |
| #114 | Documentation/status-only branch; later current status records exist | Historical documentation delta is not treated as an independent implementation |
| #193 | Arbitrary faceted B-rep Boolean contract exists on current `main` in a later, expanded form | The broader Boolean capability remains PARTIAL |
| #229 | Related Boolean test files exist on current `main`, but their blob contents differ from the closed branch | Later tests evolved; exact test-case equivalence has not been certified in this audit |
| #249 | Superseded by the canonical WP-15B navigation/user-journey draft on `main`; the old IA file is explicitly marked SUPERSEDED | WP-15B still awaits owner review/acceptance |
| #250 | Worker IPC client source and tests exist on current `main` through later integration | Historical branch is not to be merged independently |
| #253 | Supervised ModuleRuntime dispatch source and tests exist on current `main` through later integration | Historical branch is not to be merged independently |
| #255 | Durable worker lease recovery contract exists on current `main` and was subsequently updated | Durable runtime and OS security acceptance remain bounded/partial |

**Disposition:** these closed PRs are not candidates for blind merge. Source/test counterparts for their principal runtime and physics features are present on current `main`; the #229 test-delta equivalence and historical documentation-only deltas remain evidence items rather than grounds to re-open old PRs.

## Branches without a PR

Twenty non-main branches had no associated PR. The four branches below compare as already behind `main` with zero commits ahead, so their branch tips are ancestors of the current integration history:

- `docs/audit-post-pr199-multi-plane-arrangement`
- `feat/cad-planar-branching-topology-v1`
- `feat/wp-09g-e-operator-recovery`
- `test/spatial-joint-foundation-reference-suite`

The remaining 16 branch tips diverge from `main`. Inspection found current source/test counterparts for 14 code-oriented branch lineages:

- Curved profile / primitive geometry: `feat/curved-profile-extrusion`, `feat/curved-profile-extrusion-check3`, `feat/curved-profile-extrusion-check4`, `feat/curved-profile-extrusion-ci`.
- Planar mobility: `feat/planar-mobility-jacobian-diagnostic`, `feat/planar-mobility-jacobian-diagnostic-v2`, `feat/planar-mobility-rotation-log-stability`, `feat/planar-mobility-stable-difference-step`, `feat/planar-plane-frame-mobility`, `fix/planar-mobility-rotation-log-stability`.
- Schematic rendering: `feat/schematic-layout-svg-renderer-check`, `feat/schematic-layout-svg-renderer-check2`.
- Worker dispatch: `feat/wp-09f-module-runtime-worker-dispatch`, `feat/wp-09f-module-runtime-worker-dispatch-rebased`.

The following two diverged branches are documentation/audit-only candidates and were not blindly ported because their edits may be historical or superseded:

- `docs/post-pr171-undo-redo-e2e-audit`
- `docs/reconcile-pr70-arc-mesh-evidence`

All 20 branches remain untouched. A diverged branch comparison alone does not prove that its content is missing: squash/rebase integration creates divergent histories even when equivalent files and tests are now on `main`.

## Open documentation PR #280

PR #280 includes useful documentation material, notably `docs/governance/MAIN_BRANCH_PROTECTION.md` and a live audit document, but its root status updates refer to an older main SHA and older PR state. The branch is not safe to merge as-is.

The branch-protection policy document is a recommendation only. The last live check found main branch protection disabled; required checks were not enforced by GitHub. The policy has been copied to this audit branch for review and must not be described as an applied setting.

Required next steps for PR #280:
1. Rebase/reconcile against current `main` without force-pushing or discarding unique content.
2. Refresh every live SHA, PR count, workflow result, branch count and WP status in the affected documents.
3. Preserve historical snapshots under explicit historical headings.
4. Run exact-head CI and inspect review submissions/threads.
5. Merge only after the documentation is internally consistent and all applicable gates pass.

## Current implementation gaps remain

The branch audit does not change the repository's capability maturity. Current main documentation continues to describe these areas as PARTIAL or INCOMPLETE:

- Core governance, identity/authorization, threat model, secure configuration, audit, migration/rollback and branch protection.
- CAD/3D general topology and degeneracies, recompute propagation, broader curved geometry and neutral-format fidelity.
- Mechanics general multi-loop/3D configuration solving, singularity/redundancy analysis, dynamics and contact.
- Physics validated thermodynamics, fluids, electromagnetics, structural FEA/FEM, CFD, multiphysics coupling, convergence and uncertainty.
- Hardware/EDA complete PCB/library workflows, datasheet-backed electrical constraints, circuit simulation, BOM/footprint validation and safe diagnostics.
- Runtime durable recovery acceptance, host identity/authorization wiring, least privilege, filesystem/network isolation and OS CPU/memory/I/O enforcement.
- Unified Control Center WP-15F–J: settings, jobs/diagnostics/audit, workbench integration, accessibility/usability and release hardening.
- Unified API/CLI, cross-domain orchestration, supported-platform matrix, backup/restore, security/license review and formal release acceptance.

WP-15E is now integrated: authenticated read-only module/function metadata catalogue. It does not execute modules or grant permissions. The Tools catalogue correctly reports UNKNOWN because no separate governed tool registry exists.

## Rules for continued branch reconciliation

- Preserve every branch until its unique content has been inspected and disposition recorded.
- Never merge a branch merely because it is ahead of `main`; compare source, tests, contracts, dependencies and PR history.
- Never call SKIPPED, queued, in-progress, missing or UNKNOWN a PASS.
- For every merge, record exact PR head SHA, merge SHA, and post-merge CI on the exact merge SHA.
- Keep implementation status separate from integration, verification and owner acceptance.
- The repository remains **INCOMPLETE** until all approved requirements and release gates have evidence-backed acceptance.
