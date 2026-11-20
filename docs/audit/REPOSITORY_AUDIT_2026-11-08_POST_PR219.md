# Repository Audit — 2026-11-08, post-PR #219

**Repository:** `phakphum12345/universal-platform`  
**Integration branch:** `docs/phase-0-complete-requirements`  
**Pinned integration SHA:** `972f5d5787cb0f70c3f3200dd942f6b8329f08bf`  
**Main SHA:** `96e75010716226037893155b9fd4b13410fb0d6f` (unchanged)  
**Audit method:** GitHub API source/tree/PR/check-run inspection. No local working tree was available through this audit.

## 1. Repository state

- Recursive tree at the pinned integration SHA: 373 files; 150 Markdown, 191 Python and 26 JSON; tree response was not truncated.
- Open PRs at the snapshot: 0. PRs #217, #218 and #219 are merged into the integration branch.
- Main was not changed, and no deployment was performed.
- The branch metadata reports `protected=false` for the integration and main branches; required status checks are not enforced by branch protection.

## 2. Recent exact-SHA evidence

| PR | Change | Exact PR head | Exact-head checks | Merge SHA | Post-merge checks |
|---|---|---|---|---|---|
| #218 | Aggregate Boolean ray/classification work, coplanar contact work, input preflight and work counters | `b2fcc5701d066875b6161a733a23aa7439a6caf6` | workflow-sanity PASS; python-tests PASS; Chromium E2E PASS | `f2bbaf2f4868412020051c58762e2337af3a1a25` | workflow-sanity PASS; python-tests PASS; Chromium E2E PASS |
| #219 | Correct conservative global topology scan budget to charge all 3 edges of every raw fragment against all global vertices | `92726f669bb2cc5b522d9c6ebe1d0576e8fc978c` | workflow-sanity PASS; python-tests PASS | `7a0d2a21d05709ccfead7f95e57349310c878a58` | workflow-sanity PASS; python-tests PASS |
| #217 | Concave-prism Boolean exact-or-fail-closed regression and coplanar cutter boundary refinement | `921de7c2013183abd770acde714adc3b7680738b` | workflow-sanity PASS; python-tests PASS | `972f5d5787cb0f70c3f3200dd942f6b8329f08bf` | workflow-sanity PASS; python-tests IN_PROGRESS at this snapshot |

No missing, skipped or untriggered check is counted as PASS. PR #217 is merged; post-merge Python CI is still IN_PROGRESS at this snapshot.

## 3. CAD Boolean capability status

| Work item | Evidence / implementation | Assessment |
|---|---|---|
| Independent exact coverage oracle | PRs #203 and #212; exact containment, coplanarity, overlap, duplicates and area checks | PASS for bounded per-source-triangle partitions |
| Input and rational resource validation | PR #213; direct plane validation and rational bit limits | PASS for implemented bounds |
| Aggregate Boolean work budgets | PR #218; ray/triangle, coplanar contact and input preflight budgets | PASS for tested aggregate limits |
| Global topology scan budget | PR #219; charges 3 fragment edges per raw fragment against every global vertex | PASS for the corrected conservative bound |
| Material classification | PR #204 and #211; exact INSIDE / OUTSIDE / BOUNDARY / UNKNOWN and two-sided witnesses | PASS for bounded supported inputs |
| Boolean boundary selection | PR #205 and #211; UNION / INTERSECTION / DIFFERENCE / SYMMETRIC_DIFFERENCE | PASS for bounded arrangements |
| Shell assembly | PR #206; edge incidence, orientation, connected shells, cavity ownership, exact volume and B-rep validation | PASS for bounded binary64-representable outputs |
| CAD Generator integration | PRs #207 and #210; in-process service orchestration and tested box workflows | PASS for named reference fixtures |
| Concave-prism adversarial coverage | PR #217; exact-or-fail-closed test | PENDING exact-head Python CI at this snapshot |
| Exact rational output model | [Exact Rational Faceted Output Contract](../design-3d/EXACT_RATIONAL_FACETED_OUTPUT_CONTRACT.md) | DESIGN ONLY; not implemented |

### Explicit CAD limitations

