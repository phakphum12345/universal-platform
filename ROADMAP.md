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

PRs #32–#38 are complete and merged on `docs/phase-0-complete-requirements`: generalized coordinates (#32), generated joint constraints (#33), numerical constraint Jacobian (#34), geometry-aware loop evaluation (#35), fixed-body-pose coordinate fitting (#36), spatial local mobility (#37), and cross-discipline reference validation (#38). Their exact merge commits and post-merge check runs are recorded in the engineering phase plan and traceability ledger. PR #39 was used for the offline module metadata registry, not a spatial-joint implementation. The spatial-joint reference/foundation gap is closed by PR #54 at `22bbf1714224095cfd652d6887130d26facef087`. Exact PR-head run #404 (`42193562931`) passed both jobs with 452 tests; post-merge run #405 (`42193654653`) on the exact merge SHA passed both jobs with 452 tests. The suite covers all eight declared joint kinds, generated six-component residuals, finite-difference Jacobian references, local spatial mobility/rank, ground-link reversal and nontrivial joint-frame placement composition. PR #56 now implements explicit 2D PLANAR mobility: a plane-to-world frame, body/joint coplanarity and axis checks, and a projected three-variable-per-link Jacobian. PR #56 merged at `8335515b31a89efc4cacb70cf9c2e3aeb4ae16d4`. Exact PR head `8b76f89687c4685c66fee5f8bc9cd045bd589abe`; run #459 (`42197011073`) passed `workflow-sanity` and `python-tests` with 462 tests. Exact post-merge run #461 (`42197156442`) on the merge SHA passed both jobs with 462 tests.

PR #49 (profile extrusion) is integrated at `bfc3e6585106c73b29297cbda2ab9ec9d50340db`. PR #52 integrated the through-hole extension and public exports at `1d1628175dafca3f5d4d3d6b5cf01e241ec75afa`. Exact PR-head run #384 (`42191597715`) passed both jobs with 425 tests; post-merge run #385 (`42191666816`) on the exact merge SHA passed both jobs with 425 tests. The PR #50 implementation was ported because its original stacked feature branch was not an ancestor of the integration branch. PR #51's documentation index was restored to the integration line by PR #53 at `1db066915c4993e544b386c0311e332874ef4aed`; PR #53 exact head run #401 (`42192288446`) and post-merge run #402 (`42192465566`) both passed 425 tests.

Next repository-wide work is driven by the capability audit: general CAD Boolean topology beyond convex 2D cells; mesh generation and independent STL/STEP interchange; sketch constraints/feature history; schematic EDA exchange and circuit simulation; datasheet-backed electrical constraints; validated solver adapters for additional physics domains; and module runtime/isolation only after separate security and permission contracts. Each item remains PLANNED/PARTIAL until implemented and reference-tested. PR #56 closes the explicit planar plane-frame mobility gap but not general multibody dynamics or global configuration solving.


PR #35 — Geometry-aware loop-closure evaluation — merged at `223740381b81fc06a292eb90ba0653b27cbe8e7a`; exact PR-head run #283 and post-merge run #284 passed 253 tests each. This validates supplied configurations only and does not imply nonlinear configuration search or physical feasibility.


PR #36 — Geometric loop coordinate fitting — adds local bounded generalized-coordinate fitting for caller-supplied fixed body poses using all generated joint residuals. Body-pose solving and global reachability remain outside this increment.


PR #36 — Geometric loop coordinate fitting — merged at `d7b740fc98d396c130f1c17b3c6487b30b599c2c`; exact PR-head runs #288/#289 and post-merge run #290 passed 258 tests. This is a fixed-body-pose coordinate solver, not a general mechanism configuration solver.


PR #37 — Generated spatial Jacobian mobility — automatically derives local spatial mobility from joint residuals and finite-difference Jacobians, using body-pose tangent variables plus independent joint coordinates with ground pose elimination. The separate explicit PLANAR formulation is implemented by PR #56.


PR #37 — Generated spatial Jacobian mobility — merged at `41d81818385dd82497840ce93ce5aac60e3216da`; exact PR-head runs #293/#294 and post-merge run #295 passed 265 tests each. The generated adapter supports SPATIAL and explicit plane-frame PLANAR formulations; PLANAR rejects unsupported joint families and out-of-plane geometry.


PR #38 — Cross-discipline engineering reference validation — add versioned reference data and executable checks for dimensional, mechanics, electrical, thermal, geometry, transform, linear solver, static algebraic simulation, kinematics, material record, assembly, constraint and safety-boundary behavior.


PR #38 — Cross-discipline reference validation pack — merged at `587bd503dad3f6d4f66c99fe08e39e20a65c5265`; exact PR-head run #297 and post-merge run #298 passed 285 tests.


## Hardware schematic rendering increment — PR #59 merged

- Add a separate versioned layout contract rather than overloading the normalized connectivity graph.
- Implement supplied symbol geometry, explicit page-space millimetres, component placement/rotation, pin anchors and explicit routes.
- Render deterministic offline SVG and distinguish completely routed nets from incomplete ones.
- PR #59 merged at `2fd7b3144ed38491f11c6dfefa8bb793f1a2cc21`; final PR head `70003c5ec985fe487471bd68996cfb60e501f7a7`; PR head runs `42203797877` and `42203791191` passed; post-merge run `42205768788` passed both required jobs.
- Remaining hardware roadmap: symbol/library import and EDA exchange; electrical rule checking; power-domain and component-rating validation; circuit simulation; BOM/footprint reconciliation. These remain separate requirements and are not implied by SVG rendering.


## Hardware verification increment — PR #60 merged

- PR #60 merged at `e641ca19b4f28bb2e2077cf475b371125ebf237a`; exact PR head `052b48be982c09cc10deeba0f173aa493432681d`; PR and push runs `42206594529` / `42206646922` passed; post-merge run `42206719188` passed both jobs with 485 tests. Adds versioned static ERC result schema and deterministic offline rules over normalized SchematicModel v1.0.
- Rules: unconnected non-NO_CONNECT pins; multiple push-pull outputs; multiple declared power sources; power inputs without a declared POWER_OUT; power inputs mixed with signal drivers; open-drain/open-collector nets without a declared POWER_OUT.
- Record canonical input SHA-256, stable finding IDs, rule versions, severity, affected objects, evidence, recommendations and explicit limitations.
- No voltage/current/thermal/timing analysis, external standards, passive pull-up inference, waiver ledger, circuit simulation, physical verification or hardware operation.
- Follow-up roadmap remains: datasheet-backed power-domain/rating checks; EDA symbol/library import and exchange; circuit simulation; BOM/footprint reconciliation.



