# Work Package Status Register

**Baseline integration branch:** docs/phase-0-complete-requirements  
**Last verified integration baseline:** `21bee045ea4d06aa07c7130f9123afaa64372638`  
**Audit date:** 2026-11-08  
**Status:** INCOMPLETE — initial evidence-based register; update per implementation slice.

| WP | Domain | Current status | Evidence / next action |
|---|---|---|---|
| 01 | Core architecture | PARTIAL | Existing contracts and engineering core; audit module runtime boundaries and missing platform orchestration |
| 02 | CAD geometry | PARTIAL | Planar topology and bounded faceted B-rep/axis-aligned Boolean exist; general n-gon, multi-shell, arbitrary 3D Boolean and ambiguous branching remain open |
| 03 | CAD generator | PARTIAL | FeatureHistory regeneration, durable revisions/cache, local service, immutable backend add/replace/remove operations and revision-safe loopback edit API exist; real-browser editing coverage now passes; FeatureHistory v1.1 backend model/editor/regeneration merged in PR #163; undo/redo, branching/merging, feature reorder and broader CAD/kernel/UI capabilities remain open |
| 04 | Mechanics | PARTIAL | Mechanism schema, loop closure, mobility and caller-driven kinematics exist in bounded scopes; broader solver/dynamics and validation remain open |
| 05 | Physics | PARTIAL | Physics modules and central solver registry exist; broader validated solver methods and coupled multiphysics remain open |
| 06 | Hardware/electronics | PARTIAL | Hardware, schematic and electrical rule checking modules exist; broader design/simulation workflows remain open |
| 07 | Schematic/PCB | PARTIAL | Schematic/netlist and layout foundations exist; complete PCB workflows and export/validation remain open |
| 08 | Drivers | PARTIAL | Driver contracts and implementation exist; inspect and reuse existing generation capability; do not duplicate |
| 09 | Module runtime | PARTIAL | Metadata registry and runtime resource/adapter supervision exist; OS-enforced isolation and full permissioned execution remain open |
| 10 | System understanding | PARTIAL | Architecture/evidence contracts exist; authorized discovery, indexing and governed adaptation need end-to-end evidence |
| 11 | API/CLI/UI | PARTIAL | CAD loopback HTTP API and local workbench exist; broader stable platform API/CLI/UI integration remains open |
| 12 | Platform integration | PARTIAL | Several cross-module integrations exist; end-to-end user workflows and platform matrix remain open |
| 13 | Security/quality | UNKNOWN / PARTIAL | Python CI and JS syntax checks exist; real Chromium E2E is established for the CAD workbench; full dependency, license, secret and OS-isolation audits are not established |
| 14 | Final verification | FAIL / INCOMPLETE | Full repository completion gates are not met; continue evidence collection and implementation |

## Active slice

- Task: CAD-EDIT-001 — immutable FeatureHistory add/replace/remove operations.
- Source: src/universal_platform/engineering/feature_history_editor.py.
- Tests: tests/test_feature_history_editor.py.
- Contract: docs/design-3d/FEATURE_HISTORY_EDITING_CONTRACT.md.
- Acceptance: immutable transforms; stable IDs; strict dependency/cycle validation; explicit cascade removal; at least one output retained.
- PR: #152 (merged to integration branch).
- Exact PR head: 3c2469a43e48d5ac2fb7e546242d9a450dff1a87.
- Exact PR-head workflow #42396387520: workflow-sanity PASS; python-tests PASS; 840 passed in 9.23s.
- Exact merge SHA: 1a8338ae17eb783a374a36400999ead796f9a79d.
- Post-merge workflow #42396453320: both jobs PASS; 840 passed in 8.71s.
- Status: PASS for this bounded backend editing slice; overall WP-03 remains PARTIAL.

## Next dependency-ready slice

- CAD-EDIT-002 — expose safe edit operations through the local CAD Generator service and workbench, with expected-revision conflict handling, preview/validation, explicit cascade confirmation, and browser/API integration tests. Keep feature execution allow-listed and do not add user-code execution.

