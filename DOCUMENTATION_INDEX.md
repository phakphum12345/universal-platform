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

The [Implementation Status](docs/implementation/IMPLEMENTATION_STATUS.md) and [Engineering Requirements Traceability](docs/traceability/ENGINEERING_REQUIREMENTS_TRACEABILITY.md) are the source-of-truth records for code maturity and test evidence. Current integration baseline: `8335515b31a89efc4cacb70cf9c2e3aeb4ae16d4` (PR #56 merge); post-merge run `42197156442` passed workflow-sanity and python-tests, 462 tests. PR #49, #52, #54 and #56 are integrated on the engineering integration branch; this branch remains 207 commits ahead of `main`.

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
- [CAD-neutral Primitive Geometry](docs/engineering/CAD_NEUTRAL_PRIMITIVE_GEOMETRY.md) — implemented analytic primitives and profile extrusion boundaries.

## 3D design, geometry, mechanisms and manufacturing

- [3D Design Intelligence](docs/design-3d/3D_DESIGN_INTELLIGENCE.md) — 3D design scope and maturity.
- [3D Tool Generation Engine](docs/design-3d/3D_TOOL_GENERATION_ENGINE.md) — proposed tool, fixture and instrument generation.
- [3D Assembly and Kinematics](docs/design-3d/3D_ASSEMBLY_AND_KINEMATICS.md) — assembly and motion concepts.
- [3D Engineering Simulation](docs/design-3d/3D_ENGINEERING_SIMULATION.md) — proposed simulation families and validation.
- [3D Interchange and Geometry Contract](docs/design-3d/3D_INTERCHANGE_AND_GEOMETRY_CONTRACT.md) — geometry metadata and neutral exchange.
- [3D Model Validation](docs/design-3d/3D_MODEL_VALIDATION.md) — geometry, assembly and engineering validation layers.
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