## CAD topology increment — PR #61 merged

- PR #61 merged at `5f1612ec40a4e6d0f89ee7b419e5add02120f5dc` into `docs/phase-0-complete-requirements`.
- Exact PR head `29e846f513f489196ff742ed464c983a8a771225`; PR workflow run #42207436743 and push run #42207398485 passed both required checks; PR-head test evidence: 496 passed.
- Exact post-merge run #42217655332 on the merge SHA passed `workflow-sanity` and `python-tests`; **496 passed in 1.19s**.
- Adds dependency-free UNION, INTERSECTION and DIFFERENCE over convex simple polygon loops, deterministic convex-cell decomposition, schema v1.0, area accounting and strict snapshot validation.
- Deliberate limits remain: no concave loops, holes, arcs, exact arithmetic, general planar arrangements, 3D B-rep or mesh Booleans.

## CAD general planar topology — PR #62 merged (design only)

- PR #62 merged at `213b1b52ef78ae3297a88892b4cc0c6539159160`; base `5f1612ec40a4e6d0f89ee7b419e5add02120f5dc`, head `d03928bbe3472fae4f5890f6a9f481c0049b7f35`.
- PR and push runs #42217964997 / #42217937596 passed both required jobs with 496 tests; exact post-merge run #42218707816 passed both jobs on the merge SHA with **496 tests in 1.08s**.
- Adds the CAD-neutral general planar region/hole topology contract, explicit frame/unit identity, contact semantics, numerical robustness tiers and replaceable-kernel decision gate.
- Design only: no general polygon Boolean implementation, precision policy selection, kernel selection or third-party dependency is claimed.
- Next implementation gates: evaluate candidate kernels against the reference corpus and license/offline/platform requirements; implement an isolated adapter only after evidence and approval; then add mesh generation and independent interchange validation.



## PR #64 — Deterministic primitive triangle mesh (MERGED)

- PR #64 merged at `f0bfd8ad9958af9bfe678e923d52726b12eee73a`; exact head `8fe9db48cd07a66ea39d61e386ee8f362b968104`.
- Exact PR/push runs #42219983207 / #42219977049 passed both required jobs with 506 tests; exact post-merge run #42220119818 passed both jobs with **506 tests in 1.93s**.
- Adds dependency-free deterministic BoxSolid/CylinderSolid tessellation, source SHA-256 provenance, local frame/unit, explicit cylinder chordal tolerance, versioned schema and structural mesh validation.
- Scope remains Box/Cylinder only. Extruded-profile and hole meshing, arbitrary mesh self-intersection detection/repair, B-rep, 3D Boolean and STEP/STL/3MF interchange remain unsupported.


## PR #66 — Straight extruded-profile triangle mesh (MERGED)

- PR #66 merged at `1ead537afa34d2637fdb08f91b2d2bb823d411a0`; exact corrected head `1179fb69114bc76b3155d0c3e6edf50223050846`.
- Exact PR/push runs #42221102000 / #42221092727 passed both required jobs with 511 tests; exact post-merge run #42221247498 passed both jobs with **511 tests in 1.20s**.
- Adds deterministic ear-clipped caps and outward side walls for straight-edged, hole-free concave/convex ExtrudedProfileSolid.
- A clockwise-input side-wall winding defect on the first tested head was corrected; the final exact head passes the retained CW/CCW regression.
- Profile holes/arcs, arbitrary mesh self-intersection/repair, B-rep, 3D Boolean and neutral CAD interchange remain unsupported.


## PR #68 — Polygonal through-hole extrusion meshes (MERGED)

- PR #68 merged at `6ec9ba1367c22c0a14d293e57ed2d538ebfc654b`; exact corrected head `da5c8a292dacf8c300fcb48b9e92b506f1172bd8`.
- Exact PR/push runs #42222216690 / #42222207986 passed both required jobs with 514 tests; exact post-merge run #42222360177 passed both jobs with **514 tests in 1.53s**.
- Adds deterministic visible-bridge selection and ear clipping for one or more strictly-contained polygonal holes, with CW inner walls facing the void.
- Initial inner-wall winding/volume failures were corrected on the final tested head; one-hole, multiple-hole and reversed-hole-winding regressions remain.
- Curved outer/hole boundaries, arbitrary mesh self-intersection/repair, B-rep, 3D Boolean and neutral CAD interchange remain unsupported.


## PR #70 — Circular-arc profile triangle meshes (MERGED)

- PR #70 merged at `98440851b0b75216ea89013d9d2eea07b42c4416`; exact PR head `0e7d7233069e2fafb8850a15d1f1e1539bf6c883`; base `c1056671b7ad8a8ca1415a449d830db0057f5034`.
- Exact PR workflow run #42223197118 and push run #42223188816 passed both required checks with **515 tests**; exact post-merge run #42223460020 passed both checks with **515 tests in 2.01s**.
- Adds deterministic circular-arc boundary sampling for extruded profiles and polygonal holes under explicit positive chordal tolerance in source length units, preserving endpoints, frame/unit and source SHA-256 provenance.
- Per-arc subdivision uses the radial chord-deviation bound and a 100,000-segment ceiling. The result is an approximation, not exact B-rep geometry.
- Non-circular curves/splines, general mesh self-intersection/repair, B-rep, 3D Boolean and STEP/STL/3MF interchange remain unsupported.

## PR #71 — Circular-arc through-hole mesh reference (MERGED)

- PR #71 merged at `8aba562a1df6c0691c855f95ef16a9ba94089556`; exact PR head `d94d9c3b974e3ceea70ddf4a8a1b18da92b8c845`; base `98440851b0b75216ea89013d9d2eea07b42c4416`.
- Exact PR workflow run #42225768304 passed `workflow-sanity` and `python-tests`; **516 passed in 1.74s**.
- Exact post-merge run #42225830931 on the merge SHA passed both required jobs; **516 passed in 1.45s**.
- Adds a regression for a curved polygonal hole: watertight edge incidence, consistent winding, positive volume, chordal-area bound, endpoint retention, deterministic output and strict round trip.
- This closes the missing hole-arc reference in the PR #70 implementation; it does not broaden support to non-circular curves or general mesh repair.

## PR #73 — Binary STL interchange contract (MERGED)