## CAD-EDIT-002 — Revision-safe service and API editing

- PR: #154 (merged to integration branch).
- Exact PR head: d243fdee6e9fc04925eaf435b4b1e4a4cfb27ae3.
- Exact PR-head workflow #42397413655: workflow-sanity PASS; python-tests PASS; 843 passed in 9.34s.
- Exact merge SHA: 7046de5cff4a7a575de44de189bbb4fedcbdba58.
- Post-merge workflow #42397474889: both jobs PASS; 843 passed in 7.14s.
- Status: PASS for revision-safe service/API editing; overall WP-03 remains PARTIAL.

## Next dependency-ready slice

## CAD-EDIT-003 — Interactive browser FeatureHistory editing controls

- PR: #156 (merged to integration branch).
- Exact PR head: 265ca3907e05f958fbae48f48398fbbae8d70ea2.
- Exact PR-head workflow #42407785969: workflow-sanity PASS; python-tests PASS; 843 passed in 9.40s.
- Exact merge SHA: 10404099ccaa85cef24adedffa7bce789abd691e.
- Post-merge workflow #42407835073: workflow-sanity PASS; python-tests PASS; 843 passed in 9.76s.
- Review submissions: none returned; inline review threads: none; unresolved threads: 0. Automated Codex review did not complete because the review usage limit was reached; no review findings were submitted.
- Implementation: selected-feature parameter replacement, feature add/remove, explicit cascade checkbox, revision-head guard, immutable revision reload, HTTP 409 stale-write guidance and text-only rendering.
- A missing UI control-state helper discovered during verification was added; regression assertions now verify that edit controls are enabled only for the loaded current head.
- Status: PASS for bounded browser editing controls and CI; overall WP-03 remains PARTIAL.
- Browser E2E interaction testing was completed in PR #158 and is recorded below; do not retain the earlier SKIPPED state as current.

## CAD-EDIT-004 — Real-browser FeatureHistory editor coverage

- PR #158 merged to integration at `9d899f70a97372f689ba07a8e90b479bf14494b4`.
- Exact PR head `9aa96157eb6e5ebbf324aa6614178ffd8af17495`: Chromium E2E PASS (4 tests); Python suite PASS (843 tests); workflow-sanity PASS.
- Exact merge SHA: Chromium E2E PASS (4 tests; run `42438295044`); Python suite PASS (843 tests; run `42438295110`); workflow-sanity PASS.
- Coverage: startup/no uncaught page errors, current-head vs historical revision gating, parameter replacement, add/remove and explicit cascade confirmation, stale-writer HTTP 409, safe text-only rendering.
- Review submissions: 0; unresolved review threads: 0. No paid browser service or production deployment.
- Status: PASS for the browser-verification slice; overall WP-03 remains PARTIAL.

## Next dependency-ready slice

- CAD-EDIT-005 — suppression semantics contract merged in PR #162; backend model/editor/regeneration merged in PR #163. Exact PR-head and post-merge tests passed.
- CAD-EDIT-006 — revision-safe service/API operations for suppress/unsuppress merged in PR #165; strict request parsing, expected-revision compare-and-swap and loopback auth verified.
- CAD-EDIT-007 — workbench controls, explicit cascade confirmation and suppression-specific Chromium E2E merged in PR #166; exact-head and post-merge browser checks PASS.
- CAD-EDIT-008 — define undo/redo semantics as immutable revision restore operations before implementation; specify redo behavior, persistence across reload, stale-writer handling and audit evidence.


## Documentation reconciliation — PR #160

- PR #160 merged to integration at `6f4ebf774d163cb95bd580fcc36c73ebe5ceb17a`.
- Exact PR-head CI: workflow-sanity PASS; python-tests PASS after preserving the historical baseline identifier required by `tests/test_post_pr113_status_docs.py`.
- Exact post-merge CI on the merge SHA: workflow-sanity PASS; python-tests PASS. The documentation-only marker was SKIPPED and is not counted as a pass.
- Status: PASS for documentation reconciliation; no source/runtime behavior changed.


