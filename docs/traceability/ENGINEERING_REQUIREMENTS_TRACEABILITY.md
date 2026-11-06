# Engineering and 3D Requirements Traceability

**Status:** Proposed mapping baseline with narrow executable planar kinematics slices; general engineering requirements remain open.

| ID | Requirement | Primary specification | Acceptance evidence |
|---|---|---|---|
| UEIC-001 | Shared multidisciplinary engineering core | UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE | Module composition and provenance tests |
| UEIC-002 | Pluggable discipline modules | MULTIDISCIPLINARY_KNOWLEDGE_MODULES; ENGINEERING_MODULE_API_CONTRACT | Metadata-only ModuleManifest/ModuleRegistry: stable IDs, versions, license/maturity, operation schemas, permission subset checks, duplicate rejection, deterministic dependency order and snapshot tests (PR #39 code head `8ed4d4f9778a264cf3676d1821807ebdc3943fda`; PR run #305 (`42166708892`): workflow-sanity PASS, python-tests PASS, 304 tests in 0.90s; documentation-only marker SKIPPED. Final documentation-head CI pending. Runtime loading/invocation remains NOT IMPLEMENTED |
| UEIC-003 | First-principles physics models | PHYSICS_AND_FIRST_PRINCIPLES | Reference cases and dimensional checks |
| UEIC-004 | Replaceable solver adapters | ENGINEERING_SOLVER_AND_MODEL_CONTRACT; NONLINEAR_CONSTRAINT_SOLVER_CONTRACT | Bounded local nonlinear equality solver; PR #16 exact-SHA CI and post-merge evidence; replaceable adapter boundary remains in progress |
| UEIC-005 | Units, uncertainty and source lineage | ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE | Unit, propagation and provenance tests |
| UEIC-006 | Cross-domain constraints | CROSS_DOMAIN_CONSTRAINT_SOLVING; NONLINEAR_CONSTRAINT_SOLVER_CONTRACT | Scalar equality least-squares core implemented; dimension-aware residual adapters, inequality/contact and conflict analysis remain open |
| CAD-001 | Parametric 3D design | 3D_DESIGN_INTELLIGENCE | Rebuild and export tests |
| CAD-002 | Generate tools and fixtures | 3D_TOOL_GENERATION_ENGINE | Requirement-to-model acceptance cases |
| CAD-003 | Assembly and kinematics | 3D_ASSEMBLY_AND_KINEMATICS; NORMALIZED_MECHANISM_MODEL_CONTRACT; GENERAL_LOOP_CLOSURE_CONTRACT | Normalized stable-ID topology (PR #27); multi-loop topology and explicit residual bridge (PR #28); nominal/local mobility (PR #29); caller-driven position/velocity/acceleration orchestration (PR #30); explicit joint/geometry placements (PR #31). PR #32 adds v1.2 generalized-coordinate schema; PR #33 generates joint pose-consistency residuals; PR #34 generates finite-difference Jacobians; PR #35 evaluates geometry-aware fundamental loop closure for supplied configurations. PR #36 adds local generalized-coordinate fitting for fixed body poses; solving body poses, branch discovery and spatial/multibody integration remain follow-on work |
| CAD-003A | Planar two-link inverse kinematics | PLANAR_TWO_LINK_INVERSE_KINEMATICS_CONTRACT | Both branches, workspace boundaries, limits, residual tests and exact-SHA CI; PR #12 merged |
| CAD-003B | Planar four-bar loop closure and mobility estimate | PLANAR_FOUR_BAR_LOOP_CLOSURE_CONTRACT | Analytic left/right branches, reachability, closure residuals, tangent case and Kutzbach count (PR #14); stable-ID, dimension-checked model snapshot mapping and deterministic result serialization (PR #25 merged); complete four-link residual mapping and strict angle validation (PR #26 merged at `129a5f7867147b32d5582695b68d365db2b0c497`; exact PR-head CI: 156 tests passed; post-merge CI UNKNOWN). General multi-loop/3D adapter remains open |
| CAD-004 | Engineering simulation | 3D_ENGINEERING_SIMULATION | Benchmarks and convergence evidence |
| CAD-005 | Structural/civil design support | STRUCTURAL_AND_CIVIL_DESIGN | Code-basis and independent review evidence |
| CAD-006 | CAD-to-manufacturing preparation | CAD_TO_MANUFACTURING_PIPELINE | Export, drawing and BOM reconciliation |
| CAD-007 | Model validation | 3D_MODEL_VALIDATION | Geometry and validation suite |
| API-001 | Versioned module interface | ENGINEERING_MODULE_API_CONTRACT | Schema compatibility tests |
| DATA-001 | Traceable engineering data model | ENGINEERING_DATA_MODEL | Lineage and revision tests |
| SAFE-001 | Human-controlled high-impact release | ENGINEERING_SAFETY_AND_APPROVAL | Permission and approval tests |

| CAD-003D | Generalized coordinates and joint parameterization | GENERALIZED_COORDINATE_AND_JOINT_PARAMETERIZATION_CONTRACT; NORMALIZED_MECHANISM_MODEL_CONTRACT | Schema v1.2 stable coordinate IDs, explicit units/axes/limits/scales, deterministic joint mappings, family-specific validation and legacy v1.0/v1.1 compatibility (PR #32; merge e6a6a4c58fb43ad9a837e4f38558cb53ab6eb598; post-merge run #258: 225 tests PASS) |
| CAD-003E | Automatic joint constraint generation | AUTOMATIC_JOINT_CONSTRAINT_GENERATION_CONTRACT; JOINT_AND_GEOMETRY_PLACEMENT_CONTRACT; GENERALIZED_COORDINATE_AND_JOINT_PARAMETERIZATION_CONTRACT | Six-component pose-consistency residual generation from explicit body poses, joint placements and generalized coordinates for all eight joint kinds (PR #33; final PR head `68fb6a6d0c268b67786183211734a66db0a4b27c`; runs #270/#271: 241 tests PASS; squash merge `62c71e4ca1f60eff5b496305429e6d141a81d268`; post-merge run #272: 241 tests PASS) |
| CAD-003F | Automatic constraint Jacobian | AUTOMATIC_JOINT_CONSTRAINT_JACOBIAN_CONTRACT; AUTOMATIC_JOINT_CONSTRAINT_GENERATION_CONTRACT | Finite-difference Jacobian over generalized-coordinate and body-pose tangent variables, with stable row/column IDs, units, scales and bound-aware differences (PR #34; final PR head `405be03046009f286536b8aa66be973c40c64fad`; runs #278/#279: 248 tests PASS; squash merge `b8ff9e505005261bddfe246f29dd2a21d744a174`; post-merge run #280: 248 tests PASS) |

## Status

The first reusable nonlinear numerical core is implemented in PR #16. PR #19 implemented forward (default)/central finite-difference and analytic Jacobian strategies plus evaluation diagnostics. PR #20 implemented rank estimation and matrix-shape diagnostics using threshold-dependent modified Gram–Schmidt with column pivoting. PR head `43dbe1cb76eff112b6c4ea4bd348cd72f596da69` passed run #131 (`workflow-sanity` PASS; `python-tests` PASS, 127 tests). Merge commit `6651b5985391679daba15abb6bdf2f78b9ff894b`; post-merge CI lookup returned no run/status entries and remains UNKNOWN. The rank estimate is not a proof of exact mathematical rank. PR #21 implemented explicit variable scaling and a scaled-Jacobian column-norm disparity indicator. PR head `8f5c1ad54e42dd40f585c7860e37a6ac37b9dc78` passed run #142 (`workflow-sanity` PASS; `python-tests` PASS, 130 tests). Merge commit `0ce6774aac48d822ef4a0d373ada36af6e3e2d3c`; post-merge CI lookup returned no run/status entries and remains UNKNOWN. The indicator is not a formal condition number. PR #23 implemented a versioned JSON-compatible solver result snapshot with explicit nulls for diagnostics not computed. PR head `207d38d9959764756c703625e13d4122b82e0151` passed run #159 (`workflow-sanity` PASS; `python-tests` PASS, 141 tests). Merge commit `870a3f634d7a7fbd47e838f85aff4dc2f1b76162`; post-merge CI lookup returned no run/status entries and remains UNKNOWN. PR #22 added a deterministic regression matrix for overdetermined consistency/inconsistency, active bounds, finite-difference step sensitivity, analytic/central agreement and original-unit residual acceptance. Its first run #146 exposed a test-fixture step-tolerance issue (138 passed, 1 failed); corrected head `265a7420edbb21da977dd357affaec61fa63f701` passed run #147 (139 tests). Merge commit `1a3f05b5f99fa330cf0fd79e64f7ff3934211265`; post-merge CI lookup returned no run/status entries and remains UNKNOWN; PR head `db18dc115a55a2ba2aa648e7665e2d111a52e572` passed run #118 (`workflow-sanity` PASS; `python-tests` PASS, 120 tests). Merge commit `9676bdb00f3ffb1c8a2b0929fd27481b47368d43`; post-merge CI lookup returned no run/status entries and remains UNKNOWN. The solver uses damped Levenberg–Marquardt least squares for scalar equality residuals, optional projected bounds and per-equation tolerances. PR head 26730dba8ea3199e9576fa071a7207ed6c59c38d passed PR run #98 and push run #97; merge commit 77dd2de9b49773fe24324cb9732b7db5e2623ecf passed post-merge push run #99. Documentation-only markers were SKIPPED, not PASS. This does not close general mechanism-level constraint solving.

CAD-003A is IMPLEMENTED as a narrow analytic planar 2R inverse-kinematics adapter and merged in PR #12. CAD-003B is IMPLEMENTED as a narrow planar 4R circle-intersection loop closure and Kutzbach/Gruebler mobility estimate, merged in PR #14 at c33ef005896b71aa2ff0721efb87245781526ca7. PR head 31e104bf476aaccb751dac2329ab6d16455650b0 passed PR run #90 and push run #89; merge commit passed post-merge push run #91. Documentation-only markers were SKIPPED, not PASS.

Neither narrow slice closes general CAD-003. All other listed requirements remain PROPOSED / NOT IMPLEMENTED / NOT VERIFIED until source and test evidence exists. Existing HWR-001..HWR-006 remain separately defined in docs/hardware/.

## Evidence and governance gates

- Documentation coverage is not implementation evidence.
- Implemented means source exists; PASS requires executed evidence tied to an exact SHA and reproducible procedure.
- SKIPPED and UNKNOWN are never PASS.
- A narrow planar four-bar test suite does not certify arbitrary mechanisms or physical feasibility.


PR #28 adds deterministic fundamental-cycle topology for normalized mechanism graphs and a caller-supplied residual bridge to the existing nonlinear equality solver. Final PR head `ebd545ef4a47770b13878d5261966c50a5807939` passed run #220 (`workflow-sanity` PASS; `python-tests` PASS, 181 tests); documentation-only marker SKIPPED. It merged at `0b1370460dd37afc685d5b7f2ec64cdeb77659b8`; post-merge push run #221 passed on that exact merge SHA (`workflow-sanity` PASS; `python-tests` PASS, 181 tests). Automatic joint-equation generation, spatial geometry solving, mobility proof and singularity classification remain unimplemented.


## CAD-003C — Mobility / degrees-of-freedom diagnostics (PR #29)

- Adds separate nominal PLANAR/SPATIAL joint-count estimates with an explicit grounded-link ID and local configuration-specific mobility from a caller-supplied constraint Jacobian whose columns cover the complete free-body generalized-coordinate set.
- Reports estimated rank, redundant constraint rows, negative nominal DOF and possible singularity as separate fields. Singularity remains UNKNOWN without an explicit regular-configuration reference rank.
- Tests cover planar 4R nominal and local mobility, spatial revolute-pair nominal mobility, unsupported planar joint kinds, redundant rows, rank drop, negative nominal count, validation and versioned provenance snapshots.
- This is a diagnostic contract, not automatic geometric Jacobian generation or a general mechanism solver. Final tested PR head `4034e47557c2154c122e96cb348666d6d32dad78`; run #233 (`42152768589`) on that exact head: `workflow-sanity` PASS; `python-tests` PASS, 196 passed in 0.45s; documentation-only marker SKIPPED. Squash merge `a20e83314abb735448c6ebebf755b8b50cf7635e`; post-merge push run #234 (`42152843277`) on the exact merge SHA: `workflow-sanity` PASS; `python-tests` PASS, 196 passed in 0.32s. The implementation returns singularity UNKNOWN if a supplied regular-rank reference is inconsistent with a higher observed rank.


## CAD-003D — Integrated mechanism kinematics (PR #30)

- Connects normalized stable-ID mechanism topology and explicit loop residuals to position closure, PR #29 mobility/rank diagnostics, and velocity/acceleration constraint solves.
- Position, velocity and acceleration use a common ordered generalized-coordinate vector. Velocity and acceleration are solved from J*qdot + b_v = 0 and J*qddot + b_a = 0; derivative bias terms are explicit caller inputs with source labels.
- Regression coverage includes planar 4R and two-loop models, same-branch continuation, branch switch, schema/revision mismatch and versioned provenance.
- The pipeline does not auto-generate geometric joint constraints/Jacobians or derivative bias terms. It is a caller-driven integration contract, not a general 3D multibody dynamics engine.
- Exact-SHA CI evidence pending.


PR #30 initial exact-head run #237 (`42153434281`, head `bd3eb302a64854218fdca8d0c83b4bdf94283f6e)): workflow-sanity PASS; python-tests FAIL, 202 passed / 1 failed. The failure log shows the test fixture accessed `__dict__` on a slotted dataclass; corrected using `dataclasses.replace`.

PR #30 final tested head `4a7edd3865f9cbd02bcea753bf5c036150380e07`; run #242 (`42153688904`): workflow-sanity PASS; python-tests PASS, 203 passed in 0.42s. Initial fixture-only failure on `bd3eb302a64854218fdca8d0c83b4bdf94283f6e` (202 passed, 1 failed) was corrected with `dataclasses.replace`. Squash merge `b670f0c8f4d60f1c6006d1c836c1d2ff4cb728bb`; post-merge push run #243 (`42153753500`) on the exact merge SHA: workflow-sanity PASS; python-tests PASS, 203 passed in 0.51s.

## CAD-003E — Explicit joint and geometry placement (PR #31)

- Adds stable-ID `JointFramePlacement` and `GeometryPlacement` records to mechanism schema v1.1.
- Joint placement frame chain is parent-link body frame → joint frame → child-link body frame. Geometry placement is geometry-local frame → GeometryReference frame.
- Placement translations use metres; unit conversion is explicit and external. Transform endpoints are validated exactly using the existing rigid-transform contract.
- Schema v1.0 remains readable without placement records. Missing placements are reported explicitly and are never treated as identity transforms.
- PR #31 branch `feat/joint-geometry-placement-contract`, base `213b07e1ea362bf3fe6b460d5495bd505b2232e4`, tested PR head `1807a623c11655c2d80662cb0a75ca093a3e39f7`; push run #247 and PR run #248 passed workflow-sanity and python-tests (212 passed). Squash merge `26c8d15dcf0e97e1dca1f13cc5da702e758b96d9`; post-merge run #249 on exact merge SHA passed workflow-sanity and python-tests (212 passed in 0.50s). Documentation-only marker SKIPPED.
- Not included: automatic constraint equations, Jacobians, CAD inference, dynamics or physical feasibility.

## PR #30 exact merge evidence reconciliation

PR #30 final tested head `4a7edd3865f9cbd02bcea753bf5c036150380e07`; run #242 (`42153688904`): workflow-sanity PASS and python-tests PASS (203 passed). Squash merge `b670f0c8f4d60f1c6006d1c836c1d2ff4cb728bb); post-merge run #243 (`42153753500`) on the exact merge SHA: workflow-sanity PASS and python-tests PASS (203 passed). Earlier fixture-only failure on initial head was corrected and remains historical evidence.


## PR #31 exact merge evidence

PR #31 tested head `1807a623c11655c2d80662cb0a75ca093a3e39f7`; push run #247 (`42155058023`) and pull_request run #248 (`42155131491`) both passed workflow-sanity and python-tests (212 passed). Squash merge commit `26c8d15dcf0e97e1dca1f13cc5da702e758b96d9`; post-merge push run #249 (`42155225252`) on that exact merge SHA passed workflow-sanity and python-tests (212 passed in 0.50s). Documentation-only marker SKIPPED, not PASS.


## PR #32 — Generalized coordinates and joint parameterization

Schema v1.2 introduces stable-ID independent generalized coordinates and ordered per-joint parameterizations for all eight declared joint kinds. Validation checks dimensional units, normalized axes, limits, scales, ownership and family-specific metadata. Legacy topology/placement models remain valid without automatic coordinate migration. The schema remains separate from solver capability: automatic joint equations, Jacobians and derivative generation are not included.


PR #32 initial tested head `07ae6ba0c0acceb7891b9deb5de953ab72b94fe9` passed run #255 (`42157210760`): workflow-sanity PASS; python-tests PASS, 225 passed in 0.54s. Final PR head `c2b768b8f3a75a010614c1cd8a874b63f32f7ca0` passed run #257 (`42157342765`): workflow-sanity PASS; python-tests PASS, 225 passed in 0.57s. Squash merge `e6a6a4c58fb43ad9a837e4f38558cb53ab6eb598`; post-merge run #258 (`42157428741`) on the exact merge SHA passed workflow-sanity and python-tests, 225 passed in 0.59s. Documentation-only marker SKIPPED.


## PR #33 — Automatic joint constraint generation

PR #33 merged at `62c71e4ca1f60eff5b496305429e6d141a81d268`. Final PR head `68fb6a6d0c268b67786183211734a66db0a4b27c` passed runs #270 and #271 (241 tests each); post-merge run #272 on the exact merge SHA passed 241 tests. Implementation adds ordered stable-ID translational and rotational pose-consistency residuals for every normalized joint. Evaluation requires complete body pose and generalized-coordinate maps, exact frame compatibility and explicit joint placements. This is an offline geometric consistency layer only; automatic Jacobian generation is the next dependency step.


PR #33 validation history: run #263 on initial head `6c25ec2ffdd368605dc90ff67b29bc4abeaeea8b` found one fixture mismatch (237 passed, 1 failed); run #265 on corrected fixture head `be3b27627d0c71a2b3d232da93f7e37cd2729798` passed 238. Run #267 on expanded test head `e701a149592778ae8aab036d79baf49091a03012` found an extrinsic Euler composition-order defect (240 passed, 1 failed); corrected code head `0ac3c4be51b1f5940e5d530fcbe4e9394dcc66ff` passed push run #268 (`42158471339`) and PR run #269 (`42158477297`), both workflow-sanity and python-tests PASS, 241 passed. Final documentation-head and post-merge evidence pending.


## PR #34 — Automatic joint constraint Jacobian

PR #34 merged at `b8ff9e505005261bddfe246f29dd2a21d744a174`. Final PR head `405be03046009f286536b8aa66be973c40c64fad` passed runs #278/#279 (248 tests each); post-merge run #280 on the exact merge SHA passed 248 tests. The deterministic numerical Jacobian columns cover generalized coordinates and body-pose tangent variables; forward/central differences and bound-aware one-sided fallback are explicit. This is a finite-difference estimate, not a symbolic or exact analytic Jacobian.


PR #34 exact code/documentation head `c0a69866ceaf318b5e05ae4689ba018085e6363f` passed push run #276 (`42159087591`) and PR run #277 (`42159114452`): workflow-sanity PASS; python-tests PASS, 248 passed on both. Documentation-only marker SKIPPED. Merge and post-merge evidence pending.


| CAD-003G | Geometry-aware mechanism loop closure | GEOMETRY_AWARE_LOOP_CLOSURE_CONTRACT; GENERAL_LOOP_CLOSURE_CONTRACT; AUTOMATIC_JOINT_CONSTRAINT_GENERATION_CONTRACT | Deterministic fundamental-cycle grouping, generated six-component joint residuals, complete tree/closing-edge evidence and PASS/FAIL evaluation for supplied configurations (PR #35; exact PR head `9c5b5f43aa6af44da59f7b33cfa5db3448fd4d44`, run #283: 253 tests PASS; squash merge `223740381b81fc06a292eb90ba0653b27cbe8e7a`; post-merge run #284 on exact merge SHA: 253 tests PASS) |


| CAD-003H | Geometric loop coordinate fitting | GEOMETRIC_LOOP_COORDINATE_SOLVER_CONTRACT; GEOMETRY_AWARE_LOOP_CLOSURE_CONTRACT; NONLINEAR_CONSTRAINT_SOLVER_CONTRACT | Bounded local solve over stable generalized-coordinate IDs, all generated joint residuals, per-coordinate limits/scales and final geometric re-evaluation (PR #36; final PR head `d00bd6e5631fa4a0101f1c4d5a7c9e1f811cd2f1`; runs #288/#289: 258 tests PASS; squash merge `d7b740fc98d396c130f1c17b3c6487b30b599c2c`; post-merge run #290 on exact merge SHA: 258 tests PASS) |


| CAD-003I | Generated spatial local mobility | AUTOMATIC_GEOMETRIC_MOBILITY_CONTRACT; AUTOMATIC_JOINT_CONSTRAINT_JACOBIAN_CONTRACT; MECHANISM_MOBILITY_CONTRACT | Finite-difference Jacobian columns combine non-ground spatial body-pose tangent variables and independent joint coordinates; ground pose excluded; local mobility is total variables minus estimated rank (PR #37; final PR head `64927a329dcaa2f53f59f2b05d3b0e59619471d3`; runs #293/#294: 265 tests PASS; squash merge `41d81818385dd82497840ce93ce5aac60e3216da`; post-merge run #295 on exact merge SHA: 265 tests PASS). PLANAR auto-mobility remains deferred pending explicit plane-frame contract |


| VAL-REF-001 | Cross-discipline reference validation | ENGINEERING_REFERENCE_VALIDATION_PACK; tests/reference_cases/engineering_reference_cases.json | Versioned case registry with unique stable IDs, formulas, explicit tolerances and executable reference checks across quantity, mechanics, electrical, thermal, geometry, transforms, linear algebra, simulation, kinematics, materials, assembly, constraints and safety (PR #38; exact PR head `bfe0857bb1844c2f022dfcdc2890853ad8570d1f`, run #297: 285 tests PASS; squash merge `587bd503dad3f6d4f66c99fe08e39e20a65c5265`; post-merge run #298 on exact merge SHA: 285 tests PASS) |


## PR #39 — Offline module metadata registry (implementation candidate)

Adds immutable versioned module and operation declarations, deterministic registration/lookup/snapshots and dependency ordering. Invalid identifiers/versions, duplicate IDs, undeclared permissions, unsupported execution classifications, missing dependencies and cycles fail closed. The registry does not load or invoke module code. Exact PR-head CI evidence is pending.
