# Engineering and 3D Requirements Traceability

**Status:** Proposed mapping baseline with narrow executable engineering slices; general CAD/CAE and mechanism solving remain open.

| ID | Requirement | Primary specification | Acceptance evidence |
|---|---|---|---|
| UEIC-001 | Shared multidisciplinary engineering core | UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE | Module composition and provenance tests |
| UEIC-002 | Pluggable discipline modules | MULTIDISCIPLINARY_KNOWLEDGE_MODULES | Registry contract and compatibility tests |
| UEIC-003 | First-principles physics models | PHYSICS_AND_FIRST_PRINCIPLES | Reference cases and dimensional checks |
| UEIC-004 | Replaceable solver adapters | ENGINEERING_SOLVER_AND_MODEL_CONTRACT; NONLINEAR_CONSTRAINT_SOLVER_CONTRACT | Bounded local nonlinear equality solver; general mechanism adapter remains in progress |
| UEIC-005 | Units, uncertainty and source lineage | ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE | Unit, propagation and provenance tests |
| UEIC-006 | Cross-domain constraints | CROSS_DOMAIN_CONSTRAINT_SOLVING | Scalar equality least-squares core; dimension-aware adapters and inequality/contact remain open |
| CAD-003 | Assembly and kinematics | 3D_ASSEMBLY_AND_KINEMATICS; NORMALIZED_MECHANISM_MODEL_CONTRACT; JOINT_AND_GEOMETRY_PLACEMENT_CONTRACT; GENERAL_LOOP_CLOSURE_CONTRACT | PR #27 normalized model; PR #28 topology/explicit residual bridge; PR #29 mobility/Jacobian diagnostics; PR #30 integrated caller-driven kinematics; PR #31 explicit rigid joint/geometry placements with schema v1.0 compatibility |
| CAD-003A | Planar two-link inverse kinematics | PLANAR_TWO_LINK_INVERSE_KINEMATICS_CONTRACT | PR #12 analytic planar 2R regression evidence |
| CAD-003B | Planar four-bar loop closure | PLANAR_FOUR_BAR_LOOP_CLOSURE_CONTRACT | PR #14 and stable-ID 4R adapter/residual mapping PR #25/#26 |
| CAD-004 | Engineering simulation | 3D_ENGINEERING_SIMULATION | Benchmarks and convergence evidence |
| CAD-005 | Structural/civil design support | STRUCTURAL_AND_CIVIL_DESIGN | Code-basis and independent review evidence |
| CAD-006 | CAD-to-manufacturing preparation | CAD_TO_MANUFACTURING_PIPELINE | Export, drawing and BOM reconciliation |
| CAD-007 | Model validation | 3D_MODEL_VALIDATION | Geometry and validation suite |
| API-001 | Versioned module interface | ENGINEERING_MODULE_API_CONTRACT | Schema compatibility tests |
| DATA-001 | Traceable engineering data model | ENGINEERING_DATA_MODEL | Lineage and revision tests |
| SAFE-001 | Human-controlled high-impact release | ENGINEERING_SAFETY_AND_APPROVAL | Permission and approval tests |

## CAD-003 placement acceptance

- Geometry and joint placement records have stable parent IDs and explicit source/destination frame IDs.
- Joint frame chain is parent-link body frame → joint frame → child-link body frame.
- Geometry placement is geometry-local frame → declared GeometryReference frame.
- Placement translations are metres; conversions are explicit and external to the transform.
- Legacy schema v1.0 remains valid without placement records; v1.1 is required to carry placement records.
- Missing placements are reported as coverage gaps, not identity assumptions.
- PR #31 does not implement automatic constraint equations, Jacobians, CAD inference, dynamics or physical feasibility.

## Evidence and governance gates

- Documentation is not implementation evidence.
- PASS requires executed tests on the exact SHA.
- SKIPPED and UNKNOWN are never PASS.
- A narrow planar test suite does not certify arbitrary mechanisms or physical feasibility.
