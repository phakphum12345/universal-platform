# Engineering and 3D Requirements Traceability

**Status:** Proposed mapping baseline with implemented narrow planar kinematics and mobility slices; general engineering requirements remain open.

| ID | Requirement | Primary specification | Acceptance evidence |
|---|---|---|---|
| UEIC-001 | Shared multidisciplinary engineering core | UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE | Module composition and provenance tests |
| UEIC-002 | Pluggable discipline modules | MULTIDISCIPLINARY_KNOWLEDGE_MODULES; ENGINEERING_MODULE_API_CONTRACT | Metadata-only ModuleManifest/ModuleRegistry: stable IDs, versions, license/maturity, operation schemas, permission subset checks, duplicate rejection, deterministic dependency order and snapshot tests (PR #39 final head `4c07fb980afa19a36f3696d5ceed7eb35105fcc3`; run #311 (`42167103639`): workflow-sanity PASS, python-tests PASS, 308 tests in 0.57s; documentation-only marker SKIPPED; squash merge `cd552e5fa96fa21ab21a437b0103b3a195542dbc`; post-merge run #312 (`42167199845`) on exact merge SHA: both jobs PASS, 308 tests in 0.85s. Runtime loading/invocation remains NOT IMPLEMENTED |
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


| CAD-003I | Generated spatial local mobility | AUTOMATIC_GEOMETRIC_MOBILITY_CONTRACT; AUTOMATIC_JOINT_CONSTRAINT_JACOBIAN_CONTRACT; MECHANISM_MOBILITY_CONTRACT | Finite-difference Jacobian columns combine non-ground spatial body-pose tangent variables and independent joint coordinates; ground pose excluded; local mobility is total variables minus estimated rank (PR #37; final PR head `64927a329dcaa2f53f59f2b05d3b0e59619471d3`; runs #293/#294: 265 tests PASS; squash merge `41d81818385dd82497840ce93ce5aac60e3216da`; post-merge run #295 on exact merge SHA: 265 tests PASS). PLANAR auto-mobility is implemented by PR #56 with an explicit plane-frame contract |


| VAL-REF-001 | Cross-discipline reference validation | ENGINEERING_REFERENCE_VALIDATION_PACK; tests/reference_cases/engineering_reference_cases.json | Versioned case registry with unique stable IDs, formulas, explicit tolerances and executable reference checks across quantity, mechanics, electrical, thermal, geometry, transforms, linear algebra, simulation, kinematics, materials, assembly, constraints and safety (PR #38; exact PR head `bfe0857bb1844c2f022dfcdc2890853ad8570d1f`, run #297: 285 tests PASS; squash merge `587bd503dad3f6d4f66c99fe08e39e20a65c5265`; post-merge run #298 on exact merge SHA: 285 tests PASS) |


## PR #39 — Offline module metadata registry (merged)

Adds immutable versioned module and operation declarations, deterministic registration/lookup/snapshots and dependency ordering. Invalid identifiers/versions, duplicate IDs, undeclared permissions, unsupported execution classifications, missing dependencies and cycles fail closed. The registry does not load or invoke module code. Final PR head `4c07fb980afa19a36f3696d5ceed7eb35105fcc3` passed run #311 (`42167103639`), 308 tests; merge `cd552e5fa96fa21ab21a437b0103b3a195542dbc`; post-merge run #312 (`42167199845`) passed 308 tests.


| UEIC-API-001 | Validated module request/response envelopes | ENGINEERING_MODULE_API_CONTRACT; src/universal_platform/engineering/contracts.py | Immutable request/response records; stable identifiers, MAJOR.MINOR schema version, JSON-safe finite payloads, finite non-negative resource limits, explicit operational statuses, error-code validation and deterministic serialization (PR #41 final head `f669efefd7d96c9ef6041af0d9095111638ee789`; run #319 `42168026105`: 338 tests PASS; merge `a9053b02312d1319fa13f0079465fb3fc92afafd`; post-merge run #320 `42168116830`: 338 tests PASS). This does not implement module invocation. |


| EVID-001 | Validated provenance records and conservative evidence aggregation | ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE; src/universal_platform/engineering/provenance.py | SourceRef SHA-256 validation, immutable JSON-safe EvidenceRecord metadata, timezone-aware timestamps, deterministic serialization and evidence-gate precedence FAIL > UNKNOWN > SKIPPED > PASS; empty evidence returns UNKNOWN (PR #42; exact-SHA CI pending). |


| GEO-FRAME-001 | Versioned coordinate-frame and rigid-transform exchange | COORDINATE_FRAME_AND_TRANSFORM_CONTRACT; schemas/geometry/coordinate-frame-graph.schema.json | RigidTransform/FrameGraph schema v1.0 round-trip, explicit length unit, strict field/version validation, deterministic ordering, cycle/duplicate-edge rejection and same-unit composition tests (PR #43 final head `0a1460f3910ca00f385dd52f58cd06f5f52ddee8`; run #327 `42169448334`: 366 tests PASS; merge `a3884853fa039d27f0427d2ab6198fffb8e00bc8`; post-merge run #328 `42169547658`: 366 tests PASS). Mixed-unit frame graphs are explicitly unsupported. |


| UNIT-EXCHANGE-001 | Versioned dimensional Quantity serialization | QUANTITY_SCHEMA_CONTRACT; schemas/engineering/quantity.schema.json | Quantity v1.0 round-trip preserves SI value, dimension exponents and source-unit lineage; strict schema/version, finite numeric value and immutable dimension checks (PR #44 final head `130f37216afbcc753e2311bdee114b2e5a0289f2`; run #331 `42169954337`: 377 tests PASS; merge `40edecde06b966327ea09d84d911e8959f698b71`; post-merge run #332 `42170030517`: 377 tests PASS). |


| GEO-FRAME-002 | Frame-bound spatial points and displacement vectors | FRAMED_COORDINATE_CONTRACT; schemas/geometry/framed-coordinate.schema.json | FramedPoint3/FramedVector3 v1.0 JSON round-trip; explicit frame/unit binding; point transforms apply rotation+translation; vector transforms apply rotation only; mismatched units and unknown frames fail closed (PR #45; exact-SHA CI pending). |


| HWR-SCHEM-001 | Normalized hardware schematic connectivity model | HARDWARE_SCHEMATIC_NETLIST_CONTRACT; schemas/hardware/schematic.schema.json | SchematicModel v1.0 stable component/pin/net IDs, reference designators, pin electrical types, terminal endpoint checks, one-net-per-pin, NO_CONNECT enforcement and deterministic serialization (PR #46; exact-SHA CI pending). Rendering, ERC, circuit simulation and driver binding remain NOT IMPLEMENTED. |


| HWR-DRIVER-001 | Hardware driver interface and pin binding contracts | DRIVER_INTERFACE_CONTRACT; src/universal_platform/hardware/driver.py | Versioned driver/protocol/signal metadata, stable module/operation references, explicit pin bindings, schematic endpoint checks, direction compatibility and optional registry operation validation (PR #47 final head `d10f83804bc95e9896cdbf457fb30194b8e395d3`; run #345 `42171976796`: 403 tests PASS; merge `e2a66b4425e971c58fb88b14cf6fb3479f4df935`; post-merge run #346 `42172082271`: 403 tests PASS). Driver execution and physical I/O remain NOT IMPLEMENTED. |


| CAD-PRIM-001 | CAD-neutral analytic primitive geometry | CAD_NEUTRAL_PRIMITIVE_GEOMETRY; schemas/geometry/primitive-geometry.schema.json | Versioned Box/Cylinder primitives, explicit length units, SI volume/surface area, deterministic serialization, frame-aware box/cylinder bounds and reference-value tests (PR #48 final head `fda9e42f9a57a35e302516ea1454f1277d73f5bd`; run #349 `42172938440`: 412 tests PASS; merge `8c4d5a4277a63e71c10492595bd8431ec684cbe6`; post-merge run #350 `42173099340`: 412 tests PASS). B-rep, mesh, Boolean and CAD-kernel adapters remain NOT IMPLEMENTED. |


| CAD-PROFILE-001 | Parametric 2D profile extrusion | CAD_NEUTRAL_PRIMITIVE_GEOMETRY; src/universal_platform/engineering/primitive_geometry.py | Simple polygon validation, extrusion height, analytic area/perimeter/volume/surface area, deterministic v1.0 serialization and transformed AABB tests (PR #49 head `38a800d033ebbba19e1120c8cd3a47ade4088526`, run `42178039043`: 416 tests PASS; merge `bfc3e6585106c73b29297cbda2ab9ec9d50340db`; post-merge run `42186896757`: 416 tests PASS). Curved profiles and Boolean operations remain NOT IMPLEMENTED. |


| CAD-PROFILE-002 | Through-hole loops in straight-sided profile extrusion | CAD_NEUTRAL_PRIMITIVE_GEOMETRY; schemas/geometry/primitive-geometry.schema.json | IMPLEMENTED by PR #52: optional backward-compatible `holes`, strict loop topology, net area/perimeter/SI volume/surface area including inner walls, and public package exports. Exact head `bf093db34c7a7900d3d0924bccadfb40c33a30f0`; run #384 (`42191597715`): both jobs PASS, 425 tests; merge `1d1628175dafca3f5d4d3d6b5cf01e241ec75afa`; post-merge run #385 (`42191666816`): both jobs PASS, 425 tests. |


| MECH-SPATIAL-JOINT-001 | Eight-family spatial joint reference validation | SPATIAL_JOINT_REFERENCE_VALIDATION_CONTRACT; tests/fixtures/spatial_joint_reference_cases.json; tests/test_spatial_joint_reference_suite.py | IMPLEMENTED by PR #54: all eight joint kinds have deterministic residual, finite-difference Jacobian and spatial local-mobility/rank references; ground-link reversal and nontrivial joint-frame placements are covered. Exact head `3da8c733895baab939548e0ba2e81670ca0c6359`, run #404 (`42193562931`): 452 tests PASS; merge `22bbf1714224095cfd652d6887130d26facef087`; post-merge run #405 (`42193654653`): 452 tests PASS. Explicit 2D PLANAR mobility is implemented by PR #56 with a required plane-frame contract. |


| MECH-PLANAR-MOBILITY-001 | Explicit plane-frame geometric mobility | PLANAR_PLANE_FRAME_MOBILITY_CONTRACT; docs/design-3d/AUTOMATIC_GEOMETRIC_MOBILITY_CONTRACT.md; src/universal_platform/engineering/mechanism_mobility.py; tests/test_planar_geometric_mobility.py | IMPLEMENTED by PR #56: explicit plane-to-world transform, body/joint coplanarity and axis validation, deterministic projected 3-variable-per-moving-link Jacobian, supported FIXED/REVOLUTE/PRISMATIC/PLANAR references and fail-closed cases. PR #56 merged at `8335515b31a89efc4cacb70cf9c2e3aeb4ae16d4`. Exact PR head `8b76f89687c4685c66fee5f8bc9cd045bd589abe`; run #459 (`42197011073`) passed `workflow-sanity` and `python-tests` with 462 tests. Exact post-merge run #461 (`42197156442`) on the merge SHA passed both jobs with 462 tests. |


| HWR-SCHEM-002 | Versioned schematic symbol layout and SVG rendering | HARDWARE_SCHEMATIC_RENDERING_CONTRACT; schemas/hardware/schematic-layout.schema.json; src/universal_platform/hardware/schematic_layout.py | IMPLEMENTED by PR #59: strict SchematicLayout v1.0 serialization, explicit millimetre units and rotation radians, stable symbol/component/route IDs, pin-anchor mapping, deterministic SVG, route-connectivity reporting and fail-closed reference/page checks. Implementation SHA `6785cd685b9fb879ffea69eedcc04a56a2290f11`; exact-SHA run `42201375975`: workflow-sanity PASS, python-tests PASS, 477 tests. Final PR-head runs #42203797877/#42203791191 and post-merge run #42205768788 passed both jobs. ERC is implemented separately by PR #60; circuit simulation, automatic placement/routing and EDA interchange remain NOT IMPLEMENTED. |


| HWR-ERC-001 | Conservative static electrical rule checking | ELECTRICAL_RULE_CHECKING_CONTRACT; schemas/hardware/electrical-rule-check-result.schema.json; src/universal_platform/hardware/erc.py; tests/test_hardware_erc.py | IMPLEMENTED by PR #60 at merge `e641ca19b4f28bb2e2077cf475b371125ebf237a`; exact PR-head runs #42206594529/#42206646922 and post-merge run #42206719188 passed both jobs with 485 tests. Adds deterministic offline rules over normalized SchematicModel v1.0: unconnected pins, multiple push-pull outputs, multiple POWER_OUT pins, POWER_IN without declared source, POWER_IN mixed with signal drivers, and open-drain/collector without declared POWER_OUT. Result records ruleset version, canonical input SHA-256, stable findings, severity, evidence and limitations. Exact-head CI pending. Voltage/current/thermal/timing checks, standards, passive pull-up inference, circuit simulation and physical validation remain NOT IMPLEMENTED. |


| CAD-BOOLEAN-2D-001 | Convex 2D profile Boolean topology | CAD_2D_BOOLEAN_TOPOLOGY_CONTRACT; schemas/geometry/profile-boolean-result.schema.json; src/universal_platform/engineering/profile_boolean.py; tests/test_profile_boolean.py | IMPLEMENTED by PR #61 at merge `5f1612ec40a4e6d0f89ee7b419e5add02120f5dc`; exact PR-head runs #42207436743/#42207398485 passed both checks with 496 tests; exact post-merge run #42217655332 passed both checks with 496 tests. Supports convex simple polygon UNION/INTERSECTION/DIFFERENCE and deterministic convex-cell results. Concave loops, holes, arcs, general planar arrangements, exact arithmetic and 3D B-rep operations remain NOT IMPLEMENTED. |\n\n| CAD-REGION-2D-001 | General planar region topology and numerical policy | CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT; docs/design-3d/CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT.md | DESIGN CONTRACT MERGED by PR #62 at `213b1b52ef78ae3297a88892b4cc0c6539159160`; exact PR-head runs #42217964997/#42217937596 and post-merge run #42218707816 passed both checks; 496 tests. Specifies outer/hole boundaries, frame/unit identity, topology invariants, contact semantics, numerical robustness tiers, adversarial references, result evidence and replaceable-kernel gate. It does not implement general Boolean operations or select a precision policy/kernel. |


| CAD-MESH-PRIMITIVE-001 | Deterministic triangle tessellation and structural validation for analytic box/cylinder primitives | TRIANGLE_MESH_GENERATION_CONTRACT; schemas/geometry/triangle-mesh.schema.json; src/universal_platform/engineering/mesh.py; tests/test_mesh.py | IMPLEMENTED by PR #64 at merge `f0bfd8ad9958af9bfe678e923d52726b12eee73a`; exact PR-head runs #42219983207/#42219977049 and post-merge run #42220119818 passed both checks with 506 tests (post-merge 1.93s). Supports deterministic BoxSolid/CylinderSolid tessellation, source SHA-256, local frame/unit, explicit cylinder chordal error, closed edge incidence, consistent winding, positive signed volume, strict serialization and malformed topology detection. Extruded profiles, holes, arbitrary mesh self-intersection, repair, B-rep and CAD interchange remain NOT IMPLEMENTED. |


| CAD-MESH-PROFILE-001 | Deterministic triangle tessellation of straight, hole-free extruded profiles | TRIANGLE_MESH_GENERATION_CONTRACT; schemas/geometry/triangle-mesh.schema.json; src/universal_platform/engineering/mesh.py; tests/test_mesh.py | IMPLEMENTED by PR #66 at merge `1ead537afa34d2637fdb08f91b2d2bb823d411a0`; exact PR-head runs #42221102000/#42221092727 and post-merge run #42221247498 passed both checks with 511 tests (post-merge 1.20s). Adds deterministic ear-clipped caps and outward side walls for simple concave/convex straight profiles; references cover L-profile analytic volume/surface area, CW/CCW normalization, collinear boundary vertices, watertight edge topology and strict round trips. Profile arcs and holes remain NOT IMPLEMENTED. |


| CAD-MESH-HOLES-001 | Deterministic triangle tessellation of straight extruded profiles with polygonal holes | TRIANGLE_MESH_GENERATION_CONTRACT; schemas/geometry/triangle-mesh.schema.json; src/universal_platform/engineering/mesh.py; tests/test_mesh.py | IMPLEMENTED by PR #68 at merge `6ec9ba1367c22c0a14d293e57ed2d538ebfc654b`; exact PR-head runs #42222216690/#42222207986 and post-merge run #42222360177 passed both checks with 514 tests (post-merge 1.53s). Adds deterministic visible-bridge selection and ear clipping for one or more strictly-contained polygonal holes, with void-facing inner walls. Acceptance covers one/multiple-hole analytic volume and surface area, watertight edge incidence, consistent winding and reversed-hole winding. Curved boundaries remain NOT IMPLEMENTED. |


| CAD-MESH-ARCS-001 | Deterministic tessellation of circular-arc extrusion boundaries under chordal error | TRIANGLE_MESH_GENERATION_CONTRACT; schemas/geometry/triangle-mesh.schema.json; src/universal_platform/engineering/mesh.py; tests/test_mesh.py | IMPLEMENTED by PR #70 at merge `98440851b0b75216ea89013d9d2eea07b42c4416`; exact PR-head runs #42223197118/#42223188816 and post-merge run #42223460020 passed both jobs with 515 tests (post-merge 2.01s). Uses signed arc sweeps and positive chordal tolerance; deterministic segment counts follow the radial chord-error bound for outer and hole arcs. PR #71 adds the curved-hole regression at merge `8aba562a1df6c0691c855f95ef16a9ba94089556`; exact PR run #42225768304 and post-merge run #42225830931 passed both jobs with 516 tests (post-merge 1.45s). Non-circular curves/splines and general mesh repair remain NOT IMPLEMENTED. |

| CAD-STL-001 | Deterministic binary STL interchange with explicit metadata and independent reopen validation | STL_INTERCHANGE_CONTRACT; docs/design-3d/STL_INTERCHANGE_CONTRACT.md; schemas/geometry/stl-interchange-manifest.schema.json; src/universal_platform/engineering/stl_interchange.py; tests/test_stl_interchange.py | IMPLEMENTED by PR #74 at merge `1503266c18c5ed74c5756391c033437b05ae6f13`; exact PR run #42227530004 and push run #42227459289 passed both jobs with 523 tests; exact post-merge run #42227796004 passed both jobs with 523 tests in 1.31s. PR #75 adds independent bounds/signed-volume and corrupt-record references at merge `a8a7e6b28650a90665a465e7373d8ad6582f7832`; exact PR run #42228344477 passed 524 tests in 2.09s and post-merge run #42228462537 passed 524 tests in 2.20s. Arbitrary third-party STL import, external CAD application reopen, STEP and 3MF remain NOT IMPLEMENTED. |


| CAD-MESH-TOPOLOGY-001 | Face components, vertex manifoldness and duplicate/coincident vertex diagnostics | MESH_GEOMETRIC_TOPOLOGY_ANALYSIS_CONTRACT; docs/design-3d/MESH_GEOMETRIC_TOPOLOGY_ANALYSIS_CONTRACT.md; schemas/geometry/mesh-topology-analysis.schema.json; src/universal_platform/engineering/mesh_topology.py; tests/test_mesh_topology.py | IMPLEMENTED by PR #77 at merge `20e34933087a7276d0acc08e0d17b872c3973949`; exact PR run #42230501005 and push run #42230490785 passed both jobs with 533 tests; exact post-merge run #42230654227 passed both jobs with **533 tests in 1.98s**. Provides deterministic edge-connected face components, vertex-link manifoldness, exact/near-coincident diagnostics, unused-vertex detection and strict provenance-bound snapshots. Self-intersection status remains UNKNOWN; no welding/repair is performed. |

| CAD-MESH-INTERSECTION-001 | Triangle-mesh geometric self-intersection analysis | MESH_TRIANGLE_INTERSECTION_CONTRACT; docs/design-3d/MESH_TRIANGLE_INTERSECTION_CONTRACT.md; schemas/geometry/mesh-intersection-analysis.schema.json; src/universal_platform/engineering/mesh_intersection.py; tests/test_mesh_intersection.py | IMPLEMENTED by PR #80 at merge `cb91c7c49406fd02324be6b30d5570e821b4d503`; exact PR workflow #42238370626 passed workflow-sanity and python-tests with 550 tests in 2.63s; push workflow #42238360081 passed both jobs. Adds exact-rational binary64 predicates, conservative deterministic sweep, stable intersection classifications, strict source-bound schema and resource-limit UNKNOWN. `MeshTopologyAnalysis v1.0.self_intersection_status` remains UNKNOWN for compatibility; this is a separate analysis result. Post-merge CI UNKNOWN. |


| CAD-PLANAR-REGION-001 | Validated planar region input with outer boundary and holes | CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT; docs/design-3d/CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT.md; docs/decisions/PLANAR_GEOMETRY_PRECISION_POLICY.md; schemas/geometry/planar-region.schema.json; src/universal_platform/engineering/planar_region.py; tests/test_planar_region.py | IMPLEMENTED by PR #82 at merge `114bf8dd84831d7d4080922ed7069cadda380ba3`; exact PR workflow #42240159979 and push workflow #42240149518 passed with 563 tests; exact post-merge workflow #42240292055 passed with 563 tests in 2.47s. Provides separate PlanarRegion v1.0 with exact represented-binary64 rational predicates, canonical CCW outer/CW holes, strict simple-loop and non-touching hole validation, explicit frame/unit, canonical digest, strict schema and 2,048-edge bound. Boolean operations remain PLANNED and are not claimed. |


## B-rep and 3D Boolean acceptance evidence — PR #117/#118

| ID | Requirement | Implementation and evidence | Remaining boundary |
|---|---|---|---|
| CAD-BREP-001 | Closed faceted B-rep topology and deterministic mesh bridge | PR #117 merge `2dbddba4899246c1c75a169224154b9d8ec21402`; exact-head and post-merge CI passed 742 tests. `BRepSolid` v1.0 validates triangular planar single-shell topology, oriented edge uses, closed two-face incidence, connectedness, Euler/genus and positive signed volume. | No n-gons, face inner loops, multiple shells, shell healing, arbitrary curved surfaces or proof of geometric self-intersection freedom. |
| CAD-BREP-BOOLEAN-001 | Bounded 3D Boolean operations over axis-aligned box B-reps | PR #118 merge `0b7e9b4a649a8b3dcf4512cd5172640979115ed4`; exact-head and post-merge workflow #42282428283 passed 755 tests in 2.83s. Supports UNION, INTERSECTION, first-minus-rest DIFFERENCE and odd/even SYMMETRIC_DIFFERENCE over 2–16 validated boxes, with 32,768 maximum grid cells and deterministic closed output components. | Not a general CSG/B-rep kernel. Point/edge contacts remain separate components; fully enclosed cavities, arbitrary faceted solids, rotated boxes, cylinders and curved surfaces fail closed. |



## CAD Generator interactive viewport traceability — PR #146

| ID | Requirement | Implementation and evidence | Remaining boundary |
|---|---|---|---|
| CAD-GENERATOR-VIEWPORT-001 | Bounded interactive viewing of generated mesh artifacts | IMPLEMENTED narrow slice by PR #146 at merge `1813cb931876305391eeabe748741be189d5f27b`. Exact PR-head SHA `c7c15c9a007a705ef67f650d693f1794c0f104a3`, workflow #42385362330: workflow-sanity and python-tests PASS. Exact post-merge workflow #42386519328 on merge SHA: both jobs PASS; 832 tests in 9.09s. Client-side orbit, pan, zoom and reset operate on the exact returned MESH artifact; camera state is ephemeral. | PARTIAL overall CAD viewport: preview caps at 10,000 vertices/5,000 triangles; malformed mesh data fails closed. No feature-tree editing, face/edge selection, measurement, sectioning, B-rep editing, assembly navigation or general CAD kernel. Backend validation remains authoritative. |


## CAD Generator triangle inspection traceability — PR #148

| ID | Requirement | Implementation and evidence | Remaining boundary |
|---|---|---|---|
| CAD-GENERATOR-TRIANGLE-INSPECTION-001 | Select and inspect generated mesh facets | IMPLEMENTED narrow slice by PR #148 at merge `1fb9bc97c22bf0464e154f6963583edb9385d657`. Exact PR-head workflow #42391405409 on `43461346e32e1c5146c5beeab79340d7fbc387df`: both jobs PASS, 832 tests in 8.59s. Exact post-merge workflow #42391470608 on `1fb9bc97c22bf0464e154f6963583edb9385d657`: both jobs PASS, 832 tests in 7.59s. Accessible pointer/keyboard triangle selection, highlight/clear, area and centroid use mesh unit/frame. | PARTIAL overall CAD inspection: triangle facets only, no B-rep topology, edges/vertices, sketch dimensions, sectioning, face editing or assemblies. Browser E2E interaction tests not yet present. |


## FeatureHistory tree inspection traceability — PR #150

| ID | Requirement | Implementation and evidence | Remaining boundary |
|---|---|---|---|
| CAD-FEATURE-TREE-INSPECTOR-001 | Inspect FeatureHistory dependency structure and node parameters | IMPLEMENTED narrow read-only slice by PR #150 at merge `da16967de5f387f4e98d9642134626982644d479`. Exact PR-head workflow #42392209579: both jobs PASS, 833 tests in 9.15s; Node.js syntax check PASS. Exact post-merge workflow #42392264691: both jobs PASS, 833 tests in 8.73s. | PARTIAL overall feature-tree capability: 500-node preview only; suppression is end-to-end implemented by PRs #163/#165/#166; reorder, broader parameter commit, recompute propagation and visual dependency edges remain open. |


## FeatureHistory editing traceability — PR #152

| ID | Requirement | Implementation and evidence | Remaining boundary |
|---|---|---|---|
| CAD-FEATURE-TREE-EDIT-001 | Add, replace and remove FeatureHistory DAG nodes without corrupting dependencies or mutating the source snapshot | IMPLEMENTED bounded backend slice by PR #152. Exact PR head `3c2469a43e48d5ac2fb7e546242d9a450dff1a87`; workflow #42396387520: workflow-sanity PASS, python-tests PASS, 840 passed in 9.23s. Exact merge `1a8338ae17eb783a374a36400999ead796f9a79d`; post-merge workflow #42396453320: both jobs PASS, 840 passed in 8.71s. Tests cover duplicate IDs, missing dependencies, stable-ID replacement, downstream deletion protection, explicit cascade and output invariants. | PARTIAL overall editor: no browser edit controls, HTTP mutation routes, suppression, undo/redo, feature rename migration, branch/merge model or recompute propagation UI. |


## FeatureHistory service/API editing traceability — PR #154

| ID | Requirement | Implementation and evidence | Remaining boundary |
|---|---|---|---|
| CAD-FEATURE-TREE-EDIT-002 | Persist validated FeatureHistory add/replace/remove operations through revision-safe local API | IMPLEMENTED bounded service/API slice by PR #154. Exact PR head `d243fdee6e9fc04925eaf435b4b1e4a4cfb27ae3`; workflow #42397413655: workflow-sanity PASS, python-tests PASS, 843 passed in 9.34s. Exact merge `7046de5cff4a7a575de44de189bbb4fedcbdba58`; post-merge workflow #42397474889: both jobs PASS, 843 passed in 7.14s. Tests cover add/replace/remove, immutable revision reads, stale revision conflicts and strict feature payload parsing. | PARTIAL overall editor: suppression is end-to-end implemented by PRs #163/#165/#166; undo/redo, graph branch/merge and recompute propagation UI remain open. |


## FeatureHistory suppression traceability — PR #163

| ID | Requirement | Implementation and evidence | Remaining boundary |
|---|---|---|---|
| CAD-FEATURE-TREE-SUPPRESS-001 | Suppress and restore FeatureHistory nodes without deleting source nodes or invalidating historical revisions | PASS — end-to-end suppression implemented across PR #163 (backend), PR #165 (revision-safe service/API) and PR #166 (workbench/browser). PR #166 merged at `34148fc359076567eaa4b931304f61f536a41779`; exact PR-head and post-merge CI passed 854 Python tests, 5 Chromium E2E tests and workflow-sanity. Includes v1.0/v1.1 compatibility, explicit migration, immutable suppression edits, cascade/dependency/output invariants, regeneration skip/report behavior, strict API operations, explicit cascade confirmation, dependency-aware unsuppress controls and immutable revision history. | PASS for FeatureHistory suppression. Broader editor requirements (undo/redo, graph branch/merge, reorder and recompute propagation UI) remain open and are tracked separately. |


## FeatureHistory Undo/Redo traceability — R-017

| ID | Requirement | Design evidence | Status / remaining boundary |
|---|---|---|---|
| CAD-FEATURE-TREE-UNDO-REDO-001 | Undo/Redo restores earlier FeatureHistory content without rewriting or deleting immutable revisions | [FeatureHistory Undo/Redo Contract](../design-3d/FEATURE_HISTORY_UNDO_REDO_CONTRACT.md), PRs #168–#171 | PASS — bounded end-to-end Undo/Redo implemented. PR #169 adds transactional SQLite navigation stacks and append-only restore revisions; PR #170 adds strict expected-revision service/API routes; PR #171 adds current-head-gated controls, historical read-only behavior and browser acceptance. Exact PR-head and post-merge SHA `21bee045ea4d06aa07c7130f9123afaa64372638`: workflow-sanity PASS, python-tests PASS (865 tests), Chromium E2E PASS (6 tests). | Broader editor remains PARTIAL: presentation reordering is separately implemented under PRs #173–#174; graph branch/merge, recompute propagation and generalized CAD geometry are not included. |


## FeatureHistory Presentation Reordering — CAD-FEATURE-TREE-REORDER-001

| ID | Requirement | Design evidence | Status / remaining boundary |
|---|---|---|---|
| CAD-FEATURE-TREE-REORDER-001 | Reorder FeatureHistory presentation without violating dependency order or changing execution semantics | [FeatureHistory Reordering Contract](../design-3d/FEATURE_HISTORY_REORDER_CONTRACT.md), PRs #173–#174 | PASS — PR #173 implements strict complete-permutation and dependency-order validation in the service/API; PR #174 adds current-head-gated Move Up/Move Down controls and Chromium acceptance. Reorder appends an immutable revision. Exact PR-head `14df81bffdf991133b5c3b5fcbee089ba7d409c3` and post-merge SHA `3d7504ec64433e90aedf6c11ef760cf66b801390`: workflow-sanity PASS, Python tests PASS (870 tests), Chromium E2E PASS (7 tests). | Presentation order only; dependency-derived deterministic execution order is unchanged. Graph branch/merge, recompute propagation and generalized CAD geometry remain OPEN. |


## FeatureHistory Branch and Merge — CAD-FEATURE-TREE-BRANCH-MERGE-001

| ID | Requirement | Design evidence | Status / remaining boundary |
|---|---|---|---|
| CAD-FEATURE-TREE-BRANCH-MERGE-001 | Fork immutable FeatureHistory revisions into isolated branches and safely merge compatible branch changes without rewriting history | [FeatureHistory Branch and Merge Contract](../design-3d/FEATURE_HISTORY_BRANCH_MERGE_CONTRACT.md) | PARTIAL — PR #176 implements the additive SQLite branch-origin catalog, atomic fork from a verified root revision, exact base digest provenance, branch lookup/listing and transport-neutral service method. Exact PR-head and post-merge SHA `${M}`: workflow-sanity PASS, Python tests PASS (875), Chromium E2E PASS (7). Three-way merge engine, conflict reporting, merge provenance, API/UI and browser branch/merge workflow remain OPEN. |