## Documentation reconciliation — PR #161

- PR #161 merged at `35f06a304090176eb6d10697d6da67b53b1ec9ba`.
- Exact PR-head CI: workflow-sanity PASS; python-tests PASS.
- Exact post-merge CI on the merge SHA: workflow-sanity PASS; python-tests PASS. The documentation-only marker was SKIPPED and is not counted as a pass.
- Status: PASS for post-merge documentation audit; no source/runtime behavior changed.


## CAD-EDIT-005 — Suppression backend core (PR #163)

- Scope: FeatureHistory v1.1 metadata with v1.0 serialization compatibility, explicit migration, immutable suppress/unsuppress edits, active-output/dependency invariants, regeneration skip/report behavior, JSON Schema and public exports.
- Tests added for v1.0 round-trip, immutable revision digest preservation, v1.1 validation, explicit cascade, dependency-order unsuppression and regeneration skip behavior.
- Service/API/workbench/browser E2E are intentionally not claimed in this slice.
- PR #163 merged at `e6a6196aeaa84fca2eff8ce2f0417cc0a4014c2b`. Exact PR-head CI: 851 Python tests PASS, 4 Chromium E2E tests PASS, workflow-sanity PASS. Exact post-merge CI: 851 Python tests PASS, 4 Chromium E2E tests PASS, workflow-sanity PASS.


## Documentation reconciliation — PR #162

- PR #162 merged at `a952fd927e5b6a0fa7fd9701343c2bffb52091e1`.
- Exact PR-head and post-merge CI: workflow-sanity PASS; python-tests PASS.
- Suppression contract is now indexed and merged; design is not counted as implementation.


## CAD-EDIT-005 — Post-merge verification

- PR #163 exact merge SHA: `e6a6196aeaa84fca2eff8ce2f0417cc0a4014c2b`.
- Post-merge engineering workflow #42439562896: 851 Python tests PASS; workflow-sanity PASS.
- Post-merge Chromium workflow #42439562884: 4 tests PASS.
- Status: PASS for backend model/editor/regeneration; overall WP-03 remains PARTIAL until service/API/workbench integration and browser tests are complete.


## CAD-EDIT-006 / CAD-EDIT-007 — Suppression end-to-end completion

- PR #165 merged service/API operations at `038193589e7b4ca22fb0a41ef6f61e54fd8d2938`; exact PR-head and post-merge gates: 854 Python tests, 4 Chromium E2E tests and workflow-sanity PASS.
- PR #166 merged workbench controls at `34148fc359076567eaa4b931304f61f536a41779`; exact PR-head and post-merge gates: 854 Python tests, 5 Chromium E2E tests and workflow-sanity PASS.
- Browser acceptance: implicit cascade rejected; explicit cascade checkbox and confirmation required; source nodes retained; unsuppress blocked until dependencies are active; restoration creates immutable revisions.
- Status: PASS for FeatureHistory suppression end-to-end. WP-03 overall remains PARTIAL because undo/redo, branching/merging, reorder and broader CAD kernel capabilities remain open.


## Documentation reconciliation — PR #167

- PR #167 merged at `d71fc36b29f4e1b1056c738294c1529e823be671`.
- Exact PR-head and post-merge CI: 854 Python tests PASS; workflow-sanity PASS.
- FeatureHistory suppression end-to-end work packages CAD-EDIT-005/006/007 are PASS. Overall WP-03 remains PARTIAL because undo/redo, branch/merge and reorder are still open.


## CAD-EDIT-009 — Store-level Undo/Redo (PR #169)

