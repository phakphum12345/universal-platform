# Universal Platform

A cross-platform, cross-disciplinary platform for learning, research, system understanding, engineering, simulation, creation, and governed evolution.

## Current status
- Stage: Active incremental implementation on the integration branch; repository is not complete.
- Integration HEAD: `1a8338ae17eb783a374a36400999ead796f9a79d` (post-PR #152).
- Main HEAD: `96e75010716226037893155b9fd4b13410fb0d6f` (unchanged; no promotion performed).
- Historical integration baseline before PR #116 (post-PR #113, superseded): `50b5ff50e52e9f9f83d1b33030875b53ee7702e2`.
- Historical post-PR #113 workflow #42279521637: `workflow-sanity` PASS, `python-tests` PASS, **732 passed in 3.79s** (superseded by the PR #118 baseline above).
- Latest post-merge CI: PR #152 workflow #42396453320 on exact merge SHA `1a8338ae17eb783a374a36400999ead796f9a79d` — workflow-sanity PASS (including Node.js syntax check); python-tests PASS; **840 passed in 8.71s**.
- Current inventory: 349 entries, 116 Markdown, 165 Python, 24 JSON files, 85 Python test files (recursive tree at post-PR #152; truncated=false).
- Open PRs at the latest audit: 0. Local working tree: UNKNOWN (GitHub API inspection only). Branch-protection read: UNKNOWN (connected GitHub API returned 403).
- Principles: Local-first, cost-aware, evidence-driven, modular, secure.
- Hardware boundary: Analysis and simulation only; no physical control.
- Remaining scope: interactive feature-tree editing UI, feature suppression, undo/redo, B-rep face/edge selection, sectioning, general n-gon/multi-shell B-rep and arbitrary 3D Boolean; ambiguous branching topology; full STEP/AP242 and 3MF assembly interchange; broader EDA/circuit simulation; additional validated physics methods; OS-enforced sandboxing; and broader API/CLI/UI integration remain incomplete.
- Driver generation: Existing capability is to be inventoried and reused; no duplicate generator is planned.

## Initial implementation (active development)

The integration branch contains an incrementally implemented Python engineering core under src/universal_platform/engineering, including the metadata-only module registry added in PR #39. Mechanism topology, placements, generalized-coordinate parameterization, loop topology, mobility diagnostics and caller-driven kinematics are versioned contracts; each PR remains subject to exact-SHA CI.

Current modules include:
- SI-backed quantities with dimensional checks (limited initial unit registry).
- Evidence and provenance contracts with explicit evidence kinds and statuses.
- A fail-closed safety gate for offline engineering workflows.
- A validated, metadata-only ModuleManifest/ModuleOperation registry with deterministic dependency ordering; no plugin code loading or invocation.
- Validated immutable ModuleRequest/ModuleResponse envelopes with JSON-safe payloads and explicit operational statuses; no module runtime execution.
- Provenance/evidence records with source SHA-256 references and conservative PASS/FAIL/SKIPPED/UNKNOWN aggregation (PR #42 merged).
- Versioned rigid-transform/frame-graph exchange with explicit length units (PR #43 merged).
- Versioned Quantity snapshots with SI value, dimension and source-unit lineage (PR #44 merged).
- Frame-bound spatial points and displacement vectors with point/vector-correct transforms (PR #45 merged).
- Normalized hardware schematic component/pin/net connectivity model (PR #46 merged), deterministic offline SVG layout renderer (PR #59), and conservative static ERC v1.0 candidate (PR #60); no circuit simulation or physical verification.
- Hardware driver interface declarations and schematic pin bindings (PR #47 merged; metadata only).
- Frame-aware analytic Box/Cylinder primitives with deterministic serialization, SI properties and transformed bounds (PR #48 merged; not a general CAD kernel).
- Straight-sided polygon profile extrusion with validation, SI volume/surface area, deterministic serialization and transformed bounds (PR #49 merged at `bfc3e6585106c73b29297cbda2ab9ec9d50340db`; final head `38a800d033ebbba19e1120c8cd3a47ade4088526`, run #356 / `42178039043` PASS, 416 tests; post-merge run #381 / `42186896757` PASS, 416 tests).
- A small dense linear solver with partial pivoting and residual checks.
- Scalar constraint evaluation with explicit UNKNOWN handling.
- Assembly occurrence/joint contracts and nominal joint-DOF bookkeeping.
- Normalized mechanism schema v1.2 with stable generalized-coordinate IDs and explicit per-joint coordinate ordering, units, axes, bounds and scales; missing parameterization coverage remains visible.
- Automatic six-component joint pose-consistency residual generation from explicit body poses, placements and generalized coordinates for all eight declared joint families; this is not a general dynamics solver.
- Finite-difference constraint Jacobian generation over generalized coordinates and body-pose tangent variables, with stable variable/row ordering and bound-aware one-sided fallback; this is not a symbolic or analytic derivative engine.
- Geometry-aware loop-closure evaluation that combines deterministic fundamental cycles with generated joint residuals, retaining closing-edge and spanning-tree evidence for caller-supplied configurations; this is not a configuration-search solver.
- Bounded local generalized-coordinate fitting against fixed caller-supplied body poses, using every generated joint residual, declared coordinate bounds/scales and the offline nonlinear equality solver; this is not a general body-pose configuration solver.
- Spatial local mobility analysis from generated finite-difference joint Jacobians, combining non-ground body-pose tangent variables with independent joint coordinates. PR #56 adds explicit plane-frame projection for PLANAR mobility; it is integrated with exact-head and post-merge CI PASS.
- Versioned cross-discipline reference validation pack for dimensional quantities, mechanics, DC electrical, thermal expansion, analytic geometry/transforms, linear solve, static algebraic simulation, planar inverse kinematics, four-bar closure, materials, assembly, constraints and safety-boundary checks.
- Rigid coordinate transforms and a validated coordinate-frame forest with path resolution.
- A limited rooted-tree forward-kinematics adapter for fixed, revolute and prismatic joints (not a general constraint solver).
- An analytic planar two-link (2R) inverse-kinematics adapter with up/down elbow branches and residual validation (not general 3D IK).
- A planar four-bar (4R) loop-closure utility based on circle intersections, plus a stable-ID, unit-aware model snapshot adapter and Kutzbach planar mobility estimate (not a general closed-loop constraint solver).
- A new general-purpose nonlinear equality-constraint solver is introduced as a bounded, local Levenberg–Marquardt numerical core; see [Nonlinear Constraint Solver Contract](docs/engineering/NONLINEAR_CONSTRAINT_SOLVER_CONTRACT.md) for exact scope and limitations.
- A transparent linear-system simulation example with limitations and evidence.
- Starter mechanics (axial stress/strain and factor of safety), DC electrical calculations, linear thermal expansion and validated material-property records.
- Versioned module request/response envelopes.

Install and run the initial tests:

    python -m pip install -e ".[dev]"
    python -m pytest -q

This remains an incremental engineering foundation, not a completed universal platform. Narrow capabilities now include planar Boolean topology, bounded parametric sketch/feature regeneration, faceted triangular B-rep, axis-aligned box 3D Booleans, binary STL export, bounded STEP AP214 and single-object 3MF Core interchange, schematic rendering/static ERC, and three registered analytical physics solvers. These do not establish a general CAD kernel, full EDA suite, multiphysics solver, secure OS sandbox, or complete platform UI/runtime. See [Implementation Status](docs/implementation/IMPLEMENTATION_STATUS.md) and [post-PR #118 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR118.md).

## Core goals
- Learn from authorized documentation, source code, APIs, datasheets, and datasets.
- Understand applications, software, systems, dependencies, and architecture.
- Support computing, mathematics, science, software, hardware, electronics, communications, and engineering.
- Analyze ICs/chips, boards, sensors, modules, schematics and device compatibility.
- Coordinate multiple scientific and engineering disciplines through the Universal Engineering Intelligence Core (UEIC).
- Calculate, design, simulate, test, verify, and prepare manufacturing artifacts.
- Design static parts, tools, fixtures, structures, machines and moving mechanisms in 3D.
- Create new applications and adapt existing systems when authorized.
- Identify capability gaps and propose controlled self-improvements.

## Documentation map
- [Documentation Index](DOCUMENTATION_INDEX.md)
### Product and planning
- [Vision](VISION.md)
- [Master Blueprint](MASTER_BLUEPRINT.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Domain Catalogue](docs/DOMAIN_CATALOGUE.md)
- [Engineering and 3D Project Plan](docs/roadmap/ENGINEERING_AND_3D_PHASE_PLAN.md)
- [Phase 2 Numerical Reliability Plan](docs/roadmap/PHASE_2_NUMERICAL_RELIABILITY_PLAN.md)
- [Engineering Master File Plan](docs/roadmap/ENGINEERING_MASTER_FILE_PLAN.md)
- [Engineering Vertical Slice Specification](docs/roadmap/ENGINEERING_VERTICAL_SLICE_SPEC.md)
- [Engineering Technology Decisions](docs/decisions/ENGINEERING_TECHNOLOGY_DECISIONS.md)
- [Repository Capability Inventory](docs/audit/REPOSITORY_CAPABILITY_INVENTORY.md)
- [Post-PR-1 Baseline Audit](docs/audit/POST_PR1_BASELINE_AUDIT.md)

### Requirements and decisions
- [Universal Requirements](docs/requirements/UNIVERSAL_REQUIREMENTS.md)
- [Decision Register](docs/decisions/DECISION_REGISTER.md)
- [Requirements Traceability Matrix](docs/traceability/REQUIREMENTS_TRACEABILITY_MATRIX.md)
- [Engineering and 3D Traceability](docs/traceability/ENGINEERING_REQUIREMENTS_TRACEABILITY.md)

### Architecture and intelligence
- [Platform Architecture](docs/architecture/PLATFORM_ARCHITECTURE.md)
- [Universal Command System](docs/architecture/UNIVERSAL_COMMAND_SYSTEM.md)
- [System Intelligence](docs/architecture/SYSTEM_INTELLIGENCE.md)
- [Engineering Module API Contract](docs/architecture/ENGINEERING_MODULE_API_CONTRACT.md)
- [Engineering Data Model](docs/architecture/ENGINEERING_DATA_MODEL.md)

### Engineering intelligence
- [Universal Engineering Intelligence Core](docs/engineering/UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE.md)
- [Multidisciplinary Knowledge Modules](docs/engineering/MULTIDISCIPLINARY_KNOWLEDGE_MODULES.md)
- [Physics and First-Principles Modeling](docs/engineering/PHYSICS_AND_FIRST_PRINCIPLES.md)
- [Universal Calculation Engine](docs/engineering/UNIVERSAL_CALCULATION_ENGINE.md)
- [Solver and Model Contract](docs/engineering/ENGINEERING_SOLVER_AND_MODEL_CONTRACT.md)
- [Units, Uncertainty and Provenance](docs/engineering/ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE.md)
- [Cross-Domain Constraint Solving](docs/engineering/CROSS_DOMAIN_CONSTRAINT_SOLVING.md)

### 3D design and manufacturing
- [3D Design Intelligence](docs/design-3d/3D_DESIGN_INTELLIGENCE.md)
- [3D Tool Generation](docs/design-3d/3D_TOOL_GENERATION_ENGINE.md)
- [3D Assembly and Kinematics](docs/design-3d/3D_ASSEMBLY_AND_KINEMATICS.md)
- [Generalized Coordinate and Joint Parameterization](docs/design-3d/GENERALIZED_COORDINATE_AND_JOINT_PARAMETERIZATION_CONTRACT.md)
- [Spatial Joint Reference Validation](docs/design-3d/SPATIAL_JOINT_REFERENCE_VALIDATION_CONTRACT.md)
- [Planar Plane-Frame Mobility](docs/design-3d/PLANAR_PLANE_FRAME_MOBILITY_CONTRACT.md)
- [Assembly Tree Forward-Kinematics Contract](docs/design-3d/ASSEMBLY_TREE_FORWARD_KINEMATICS_CONTRACT.md)
- [Planar Two-Link Inverse-Kinematics Contract](docs/design-3d/PLANAR_TWO_LINK_INVERSE_KINEMATICS_CONTRACT.md)
- [Planar Four-Bar Loop-Closure Contract](docs/design-3d/PLANAR_FOUR_BAR_LOOP_CLOSURE_CONTRACT.md)
- [Nonlinear Constraint Solver Contract](docs/engineering/NONLINEAR_CONSTRAINT_SOLVER_CONTRACT.md)
- [3D Engineering Simulation](docs/design-3d/3D_ENGINEERING_SIMULATION.md)
- [Structural and Civil Design](docs/design-3d/STRUCTURAL_AND_CIVIL_DESIGN.md)
- [CAD to Manufacturing](docs/design-3d/CAD_TO_MANUFACTURING_PIPELINE.md)
- [3D Model Validation](docs/design-3d/3D_MODEL_VALIDATION.md)
- [2D Convex Profile Boolean Topology](docs/design-3d/CAD_2D_BOOLEAN_TOPOLOGY_CONTRACT.md)
- [Faceted B-rep Topology](docs/design-3d/FACETED_BREP_TOPOLOGY_CONTRACT.md)
- [Axis-Aligned Faceted B-rep Boolean](docs/design-3d/AXIS_ALIGNED_BREP_BOOLEAN_CONTRACT.md)

### Hardware, laboratories, governance
- [Device Intelligence](docs/hardware/DEVICE_INTELLIGENCE.md)
- [Schematic Intelligence](docs/hardware/SCHEMATIC_INTELLIGENCE.md)
- [Hardware-to-Software Mapping](docs/hardware/HARDWARE_TO_SOFTWARE_MAPPING.md)
- [Driver Architecture Intelligence](docs/hardware/DRIVER_ARCHITECTURE_INTELLIGENCE.md)
- [Driver Refactoring Engine](docs/hardware/DRIVER_REFACTORING_ENGINE.md)
- [Schematic/Driver Traceability](docs/hardware/SCHEMATIC_DRIVER_TRACEABILITY.md)
- [Hardware Schematic Netlist Contract](docs/hardware/HARDWARE_SCHEMATIC_NETLIST_CONTRACT.md)
- [Electrical Rule Checking Contract](docs/hardware/ELECTRICAL_RULE_CHECKING_CONTRACT.md)
- [Hardware Design Verification](docs/hardware/HARDWARE_DESIGN_VERIFICATION.md)
- [Virtual Lab and Simulation](docs/laboratories/VIRTUAL_LAB_AND_SIMULATION.md)
- [Engineering Safety and Approval](docs/governance/ENGINEERING_SAFETY_AND_APPROVAL.md)

### Integration and evolution
- [Project Integration Policy](docs/integration/PROJECT_INTEGRATION.md)
- [Platform Self-Evolution](docs/evolution/PLATFORM_SELF_EVOLUTION.md)

## Safety and evidence
No claim of success without evidence. Untrusted code must be isolated. Privileged actions, production changes, deployment, physical device control, and self-modification require explicit human approval. Initial device scope is analysis and simulation only.

Documentation and proposals do not mean capabilities are implemented. Evidence statuses must distinguish PASS, FAIL, SKIPPED, and UNKNOWN, with exact versions and reproducible checks where applicable. A completed solver run is not automatically an engineering PASS.


### CAD-neutral geometry

- CAD-neutral geometry now includes analytic Box/Cylinder and profile extrusion; PlanarRegion set Booleans with bounded point-contact handling (PR #95); deterministic mesh generation and self-intersection analysis; binary STL export; bounded STEP AP214 faceted triangle-shell import/export (PR #99); and bounded single-object 3MF Core import/export (PR #97). PR #117 adds a validated single-shell triangular faceted B-rep topology model and mesh bridge. PR #118 adds exact-grid UNION/INTERSECTION/DIFFERENCE/XOR for 2–16 axis-aligned box B-reps with a 32,768-cell ceiling. This is not a general B-rep kernel: n-gon/inner loops, multiple shells/cavities, arbitrary faceted solids, rotated solids, curved surfaces, general 3D arrangements, ambiguous branching, full STEP/AP242 and 3MF assemblies remain open. See the [Faceted B-rep Topology Contract](docs/design-3d/FACETED_BREP_TOPOLOGY_CONTRACT.md) and [Axis-Aligned B-rep Boolean Contract](docs/design-3d/AXIS_ALIGNED_BREP_BOOLEAN_CONTRACT.md).
- Through-hole loops, net-area/perimeter calculations, inner-wall surface area and backward-compatible optional serialization are integrated by PR #52 at `1d1628175dafca3f5d4d3d6b5cf01e241ec75afa`; exact head run #384 / `42191597715` and post-merge run #385 / `42191666816` both PASS, 425 tests each.
- Eight-family spatial-joint reference suite (residuals, Jacobian, spatial mobility/rank, ground reversal and nontrivial placements) is integrated by PR #54 at `22bbf1714224095cfd652d6887130d26facef087`; exact head run #404 / `42193562931` and post-merge run #405 / `42193654653` both PASS, 452 tests each.


## Current verified integration baseline (2026-11-06)

The integration branch is at `502d49baf58e43938d2746859e10817badd43f6e` after PR #78. PR #78 adds the triangle-mesh self-intersection design contract only; it does not implement the algorithm. Its exact PR-head workflow passed both required jobs (533 tests reported by the PR evidence), while post-merge CI for the integration SHA remains UNKNOWN. The full current audit and remaining capability gaps are recorded in [Repository Audit 2026-11-06](docs/audit/REPOSITORY_AUDIT_2026-11-06.md).


## Current verified integration baseline (post-PR #80)

Integration branch HEAD: `cb91c7c49406fd02324be6b30d5570e821b4d503`. PR #80 implements additive exact-rational triangle-mesh intersection analysis; exact PR workflow #42238370626 passed both required jobs with 550 tests, and push workflow #42238360081 passed both jobs. Post-merge CI for the integration SHA remains UNKNOWN. See [post-PR #80 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR80.md). This does not mean the entire platform is complete.


## Current verified integration baseline (post-PR #81)

Integration HEAD `1eceffbbdabd0d40f508a26dd14f99b70bc3dd53`; post-merge workflow #42239244546 passed workflow-sanity and python-tests with 550 tests in 1.97s. Recursive tree: 199 files, 92 Markdown, 90 Python, 13 schemas and 48 test files. PR #82 is the next candidate increment for a separate exact-predicate PlanarRegion input model; it does not yet implement general planar Boolean operations. See [post-PR #81 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR81.md).


## Current verified integration baseline (post-PR #82)

Integration HEAD `114bf8dd84831d7d4080922ed7069cadda380ba3`. PR #82 PlanarRegion v1.0 is merged; PR-head and push CI passed 563 tests, and post-merge workflow #42240292055 passed both required jobs with 563 tests in 2.47s. Current tree: 204 files, 94 Markdown, 92 Python, 14 schemas and 49 test files. General planar Boolean operations remain unimplemented. See [post-PR #82 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR82.md).


## Current verified integration baseline (post-PR #84)

Integration HEAD: `1b75e2dab5b64d2d089e410bba02187d28772193`. PR #84 adds a bounded pairwise exact-rational PlanarRegion Boolean API for UNION, INTERSECTION, DIFFERENCE and SYMMETRIC_DIFFERENCE, including disconnected components and holes. Exact PR-head workflow #42250468895 passed both required jobs with **580 tests in 2.14s**; exact post-merge workflow #42250583756 passed both required jobs with **580 tests in 2.96s**. The integration branch is 235 commits ahead and 0 behind `main` (`96e75010716226037893155b9fd4b13410fb0d6f`). Tree: 208 files, 95 Markdown, 94 Python, 15 JSON schemas and 48 test files. Point-touching/branching outputs fail closed; this is not a general CAD/B-rep kernel. See [post-PR #84 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR84.md).


## Current verified integration baseline (post-PR #88)

Integration HEAD `bd9379617f1bc88772137a6e9886e33cb0bed3cb`; `main` remains `96e75010716226037893155b9fd4b13410fb0d6f`; integration is 239 ahead / 0 behind. PRs #84–#88 are merged into integration only. The CAD vertical slice now supports pairwise and multi-region PlanarRegion Booleans, extrusion to an analytic solid, and validated watertight triangle meshing. PR #88 exact-head and push CI passed 607 tests each; post-merge workflow #42252619167 passed both required jobs with 607 tests. Tree: 216 files, 96 Markdown, 99 Python, 17 schemas, 51 test files. B-rep/3D Boolean, feature history, sketch constraints and STEP/3MF remain open. See [post-PR #88 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR88.md).


## Parametric sketch foundation (PR #90)

The integration branch now includes versioned 2D `ParametricSketch` records, straight segments and eight initial constraints (horizontal, vertical, coincident, distance, horizontal/vertical distance, fixed X/Y). The adapter reuses the bounded nonlinear solver and reports its convergence and rank diagnostics. PR #90 merge SHA `e2d631b49910e3d7f05fea6337742fd87385fb81`; exact-head run #42260796531 and post-merge run #42260977543 both passed 618 tests. This is a bounded point/line sketch foundation, not a complete interactive CAD sketcher. See [Parametric Sketch Constraint Contract](docs/design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md).


## Parametric CAD pipeline: sketch → region → feature history → mesh

The integration branch now supports a bounded end-to-end parametric pipeline: 2D point/line sketches with eight geometric/dimensional constraints; conversion of converged closed loops into canonical planar regions with holes and nested islands; a deterministic feature DAG with allow-listed regeneration for sketch profiles, planar Boolean, extrusion and watertight mesh validation. PR #90 (618 tests), #91 docs (620), #92 (627) and #93 (636) passed their recorded CI gates; PR #93 post-merge run #42263296016 passed both jobs with 636 tests. See [Feature History and Regeneration Contract](docs/design-3d/FEATURE_HISTORY_REGENERATION_CONTRACT.md) and [Parametric Sketch Constraint Contract](docs/design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md).


## Planar Boolean point-contact topology (PR #95)

Point-touching but otherwise disjoint material components now remain separate canonical PlanarRegion outputs using an exact-rational planar rotation-system boundary pairing rule. Edge-adjacent boundaries still dissolve into a single region. Ambiguous branching, unbalanced incidence and invalid hole topology still fail closed. PR #95 exact-head and post-merge CI both passed 639 tests. See [CAD Boolean Point-Contact Topology Contract](docs/design-3d/CAD_BOOLEAN_POINT_CONTACT_CONTRACT.md).


## 3MF Core mesh interchange (PR #97)

The integration branch now exports and imports a bounded single-object 3MF Core profile for validated watertight triangle meshes. It preserves source geometry digest, solid/frame IDs and supported units, uses deterministic ZIP/XML output, and rejects unsafe or unsupported package structures. PR #97 exact-head and post-merge CI both passed 650 tests. This does not implement full 3MF assemblies/extensions or STEP. See [3MF Core Mesh Interchange Contract](docs/engineering/3MF_CORE_MESH_INTERCHANGE_CONTRACT.md).


## Runtime resource and recovery (integrated foundation)

PR #107 integrates the bounded runtime foundation: resource registry, bounded logs, recovery lifecycle/evidence, trusted-worker process supervision, adapter catalog, in-memory quotas/leases and local metrics. PR #113 adds in-process adapter routing, local cross-process evidence locking with an unkeyed SHA-256 hash chain, and threshold-based health monitoring. Exact PR #113 head and post-merge CI passed 732 tests. These are partial runtime primitives, not a production self-healing platform or security sandbox. See [Runtime Resource Adapter and Recovery](docs/architecture/RESOURCE_ADAPTER_RECOVERY.md) and [post-PR #113 audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR113.md).


## CAD Generator local API (PR #138)

The revision-aware `CADGeneratorService` now has a local HTTP adapter with explicit startup, IPv4 loopback-only binding, dynamic port by default, bearer authentication, strict JSON/body/time limits, immutable revision save/read/list and exact-revision regeneration. A local SQLite audit log records request lifecycle metadata in a SHA-256 hash chain without storing credentials or model bodies.

The HTTP adapter is not a public or remote service. Do not expose it through LAN binding, SSH/port forwarding, reverse proxies or firewall rules. TLS, rate limiting, browser session management and remote access are not implemented. The API contract and current verification evidence are linked in [Documentation Index](DOCUMENTATION_INDEX.md).


## Local CAD Generator workbench (PR #140)

The loopback API now serves a same-origin responsive workbench for entering a bearer token, pasting/editing FeatureHistory JSON, appending immutable revisions, listing and loading revisions, and regenerating an exact revision. The token is held in page memory only. The UI uses restrictive CSP, no external resources and no CORS. This is a JSON/revision workbench, not yet a graphical sketch editor or CAD viewport. See [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md).


## Visual polygon sketch editor (PR #142)

The local CAD workbench now includes a bounded 2D SVG polygon editor with click-to-add, numeric coordinates, undo/clear and extrusion-height input. An authenticated template endpoint builds a strict fixed-coordinate ParametricSketch → Extrusion → Mesh FeatureHistory; the user reviews the JSON, saves an immutable revision, then regenerates to run geometry and watertight-mesh validation. The initial editor is limited to straight-edge polygons, 3–64 vertices and X 0–26 mm / Y 0–15 mm. It is not yet a general sketcher or 3D viewport.


## Source-linked isometric mesh preview — PR #144

The workbench now renders a bounded static isometric SVG from the exact MESH FeatureArtifact returned by regeneration. It displays source revision, vertex/triangle counts, content and computation SHA-256 digests, and backend validation flags (valid, watertight, consistently_oriented). Preview limits are 10,000 vertices and 5,000 triangles; the full artifact remains in the operation result. This is not an interactive viewport or CAD certification. See [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) and [post-PR #144 audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR144.md).


## Interactive mesh viewport — PR #146

The local CAD workbench now supports bounded client-side orbit, pan, zoom and reset controls over the exact source-linked MESH FeatureArtifact. Camera state is ephemeral and does not mutate FeatureHistory or backend geometry. Rendering is limited to 10,000 vertices and 5,000 triangles; malformed vertices and triangle indices fail closed for preview rendering. Backend mesh validation remains authoritative. This is an interactive triangle-mesh viewer, not a general CAD viewport: selection, measurement, sectioning, B-rep editing and assembly navigation remain open. See [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) and [post-PR #146 audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR146.md).


## Mesh triangle selection and measurement — PR #148

The local CAD workbench now supports selecting an individual rendered triangle facet by pointer click or keyboard activation, highlighting it, clearing the selection and reporting its area and centroid. Measurements use the mesh's declared length unit and frame. The interaction is display-only and does not mutate the source history or generated artifact. This is triangle-facet inspection, not B-rep face selection or general CAD measurement. CI: exact PR-head run #42391405409 passed 832 tests; exact post-merge run #42391470608 passed 832 tests. See [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) and [post-PR #148 audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR148.md).


## FeatureHistory tree inspector — PR #150

The local CAD workbench now provides a bounded, read-only FeatureHistory tree preview. It orders nodes deterministically by dependencies, reports malformed/cyclic graph structures without rendering them, caps the preview at 500 nodes, and lets users inspect a selected feature's ID, kind, inputs and parameters. It refreshes from edited, generated or loaded JSON and does not mutate source history. CI validates the browser script with `node --check`. Backend immutable add/replace/remove graph operations were added by PR #152; the browser tree remains read-only and does not yet expose editing controls or commit edits through the HTTP API. See [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) and [post-PR #150 audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR150.md).


## FeatureHistory immutable edit operations — PR #152

The engineering core now provides immutable add, replace and remove operations for FeatureHistory DAG documents. Replacement preserves stable feature IDs; deletion refuses to orphan downstream features unless cascade removal is explicitly requested; the output invariant is preserved. The operations return a newly validated document and do not mutate stored revisions. PR #152 exact head `3c2469a43e48d5ac2fb7e546242d9a450dff1a87`: workflow #42396387520 passed workflow-sanity and python-tests (**840 passed in 9.23s**). Exact post-merge workflow #42396453320 on `1a8338ae17eb783a374a36400999ead796f9a79d`: both jobs passed (**840 passed in 8.71s**). This is a backend editing primitive, not yet an interactive editor, suppression/undo system or API mutation workflow. See [FeatureHistory Editing Contract](docs/design-3d/FEATURE_HISTORY_EDITING_CONTRACT.md) and [post-PR #152 audit](docs/audit/REPOSITORY_AUDIT_2026-11-08_POST_PR152.md).
