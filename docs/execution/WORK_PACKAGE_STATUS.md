# Work Package Status Register

**Baseline integration branch:** docs/phase-0-complete-requirements  
**Last verified integration baseline:** `35f06a304090176eb6d10697d6da67b53b1ec9ba`  
**Audit date:** 2026-11-08  
**Status:** INCOMPLETE — initial evidence-based register; update per implementation slice.

| WP | Domain | Current status | Evidence / next action |
|---|---|---|---|
| 01 | Core architecture | PARTIAL | Existing contracts and engineering core; audit module runtime boundaries and missing platform orchestration |
| 02 | CAD geometry | PARTIAL | Planar topology and bounded faceted B-rep/axis-aligned Boolean exist; general n-gon, multi-shell, arbitrary 3D Boolean and ambiguous branching remain open |
| 03 | CAD generator | PARTIAL | FeatureHistory regeneration, durable revisions/cache, local service, immutable backend add/replace/remove operations and revision-safe loopback edit API exist; real-browser editing coverage now passes; FeatureHistory v1.1 backend model/editor/regeneration is implemented in PR #163 pending merge; revision-safe service/API/workbench integration, undo/redo, branching/merging and broader CAD/kernel/UI capabilities remain open |
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

- CAD-EDIT-005 — suppression semantics contract merged in PR #162. Backend model/editor/regeneration implementation is in PR #163; exact-head validation is pending.
- CAD-EDIT-006 — add revision-safe service/API operations for suppress/unsuppress, preserving expected-revision compare-and-swap, strict request parsing and historical-revision read-only behavior. Keep UI/browser work separate.


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
- PR #163 is open; verify latest exact head and all CI before merge.