- Adds persistent SQLite navigation stacks and revision action metadata without rewriting existing revision snapshots or digests.
- Legacy histories backfill Undo targets from their immutable revision chain.
- Undo/Redo append a new revision with current head as parent; all stack and head changes occur in one transaction.
- A new edit after Undo clears Redo. Stale expected revisions leave both stacks and revision count unchanged.
- Exact PR-head CI: 860 Python tests PASS; workflow-sanity PASS. Store slice is not yet merged at this status snapshot.


## CAD-EDIT-009 — Store-level Undo/Redo post-merge

- PR #169 merged at `93744335f3e50a07dde2f78a18f9a307308b73ef`.
- Exact PR-head and post-merge CI: 860 Python tests PASS; workflow-sanity PASS.
- The store preserves immutable source revisions and digests; navigation state is persisted transactionally.

## CAD-EDIT-010 — Service/API Undo/Redo (PR #170)

- Adds service access to navigation state, strict GET navigation route and POST Undo/Redo operations.
- Expected-revision CAS applies; NO_UNDO/NO_REDO are explicit 409 responses; no arbitrary target revision is accepted.
- Pending exact-head CI and merge. Workbench/browser layer remains open.


## CAD-EDIT-010 — Service/API Undo/Redo post-merge

- PR #170 merged at `2afbb2585e541ad7ccefe7a3755742c3b1b85d9d`.
- Exact PR-head CI: 865 Python tests, 5 Chromium E2E tests and workflow-sanity PASS.
- Exact post-merge CI: 865 Python tests and workflow-sanity PASS; Chromium E2E 4 PASS / 1 ERROR due a test-fixture timing race on revision option readiness. No service/API test failed.

## CAD-EDIT-011 — Workbench Undo/Redo (PR #171)

- Adds persistent navigation availability, current-head gating, Undo/Redo actions and invalid revision guards.
- Adds browser coverage for reload persistence and redo invalidation after a new edit.
- Pending exact-head and post-merge gates.


## CAD-EDIT-011 — Undo/Redo workbench (PR #171)

- Adds Undo/Redo buttons driven by server navigation state and enabled only when the current head snapshot is actually loaded.
- Historical revision selection and loading remain read-only; returning the dropdown to the head does not re-enable mutations until the head is loaded again.
- Guards empty/invalid revision values before Load/Regenerate, fixing the PR #170 post-merge `revision=0` timing race.
- Browser coverage checks multi-step Undo/Redo, reload persistence, historical read-only gating and redo invalidation after a new edit.
- Pending exact-head and post-merge gates.


## CAD-EDIT-011 — Undo/Redo workbench end-to-end completion

- PR #171 merged at `21bee045ea4d06aa07c7130f9123afaa64372638`.
- Exact PR-head and post-merge CI: 865 Python tests PASS, 6 Chromium E2E tests PASS, workflow-sanity PASS.
- Workbench controls are driven by persistent server navigation state; actions are enabled only when the actual loaded snapshot is the current head.
- Browser tests verify historical read-only behavior, multi-step Undo/Redo, persistence after reload and Redo invalidation after a new edit.
- Status: PASS for FeatureHistory Undo/Redo end-to-end. WP-03 remains PARTIAL for broader CAD branching/merging, reorder, generalized B-rep and other kernel/editor capabilities.


## CAD-EDIT-008 through CAD-EDIT-011 — FeatureHistory Undo/Redo end-to-end PASS

- PR #168 defined the contract; PR #169 implemented the store; PR #170 implemented service/API; PR #171 implemented workbench/browser acceptance.
- Final merge SHA: `21bee045ea4d06aa07c7130f9123afaa64372638`.
- Exact PR-head and post-merge CI: 865 Python tests PASS, 6 Chromium E2E tests PASS, workflow-sanity PASS.
- Undo/Redo appends immutable revisions, persists stacks across restart, clears Redo after new edits, rejects stale writers and keeps historical views read-only.
- R-017 status: PASS for linear FeatureHistory Undo/Redo. WP-03 remains PARTIAL due graph branching/merging, feature reorder, generalized B-rep and other CAD kernel capabilities.