- PR #73 merged at `24f0b7083d95fb5582e26f4614a227250e0a2de0`; exact PR head `39f3325260baa084d8e817554a9c9fd1702922c0`; base `6cdfffc8d9fffadb7162977c77efd54445bb9471`.
- Exact PR workflow #42226759918 and push workflow #42226749519 passed both required checks with **516 tests**; PR test log: 516 passed in 2.11s.
- Exact post-merge run #42226889599 passed `workflow-sanity` and `python-tests` on the merge SHA; **516 passed in 1.11s**.
- Defines deterministic binary STL export with a mandatory metadata sidecar, explicit frame/unit/provenance/tolerance, SHA-256 binding, binary32 quantization, resource limits and independent test-reader requirements.
- Design only; no STL exporter/importer, STEP/3MF support, third-party runtime dependency or external CAD toolchain selection is claimed.

## PR #74 — Deterministic binary STL export (MERGED)

- PR #74 merged at `1503266c18c5ed74c5756391c033437b05ae6f13`; exact PR head `e7491d976177a51933f62e5eefcab90d11dcc19f`; base `24f0b7083d95fb5582e26f4614a227250e0a2de0`.
- Exact PR workflow #42227530004 passed both required checks with **523 tests in 1.61s**; exact push workflow #42227459289 passed both checks with **523 tests in 1.12s**.
- Exact post-merge run #42227796004 passed both required jobs on the merge SHA; **523 tests in 1.31s**.
- Adds deterministic binary STL export, strict sidecar manifest v1.0, source frame/unit/provenance/tolerance, payload SHA-256, measured binary32 quantization error, caller-context validation and a 1,000,000-facet ceiling.
- Independent test-only parser covers Box, Cylinder, straight-hole and circular-arc-hole output. Arbitrary STL import and external CAD application reopen remain unsupported.

## PR #75 — Independent STL geometric reopen references (MERGED)

- PR #75 merged at `a8a7e6b28650a90665a465e7373d8ad6582f7832`; exact PR head `0d17638b6c361abfed7d0501576b0bc7de277809`; base `1503266c18c5ed74c5756391c033437b05ae6f13`.
- Exact PR workflow #42228344477 passed both jobs with **524 tests in 2.09s**; exact post-merge run #42228462537 passed both jobs with **524 tests in 2.20s**.
- Independent reader now computes quantized bounds and signed volume directly from serialized facet records using a coordinate-error-derived volume bound; corrupt NaN coordinates and inconsistent normals are rejected even with recomputed payload digests.

## PR #76 — Mesh geometric topology analysis contract (MERGED)

- PR #76 merged at `ff486f8ae4569ca8122f0294f55d18b21b32d10c`; exact PR head `526a2cb0632154e52596e3322a107ee8dddc4d4d`; base `a8a7e6b28650a90665a465e7373d8ad6582f7832`.
- Exact PR workflow #42229095708 and push workflow #42229046675 passed both required jobs with **524 tests in 2.25s**; exact post-merge run #42229207672 passed both jobs with **524 tests in 1.60s**.
- Defines additive diagnostics for edge-connected components, vertex-link manifoldness, unused vertices, exact/near-coincident coordinates and explicit UNKNOWN self-intersection status.

## PR #77 — Mesh geometric topology analysis implementation (MERGED)

- PR #77 merged at `20e34933087a7276d0acc08e0d17b872c3973949`; exact PR head `66593ebb6658f0e0fc43d17f90b6c8360e5969d2`; base `ff486f8ae4569ca8122f0294f55d18b21b32d10c`.
- Exact PR workflow #42230501005 and push workflow #42230490785 passed both required jobs with **533 tests in 2.08s**; exact post-merge run #42230654227 passed both jobs with **533 tests in 1.98s**.
- Adds MeshTopologyAnalysis v1.0 and analyze_mesh_topology without changing validate_triangle_mesh. Reports source/frame/unit/digests, edge-connected face components, vertex-link manifoldness, exact/near-coincident groups, unused vertices and stable issue codes.
- Near-coincident grouping uses explicit source-unit tolerance, deterministic 3D buckets and a 5,000,000 neighbor-comparison ceiling; no welding/snap/repair.
- Self-intersection status remains UNKNOWN.

## PR #78 — Triangle-mesh self-intersection contract (DESIGN ONLY)

- Defines separate MeshIntersectionAnalysis semantics, deterministic AABB broad phase, exact represented-input predicate policy, shared-edge/shared-vertex adjacency exceptions, resource-limit UNKNOWN behavior and an independent rational reference corpus.
- Keeps PR #77's MeshTopologyAnalysis v1.0 backward compatible with self_intersection_status UNKNOWN.
- No triangle-triangle intersection implementation or PASS claim is made by this design PR.

## Next repository increments

1. Implement triangle-triangle self-intersection according to PR #78; retain UNKNOWN until the exact-predicate and adversarial corpus pass.
2. General planar-region Boolean operations beyond convex loops, with a selected precision policy and independent adversarial reference corpus.
3. Neutral CAD interchange (external STL import and STEP/3MF) with independent external-tool reopen validation.
4. Parametric sketch constraints, solver diagnostics and versioned feature history with deterministic recomputation.
5. Hardware EDA symbol/library exchange, BOM/footprint reconciliation, datasheet-backed electrical limits and circuit simulation.
6. Additional validated physics/solver adapters with independent domain reference cases.
7. Module runtime invocation, permissions, sandboxing, quotas, cancellation and audit only after threat model and isolation contracts are implemented and tested.





## Repository audit baseline — 2026-11-06

- Integration branch exact SHA: `502d49baf58e43938d2746859e10817badd43f6e`; `main` remains `96e75010716226037893155b9fd4b13410fb0d6f` and is 229 commits behind the integration branch.
- PR #78 is merged as a design contract only. Its exact PR-head workflow passed; post-merge CI for the integration SHA is UNKNOWN.
- First implementation gate: PR #80, triangle-mesh self-intersection analysis. Keep the result additive and preserve MeshTopologyAnalysis v1.0 semantics.
- Subsequent gated work: general planar topology/Boolean operations; B-rep and neutral CAD import/export; parametric sketch and feature history; EDA interchange and electrical/circuit validation; domain-validated physics adapters; secure module runtime; then end-to-end API/CLI/UI integration.
- This is a proposed dependency sequence, not evidence that these features already exist. Each item remains PLANNED until source, tests and exact-SHA evidence are inspected.
- See [Repository Audit 2026-11-06](docs/audit/REPOSITORY_AUDIT_2026-11-06.md) for scope, evidence and limitations.


## PR #80 — Triangle-mesh self-intersection analysis (IMPLEMENTED)

