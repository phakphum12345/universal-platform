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

## PR #77 — Mesh geometric topology analysis implementation (IMPLEMENTATION CANDIDATE)

- Adds `MeshTopologyAnalysis` v1.0 and `analyze_mesh_topology` without changing `validate_triangle_mesh`.
- Records solid/frame/unit identity, source and canonical mesh SHA-256, counts, connected face components, exact/near-coincident groups, non-manifold vertex fans, unused vertices and stable issue codes.
- Near-coincident grouping uses explicit source-unit tolerance, deterministic 3D buckets and a 5,000,000 neighbor-comparison ceiling; no welding/snap/repair.
- `self_intersection_status` remains UNKNOWN; geometric triangle-triangle testing is a separate future gate.
- Exact-head and post-merge CI evidence pending.

## Next repository increments

1. Complete PR #77 mesh topology diagnostics; then design and implement triangle-triangle self-intersection separately.
2. General planar-region Boolean operations beyond convex loops, with a selected precision policy and independent adversarial reference corpus.
3. Neutral CAD interchange (external STL import and STEP/3MF) with independent external-tool reopen validation.
4. Parametric sketch constraints, solver diagnostics and versioned feature history with deterministic recomputation.
5. Hardware EDA symbol/library exchange, BOM/footprint reconciliation, datasheet-backed electrical limits and circuit simulation.
6. Additional validated physics/solver adapters with independent domain reference cases.
7. Module runtime invocation, permissions, sandboxing, quotas, cancellation and audit only after threat model and isolation contracts are implemented and tested.



