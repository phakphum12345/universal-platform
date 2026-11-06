# Universal Platform

A cross-platform, cross-disciplinary platform for learning, research, system understanding, engineering, simulation, creation, and governed evolution.

## Current status
- Stage: Phase 0 requirements baseline with active, incremental engineering-core implementation
- Implementation: Initial Python engineering core, rigid transforms, coordinate-frame forest, limited rooted-tree forward kinematics, analytic planar two-link inverse kinematics and a narrow planar four-bar loop-closure adapter; broader UEIC/CAD/CAE capabilities remain incomplete
- Principles: Local-first, cost-aware, evidence-driven, modular, secure
- Hardware boundary: Analysis and simulation only; no physical control
- Integration: Existing projects remain independent until assessed and explicitly approved
- Driver generation: Existing capability to be inventoried and reused; no duplicate generator is planned
- Engineering design: Owner-approved scope; specifications remain proposed and unimplemented

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

This is an initial foundation, not a completed universal engineering system. General CAD/B-rep, mesh/STEP/STL export, FEA/CFD, nonlinear and multiphysics solving, general inverse/closed-loop kinematics, collision/dynamics analysis, hardware schematic intelligence and generic driver generation remain unimplemented or require separate audited adapters. See [Implementation Status](docs/implementation/IMPLEMENTATION_STATUS.md).

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

- Analytic Box/Cylinder primitives, straight/curved profile extrusion, through-holes, and convex 2D profile UNION/INTERSECTION/DIFFERENCE (PR #61); general planar region topology is specified but not implemented (PR #62). PR #64 adds deterministic Box/Cylinder triangle meshes; PR #66 adds straight concave/convex profile meshes; PR #68 adds polygonal through-hole meshes; PR #70 adds circular-arc outer/hole boundary tessellation under explicit chordal tolerance. PR #71 adds the curved-hole mesh regression; post-merge CI passed 516 tests. Mesh validation remains structural only; general mesh self-intersection/repair, 3D Booleans, B-rep and STEP/STL/3MF interchange remain unsupported. PR #73 defines the binary STL export/sidecar contract; PR #74 implements deterministic binary STL export with a strict metadata sidecar (523-test post-merge CI PASS). PR #75 adds independent bounds/signed-volume and corrupt-record references (524-test post-merge CI PASS). PR #76 defines the mesh topology-analysis contract; PR #77 implements connected shells, vertex fans and duplicate/coincident coordinate diagnostics (533-test post-merge CI PASS). Triangle-triangle self-intersection remains UNKNOWN and is specified separately in PR #78. Arbitrary STL import, external CAD reopen, STEP and 3MF remain unsupported.
- Through-hole loops, net-area/perimeter calculations, inner-wall surface area and backward-compatible optional serialization are integrated by PR #52 at `1d1628175dafca3f5d4d3d6b5cf01e241ec75afa`; exact head run #384 / `42191597715` and post-merge run #385 / `42191666816` both PASS, 425 tests each.
- Eight-family spatial-joint reference suite (residuals, Jacobian, spatial mobility/rank, ground reversal and nontrivial placements) is integrated by PR #54 at `22bbf1714224095cfd652d6887130d26facef087`; exact head run #404 / `42193562931` and post-merge run #405 / `42193654653` both PASS, 452 tests each.
