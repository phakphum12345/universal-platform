# Engineering and 3D Requirements Traceability

**Status:** Proposed mapping baseline with narrow executable planar kinematics slices; general engineering requirements remain open.

| ID | Requirement | Primary specification | Acceptance evidence |
|---|---|---|---|
| UEIC-001 | Shared multidisciplinary engineering core | UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE | Module composition and provenance tests |
| UEIC-002 | Pluggable discipline modules | MULTIDISCIPLINARY_KNOWLEDGE_MODULES | Registry contract and compatibility tests |
| UEIC-003 | First-principles physics models | PHYSICS_AND_FIRST_PRINCIPLES | Reference cases and dimensional checks |
| UEIC-004 | Replaceable solver adapters | ENGINEERING_SOLVER_AND_MODEL_CONTRACT | Adapter contract and failure tests |
| UEIC-005 | Units, uncertainty and source lineage | ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE | Unit, propagation and provenance tests |
| UEIC-006 | Cross-domain constraints | CROSS_DOMAIN_CONSTRAINT_SOLVING | Infeasibility and conflict tests |
| CAD-001 | Parametric 3D design | 3D_DESIGN_INTELLIGENCE | Rebuild and export tests |
| CAD-002 | Generate tools and fixtures | 3D_TOOL_GENERATION_ENGINE | Requirement-to-model acceptance cases |
| CAD-003 | Assembly and kinematics | 3D_ASSEMBLY_AND_KINEMATICS | Joint, DOF and motion tests |
| CAD-003A | Planar two-link inverse kinematics | PLANAR_TWO_LINK_INVERSE_KINEMATICS_CONTRACT | Both branches, workspace boundaries, limits, residual tests and exact-SHA CI; PR #12 merged |
| CAD-003B | Planar four-bar loop closure and mobility estimate | PLANAR_FOUR_BAR_LOOP_CLOSURE_CONTRACT | Left/right branches, circle reachability, closure residuals, tangent case and Kutzbach count; PR #14 merged |
| CAD-004 | Engineering simulation | 3D_ENGINEERING_SIMULATION | Benchmarks and convergence evidence |
| CAD-005 | Structural/civil design support | STRUCTURAL_AND_CIVIL_DESIGN | Code-basis and independent review evidence |
| CAD-006 | CAD-to-manufacturing preparation | CAD_TO_MANUFACTURING_PIPELINE | Export, drawing and BOM reconciliation |
| CAD-007 | Model validation | 3D_MODEL_VALIDATION | Geometry and validation suite |
| API-001 | Versioned module interface | ENGINEERING_MODULE_API_CONTRACT | Schema compatibility tests |
| DATA-001 | Traceable engineering data model | ENGINEERING_DATA_MODEL | Lineage and revision tests |
| SAFE-001 | Human-controlled high-impact release | ENGINEERING_SAFETY_AND_APPROVAL | Permission and approval tests |

## Status

CAD-003A is IMPLEMENTED as a narrow analytic planar 2R inverse-kinematics adapter and merged in PR #12. CAD-003B is IMPLEMENTED as a narrow planar 4R circle-intersection loop closure and Kutzbach/Gruebler mobility estimate, merged in PR #14 at c33ef005896b71aa2ff0721efb87245781526ca7. PR head 31e104bf476aaccb751dac2329ab6d16455650b0 passed PR run #90 and push run #89; merge commit passed post-merge push run #91. Documentation-only markers were SKIPPED, not PASS.

Neither narrow slice closes general CAD-003. All other listed requirements remain PROPOSED / NOT IMPLEMENTED / NOT VERIFIED until source and test evidence exists. Existing HWR-001..HWR-006 remain separately defined in docs/hardware/.

## Evidence and governance gates

- Documentation coverage is not implementation evidence.
- Implemented means source exists; PASS requires executed evidence tied to an exact SHA and reproducible procedure.
- SKIPPED and UNKNOWN are never PASS.
- A narrow planar four-bar test suite does not certify arbitrary mechanisms or physical feasibility.
