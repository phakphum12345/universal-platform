# Engineering and 3D Requirements Traceability

**Status:** Proposed mapping baseline with narrow executable planar kinematics slices; general engineering requirements remain open.

| ID | Requirement | Primary specification | Acceptance evidence |
|---|---|---|---|
| UEIC-001 | Shared multidisciplinary engineering core | UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE | Module composition and provenance tests |
| UEIC-002 | Pluggable discipline modules | MULTIDISCIPLINARY_KNOWLEDGE_MODULES | Registry contract and compatibility tests |
| UEIC-003 | First-principles physics models | PHYSICS_AND_FIRST_PRINCIPLES | Reference cases and dimensional checks |
| UEIC-004 | Replaceable solver adapters | ENGINEERING_SOLVER_AND_MODEL_CONTRACT; NONLINEAR_CONSTRAINT_SOLVER_CONTRACT | Bounded local nonlinear equality solver; PR #16 exact-SHA CI and post-merge evidence; replaceable adapter boundary remains in progress |
| UEIC-005 | Units, uncertainty and source lineage | ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE | Unit, propagation and provenance tests |
| UEIC-006 | Cross-domain constraints | CROSS_DOMAIN_CONSTRAINT_SOLVING; NONLINEAR_CONSTRAINT_SOLVER_CONTRACT | Scalar equality least-squares core implemented; dimension-aware residual adapters, inequality/contact and conflict analysis remain open |
| CAD-001 | Parametric 3D design | 3D_DESIGN_INTELLIGENCE | Rebuild and export tests |
| CAD-002 | Generate tools and fixtures | 3D_TOOL_GENERATION_ENGINE | Requirement-to-model acceptance cases |
| CAD-003 | Assembly and kinematics | 3D_ASSEMBLY_AND_KINEMATICS | Joint, DOF and motion tests |
| CAD-003A | Planar two-link inverse kinematics | PLANAR_TWO_LINK_INVERSE_KINEMATICS_CONTRACT | Both branches, workspace boundaries, limits, residual tests and exact-SHA CI; PR #12 merged |
| CAD-003B | Planar four-bar loop closure and mobility estimate | PLANAR_FOUR_BAR_LOOP_CLOSURE_CONTRACT | Analytic left/right branches, reachability, closure residuals, tangent case and Kutzbach count (PR #14); stable-ID, dimension-checked model snapshot mapping and deterministic result serialization (PR #25 merged at `6198529d0e816898ad84e20efa153d54c6e0c61d`; exact PR-head CI: 155 tests passed; post-merge CI UNKNOWN). General multi-loop/3D adapter remains open |
| CAD-004 | Engineering simulation | 3D_ENGINEERING_SIMULATION | Benchmarks and convergence evidence |
| CAD-005 | Structural/civil design support | STRUCTURAL_AND_CIVIL_DESIGN | Code-basis and independent review evidence |
| CAD-006 | CAD-to-manufacturing preparation | CAD_TO_MANUFACTURING_PIPELINE | Export, drawing and BOM reconciliation |
| CAD-007 | Model validation | 3D_MODEL_VALIDATION | Geometry and validation suite |
| API-001 | Versioned module interface | ENGINEERING_MODULE_API_CONTRACT | Schema compatibility tests |
| DATA-001 | Traceable engineering data model | ENGINEERING_DATA_MODEL | Lineage and revision tests |
| SAFE-001 | Human-controlled high-impact release | ENGINEERING_SAFETY_AND_APPROVAL | Permission and approval tests |

## Status

The first reusable nonlinear numerical core is implemented in PR #16. PR #19 implemented forward (default)/central finite-difference and analytic Jacobian strategies plus evaluation diagnostics. PR #20 implemented rank estimation and matrix-shape diagnostics using threshold-dependent modified Gram–Schmidt with column pivoting. PR head `43dbe1cb76eff112b6c4ea4bd348cd72f596da69` passed run #131 (`workflow-sanity` PASS; `python-tests` PASS, 127 tests). Merge commit `6651b5985391679daba15abb6bdf2f78b9ff894b`; post-merge CI lookup returned no run/status entries and remains UNKNOWN. The rank estimate is not a proof of exact mathematical rank. PR #21 implemented explicit variable scaling and a scaled-Jacobian column-norm disparity indicator. PR head `8f5c1ad54e42dd40f585c7860e37a6ac37b9dc78` passed run #142 (`workflow-sanity` PASS; `python-tests` PASS, 130 tests). Merge commit `0ce6774aac48d822ef4a0d373ada36af6e3e2d3c`; post-merge CI lookup returned no run/status entries and remains UNKNOWN. The indicator is not a formal condition number. PR #23 implemented a versioned JSON-compatible solver result snapshot with explicit nulls for diagnostics not computed. PR head `207d38d9959764756c703625e13d4122b82e0151` passed run #159 (`workflow-sanity` PASS; `python-tests` PASS, 141 tests). Merge commit `870a3f634d7a7fbd47e838f85aff4dc2f1b76162`; post-merge CI lookup returned no run/status entries and remains UNKNOWN. PR #22 added a deterministic regression matrix for overdetermined consistency/inconsistency, active bounds, finite-difference step sensitivity, analytic/central agreement and original-unit residual acceptance. Its first run #146 exposed a test-fixture step-tolerance issue (138 passed, 1 failed); corrected head `265a7420edbb21da977dd357affaec61fa63f701` passed run #147 (139 tests). Merge commit `1a3f05b5f99fa330cf0fd79e64f7ff3934211265`; post-merge CI lookup returned no run/status entries and remains UNKNOWN; PR head `db18dc115a55a2ba2aa648e7665e2d111a52e572` passed run #118 (`workflow-sanity` PASS; `python-tests` PASS, 120 tests). Merge commit `9676bdb00f3ffb1c8a2b0929fd27481b47368d43`; post-merge CI lookup returned no run/status entries and remains UNKNOWN. The solver uses damped Levenberg–Marquardt least squares for scalar equality residuals, optional projected bounds and per-equation tolerances. PR head 26730dba8ea3199e9576fa071a7207ed6c59c38d passed PR run #98 and push run #97; merge commit 77dd2de9b49773fe24324cb9732b7db5e2623ecf passed post-merge push run #99. Documentation-only markers were SKIPPED, not PASS. This does not close general mechanism-level constraint solving.

CAD-003A is IMPLEMENTED as a narrow analytic planar 2R inverse-kinematics adapter and merged in PR #12. CAD-003B is IMPLEMENTED as a narrow planar 4R circle-intersection loop closure and Kutzbach/Gruebler mobility estimate, merged in PR #14 at c33ef005896b71aa2ff0721efb87245781526ca7. PR head 31e104bf476aaccb751dac2329ab6d16455650b0 passed PR run #90 and push run #89; merge commit passed post-merge push run #91. Documentation-only markers were SKIPPED, not PASS.

Neither narrow slice closes general CAD-003. All other listed requirements remain PROPOSED / NOT IMPLEMENTED / NOT VERIFIED until source and test evidence exists. Existing HWR-001..HWR-006 remain separately defined in docs/hardware/.

## Evidence and governance gates

- Documentation coverage is not implementation evidence.
- Implemented means source exists; PASS requires executed evidence tied to an exact SHA and reproducible procedure.
- SKIPPED and UNKNOWN are never PASS.
- A narrow planar four-bar test suite does not certify arbitrary mechanisms or physical feasibility.