- The public B-rep and mesh schemas use binary64 coordinates. Exact rational shell coordinates that do not round-trip losslessly are rejected. They are never rounded or tolerance-welded.
- The concave-prism test has exposed rational coordinates such as thirds/sixths in the arrangement. The exact rational output profile is required before such results can be emitted as a durable solid.
- Point/edge-only coplanar contact, arbitrary tangencies, branching and unsupported degeneracies remain fail-closed.
- Nested positive material islands and generalized shell-parent semantics remain unsupported.
- The coverage oracle certifies each source triangle partition; it is not a universal proof of all global arrangements for arbitrary multi-solid topology.
- The current CAD Boolean service is in-process/offline. No unrestricted Boolean authoring HTTP/browser endpoint is established.
- The reference corpus is evidence for named cases, not proof of unrestricted arbitrary-faceted B-rep Boolean support.

**CAD verdict:** PASS for the explicitly bounded reference cases and fail-closed rules; PARTIAL / INCOMPLETE for arbitrary faceted Boolean.

## 4. Cross-domain repository inventory

This is a targeted source and documentation inventory, not a complete runtime, hardware or security certification.

| Work package | Current evidence | Remaining work | Status |
|---|---|---|---|
| Core / UEIC | Module registry, contracts, provenance and safety gates | Governed end-to-end orchestration and lifecycle | PARTIAL |
| Mechanics | Normalized mechanism schema, constraints/Jacobians, loop closure, mobility and kinematics | General spatial solving, dynamics, singularity/reference coverage and cross-domain coupling | PARTIAL |
| Physics | Solver registry; axial stress, Ohm's law and linear thermal expansion | More authoritative reference cases and coupled multiphysics | PARTIAL |
| Hardware / EDA | Driver, schematic, layout and ERC foundations | EDA interoperability, simulation, PCB manufacturing/export and electrical/thermal validation | PARTIAL |
| Driver architecture | Existing driver-related sources and contracts | Verify canonical generic Driver Generation source and supported OS/device matrix; do not duplicate it | PARTIAL / SOURCE UNKNOWN |
| CAD / 3D | Mesh, B-rep, planar Boolean, feature history, faceted Boolean and generator service | Exact rational output, degeneracies, wider adversarial corpus and authoring integration | PARTIAL |
| Runtime / adapters | Resource adapters, recovery, evidence and health foundations | OS-enforced sandboxing, permission boundaries and adversarial resource tests | PARTIAL |
| API / UI | Loopback-only CAD API and FeatureHistory workbench | Cross-domain APIs, CLI and generalized end-to-end user workflows | PARTIAL |
| Security / release quality | Python CI, workflow sanity and selected Chromium E2E | Dependency/license/secret audit, threat model and branch-protection evidence | PARTIAL |
| Repository-wide acceptance | Documentation and domain inventories | Requirement-by-requirement acceptance on exact SHAs across all domains | INCOMPLETE |

## 5. Required next sequence

1. Finish PR #217 exact-head Python tests; inspect reviews, threads, exact base/head SHAs and mergeability; merge only to integration if all required checks pass.
2. Implement the versioned exact rational faceted output profile from the linked contract, preserving legacy binary64 schemas.
3. Add exact rational shell/self-intersection validation and deterministic serialization, with resource ceilings and tamper tests.
4. Expand adversarial Boolean cases: multiple crossings per face, rotated/concave solids, cavities, disconnected outputs, thin features, input-order invariance and supported/unsupported degeneracies.
5. Reconcile the latest exact SHA, PR evidence, implementation status and requirements traceability.
6. Continue the Mechanics, Physics, Hardware, Drivers, Runtime, API/UI, security and licensing audits.
7. Run exact-head and post-merge checks for every change. Keep `main` unchanged unless separately authorized.

## 6. Evidence semantics

- **PASS** requires implementation plus exact-SHA tests and applicable post-merge evidence.
- **FAIL** records a demonstrated failing gate or unsupported case.
- **SKIPPED** and missing/untriggered checks are not PASS.
- **UNKNOWN** remains UNKNOWN when evidence or access is unavailable.
- A bounded fixture does not establish universal capability.

**Overall repository status: INCOMPLETE.** No deployment or promotion to `main` is authorized by this audit.
