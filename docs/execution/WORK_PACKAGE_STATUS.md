# Work Package Status Register

**Baseline integration branch:** `docs/phase-0-complete-requirements`  
**Last verified integration baseline:** `c14cde5eacfa31b1ebc5be0ec3641610ecceb4de` (PR #233 squash merge)  
**Audit date:** 2026-11-10  
**Status:** INCOMPLETE — evidence-based register; update after each verified implementation slice.

| WP | Domain | Current status | Evidence / next action |
|---|---|---|---|
| 01 | Core architecture | PARTIAL | Existing contracts and engineering core; audit module runtime boundaries and missing platform orchestration |
| 02 | CAD geometry | PARTIAL | Bounded exact faceted Boolean pipeline and invocation-wide resource accounting exist; arbitrary branching/tangencies, nested material islands and broader independent adversarial coverage remain open |
| 03 | CAD generator | PARTIAL | FeatureHistory workflows and bounded extrusion/Boolean services exist; general parametric feature generation, recompute propagation and broader interchange remain open |
| 04 | Mechanics | PARTIAL | Mechanism schema, loop closure, mobility and caller-driven kinematics exist in bounded scopes; broader spatial solver/dynamics remain open |
| 05 | Physics | PARTIAL | Central registry, three bounded analytical solvers, reference catalogue, boundary-condition/assumption evidence and bounded linear algebra tests exist; conservation validation, uncertainty, convergence and FEA/CFD remain open |
| 06 | Hardware/electronics | PARTIAL | Hardware, schematic and conservative static ERC foundations exist; component intelligence, measured diagnostics and simulation remain open |
| 07 | Schematic/PCB | PARTIAL | Schematic/netlist and layout foundations exist; complete PCB workflows and export/validation remain open |
| 08 | Drivers | PARTIAL | Driver contracts and implementation exist; inventory/reuse existing Driver Generation; no duplicate generator or physical I/O capability is claimed |
| 09 | Module runtime | PARTIAL | Windows Job Object process-tree implementation and acceptance tests authored on PR branch; exact-head Windows CI pending. Worker IPC, ModuleRuntime integration, worker-owned lease lifecycle, fault-injection coverage and OS sandboxing remain open |
| 10 | System understanding | PARTIAL | Architecture/evidence contracts exist; authorized discovery, indexing and governed adaptation need end-to-end evidence |
| 11 | API/CLI/UI | PARTIAL | CAD loopback HTTP API and local workbench exist; broader stable platform API/CLI/UI integration remains open |
| 12 | Platform integration | PARTIAL | Several cross-module integrations exist; end-to-end user workflows and platform matrix remain open |
| 13 | Security/quality | UNKNOWN / PARTIAL | Python CI and JS syntax checks exist; real Chromium E2E is established for CAD workbench; full dependency, license, secret and OS-isolation audits are not established |
| 14 | Final verification | FAIL / INCOMPLETE | Full repository completion gates are not met; continue evidence collection and implementation |

## Latest verified implementation slices — 2026-11-10

| PR | Scope | Exact PR head / merge | Evidence | Status |
|---|---|---|---|---|
| #228 | Invocation-wide Boolean resource accounting | merge `86338231badc850a642e9aa347a3cbedb1e27e01` | PR-head and post-merge `python-tests`, `workflow-sanity`, Chromium E2E PASS | PASS for bounded resource ledger |
| #230 | Supported exact XOR topology; fail closed for branching/intersecting non-manifold case | merge `2c9a04670fa459f2e42d9a20a9e22db0c8be7dc5` | PR-head and post-merge Python/workflow-sanity PASS | PASS for supported test matrix; kernel remains PARTIAL |
| #232 | Independent reference cases for built-in analytical Physics solvers | merge `2636c181f7ca31523d0b0749feacce933bcd973d` | PR-head and post-merge Python/workflow-sanity PASS | PASS for three bounded analytical solver families |
| #233 | Linear algebra exact reference, pivoting, singular rejection, residual and Physics evidence metadata | head `58d94aa0150d0bc8ccc752bd1b3aeef05f8354cd`; merge `c14cde5eacfa31b1ebc5be0ec3641610ecceb4de` | Exact-head run `42745104718`: Python and workflow-sanity PASS; 0 review threads; mergeability true. Post-merge run `42790385802` was QUEUED at audit time. | PASS for bounded test/documentation slice; post-merge CI UNKNOWN/PENDING |

**Guardrails:** PR #231 is excluded from the main roadmap work-package count as requested. PR #229 was closed without merge after unsupported topology failed validation. A skipped or missing check is never PASS. The integration branch is not `main`; do not promote or merge to `main` without separate approval.

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


## CAD-EDIT-011 — Undo/Redo workbench (PR #171) — PASS

- PR #171 merged at `21bee045ea4d06aa07c7130f9123afaa64372638`.
- Exact PR-head and post-merge CI: workflow-sanity PASS; python-tests PASS (865 tests); Chromium E2E PASS (6 tests).
- Browser coverage checks multi-step Undo/Redo, reload persistence, historical read-only gating, redo invalidation after a new edit and revision-option readiness.
- Status: PASS for end-to-end FeatureHistory Undo/Redo; WP-03 overall remains PARTIAL.


## FeatureHistory Branch/Fork/Merge — end-to-end (PRs #175–#180)

- PR #175: branch/merge contract; merged.
- PR #176: additive SQLite branch catalog and immutable fork creation; merged.
- PR #177: pure three-way merge analyzer and typed conflicts; merged.
- PR #178: transactional merge append, expected-head revalidation and provenance; merged.
- PR #179: strict loopback branch list/fork/merge API and revision provenance inspection; merged at `01d9afaeb9a7f9c3eecee7659d966bdcbae55983`.
- PR #180: branch/merge workbench and browser acceptance; merged at `6be2e6ee1fc18f4d1bfebb8ad76639aed11e4aed`.
- PR #179 exact PR-head/post-merge: workflow-sanity PASS, Python 889 PASS, Chromium 7 PASS.
- PR #180 exact PR-head/post-merge: workflow-sanity PASS, Python 889 PASS, Chromium 9 PASS.
- **Status: PASS** for bounded FeatureHistory branch/fork/merge end-to-end. Overall CAD and Universal Platform remain PARTIAL / INCOMPLETE.


## CAD B-rep topology — PR #181

- PR #181 merged at `ea9dfc13503c5d41739804e0ab5b68fe87e74d1b` (exact PR head `70be8fb3c091fd391d994da01c0fb6b4cb912dfd`).
- Schema/profile v2.0 supports polygonal planar faces and face inner loops; exact rational predicates validate planarity, loop simplicity, strict containment and orientation.
- Genus-1 square through-hole shell reference passes; v1.0 triangular snapshots remain importable.
- Exact PR-head/post-merge: workflow-sanity PASS; Python 892 PASS. Chromium E2E SKIPPED/not triggered (no UI change).
- **Status: PASS** for single-shell polygonal BRep with face holes. Multi-shell solids, general 3D Boolean and polygonal/hole mesh triangulation remain OPEN.


## CAD-BREP-002 — Polygonal and holed B-rep mesh triangulation (PR #182 PASS)

- Source: `src/universal_platform/engineering/brep.py`, `triangle_mesh_from_brep`.
- Reuses: `mesh._triangulate_profile_region` for deterministic bridge-and-ear clipping.
- Tests: `tests/test_faceted_brep.py`.
- Contract: `docs/design-3d/FACETED_BREP_MESH_TRIANGULATION_CONTRACT.md`.
- Acceptance: n-gon faces; face inner loops; preserved outer-loop orientation; no new geometric vertices; source ID/frame/unit/digest preservation; valid/watertight/consistently-oriented mesh; deterministic output; fail-closed resource limits.
- Resource bounds: 10,000 boundary vertices per face; 200,000 output triangles per solid.
- Base integration SHA: `1b67f0ae56b0d9fb2a86dc1bb0fbfe5b1a3bfa34`.
- Exact PR head: `c4c1a5c642096f2c030982c567fe308cb2df07e4`.
- Merge SHA: `9c84d4d94030c0e3084d7a288064491d8160a71f`.
- Exact PR-head workflow #42459969975: workflow-sanity PASS; Python 894 PASS (14.43s).
- Post-merge workflow #42460044330: workflow-sanity PASS; Python 894 PASS (14.56s).
- Chromium E2E: SKIPPED/not triggered because no UI surface changed.
- PR #182 merged to integration only; main unchanged.
- Status: PASS for this bounded adapter; WP-02 and repository overall remain PARTIAL / INCOMPLETE.


## CAD-BREP-BOOLEAN-001 — Arbitrary faceted Boolean design gate

- Baseline: integration SHA `2e436b34150b9e068d0a1b38a8841d5c6c0e6eec`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`.
- Contract: `docs/design-3d/ARBITRARY_FACETED_BREP_BOOLEAN_CONTRACT.md`.
- Audit: `docs/audit/REPOSITORY_AUDIT_2026-11-08_PRE_PR192.md`.
- Existing mesh intersection analysis is an exact-rational analysis API; it is not a Boolean arrangement or fragment assembly engine.
- PR #191 remains restricted to axis-aligned box outer/cavity components.
- Gate A (next implementation slice): deterministic exact triangle-pair intersection events and triangle fragment splitting for a narrow transverse-intersection profile.
- Coplanar overlap, tangency, contact branching and ambiguous boundary classification must fail closed until dedicated reference-backed gates pass.
- Status: PLANNED — documentation and acceptance contract only; no arbitrary-faceted Boolean implementation or PASS claim.


## CAD-BREP-BOOLEAN-001A — Exact transverse triangle-pair segment primitive

- Source: `src/universal_platform/engineering/triangle_intersection_events.py`.
- Tests: `tests/test_triangle_intersection_events.py`.
- Public API: `TriangleIntersectionSegment`, `extract_transverse_triangle_intersection`.
- Behavior: deterministic pair ordering; exact represented-binary64 rational endpoint construction; strict endpoint/plane/triangle checks; canonical serialization; no source mutation.
- Supported profile: proper transverse pair crossings only. Disjoint pairs return `None`; coplanar overlap, contact, duplicate/degenerate and unsupported classifications fail closed.
- Explicit non-claims: no triangle fragment splitting, point-in-solid classification, Boolean operation, or solid assembly.
- PR: #195, merged at `79cb8cce7686734e4be21a5ab0d2ff6a4ce2397b`; exact PR head `1bcfa0ceb1aab8839ec7ee5e06ae8ffe0ecc6e9e`.
- Exact-head workflow #42468475501: workflow-sanity PASS; Python tests 921 PASS (21.16s). An earlier fixture-source-kind failure was corrected before this passing run.
- Post-merge CI/status on the merge SHA: UNKNOWN; no associated run or combined status was returned. Browser E2E not triggered for this geometry-core-only change.
- Status: PASS for the narrow exact transverse segment primitive at PR head; post-merge verification UNKNOWN. Triangle splitting and Boolean operations remain OPEN.


## PR #195 post-merge evidence boundary

- Exact merge SHA: `79cb8cce7686734e4be21a5ab0d2ff6a4ce2397b`.
- Exact PR-head workflow #42468475501: workflow-sanity PASS; Python 921 PASS (21.16s).
- The available workflow query returned no post-merge run and combined commit statuses were empty; record post-merge CI as UNKNOWN, not PASS.
- Audit: `docs/audit/REPOSITORY_AUDIT_2026-11-08_POST_PR195.md`.


## CAD-BREP-BOOLEAN-001B — Exact triangle split by intersecting plane

- Source candidate: `src/universal_platform/engineering/triangle_intersection_events.py`.
- Public API candidate: `TriangleFragment`, `split_triangle_by_intersecting_plane`.
- Tests candidate: `tests/test_triangle_intersection_events.py`.
- Scope: for a properly intersecting triangle pair, split one source triangle by the full cutter-plane chord using exact-rational half-plane clipping; triangulate both convex sides deterministically; preserve source winding; verify exact area conservation and a maximum of three output triangles.
- Disjoint pairs return one unchanged fragment. Coplanar/contact/degenerate cases fail closed through the existing event contract.
- Explicit non-claims: no full-mesh arrangement, multi-plane accumulation, Boolean material classification, fragment boundary pairing or solid assembly.
- PR #197 merged at `f31ca0135cafc17c1489d88f62c09be1c18cc97e`; exact PR head `49029f71f161afe2d3ba787c66eb21bd2127c02d`.
- Exact-head workflow #42468939670: workflow-sanity PASS; Python tests 925 PASS (31.98s). An earlier fragment-side expectation was corrected before this passing run.
- Post-merge CI/status on merge SHA: UNKNOWN; no associated run or combined status was returned. Browser E2E not triggered for this geometry-core-only change.
- Status: PASS for the bounded single-plane triangle fragment splitter at PR head; post-merge verification UNKNOWN. Full-mesh arrangement and Boolean assembly remain OPEN.


## PR #197 post-merge evidence boundary

- Exact merge SHA: `f31ca0135cafc17c1489d88f62c09be1c18cc97e`.
- Exact PR-head workflow #42468939670: workflow-sanity PASS; Python 925 PASS (31.98s).
- The available workflow query returned no post-merge run and combined commit statuses were empty; post-merge CI is UNKNOWN, not PASS.
- Audit: `docs/audit/REPOSITORY_AUDIT_2026-11-08_POST_PR197.md`.


## CAD-BREP-BOOLEAN-001C — Exact multi-plane per-triangle arrangement (PR #199)

- PR #199 merged to `docs/phase-0-complete-requirements` only.
- Exact PR head: `6e4508fdf0f6f3a0a6498f916f13c2970f204523`.
- Merge SHA / integration HEAD: `bc5f2a1bffb632ef1440ea9740e69f89cf50737e`.
- Source: `src/universal_platform/engineering/triangle_fragment_arrangement.py`; tests: `tests/test_triangle_fragment_arrangement.py`.
- API: `RationalPlane`, `RationalTriangleFragment`, `arrange_triangles_by_planes`.
- Ordered exact-rational plane clipping, side provenance, source-winding preservation, exact area conservation and per-call fragment/rational-bit ceilings.
- Exact PR-head workflow #42470843529: workflow-sanity PASS; Python tests PASS. Documentation-marker step SKIPPED and not counted as PASS.
- Post-merge CI/status: UNKNOWN; no associated post-merge run or combined status was returned.
- Reviews: 0; inline review threads: 0; unresolved threads: 0.
- PASS only for the bounded per-source-triangle primitive at PR head. Global mesh arrangement, cross-facet identity/adjacency, independent coverage oracle, material classification and Boolean shell assembly remain OPEN.
- `main` unchanged at `96e75010716226037893155b9fd4b13410fb0d6f`; no branch deletion or deployment.

## Next dependency-ready CAD slice

- Global multi-triangle arrangement without float round-trips.
- Canonical global fragment/vertex identities and adjacency across source facets.
- Independent exact coverage oracle for gaps, overlaps, duplicate coverage, orientation and area.
- Aggregate resource ceilings for candidate pairs, fragments, memory and rational growth.
- Keep coplanar overlap, tangency, branching and contact fail-closed until reference-backed gates pass.


## CAD / repository progress reconciliation — 2026-11-08 (post-PR #207)

**Pinned integration baseline:** `f77e3cf7ba413c97d32c3a800e07938d50bd7ce8`  
**Main:** `96e75010716226037893155b9fd4b13410fb0d6f` (unchanged).

- **WP-02 CAD geometry — PARTIAL.** PRs #200–#206 add global exact topology, T-junction diagnostics, edge subdivision, independent coverage oracle, exact material classification, Boolean boundary selection and validated shell assembly. These are bounded primitives; automatic cross-solid intersection discovery and global face splitting remain open. Coplanar/tangential/contact/branching degeneracies remain fail-closed. Binary64 B-rep output rejects non-lossless rational coordinates.
- **WP-03 CAD Generator — PARTIAL.** PR #207 exports the Boolean pipeline and adds `CADGeneratorService.execute_prearranged_boolean`. It consumes caller-supplied complete per-face partitions; it does not compute arbitrary 3D intersections and does not add an unrestricted HTTP/browser Boolean endpoint.
- **WP-04 Mechanics — PARTIAL.** Existing normalized mechanism schema, constraints/Jacobians, loop closure, mobility and kinematics are bounded. General spatial dynamics and full solver validation remain open.
- **WP-05 Physics — PARTIAL.** Central solver registry and starter physics modules exist; coupled multiphysics and wider authoritative reference coverage remain open.
- **WP-06/07 Hardware, EDA and PCB — PARTIAL.** Driver, schematic, layout and ERC foundations exist. Full PCB workflow, electrical simulation and manufacturing/export validation remain open.
- **WP-08 Drivers — PARTIAL / SOURCE UNKNOWN.** Preserve existing driver-generation capability; identify and verify its canonical source before extending it. Do not duplicate it.
- **WP-09 Runtime — PARTIAL.** Adapter/resource/evidence/health/recovery foundations exist; OS-enforced isolation and full permission enforcement remain open.
- **WP-10/12 System understanding and platform integration — PARTIAL.** Documentation and module contracts exist; end-to-end authorized discovery/adaptation and cross-domain workflows remain unverified.
- **WP-11 API/CLI/UI — PARTIAL.** CAD loopback API and workbench exist; generalized platform API/CLI and broad integration remain open.
- **WP-13 Security/quality — PARTIAL.** Python CI, workflow sanity and Chromium E2E exist. Full dependency/license/secret audit, threat model and OS-isolation proof remain open. Inspected branch protection is disabled; required checks are not enforced by GitHub branch protection.
- **WP-14 Final verification — FAIL / INCOMPLETE.** Repository-wide requirements and acceptance gates are not all met.

PR #207 exact head `e34799b131d8bcc4e9f893529659c80f40b7bb90`: workflow-sanity PASS, python-tests PASS and Chromium E2E PASS. PR #207 merge SHA: `f77e3cf7ba413c97d32c3a800e07938d50bd7ce8`. Post-merge SHA `f77e3cf7ba413c97d32c3a800e07938d50bd7ce8`: workflow-sanity PASS, python-tests PASS and Chromium E2E PASS.

See [Repository Audit post-PR #207](../audit/REPOSITORY_AUDIT_2026-11-08_POST_PR207.md) and [Arbitrary Faceted B-rep Boolean Contract](../design-3d/ARBITRARY_FACETED_BREP_BOOLEAN_CONTRACT.md).


## Runtime / Physics integration — PR #236 candidate (in progress)

- Base integration SHA: `95253414616c992c606c0e73d69c48c30df4cd36` (PR #235 merge).
- Scope: bridge the existing three built-in analytical physics solvers through the host-controlled ModuleRuntime without duplicating solver equations.
- Candidate source: `src/universal_platform/engineering/physics_module_adapter.py`.
- Candidate tests: `tests/test_physics_module_adapter.py`.
- Contract: `docs/architecture/PHYSICS_MODULE_RUNTIME_BRIDGE.md`.
- Policy: explicit host grant `engineering.physics.solve`, canonical input units, Apache-2.0 allow-list by default, no external dependencies, retained solver evidence/limitations.
- Status: IN_PROGRESS — exact-head CI and review evidence pending. This does not establish OS isolation or general plugin loading.


## WP-09 Windows Job Object containment — design gate (2026-11-13)

- Latest verified integration baseline for this work: `c3d9800ebb46caff38bf18c13142e218ee2c6c63` (PR #240 merge).
- Existing supervisor behavior was re-read at this baseline: POSIX process-group cleanup exists; Windows uses `CREATE_NEW_PROCESS_GROUP` and terminates only the direct child.
- PR #241 adds a Windows CI job only. Its exact head `cb8ed040d3a7612468d08ddfe455e17fc2ada7b4` has CI PASS, but it has 0 formal review submissions; no Windows Job Object implementation is present.
- Added `docs/runtime/WINDOWS_JOB_OBJECT_CONTAINMENT_CONTRACT.md` on branch `docs/wp-09-windows-job-object-contract`.
- Contract requires race-free suspended process creation, Job Object assignment before the primary thread resumes, kill-on-close, fail-closed assignment errors, explicit handle ownership, descendant/pipe cleanup tests and no false sandbox/resource-enforcement claims.
- This is a documentation/design gate only. Windows Job Object implementation, worker protocol, ModuleRuntime integration and lease retention until confirmed worker termination remain OPEN.
- Validation of this documentation slice: PR #242 exact-head run `43278690197` completed successfully: `python-tests` PASS and `workflow-sanity` PASS; its documentation-only marker step was SKIPPED and is not counted as PASS. This run is not evidence for this new branch.
- Status: DESIGN CONTRACT ADDED; implementation and this branch's CI are UNKNOWN/PENDING until a PR is opened and its exact-head workflows complete.


## WP-09C — Windows Job Object process-tree containment (implementation branch)

- Branch: `feat/wp-09-windows-job-object`, based on the WP-09 contract branch head `1ff4a0515d560466171b4cca7218e1693352d589`.
- Added `src/universal_platform/runtime/windows_job.py`: private kill-on-close Job Object; suspended-process assignment; primary-thread invariant check; process-tree termination; OS active-process query; bounded wait and handle cleanup.
- Updated `src/universal_platform/runtime/supervisor.py`: Windows process creation uses CREATE_SUSPENDED, assignment precedes resume, timeout/cancel target the job, normal root exit waits for descendants, and cleanup raises if OS job emptiness cannot be confirmed.
- Added Windows tests for root-exits-first grandchild cleanup, assignment failure without worker execution, timeout of descendants and cancellation of descendants; strengthened WorkerSpec container validation.
- Added `windows-process-supervisor` CI job on `windows-latest` / Python 3.12.
- Added `docs/runtime/WP09_RUNTIME_FUNCTION_AUDIT.md` with a function-by-function audit of WorkerSpec, WindowsJob, PythonProcessSupervisor, ModuleRuntime and ResourceAllocator.
- Exact implementation head at audit preparation: pending final PR creation; no CI evidence yet. All Windows-only tests are skipped on non-Windows and are not counted as PASS.
- Current maturity: IMPLEMENTATION AUTHORED / CI UNKNOWN. WP-09 remains PARTIAL.
- Explicit remaining work: fault injection for API/handle/reader failures; remove or formally support private `Popen._handle`; versioned worker IPC; ModuleRuntime process dispatch; lease held until process tree empty; crash recovery; security review. No sandbox or OS resource enforcement is claimed.
\n\n## WP-09D — Versioned Worker IPC framing (in progress, 2026-11-13)\n\n- Base: WP-09C merge `b6e02988b009754fbf0ccdfc032c33174355e5c6`.\n- Branch: `feat/wp-09d-versioned-worker-ipc`.\n- Added `src/universal_platform/runtime/worker_protocol.py`: version 1.0 envelope, length-prefixed UTF-8 JSON frames, strict message types, bounded request IDs and configurable maximum frame size.\n- Decoder rejects malformed/truncated/oversized frames, duplicate keys, unknown fields/versions/types and non-finite JSON values; clean EOF is distinct from partial data.\n- Added `tests/test_runtime_worker_protocol.py` covering the framing and failure paths.\n- This slice is transport-only. ModuleRuntime dispatch, process launch/IPC wiring, host-side schema/permission checks, cancellation correlation, crash semantics and lease coupling remain OPEN.\n- Exact-head CI and review: PENDING. WP-09 remains PARTIAL.\n