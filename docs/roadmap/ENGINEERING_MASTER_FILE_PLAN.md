# Engineering Master File Plan — UEIC and 3D Design

**Status:** PROPOSED DELIVERY BASELINE  
**Scope direction:** CONFIRMED by owner  
**Implementation authorization:** Not implied by this plan  
**Driver Generation:** Existing capability to locate and reuse; do not duplicate

## 1. Purpose

This is the authoritative file-level delivery plan for the Universal Engineering Intelligence Core (UEIC), multidisciplinary engineering modules and 3D design/tool-generation system. It defines documentation, contracts, schemas, source modules, tests, fixtures and evidence artifacts to be created or extended after the source inventory and architecture gates pass.

The plan is intentionally technology-neutral. File extensions and module boundaries below are logical targets, not a decision to use a particular language, CAD kernel, solver, database or service topology.

## 2. File-state vocabulary

- EXISTING-DOC: documentation already present in the audited branch.
- ADD-DOC: documentation artifact required by this plan.
- ADD-SCHEMA: versioned machine-readable contract to create after format decision.
- ADD-SOURCE: implementation target; do not create before the architecture gate.
- ADD-TEST: automated test target.
- ADD-FIXTURE: reference input/model/dataset target.
- EXTERNAL-ADAPTER: integration to an existing external tool or project.
- REUSE: inspect and consume existing implementation; do not recreate.
- UNKNOWN: location/existence not established.

## 3. Existing documentation to retain and extend