- Merged at `cb91c7c49406fd02324be6b30d5570e821b4d503`; exact PR head `009ab1b24578579c0f6c6bbf3d4f8e3ee42fc181`.
- Exact PR workflow #42238370626 passed workflow-sanity and python-tests with 550 tests; push workflow #42238360081 passed both required jobs.
- Adds `MeshIntersectionAnalysis v1.0` and `analyze_mesh_intersections`, with deterministic conservative sweep, exact rational predicates, stable classifications, source digests, strict schema and fail-closed resource limits.
- `MeshTopologyAnalysis v1.0` remains unchanged; its `self_intersection_status` remains UNKNOWN. Intersection results are a separate analysis.
- Post-merge CI on the integration SHA is UNKNOWN; do not mark this evidence PASS.

## Next gated increment

General planar-region Boolean topology beyond convex loops is next, but implementation must wait for an explicit precision policy and independent adversarial reference corpus. Then proceed to B-rep/3D Boolean, CAD interchange, parametric sketch/feature history, EDA/electrical simulation, validated physics adapters, secure module runtime, and cross-domain API/CLI/UI integration. See [post-PR #80 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR80.md).


## Next increment — PlanarRegion v1 (PR #82 candidate)

- Add a separate region model with one outer boundary and zero or more holes; keep convex ProfileLoop v1.0 unchanged.
- Validate simple loops, strict hole containment/non-touching, canonical outer CCW/hole CW winding, stable cyclic origin, explicit frame/unit, exact represented-binary64 rational predicates and deterministic digest.
- Use a dependency-free precision policy; no epsilon snapping, quantization or third-party kernel dependency is introduced.
- This increment is region input/validation only. Boolean union/intersection/difference/symmetric difference remain a subsequent PR requiring independent topology/area references, error bounds and resource limits.
- Candidate implementation is in PR #82; do not mark implemented until exact-head CI passes and the PR is merged with post-merge verification.


## PR #82 — PlanarRegion v1.0 input model (IMPLEMENTED)

- Merged at `114bf8dd84831d7d4080922ed7069cadda380ba3`; exact PR head `a2df003b7dfe66c6ccaf605cfb8ee83d0780668e`.
- PR workflow #42240159979 and push workflow #42240149518 passed both required jobs with 563 tests; post-merge workflow #42240292055 passed both jobs with 563 tests in 2.47s.
- Adds exact-rational represented-binary64 predicates, canonical outer/hole winding, strict simple-loop and hole checks, explicit frame/unit, canonical digest, strict schema and a 2,048-edge bound.
- Existing convex ProfileLoop v1.0 remains unchanged. General planar Boolean operations are still PLANNED, not implemented.

## Next increment — exact planar-region Boolean arrangement

Implement union, intersection, difference and symmetric difference for PlanarRegion sets with multiple components and holes. Require independent exact-rational topology/area references, deterministic boundary graph traversal, output rounding/error bounds, and resource-limit UNKNOWN behavior before declaring completion. See [post-PR #82 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR82.md).


## PR #84 — Pairwise exact PlanarRegion Boolean engine (MERGED)

- Merge SHA / integration HEAD: `1b75e2dab5b64d2d089e410bba02187d28772193`; base `8d62d1940cdae10e2f3f760dbb1296cd714c0017`; exact PR head `999235de2627f948a6fba8c4c9a038cea7cf8857`.
- PR-head workflow #42250468895 and exact post-merge workflow #42250583756 passed both required jobs; **580 tests** on each (2.14s PR-head, 2.96s post-merge).
- Adds pairwise UNION / INTERSECTION / DIFFERENCE / SYMMETRIC_DIFFERENCE for PlanarRegion v1.0, exact rational arrangement predicates, multiple components/holes, deterministic cycles, binary64 coordinate and area rounding-error reporting, strict result schema and snapshot import validation.
- Limits: 256 total input edges; point-touching/branching output fails closed; frames/units must match; no implicit conversion, snap, repair, B-rep, 3D Boolean or arcs/splines. Existing convex ProfileLoop v1.0 remains unchanged.
- Next: broaden independent rational/adversarial references; specify point-contact traversal semantics; design pairwise result aggregation/region-set API; then continue sketch/feature history, B-rep/interchange, EDA/circuit simulation, multiphysics adapters and secure runtime. See [post-PR #84 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR84.md).


## PR #86 — Planar Boolean reference corpus (MERGED)

Exact corrected PR-head #42251459190 passed 592 tests; post-merge #42251569128 passed 592 tests. Adds equal-geometry identities, oblique polygon commutativity, directional difference, edge contact, multi-hole preservation and edge-budget tests.

## PR #87 — Multi-region PlanarRegion Boolean (MERGED)

Merge SHA `316e0d6c3166470bc839d3c880a38720bd854577`. PR/push workflows #42251905120 / #42251876359 passed 600 tests each; post-merge #42252022902 passed 600. Adds one-arrangement multi-region UNION, INTERSECTION, DIFFERENCE and SYMMETRIC_DIFFERENCE, result schema and snapshot validation.

## PR #88 — PlanarRegion to 3D extrusion adapter (MERGED)

Merge SHA `bd9379617f1bc88772137a6e9886e33cb0bed3cb`; PR/push workflows #42252525813 / #42252493832 passed 607 tests each; post-merge #42252619167 passed 607. Adds source-digest-preserving extrusion from PlanarRegion to ExtrudedProfileSolid and verifies Boolean → extrusion → watertight mesh.

Next CAD gates: deterministic point-contact topology, parametric sketch constraints, feature history/regeneration, B-rep/3D Booleans and STEP/3MF. Hardware EDA, circuit simulation, validated multiphysics and secure runtime remain separate open workstreams. See [post-PR #88 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR88.md).


## PR #90 — Parametric Sketch Constraint Foundation (MERGED)

- Merge SHA: `e2d631b49910e3d7f05fea6337742fd87385fb81`.
- Exact PR-head run #42260796531: workflow-sanity PASS; python-tests PASS, 618 tests.
- Post-merge run #42260977543: both required jobs PASS, 618 tests.
- Adds immutable 2D points, straight segments and HORIZONTAL, VERTICAL, COINCIDENT, DISTANCE, HORIZONTAL_DISTANCE, VERTICAL_DISTANCE, FIX_X and FIX_Y constraints; reuses existing nonlinear solver.
- Remaining sketch scope: angle/tangent/equal/symmetry/radius constraints, arcs/splines, inference, drag solver and validated closed-loop-to-PlanarRegion adapter.

Next dependency order: closed-loop sketch-to-region adapter → feature DAG/history → deterministic feature regeneration → B-rep/3D Boolean kernel → STEP/3MF interchange. See [Parametric Sketch Constraint Contract](docs/design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md).


## PR #92 — Closed Sketch Loop to PlanarRegion (MERGED)

- Merge SHA: `ecc5b7acebdfd48ccf07e64c53f169caf268193a`.
- Exact PR-head and push CI runs #42261996879 / #42261963319 passed both required jobs, 627 tests; post-merge run #42262116610 passed both jobs, 627 tests.
- Converts converged sketch segments into deterministic cycles, rejects open/branching/duplicate/self-intersecting/touching loops, classifies nested loops and emits canonical regions with holes and nested islands.
- Straight-edge loops only; point contacts fail closed.

## PR #93 — Feature History and Regeneration (MERGED)

- Merge SHA: `0983de4c8839070e2a27cd7b8e704f975d176abf`.
- Exact PR-head run #42263173745 and post-merge run #42263296016 both passed both required jobs, 636 tests.
- Adds a deterministic DAG and allow-listed SKETCH_PROFILE → PLANAR_BOOLEAN → EXTRUSION → MESH regeneration pipeline with per-feature SHA-256, cycle/dangling-reference validation and all-or-nothing failure semantics.
- No arbitrary code execution, persistent document service, durable/cross-process cache, suppression/branch history, B-rep or general 3D Boolean. The follow-on incremental cache is process-local and requires a prior successful result.

Next: extend sketch constraint families and arc/spline support; add feature edit/recompute semantics and persistent document contracts; then resolve planar point-contact topology before B-rep/3D Boolean and STEP/3MF.


## PR #95 — Planar Boolean Point-Contact Topology (MERGED)

- Merge SHA: `2eea0bdc9226c8ec3b3d5458e3902ee01b8314f0`.
- Exact PR-head run #42264798640 and post-merge run #42264923364 both passed `workflow-sanity` and `python-tests`, 639 tests.
- Replaces blanket point-contact rejection with exact-rational clockwise-predecessor boundary pairing; point-only contacts preserve separate output components; shared edges still dissolve.
- Ambiguous branch incidence, coincident outgoing branches, repeated-vertex cycles and invalid hole topology remain fail-closed.

See [CAD Boolean Point-Contact Topology Contract](docs/design-3d/CAD_BOOLEAN_POINT_CONTACT_CONTRACT.md). General B-rep/3D Boolean remains open.


## PR #97 — Bounded 3MF Core Mesh Interchange (MERGED)

- Merge SHA: `9b415f7c6be0f537feb67cbe86a911dc0ef5f662`.
- Exact PR-head run #42265918058 and post-merge run #42266044427 both passed required jobs, 650 tests.
- Adds deterministic one-object/one-mesh 3MF Core import/export with strict OPC package validation, provenance metadata, supported unit mapping and size/path/XML safety limits.
- Full 3MF assemblies, transforms, materials, colors, textures, extensions and unknown-part preservation remain unsupported. STEP import/export remains OPEN.

See [3MF Core Mesh Interchange Contract](docs/engineering/3MF_CORE_MESH_INTERCHANGE_CONTRACT.md).


## Current integration status — 2026-11-07 (post-PR #118)

Integration HEAD `0b7e9b4a649a8b3dcf4512cd5172640979115ed4`; `main` remains `96e75010716226037893155b9fd4b13410fb0d6f`. Integration is 265 ahead / 0 behind. Historical pre-PR #116 integration baseline (post-PR #113): `50b5ff50e52e9f9f83d1b33030875b53ee7702e2`. Historical post-PR #113 workflow #42279521637 passed both required jobs with 732 tests in 3.79s. PR #116–#118 are integrated on `docs/phase-0-complete-requirements`. Post-merge workflow #42282428283 on the exact integration SHA passed `workflow-sanity` and `python-tests` with **755 tests in 2.83s**. Recursive tree: 279 files, 105 Markdown, 149 Python, 21 JSON schemas and 75 test files. No open PRs at audit time. Local working-tree state is UNKNOWN (GitHub API inspection only).

### Latest integrated increments
- PR #116 — opt-in adapter fallback during recovery; exact-head 737 tests and post-merge 747 tests.
- PR #117 — faceted triangular B-rep topology and mesh bridge; exact-head and post-merge 742 tests.
- PR #118 — bounded exact-grid 3D Boolean operations for axis-aligned box B-reps; exact-head and post-merge 755 tests.
- Main has not been updated or promoted.

### Remaining work packages — continue in dependency order
1. **Boolean topology robustness:** extend the planar rotation-system and B-rep boundary tests for ambiguous branching/coincident outgoing edges, vertex/edge contacts, thin features and invalid incidence. Preserve deterministic fail-closed behavior until an independently generated exact reference corpus passes. Planar point-only contact handling is implemented by PR #95; it does not resolve ambiguous branching.
2. **General faceted B-rep:** add n-gon face loops and inner loops, then multi-shell solid semantics for enclosed cavities. Require exact topology invariants, orientation/containment checks and independent fixtures before changing the schema.
3. **General 3D Boolean:** add arbitrary faceted-solid splitting and arrangement classification only after multi-shell topology and a precision/tolerance policy exist. Include coplanar overlap, tangency, edge/vertex contact, near-degenerate and thin-feature references with resource ceilings.
4. **Parametric CAD depth:** extend sketch constraints beyond the current eight point/straight-line kinds; add arcs/splines and solver diagnostics. Persistent revisioned source documents are implemented in branch `feat/cad-feature-history-durable-revisions-v1` using local SQLite, append-only SHA-256 revisions and optimistic concurrency; exact-head CI/merge are pending. Durable computed-artifact serialization/rehydration, suppression and edit/branch history remain separate OPEN work. Incremental in-memory cache reuse with dependency-digest invalidation is implemented.
5. **CAD generator workflow:** connect sketch → feature history → solid → mesh/interchange to durable documents, API, interactive UI and revisioned export workflows. Driver generation already exists as a separate capability to inventory/reuse; do not duplicate it.
6. **Interchange completeness:** retain bounded STEP AP214 faceted triangle-shell and single-object 3MF Core support; add external application round-trip validation, full STEP/AP242 and 3MF assemblies only with explicit profile/tolerance contracts.
7. **Hardware EDA:** native schematic/PCB/library interchange, datasheet-backed electrical constraints, pin/footprint reconciliation, BOM lifecycle and circuit simulation.
8. **Multi-method physics:** add validated analytical/numerical/simulation solvers by domain, with dimensional and conservation checks, convergence evidence, uncertainty propagation and independent reference/cross-check suites.
9. **Runtime and platform integration:** OS/container sandbox, OS-enforced CPU/memory/disk/network quotas, Windows process-tree containment, checkpoint/heartbeat/restart, durable state, signed evidence, approval/permission integration, secure module invocation and API/CLI/UI end-to-end tests.

### Release and governance gates
- One bounded concern per PR; exact base/head SHA, reviews, unresolved threads and exact-head CI must be inspected before merge consideration.
- Require post-merge CI on the exact integration SHA; missing or skipped checks are not PASS.
- No promotion to `main`, deployment, physical actuation, firmware write, or privileged operation without explicit human approval.
- Do not claim overall completion until requirements traceability, security review, platform matrix, persistent workflow and end-to-end acceptance evidence all pass.

See [Repository Audit post-PR #118](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR118.md).


## CAD parametric sketch continuation — post-PR #124

Integration baseline: `a17a6359b4689fedbbcfbec769704a0322e027da` (PR #124 merged; post-merge CI PASS, 780 tests). `main` remains unchanged.

- Current increment branch: `feat/cad-parametric-sketch-angle-constraint-v1`.
- Adds signed directed `ANGLE` between two stable segment references, measured in radians in [-π, π], and extends ParametricSketch schema to v1.1 while retaining v1.0 snapshot reads.
- Angle constraints are bounded to non-degenerate straight segments and the existing local nonlinear solver. They do not imply tangent/radius or curved geometry support.
- Tangent and radius/diameter remain OPEN until a versioned circular-arc model and independent geometry references exist.
- Exact-head CI and post-merge CI are mandatory; this branch remains unverified until its exact SHA completes both jobs.


## CAD parametric sketch continuation — post-PR #125

Integration baseline: `2befee9e3ed3c3dbd24add4b3c6b6b0e4b7069e9` (PR #125 merged; post-merge CI PASS, 785 tests). `main` remains unchanged.

- PR #126 merged circular arcs with RADIUS and endpoint TANGENT. Next increment is bounded curved-loop tessellation and PlanarRegion conversion.
- Adds `SketchArc` with explicit center/start/end point IDs and clockwise direction.
- `RADIUS` adds start/end radial equations; each arc must have exactly one positive radius constraint.
- `TANGENT` binds a straight segment to a circular arc at a shared endpoint and solves a normalized orthogonality residual.
- Straight-line sketch-to-region conversion now fails closed when arcs are present; it must not silently drop curved geometry.
- Exact-head CI is pending. Curved-loop topology, curved planar Boolean, mesh tessellation and curved B-rep are separate future increments.


## CAD sketch baseline — post-PR #126

Integration baseline: `5d8e8a4430aa991aac6ef9d70d0bcf6c575f4acd` (PR #126 merged; post-merge CI PASS, 791 tests). `main` remains unchanged.

- ParametricSketch v1.2 supports stable circular arc references, one positive RADIUS constraint per arc, and straight-segment-to-arc endpoint TANGENT.
- The existing straight-line sketch-to-region converter rejects arcs; no curved geometry is silently discarded.
- Next: explicit chord-error-bounded arc tessellation, cycle reconstruction and curved-profile PlanarRegion conversion, with source digest and deviation evidence. Curved Boolean/B-rep remain separate work.


## CAD curved sketch-to-region increment — PR #128 MERGED

- Integration merge SHA: `30deb5290e4a84b8ce86848dcac21309d0b1ad95`; main remains unchanged at `96e75010716226037893155b9fd4b13410fb0d6f`.
- Adds deterministic chord-error-bounded tessellation for circular arcs and cycle reconstruction for closed loops containing segments, arcs, or mixed boundaries.
- The conversion preserves frame/unit, source sketch digest, nested-loop and hole semantics, and rejects open, branching, duplicate, self-intersecting, touching or over-limit topology.
- Exact PR-head CI: 801 tests PASS on `5c2690760d77639c0db5795f0c8571c52944c6d9`; exact post-merge CI workflow #42374839944: 801 tests PASS on the merge SHA.
- This is polygonal approximation, not exact curved geometry. Curved Boolean, curved B-rep, arc-to-arc tangent and splines remain OPEN.
- Next dependency: extend feature-history durable artifact serialization/rehydration and validate the sketch → region → extrusion → mesh pipeline using the new curved-profile input. Keep kernel/curved Boolean selection separate and evidence-driven.


## FeatureHistory durable artifact increment — PR #131/#132 MERGED

- PR #131 added strict rehydration for all four allow-listed FeatureArtifact kinds: SKETCH_PROFILE, PLANAR_BOOLEAN, EXTRUSION and MESH. Mesh validation is recomputed during restore.
- PR #132 added an optional local SQLite artifact cache, keyed by history ID, feature ID and algorithm-version-aware computation SHA-256. Cache entries are canonical, idempotent and immutable; cache corruption causes regeneration to fail closed.
- Exact PR-head and post-merge CI for PR #132 passed both required jobs, 812 tests. Integration merge SHA: `f2cac75f7d4594ccb3a1ff70e56faa4ebe32f523`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`.
- Source-document revision storage (PR #124) and computed-artifact cache (PR #132) are separate local SQLite stores. Next acceptance increment: reopen both stores in a fresh process, load a selected FeatureHistory revision, regenerate with the artifact cache, and verify all expected outputs/digests without recomputation.
- Follow-on: CAD generator API/UI and revisioned authoring workflows; suppression and branch/merge editing; cache retention/compaction and backup strategy. Do not claim distributed persistence or signed/tamper-proof storage.


## Durable FeatureHistory + artifact cache acceptance — PR #134 MERGED

- PR #134 proves the two separate local SQLite stores work together across an actual new Python interpreter: save source FeatureHistory revision → regenerate and persist artifacts → start child process → reopen source and artifact stores → load the exact revision → reuse all artifacts.
- The child process reused `profile`, `extrusion` and `mesh` with zero recomputation; content digests matched and the final mesh passed watertight/orientation validation.
- Exact PR-head and post-merge CI passed both required jobs, **813 tests**. Integration SHA: `e4a1add528e4fd77c88df96d428ff629e2f4b655`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`.
- The next implementation priority is the CAD generator workflow: a narrow API/service layer that accepts a versioned FeatureHistory snapshot, stores revisions, runs allow-listed regeneration with the local artifact cache, and returns revision/artifact provenance and validation. Add an interactive UI only after API contracts and error states are stable.
- Still OPEN: cache retention/compaction, backup/restore, encryption-at-rest, signed evidence, suppression, branch/merge editing, general B-rep/curved Boolean and manufacturing validation.


## CAD Generator application service — PR #136 MERGED

- `CADGeneratorService` now joins immutable source revisions, local artifact caching and allow-listed regeneration without exposing a transport.
- It accepts typed histories or strict JSON snapshots, persists with optimistic revision checks, reads exact revisions, regenerates with the local cache and returns revision/artifact provenance.
- Public exports added: `CADGeneratorService`, `CADGeneratorRun`, `SQLiteFeatureArtifactCache`, `FeatureArtifactCacheIntegrityError`.
- Exact-head and post-merge CI passed both required jobs; 817 tests. Integration SHA: `ab0006c1ead3e6848f90e30c804d38a3029218f3`; main remains unchanged at `96e75010716226037893155b9fd4b13410fb0d6f`.
- Next implementation increment: transport adapter (HTTP or CLI) with explicit request/response schemas, authentication/authorization, size/time limits, audit, cancellation, structured errors and loopback-only binding by default. Remote/public access must require explicit separate approval. Add UI only after transport contracts stabilize.


## CAD Generator loopback API — PR #138 MERGED

- Implemented an explicit-start local HTTP adapter for the revision-aware CAD Generator service.
- Provides authenticated health, immutable history save, revision list/read and exact-revision regeneration.
- Uses IPv4 loopback only (`127.0.0.1`), dynamic port by default, bearer token, strict JSON/body/time limits and same-origin checks.
- Adds SQLite append-only request lifecycle audit with SHA-256 chain verification. It does not log credentials or model payloads.
- Exact-head CI passed both required jobs with 822 tests; exact post-merge workflow #42380918862 passed both required jobs with 822 tests.
- Integration SHA: `674b6a52c725b6e3f4b4e083b602aab3a138104e`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`.
- Next implementation slice: same-origin local CAD authoring UI served by the loopback API; remote/public exposure remains prohibited and outside this increment.


## Local CAD Generator workbench — PR #140 MERGED

- Added a same-origin static FeatureHistory workbench served by the loopback API.
- Users can paste/edit strict FeatureHistory JSON, append immutable revisions, list/load exact revisions and regenerate the selected revision.
- Token remains in memory only; static assets use restrictive CSP, no external resources, no CORS and same-origin requests.
- Exact-head and post-merge CI passed both required jobs; 823 tests. Integration SHA: `f3abe346a259f2f3f3ed767889dba32be6a284b9`; main remains unchanged.
- The workbench is not yet a visual CAD editor. Next increment: a bounded 2D polygon sketch editor that constructs validated FeatureHistory records, followed by mesh preview and explicit validation. Arc editing, general B-rep and complex topology remain later increments.


## Visual polygon sketch editor — PR #142 MERGED

- Added a bounded SVG 2D polygon canvas and exact-coordinate controls to the local CAD workbench.
- The authenticated polygon template endpoint creates a fixed-coordinate ParametricSketch v1.2, closed segments, extrusion and mesh FeatureHistory.
- Users review generated JSON, append an immutable revision, then explicitly regenerate. The regeneration pipeline remains responsible for self-intersection and watertight mesh validation.
- Bounds: 3–64 vertices, X 0–26 mm, Y 0–15 mm; straight edges only.
- Exact-head and post-merge CI passed both required jobs; 832 tests. Integration SHA: `18179f1d2d5f51fcf9d06f971fbc922f3e0cd5c7`; main remains unchanged.
- Next: interactive mesh viewport controls (orbit, pan and zoom) with bounded input/rendering and browser-level regression tests. Keep the static preview available as a safe fallback; do not imply B-rep editing or a general CAD kernel.


## CAD Generator source-linked mesh preview — PR #144 MERGED

- Added a static isometric SVG preview sourced from the exact MESH FeatureArtifact returned by regeneration; no geometry is reconstructed from the sketch.
- Shows source revision, mesh counts, artifact content/computation digests and canonical backend validation flags/issues.
- Rendering is bounded to 10,000 vertices and 5,000 triangles; full artifact JSON remains available. Backend validation remains authoritative.
- Exact PR-head run #42383293137 and post-merge run #42383384086 both passed workflow-sanity and python-tests. The post-merge run is tied to exact integration SHA da5b34182396c485760aa1940ab2623d52d89cbc; test-count detail was not captured.
- PR #146 completes the bounded interactive orbit/pan/zoom camera controls. Next CAD increments should address feature-tree/selection/measurement or geometry-kernel capabilities as separate, validated slices; sectioning, assemblies and arbitrary geometry remain later work.


## CAD Generator interactive mesh viewport — PR #146 MERGED

- Adds client-side pointer-drag orbit, Shift/middle-button pan, wheel/button zoom and reset controls over the exact source-linked MESH FeatureArtifact.
- Camera pitch, pan and zoom are bounded; zoom range is 0.5×–4×. Camera state is ephemeral and does not mutate FeatureHistory, backend artifacts or audit records.
- Preview remains capped at 10,000 vertices and 5,000 triangles. Malformed/non-finite vertices and malformed triangle indices fail closed for rendering; backend validation remains authoritative.
- Exact PR-head SHA `c7c15c9a007a705ef67f650d693f1794c0f104a3`, workflow #42385362330: workflow-sanity PASS and python-tests PASS.
- Exact post-merge SHA `1813cb931876305391eeabe748741be189d5f27b`, workflow #42386519328: workflow-sanity PASS and python-tests PASS; **832 passed in 9.09s**.
- Main remains `96e75010716226037893155b9fd4b13410fb0d6f`; integration is 391 commits ahead and 0 behind at this audit. Local working tree and branch protection remain UNKNOWN.
- Capability boundary: interactive triangle-mesh viewing only. Feature-tree editing, selection, measurement, sectioning, B-rep editing, assembly view and general CAD-kernel operations remain open.


## CAD Generator triangle selection and measurement — PR #148 MERGED

- Adds accessible pointer/keyboard selection for rendered triangle facets, selected-facet highlighting and a clear-selection action.
- Reports triangle area using the cross-product formula and centroid using the original mesh vertices, in the mesh-declared length unit and frame.
- Selection and measurements are ephemeral client-side state; they do not mutate FeatureHistory, FeatureArtifacts, API data or audit records.
- Exact PR-head SHA `43461346e32e1c5146c5beeab79340d7fbc387df`, workflow #42391405409: workflow-sanity PASS; python-tests PASS; **832 passed in 8.59s**.
- Exact post-merge SHA `1fb9bc97c22bf0464e154f6963583edb9385d657`, workflow #42391470608: workflow-sanity PASS; python-tests PASS; **832 passed in 7.59s**.
- Capability boundary: triangle-facet inspection only, not B-rep topology selection, sketch dimensions, sectioning, face editing or general CAD kernel.
- Main remains `96e75010716226037893155b9fd4b13410fb0d6f`; integration is 393 commits ahead and 0 behind. Local working tree and branch protection remain UNKNOWN.


## CAD Generator FeatureHistory tree inspector — PR #150 MERGED

- Adds a read-only structural preview of the current FeatureHistory JSON snapshot.
- Computes deterministic topological order from feature dependencies; malformed nodes, duplicate IDs, invalid outputs, missing/self references and cycles fail closed for the preview.
- Preview is bounded to 500 nodes and displays feature IDs, kinds, dependency references and selected-node parameters using text-only DOM APIs.
- Refreshes after JSON input, template generation and revision loading; it does not edit, save or regenerate the model.
- CI adds `node --check` for the packaged CAD Generator browser script without a new dependency.
- Exact PR-head SHA `2958c270eebbbba884b59ed06714946622adeb67`, workflow #42392209579: workflow-sanity PASS and python-tests PASS; **833 passed in 9.15s**.
- Exact post-merge SHA `da16967de5f387f4e98d9642134626982644d479`, workflow #42392264691: both jobs PASS; **833 passed in 8.73s**.
- Capability boundary: read-only feature-tree inspector, not a graphical DAG editor or parametric feature editing/recompute system. Main remains `96e75010716226037893155b9fd4b13410fb0d6f`.


## CAD Generator interactive FeatureHistory editing — PR #156 MERGED

- Adds selected-feature parameter replacement, feature add and feature removal to the local same-origin CAD workbench.
- Operations call the revision-safe loopback API and append immutable source revisions. Historical revisions are read-only; editing controls are gated to the loaded current head.
- Dependent deletion requires an explicit cascade checkbox. Stale revision conflicts are surfaced with refresh guidance.
- The browser code uses text-only rendering; no user code or new feature kinds are introduced.
- Exact PR head `265ca3907e05f958fbae48f48398fbbae8d70ea2`: workflow-sanity PASS; python-tests PASS; 843 passed in 9.40s.
- Exact merge SHA `10404099ccaa85cef24adedffa7bce789abd691e`: post-merge workflow #42407835073 passed both jobs; 843 passed in 9.76s.
- Remaining: browser E2E interaction tests, suppression, reorder semantics, undo/redo, branch/merge history, expression parameters, B-rep editing and geometry recomputation propagation. This PR is a bounded source-history editor, not a complete CAD editor.


## CAD FeatureHistory browser E2E — PR #158 MERGED

- Adds a dedicated real-Chromium Playwright workflow for the local FeatureHistory editor.
- Four browser tests pass on both the exact PR head and exact post-merge integration SHA.
- Post-merge Python regression suite: 843 passed; workflow sanity PASS.
- Merge SHA: `9d899f70a97372f689ba07a8e90b479bf14494b4`.
- This closes the browser-automation evidence gap for the current bounded add/replace/remove editor. It does not close the feature suppression, reorder semantics, undo/redo, branch/merge, B-rep editing or general CAD kernel work packages.


## FeatureHistory suppression backend core — PR #163 MERGED

- FeatureHistory v1.1 adds a canonical `suppressed_feature_ids` set while preserving strict v1.0 loading, serialization and stored revision digests.
- Added explicit v1.0 → v1.1 migration, immutable suppress/unsuppress helpers, explicit transitive cascade, dependency/output invariants and regeneration skip/report behavior.
- Suppressed source nodes are retained; no artifact-cache cleanup or deletion is performed.
- PR #163 merged at `e6a6196aeaa84fca2eff8ce2f0417cc0a4014c2b`. Exact PR-head CI: 851 Python tests PASS, 4 Chromium E2E tests PASS, workflow-sanity PASS. Exact post-merge CI: 851 Python tests PASS, 4 Chromium E2E tests PASS, workflow-sanity PASS.
- **Next:** CAD-EDIT-006 revision-safe service/API operations; CAD-EDIT-007 workbench controls, explicit cascade confirmation and suppression-specific Chromium E2E.
- **Still open:** end-to-end suppression UX, undo/redo, graph branch/merge, feature reordering, generalized B-rep/3D Boolean, broader platform integration and full repository verification. This PR does not make the repository COMPLETE.


## FeatureHistory suppression — end-to-end complete

- PR #165 merged revision-safe service/API operations at `038193589e7b4ca22fb0a41ef6f61e54fd8d2938`; exact PR-head and post-merge CI passed 854 Python tests, 4 Chromium E2E tests and workflow-sanity.
- PR #166 merged workbench suppression controls and browser acceptance at `34148fc359076567eaa4b931304f61f536a41779`; exact PR-head and post-merge CI passed 854 Python tests, 5 Chromium E2E tests and workflow-sanity.
- Suppression now preserves source nodes and immutable revisions, requires explicit cascade confirmation, prevents unsuppress while dependencies remain suppressed and reports skipped nodes during regeneration.
- **Status:** PASS for FeatureHistory suppression requirement R-016.
- **Next CAD editor work:** CAD-EDIT-008 — define immutable revision restore semantics for undo/redo, including redo-stack persistence, audit history and stale-writer behavior, before implementing controls.
- **Still open:** graph branch/merge, feature reordering, generalized B-rep/3D Boolean, broader hardware/physics/runtime integration and whole-repository completion.


## FeatureHistory undo/redo — design phase

- CAD-EDIT-008 contract drafted at `docs/design-3d/FEATURE_HISTORY_UNDO_REDO_CONTRACT.md`.
- Design uses persistent SQLite Undo/Redo stacks and append-only restore revisions; prior snapshots and digests are never rewritten or deleted.
- New normal edits clear Redo; Undo/Redo use expected-revision compare-and-swap and atomically append a new revision plus navigation-state changes.
- Existing histories initialize deterministic Undo state from their immutable linear revision chain.
- PR #168 merged the contract at `6c5f77168cca1947bf79678696613ef1ef9c84ea`.
- PR #169 implements the store layer: persistent stacks, atomic append-only restore revisions, legacy backfill, CAS and fail-closed validation. Exact-head CI: 860 Python tests PASS, workflow-sanity PASS; merge pending.
- **Next:** merge the store slice after exact-head checks, then add service/API navigation operations, followed by workbench/browser E2E.
