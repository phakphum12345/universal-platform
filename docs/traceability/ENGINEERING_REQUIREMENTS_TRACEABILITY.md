# Engineering and 3D Requirements Traceability

**Status:** Proposed mapping baseline with narrow executable planar kinematics slices; general engineering requirements remain open.

| ID | Requirement | Primary specification | Acceptance evidence |
|---|---|---|---|
| UEIC-001 | Shared multidisciplinary engineering core | UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE | Module composition and provenance tests |
| UEIC-002 | Pluggable discipline modules | MULTIDISCIPLINARY_KNOWLEDGE_MODULES; ENGINEERING_MODULE_API_CONTRACT | Metadata-only ModuleManifest/ModuleRegistry: stable IDs, versions, license/maturity, operation schemas, permission subset checks, duplicate rejection, deterministic dependency order and snapshot tests (PR #39; exact-SHA CI pending). Runtime loading/invocation remains NOT IMPLEMENTED |
| UEIC-003 | First-principles physics models | PHYSICS_AND_FIRST_PRINCIPLES | Reference cases and dimensional checks |
| UEIC-004 | Replaceable solver adapters | ENGINEERING_SOLVER_AND_MODEL_CONTRACT; NONLINEAR_CONSTRAINT_SOLVER_CONTRACT | Bounded local nonlinear equality solver; PR #16 exact-SHA CI and post-merge evidence; replaceable adapter boundary remains in progress |
| UEIC-005 | Units, uncertainty and source lineage | ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE | Unit, propagation and provenance tests |
| UEIC-006 | Cross-domain constraints | CROSS_DOMAIN_CONSTRAINT_SOLVING; NONLINEAR_CONSTRAINT_SOLVER_CONTRACT | Scalar equality least-squares core implemented; dimension-aware residual adapters, inequality/contact and conflict analysis remain open |
| CAD-001 | Parametric 3D design | 3D_DESIGN_INTELLIGENCE | Rebuild and export tests |
| CAD-002 | Generate tools and fixtures | 3D_TOOL_GENERATION_ENGINE | Requirement-to-model acceptance cases |
| CAD-003 | Assembly and kinematics | 3D_ASSEMBLY_AND_KINEMATICS; NORMALIZED_MECHANISM_MODEL_CONTRACT; GENERAL_LOOP_CLOSURE_CONTRACT | Normalized stable-ID topology (PR #27); multi-loop topology and explicit residual bridge (PR #28); nominal/local mobility (PR #29); caller-driven position/velocity/acceleration orchestration (PR #30); explicit joint/geometry placements (PR #31); generalized-coordinate schema (PR #32); joint residual generation (PR #33); finite-difference Jacobians (PR #34); geometry-aware closure evaluation (PR #35); fixed-pose coordinate fitting (PR #36); spatial local mobility (PR #37); reference pack (PR #38). General body-pose solving, branch discovery, spatial multibody integration and physical feasibility remain open |
| CAD-003A | Planar two-link inverse kinematics | PLANAR_TWO_LINK_INVERSE_KINEMATICS_CONTRACT | Both branches, workspace boundaries, limits, residual tests and exact-SHA CI; PR #12 merged |
| CAD-003B | Planar four-bar loop closure and mobility estimate | PLANAR_FOUR_BAR_LOOP_CLOSURE_CONTRACT | Analytic branches, reachability, closure residuals and stable-ID model adapter; general multi-loop/3D adapter remains open |
| CAD-003D | Generalized coordinates and joint parameterization | GENERALIZED_COORDINATE_AND_JOINT_PARAMETERIZATION_CONTRACT | Schema v1.2 stable IDs, units/axes/limits/scales and compatibility (PR #32) |
| CAD-003E | Automatic joint constraint generation | AUTOMATIC_JOINT_CONSTRAINT_GENERATION_CONTRACT | Six-component pose residuals for eight joint kinds (PR #33) |
| CAD-003F | Automatic constraint Jacobian | AUTOMATIC_JOINT_CONSTRAINT_JACOBIAN_CONTRACT | Finite-difference Jacobian with stable row/column IDs and units (PR #34) |
| VAL-REF-001 | Cross-discipline reference validation | ENGINEERING_REFERENCE_VALIDATION_PACK | Versioned executable reference registry; PR #38; 285 tests in exact PR-head and post-merge workflows |