| Area | Existing file | Plan |
|---|---|---|
| Requirements | docs/requirements/UNIVERSAL_REQUIREMENTS.md | Extend only when new requirements are approved |
| Platform architecture | docs/architecture/PLATFORM_ARCHITECTURE.md | Link UEIC as a domain-neutral engineering subsystem |
| UEIC API | docs/architecture/ENGINEERING_MODULE_API_CONTRACT.md | Extend with finalized schemas and compatibility policy |
| Engineering data | docs/architecture/ENGINEERING_DATA_MODEL.md | Extend with typed geometry, simulation and evidence references |
| UEIC core | docs/engineering/UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE.md | Master logical core specification |
| Discipline catalogue | docs/engineering/MULTIDISCIPLINARY_KNOWLEDGE_MODULES.md | Module registry/lifecycle specification |
| Physics | docs/engineering/PHYSICS_AND_FIRST_PRINCIPLES.md | Model validity and reference-case catalogue |
| Calculation | docs/engineering/UNIVERSAL_CALCULATION_ENGINE.md | Reuse/extend after source audit |
| Solver contract | docs/engineering/ENGINEERING_SOLVER_AND_MODEL_CONTRACT.md | Solver adapter contract |
| Units/provenance | docs/engineering/ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE.md | Cross-cutting quantity/evidence contract |
| Cross-domain | docs/engineering/CROSS_DOMAIN_CONSTRAINT_SOLVING.md | Constraint graph and conflict policy |
| CAD design | docs/design-3d/3D_DESIGN_INTELLIGENCE.md | Parametric CAD and import/export requirements |
| Tool generation | docs/design-3d/3D_TOOL_GENERATION_ENGINE.md | Tool/fixture/mechanism requirements |
| Assembly | docs/design-3d/3D_ASSEMBLY_AND_KINEMATICS.md | Joint, DOF, motion and tolerance requirements |
| Simulation | docs/design-3d/3D_ENGINEERING_SIMULATION.md | CAE and validation requirements |
| Manufacturing | docs/design-3d/CAD_TO_MANUFACTURING_PIPELINE.md | DFM/DFA and controlled export |
| Validation | docs/design-3d/3D_MODEL_VALIDATION.md | Model verification and evidence |
| Structural/civil | docs/design-3d/STRUCTURAL_AND_CIVIL_DESIGN.md | Standards and professional review |
| Hardware | docs/hardware/*.md | Preserve HWR-001..HWR-006; connect to UEIC without duplicating driver generation |
| Governance | docs/governance/ENGINEERING_SAFETY_AND_APPROVAL.md | Mandatory across the lifecycle |
| Audit | docs/audit/REPOSITORY_CAPABILITY_INVENTORY.md | Record evidence and unresolved inventory |

## 4. Additional documentation artifacts

| Priority | Target path | Purpose | Dependency |
|---|---|---|---|
| P0 | docs/audit/REPOSITORY_CAPABILITY_INVENTORY.md | Actual repository/source capability inventory | Initial audit |
| P0 | docs/roadmap/ENGINEERING_MASTER_FILE_PLAN.md | This file; canonical file map | Requirements baseline |
| P0 | docs/roadmap/ENGINEERING_VERTICAL_SLICE_SPEC.md | First end-to-end workflow and acceptance gates | Owner selects use case |
| P0 | docs/decisions/ENGINEERING_TECHNOLOGY_DECISIONS.md | Record CAD/solver/schema/tool evaluations and decisions | Full source inventory |
| P1 | docs/engineering/ENGINEERING_REFERENCE_CASES.md | Reference equations, expected values, tolerances and validation sources | Discipline priority |
| P1 | docs/engineering/ENGINEERING_FAILURE_MODES.md | Numerical, model, data, geometry and integration failure taxonomy | API/data contracts |
| P1 | docs/design-3d/3D_INTERCHANGE_AND_GEOMETRY_CONTRACT.md | Coordinate frames, topology, units, neutral exchange and round-trip rules | CAD candidate evaluation |
| P1 | docs/design-3d/3D_MOTION_AND_MECHANISM_REFERENCE_CASES.md | Joint/DOF and kinematic acceptance fixtures | Kinematics scope |
| P1 | docs/governance/ENGINEERING_HAZARD_REGISTER.md | Hazard identification, risk controls and review ownership | First vertical slice |
| P1 | docs/testing/ENGINEERING_TEST_STRATEGY.md | Unit, contract, reference, integration and regression testing | Architecture baseline |
| P2 | docs/operations/ENGINEERING_RESOURCE_BUDGET.md | Local compute, memory, storage, runtime and cost budgets | Benchmarking |
| P2 | docs/operations/ENGINEERING_RELEASE_AND_ROLLBACK.md | Packaging, release, versioning and rollback controls | Stable implementation |

## 5. Logical source layout — create only after architecture approval

The names below are proposed logical boundaries. Consolidate or rename them if the inspected existing project already has suitable modules.

### 5.1 UEIC foundation
- core/ueic/problem_intake
- core/ueic/discipline_registry
- core/ueic/model_planner
- core/ueic/constraint_graph
- core/ueic/solver_orchestrator
- core/ueic/evidence_recorder
- core/ueic/review_gateway

### 5.2 Shared engineering services
- core/engineering/quantities
- core/engineering/units
- core/engineering/coordinate_frames
- core/engineering/provenance
- core/engineering/uncertainty
- core/engineering/validation

### 5.3 Discipline modules
- domains/physics
- domains/mathematics
- domains/mechanics
- domains/materials
- domains/thermodynamics
- domains/fluid_dynamics
- domains/electrical_electronics
- domains/control
- domains/chemistry
- domains/manufacturing
- domains/structural_civil
- domains/computing

Each discipline is a separately versioned module behind the shared contract. Do not create empty folders or placeholder implementations merely to match this list.

### 5.4 3D/CAD subsystem
- engineering3d/geometry
- engineering3d/parametric_design
- engineering3d/parts
- engineering3d/assemblies
- engineering3d/kinematics
- engineering3d/tool_generation
- engineering3d/cad_adapters
- engineering3d/validation
- engineering3d/export

### 5.5 External adapters and existing capability
- adapters/solver
- adapters/cad
- adapters/simulation
- adapters/driver_generation — EXTERNAL-ADAPTER / REUSE only after locating the existing Driver Generation source.

### 5.6 Test and evidence layout
- tests/unit
- tests/contracts
- tests/reference_cases
- tests/integration
- tests/regression
- tests/fixtures/engineering
- tests/fixtures/cad
- tests/fixtures/mechanisms
- evidence/baselines
- evidence/validation

## 6. Machine-readable contracts to create after schema decision

| Schema target | Core entities |
|---|---|
| schemas/engineering/module-manifest.schema.json | module ID/version, lifecycle, domain, dependencies, license, permissions |
| schemas/engineering/engineering-case.schema.json | task, requirements, variables, constraints, selected modules |
| schemas/engineering/quantity.schema.json | value, unit, dimension, uncertainty, provenance |
| schemas/engineering/model.schema.json | equations, validity range, assumptions, boundary conditions |
| schemas/engineering/solver-request.schema.json | model, solver, resource limits, authorization, cancellation |
| schemas/engineering/solver-result.schema.json | outputs, numerical health, warnings, status, evidence |
| schemas/engineering/evidence-record.schema.json | procedure, criterion, result, environment, reviewer |
| schemas/geometry/coordinate-frame.schema.json | frame identity, origin, axes, handedness, units |
| schemas/geometry/cad-model.schema.json | model revision, units, geometry refs, feature history, provenance |
| schemas/geometry/assembly.schema.json | part occurrences, revisions, joints, constraints |
| schemas/geometry/motion-case.schema.json | DOF, joint limits, motion profiles, outputs |
| schemas/geometry/manufacturing-package.schema.json | drawings, BOM, materials, process, export manifest |

Schema language/version, serialization and compatibility policy remain OPEN until a vertical slice and toolchain evaluation.

## 7. Test and fixture plan

- Dimensional analysis: valid and invalid equations.
- Unit conversion: canonical and domain-specific units.
- Provenance: derived values preserve source lineage.
- Solver adapters: invalid input, timeout, cancellation, non-convergence and malformed output.
- Cross-domain constraints: feasible, infeasible and conflicting models.
- Physics: analytical reference cases and limiting conditions.
- Geometry: valid solids, degeneracy, self-intersection and unit/scale preservation.
- CAD interchange: import/export/reopen and round-trip comparison.
- Assembly: fixed/revolute/prismatic joints, DOF, over-constraint and collision.
- Kinematics: position, velocity, acceleration, limits and singularity fixtures.
- Manufacturing: BOM reconciliation, process constraints and export integrity.
- Governance: permission denial, approval required, audit completeness and no physical-control path.

Every test must pin input revision, expected criterion, tolerances, tool version and evidence output. Expected values require authoritative references or independently reviewed calculations.

## 8. Reuse/extend/create decision rules

1. REUSE if existing code meets the contract, has acceptable license/security, tests and maintenance.
2. EXTEND if the existing component is structurally suitable and a minimal compatible change can meet requirements.
3. ADAPTER if a stable external tool or existing Driver Generation can be consumed without taking ownership of its internals.
4. CREATE only when the inventory shows a real capability gap and the owner approves the architecture.
5. DEFER if licensing, validation, safety, compute cost or maintenance is unacceptable.
6. UNKNOWN if source, tests or provenance cannot be inspected.

Do not duplicate Driver Generation. Do not choose a CAD kernel or solver before comparing capabilities, licensing, offline behavior, platform support, interoperability and validation.

## 9. Change-control gates

- Gate A — Full source inventory and Driver Generation location.
- Gate B — Requirements and architecture review.
- Gate C — Technology decision and license/security review.
- Gate D — Vertical-slice specification and acceptance tests.
- Gate E — Owner authorization for code diff.
- Gate F — Isolated implementation and test evidence.
- Gate G — Human review before merge/release.
- Gate H — Separate authorization for any future physical execution.

## 10. Current completion state

Documentation specifications: substantial baseline exists.  
Repository source inventory: PARTIAL / BLOCKED.  
Driver Generation location: UNKNOWN.  
Technology decisions: OPEN.  
Vertical slice: OPEN.  
Implementation: NOT STARTED / NOT VERIFIED.  
No code diff, merge or deployment is authorized by this file plan.
