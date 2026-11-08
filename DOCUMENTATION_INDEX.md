# Documentation Index

**Repository:** `phakphum12345/universal-platform`  
**Historical inventory baseline:** `9507b9fab758465763c60d02f8da83d7d8131d2d` (PR #50 head). The index was restored to the integration branch by PR #53 and extended with the spatial-joint reference contract in PR #54.  
**Inventory result:** 78 Markdown files in the recursive Git tree at the pinned baseline; this new index is intentionally excluded from that baseline count. The recursive tree response was not truncated.  
**Purpose:** Canonical navigation for product intent, architecture, engineering contracts, hardware, CAD/3D, implementation evidence, requirements and operations.

## How to read documentation status

- **IMPLEMENTED** — source code exists for the stated narrow behavior. This label does not imply a complete product capability.
- **PARTIAL** — some sub-capabilities exist; important scope remains missing.
- **PLANNED** — proposed design or roadmap only; implementation is not established.
- **BLOCKED** — a required prerequisite or owner decision prevents progress.
- **UNKNOWN** — available evidence is insufficient to classify the implementation.
- **PASS / FAIL / SKIPPED / UNKNOWN** are evidence outcomes, not maturity labels. A documentation statement or successful workflow alone does not establish physical or engineering validity.

The [Implementation Status](docs/implementation/IMPLEMENTATION_STATUS.md) and [Engineering Requirements Traceability](docs/traceability/ENGINEERING_REQUIREMENTS_TRACEABILITY.md) are the source-of-truth records for code maturity and test evidence. Historical documentation baselines remain pinned in their respective audit entries. Last audited integration snapshot: 93744335f3e50a07dde2f78a18f9a307308b73ef; PR #169 post-merge workflow-sanity and python-tests (860 tests) passed. Main remains 96e75010716226037893155b9fd4b13410fb0d6f; integration is 414 commits ahead / 0 behind. Inventory at this baseline: 359 entries, 122 Markdown, 167 Python, 24 JSON files and 86 Python test files. FeatureHistory suppression is end-to-end IMPLEMENTED; Undo/Redo store is IMPLEMENTED by PR #169; service/API is in PR #170 and workbench/browser E2E remain open; branching/merging, reorder, generalized B-rep and overall repository completion remain INCOMPLETE.

## Repository-level product and governance

- [README](README.md) — entry point, current scope and documentation map.
- [Vision](VISION.md) — product purpose and principles.
- [Master Blueprint](MASTER_BLUEPRINT.md) — consolidated capability and architecture blueprint.
- [Roadmap](ROADMAP.md) — phased delivery and evidence gates.
- [Contributing](CONTRIBUTING.md) — contribution and change expectations.
- [Decision Register](docs/decisions/DECISION_REGISTER.md) — confirmed decisions, proposals and open questions.
- [Engineering Technology Decisions](docs/decisions/ENGINEERING_TECHNOLOGY_DECISIONS.md) — tool, solver and CAD technology evaluation policy.
- [Domain Catalogue](docs/DOMAIN_CATALOGUE.md) — cross-disciplinary domain taxonomy.
- [Universal Requirements](docs/requirements/UNIVERSAL_REQUIREMENTS.md) — top-level requirements and quality attributes.
- [Requirements Traceability Matrix](docs/traceability/REQUIREMENTS_TRACEABILITY_MATRIX.md) — product-level requirement status and remaining gaps.

## Architecture and system contracts

- [Platform Architecture](docs/architecture/PLATFORM_ARCHITECTURE.md) — conceptual layers and boundaries.
- [Engineering Data Model](docs/architecture/ENGINEERING_DATA_MODEL.md) — engineering entities, revisions, units and provenance.
- [Engineering Module API Contract](docs/architecture/ENGINEERING_MODULE_API_CONTRACT.md) — module metadata, request/response and authority boundary.
- [Frame-bound Coordinate Contract](docs/architecture/FRAMED_COORDINATE_CONTRACT.md) — framed points and displacement vectors.
- [System Intelligence](docs/architecture/SYSTEM_INTELLIGENCE.md) — authorized discovery and adaptation workflow.
- [Universal Command System](docs/architecture/UNIVERSAL_COMMAND_SYSTEM.md) — proposed cross-interface task envelope and lifecycle.

## Engineering intelligence, physics and calculation

- [Universal Engineering Intelligence Core](docs/engineering/UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE.md) — UEIC responsibilities and maturity.
- [Multidisciplinary Knowledge Modules](docs/engineering/MULTIDISCIPLINARY_KNOWLEDGE_MODULES.md) — discipline module taxonomy and interoperability.
- [Physics and First-Principles Modeling](docs/engineering/PHYSICS_AND_FIRST_PRINCIPLES.md) — proposed reusable physical models.
- [Universal Calculation Engine](docs/engineering/UNIVERSAL_CALCULATION_ENGINE.md) — calculation record and domain engine proposal.
- [Engineering Solver and Model Contract](docs/engineering/ENGINEERING_SOLVER_AND_MODEL_CONTRACT.md) — solver invocation and reproducibility.
- [Nonlinear Constraint Solver Contract](docs/engineering/NONLINEAR_CONSTRAINT_SOLVER_CONTRACT.md) — implemented narrow numerical solver and limitations.
- [Quantity Schema Contract](docs/engineering/QUANTITY_SCHEMA_CONTRACT.md) — typed SI quantity interchange.
- [Units, Uncertainty and Provenance](docs/engineering/ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE.md) — units, evidence and lineage.
- [Cross-Domain Constraint Solving](docs/engineering/CROSS_DOMAIN_CONSTRAINT_SOLVING.md) — proposed multidisciplinary constraint model.
- [Mechanism Constraint Adapter Contract](docs/engineering/MECHANISM_CONSTRAINT_ADAPTER_CONTRACT.md) — proposed general adapter boundary.
- [Engineering Failure Modes](docs/engineering/ENGINEERING_FAILURE_MODES.md) — error taxonomy and failure semantics.
- [Engineering Reference Cases](docs/engineering/ENGINEERING_REFERENCE_CASES.md) — reference-case design catalogue.
- [CAD-neutral Primitive Geometry](docs/engineering/CAD_NEUTRAL_PRIMITIVE_GEOMETRY.md) — analytic primitives, straight/curved profile extrusion and known CAD-kernel boundaries.

- [FeatureHistory Suppression Contract](docs/design-3d/FEATURE_HISTORY_SUPPRESSION_CONTRACT.md) — end-to-end suppression semantics, v1.0/v1.1 compatibility, API/UI and acceptance evidence.
- [FeatureHistory Undo/Redo Contract](docs/design-3d/FEATURE_HISTORY_UNDO_REDO_CONTRACT.md) — proposed persistent, append-only undo/redo semantics and acceptance gates; design only.
- [CAD Generator HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) — authenticated loopback endpoints, strict request schemas and revision-safe editing.

## 3D design, geometry, mechanisms and manufacturing

- [3D Design Intelligence](docs/design-3d/3D_DESIGN_INTELLIGENCE.md) — 3D design scope and maturity.
- [3D Tool Generation Engine](docs/design-3d/3D_TOOL_GENERATION_ENGINE.md) — proposed tool, fixture and instrument generation.
- [3D Assembly and Kinematics](docs/design-3d/3D_ASSEMBLY_AND_KINEMATICS.md) — assembly and motion concepts.
- [3D Engineering Simulation](docs/design-3d/3D_ENGINEERING_SIMULATION.md) — proposed simulation families and validation.
- [3D Interchange and Geometry Contract](docs/design-3d/3D_INTERCHANGE_AND_GEOMETRY_CONTRACT.md) — geometry metadata and neutral exchange.
- [3D Model Validation](docs/design-3d/3D_MODEL_VALIDATION.md) — geometry, assembly and engineering validation layers.
- [Deterministic Primitive Triangle Mesh Contract](docs/design-3d/TRIANGLE_MESH_GENERATION_CONTRACT.md) — implemented Box/Cylinder and straight/arc profile tessellation, including polygonal holes, with structural validation scope.
- [Binary STL Interchange](docs/design-3d/STL_INTERCHANGE_CONTRACT.md) — implemented binary export and metadata sidecar; arbitrary import remains open.
- [Mesh Geometric Topology Analysis](docs/design-3d/MESH_GEOMETRIC_TOPOLOGY_ANALYSIS_CONTRACT.md) — implemented diagnostic layer; self-intersection remains open.
- [Mesh Triangle Intersection](docs/design-3d/MESH_TRIANGLE_INTERSECTION_CONTRACT.md) — implemented additive exact-rational intersection analysis; topology v1.0 remains backward compatible.
- [3D Motion and Mechanism Reference Cases](docs/design-3d/3D_MOTION_AND_MECHANISM_REFERENCE_CASES.md) — deterministic mechanism fixtures.
- [CAD to Manufacturing Pipeline](docs/design-3d/CAD_TO_MANUFACTURING_PIPELINE.md) — proposed manufacturing artifact workflow.
- [Structural and Civil Design](docs/design-3d/STRUCTURAL_AND_CIVIL_DESIGN.md) — proposed structural/civil engineering scope.
- [Coordinate Frames and Rigid Transforms](docs/design-3d/COORDINATE_FRAMES_AND_RIGID_TRANSFORMS.md) — transform conventions and API.
- [Coordinate Frame and Transform Contract](docs/design-3d/COORDINATE_FRAME_AND_TRANSFORM_CONTRACT.md) — frame graph and serialization.
- [Assembly Tree Forward-Kinematics Contract](docs/design-3d/ASSEMBLY_TREE_FORWARD_KINEMATICS_CONTRACT.md) — limited tree-only FK.
- [Joint and Geometry Placement Contract](docs/design-3d/JOINT_AND_GEOMETRY_PLACEMENT_CONTRACT.md) — schema v1.1 placements.
- [Normalized Mechanism Model Contract](docs/design-3d/NORMALIZED_MECHANISM_MODEL_CONTRACT.md) — stable-ID links, joints and references.
- [Generalized Coordinate and Joint Parameterization](docs/design-3d/GENERALIZED_COORDINATE_AND_JOINT_PARAMETERIZATION_CONTRACT.md) — schema v1.2 coordinate mapping.
- [Spatial Joint Reference Validation](docs/design-3d/SPATIAL_JOINT_REFERENCE_VALIDATION_CONTRACT.md) — eight-family reference coverage and acceptance criteria.
- [General Loop Closure Contract](docs/design-3d/GENERAL_LOOP_CLOSURE_CONTRACT.md) — graph topology and loop concepts.
- [Geometry-aware Loop Closure Contract](docs/design-3d/GEOMETRY_AWARE_LOOP_CLOSURE_CONTRACT.md) — evaluation of supplied configurations.
- [Geometric Loop Coordinate Solver Contract](docs/design-3d/GEOMETRIC_LOOP_COORDINATE_SOLVER_CONTRACT.md) — bounded coordinate fitting with fixed body poses.
- [Automatic Joint Constraint Generation](docs/design-3d/AUTOMATIC_JOINT_CONSTRAINT_GENERATION_CONTRACT.md) — generated pose-consistency residuals.
- [Automatic Joint Constraint Jacobian](docs/design-3d/AUTOMATIC_JOINT_CONSTRAINT_JACOBIAN_CONTRACT.md) — finite-difference Jacobian contract.
- [Automatic Geometric Mobility](docs/design-3d/AUTOMATIC_GEOMETRIC_MOBILITY_CONTRACT.md) — spatial local mobility diagnostics.
- [Planar Plane-Frame Mobility](docs/design-3d/PLANAR_PLANE_FRAME_MOBILITY_CONTRACT.md) — implemented PR #56 contract, acceptance criteria and exact CI evidence.
- [Planar Two-Link Inverse Kinematics](docs/design-3d/PLANAR_TWO_LINK_INVERSE_KINEMATICS_CONTRACT.md) — narrow analytic planar 2R adapter.
- [Planar Four-Bar Loop Closure](docs/design-3d/PLANAR_FOUR_BAR_LOOP_CLOSURE_CONTRACT.md) — narrow planar 4R closure and mobility estimate.

## Hardware, schematic and drivers

- [Device Intelligence](docs/hardware/DEVICE_INTELLIGENCE.md) — IC, board, sensor and module analysis.
- [Schematic Intelligence](docs/hardware/SCHEMATIC_INTELLIGENCE.md) — proposed schematic interpretation capability.
- [Hardware Schematic Netlist Contract](docs/hardware/HARDWARE_SCHEMATIC_NETLIST_CONTRACT.md) — implemented connectivity graph model.
- [Hardware Design Verification](docs/hardware/HARDWARE_DESIGN_VERIFICATION.md) — proposed hardware verification rules and outputs.
- [Hardware-to-Software Mapping](docs/hardware/HARDWARE_TO_SOFTWARE_MAPPING.md) — proposed device-to-software mapping.
- [Driver Architecture Intelligence](docs/hardware/DRIVER_ARCHITECTURE_INTELLIGENCE.md) — driver architecture analysis.
- [Hardware Driver Interface Contract](docs/hardware/DRIVER_INTERFACE_CONTRACT.md) — metadata-only interface and pin-binding subset.
- [Driver Refactoring Engine](docs/hardware/DRIVER_REFACTORING_ENGINE.md) — proposed governed refactoring workflow.
- [Schematic-to-Driver Traceability](docs/hardware/SCHEMATIC_DRIVER_TRACEABILITY.md) — cross-artifact traceability and implemented subset.

## Implementation evidence, audits and traceability

- [Implementation Status](docs/implementation/IMPLEMENTATION_STATUS.md) — current merged baseline and exact CI evidence.
- [Engineering Requirements Traceability](docs/traceability/ENGINEERING_REQUIREMENTS_TRACEABILITY.md) — requirement-to-code/schema/test evidence.
- [Requirements Traceability Matrix](docs/traceability/REQUIREMENTS_TRACEABILITY_MATRIX.md) — top-level requirement coverage.
- [Repository Capability Inventory](docs/audit/REPOSITORY_CAPABILITY_INVENTORY.md) — historical audit snapshot; use newer implementation status for current code state.
- [Post-PR-1 Baseline Audit](docs/audit/POST_PR1_BASELINE_AUDIT.md) — historical baseline reconciliation.

## Governance, integration, laboratory and operations

- [Engineering Safety and Approval](docs/governance/ENGINEERING_SAFETY_AND_APPROVAL.md) — safety tiers and approval boundaries.
- [Engineering Hazard Register](docs/governance/ENGINEERING_HAZARD_REGISTER.md) — starter hazard register.
- [Project Integration Policy](docs/integration/PROJECT_INTEGRATION.md) — no automatic integration of external projects.
- [Virtual Lab and Simulation](docs/laboratories/VIRTUAL_LAB_AND_SIMULATION.md) — proposed isolated experiment environments.
- [Platform Self-Evolution](docs/evolution/PLATFORM_SELF_EVOLUTION.md) — governed capability lifecycle.
- [Engineering Release and Rollback](docs/operations/ENGINEERING_RELEASE_AND_ROLLBACK.md) — proposed release and rollback controls.
- [Engineering Resource Budget](docs/operations/ENGINEERING_RESOURCE_BUDGET.md) — resource measurement framework.
- [Engineering Reference Validation Pack](docs/reference/ENGINEERING_REFERENCE_VALIDATION_PACK.md) — executable cross-discipline reference cases.
- [Engineering Test Strategy](docs/testing/ENGINEERING_TEST_STRATEGY.md) — test levels, evidence semantics and current coverage.
- [Engineering and 3D Phase Plan](docs/roadmap/ENGINEERING_AND_3D_PHASE_PLAN.md) — phased engineering delivery plan.
- [Engineering Master File Plan](docs/roadmap/ENGINEERING_MASTER_FILE_PLAN.md) — planned file/module inventory.
- [Engineering Vertical Slice Specification](docs/roadmap/ENGINEERING_VERTICAL_SLICE_SPEC.md) — end-to-end slice acceptance.
- [Phase 2 Numerical Reliability Plan](docs/roadmap/PHASE_2_NUMERICAL_RELIABILITY_PLAN.md) — numerical reliability work packages.

## Maintenance rules

1. Update this index whenever a Markdown file is added, moved or renamed.
2. Keep implementation status tied to source paths, schemas, tests, exact commit SHAs and workflow evidence.
3. Mark proposals as PLANNED; do not upgrade maturity based on document presence.
4. Keep historical audits labelled historical and link to the current status ledger.
5. Check relative links after documentation changes; report any link not verifiable from the pinned tree as UNKNOWN.


- [Repository Audit 2026-11-06](docs/audit/REPOSITORY_AUDIT_2026-11-06.md) — historical PR #78 baseline.
- [Repository Audit post-PR #80](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR80.md) — current integration SHA, PR #80 evidence, maturity boundaries and remaining gated work.

- [Planar Geometry Precision Policy](docs/decisions/PLANAR_GEOMETRY_PRECISION_POLICY.md) — dependency-free exact-rational predicate policy for PlanarRegion v1.
- [Repository Audit post-PR #81](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR81.md) — current baseline, tree counts, maturity boundaries and next gated work.

- [Planar Region Model](schemas/geometry/planar-region.schema.json) — PlanarRegion v1.0 schema; exact-rational input validation and hole topology.
- [Planar Geometry Precision Policy](docs/decisions/PLANAR_GEOMETRY_PRECISION_POLICY.md) — selected dependency-free predicate policy.
- [Repository Audit post-PR #82](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR82.md) — current baseline, tree counts, implemented maturity and remaining gated work.


- [Repository Audit post-PR #84](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR84.md) — integration SHA, exact PR-head/post-merge CI, PlanarRegion Boolean implementation scope and remaining gates.
- [PlanarRegion Boolean Result](schemas/geometry/planar-region-boolean-result.schema.json) — versioned result envelope, source digests, output regions and rounding-error metrics.


- [Repository Audit post-PR #88](docs/audit/REPOSITORY_AUDIT_2026-11-06_POST_PR88.md) — exact integration SHA, PR #84–#88 evidence, CAD Boolean-to-mesh vertical slice and remaining engineering gates.
- [PlanarRegion Set Boolean Result](schemas/geometry/planar-region-set-boolean-result.schema.json) — versioned multi-region Boolean output envelope.
- [PlanarRegion Extrusion Result](schemas/geometry/planar-region-extrusion-result.schema.json) — source-bound conversion from PlanarRegion to ExtrudedProfileSolid.


- [Parametric Sketch Constraint Contract](docs/design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md) — v1.0 point/line sketch data model, supported constraints, solver semantics, limitations and PR #90 evidence.
- [Parametric Sketch Schema](schemas/geometry/parametric-sketch.schema.json) — strict JSON Schema for versioned 2D sketches.


- [Feature History and Regeneration Contract](docs/design-3d/FEATURE_HISTORY_REGENERATION_CONTRACT.md) — versioned DAG, allow-listed feature execution, deterministic regeneration, artifact hashes and failure semantics.
- [Feature History Schema](schemas/geometry/feature-history.schema.json) — strict v1.0 feature graph schema.
- [Parametric Sketch Constraint Contract](docs/design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md) — 2D parametric sketch model and initial constraint families.


- [CAD Boolean Point-Contact Topology Contract](docs/design-3d/CAD_BOOLEAN_POINT_CONTACT_CONTRACT.md) — exact-rational boundary pairing, point-contact component semantics, failure modes and PR #95 evidence.


- [3MF Core Mesh Interchange Contract](docs/engineering/3MF_CORE_MESH_INTERCHANGE_CONTRACT.md) — supported 3MF profile, provenance, deterministic package output, parser safety and explicit interoperability limits.

- [Runtime Resource Adapter and Recovery](docs/architecture/RESOURCE_ADAPTER_RECOVERY.md) — typed resource registry, bounded log ingestion, recovery lifecycle, process supervision, adapter replacement, quota leases, resource sampling and remaining security gates.


- [Repository Audit post-PR #113](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR113.md) — current exact integration/main SHAs, tree inventory, PR #99/#107/#110/#113 evidence and remaining CAD/EDA/physics/runtime gates.
- [Physics and First-Principles Modeling](docs/engineering/PHYSICS_AND_FIRST_PRINCIPLES.md) — central solver registry boundary, built-in analytical solvers and unimplemented domain families.
- [Runtime Resource Adapter and Recovery](docs/architecture/RESOURCE_ADAPTER_RECOVERY.md) — current registry, recovery, trusted process supervision, adapter routing, evidence integrity, resource health and security limits.


- [Faceted B-rep Topology Contract](docs/design-3d/FACETED_BREP_TOPOLOGY_CONTRACT.md) — v1.0 closed triangular planar shell topology, exact validation invariants, mesh bridge and explicit limitations.
- [Faceted B-rep Solid Schema](schemas/geometry/faceted-brep-solid.schema.json) — strict versioned topology snapshot schema.


- [Axis-Aligned Faceted B-rep Boolean Contract](docs/design-3d/AXIS_ALIGNED_BREP_BOOLEAN_CONTRACT.md) — bounded exact-grid UNION/INTERSECTION/DIFFERENCE/XOR for 2–16 axis-aligned box B-rep inputs.
- [B-rep Boolean Result Schema](schemas/geometry/brep-boolean-result.schema.json) — strict result envelope, source digests and component shells.


## CAD Generator local API — PR #138

- [CAD Generator Service Contract](docs/design-3d/CAD_GENERATOR_SERVICE_CONTRACT.md) — revision-aware in-process service, durable source revisions and artifact cache.
- [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) — implemented authenticated, loopback-only local HTTP adapter, dynamic port, strict request bounds and append-only local audit evidence.
- [Implementation Status](docs/implementation/IMPLEMENTATION_STATUS.md) — exact integration SHA, current CI evidence and remaining work.


## CAD Generator local workbench — PR #140

- [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) — includes the same-origin local FeatureHistory workbench, token handling, CSP and capability boundaries.
- Static UI assets: `src/universal_platform/engineering/static/cad_generator.html`, `cad_generator.css`, `cad_generator.js`.
- The current workbench edits FeatureHistory JSON and manages revisions; graphical sketch editing and a CAD viewport remain OPEN.


## Visual polygon sketch editor — PR #142

- [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) — includes the bounded polygon template endpoint and same-origin visual sketch workflow.
- [CAD Generator implementation](docs/implementation/IMPLEMENTATION_STATUS.md) — exact PR-head/post-merge CI evidence and remaining visual CAD scope.
- The editor creates straight-edge polygon FeatureHistory snapshots; arcs, holes, general constraints and 3D viewport remain OPEN.


## Source-linked mesh preview — PR #144

- [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) — static isometric SVG preview, exact artifact provenance and backend validation display.
- [Post-PR #144 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR144.md) — exact integration/main SHAs, PR #144 CI and current capability boundary.
- Interactive orbit/pan/zoom, selection, sectioning and general CAD viewport remain OPEN.


## Interactive mesh viewport — PR #146

- [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) — bounded client-side orbit, pan, zoom and reset controls over the generated mesh artifact.
- [Post-PR #146 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR146.md) — exact integration/main SHAs, exact PR-head and post-merge CI evidence, repository inventory and audit limitations.
- Feature-tree editing, selection, measurement, sectioning, B-rep editing and general CAD-kernel operations remain OPEN.


## Mesh triangle selection and measurement — PR #148

- [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) — accessible triangle-facet selection, highlighting, area and centroid display using mesh units and frame.
- [Post-PR #148 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR148.md) — exact PR-head/post-merge CI evidence, current tree inventory and remaining capability limits.
- B-rep face/edge selection, sectioning, editing and general CAD-kernel operations remain OPEN.


## FeatureHistory tree inspector — PR #150

- [CAD Generator Loopback HTTP API Contract](docs/design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md) — bounded read-only FeatureHistory tree preview and selected-node inspection.
- [Post-PR #150 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-07_POST_PR150.md) — exact PR-head/post-merge CI, JavaScript syntax validation, tree inventory and security-audit limitations.
- Backend immutable add/replace/remove graph operations, revision-safe loopback service/API editing and bounded browser parameter/add/remove controls are implemented by PRs #152, #154 and #156. Browser E2E interaction coverage, feature suppression, undo/redo, reordering and recompute propagation remain OPEN.


## Documentation-driven execution

- [Master Execution](docs/execution/MASTER_EXECUTION.md) — audit, implementation, PR, verification and documentation synchronization loop.
- [Work Package Status](docs/execution/WORK_PACKAGE_STATUS.md) — evidence-based status across the repository work packages.
- [FeatureHistory Editing Contract](docs/design-3d/FEATURE_HISTORY_EDITING_CONTRACT.md) — immutable add/replace/remove operations and graph-safety rules.
- [Pre-execution Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-08_PRE_EXECUTION.md) — verified branch, CI, inventory, known gaps and evidence limitations.

- [Post-PR #152 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-08_POST_PR152.md) — exact PR-head and post-merge CI evidence, implementation scope and remaining gates.

- [Post-PR #154 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-08_POST_PR154.md) — exact PR-head and post-merge CI evidence for revision-safe FeatureHistory API editing.
- [Post-PR #156 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-08_POST_PR156.md) — exact PR-head/post-merge CI evidence for browser FeatureHistory editing controls and remaining quality gates.

- [Post-PR #158 Repository Audit](docs/audit/REPOSITORY_AUDIT_2026-11-08_POST_PR158.md) — exact PR-head and post-merge CI evidence for real Chromium FeatureHistory editor coverage; remaining CAD and repository-wide gaps.
