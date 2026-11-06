# Implementation Status — UEIC Foundation

**Integration branch:** `docs/phase-0-complete-requirements`  
**Integration HEAD:** `114bf8dd84831d7d4080922ed7069cadda380ba3` (PR #82 PlanarRegion v1.0 input model).
**Exact post-merge CI:** PR #82 merge SHA `114bf8dd84831d7d4080922ed7069cadda380ba3`; workflow #42240292055: workflow-sanity PASS and python-tests PASS; **563 passed in 2.47s**. Documentation-only marker step SKIPPED.  
**Branch relationship:** default branch `main` remains at `96e75010716226037893155b9fd4b13410fb0d6f`; integration is substantially ahead and has not been merged to `main`. This work has not been merged to `main`.  
**Working-tree state:** UNKNOWN — this audit uses GitHub API evidence; no local checkout/working tree is available to inspect.  
**Spatial-joint reference coverage:** PR #54 now validates all eight declared joint kinds with a versioned fixture, generated six-component residuals, finite-difference Jacobian references, spatial local-mobility/rank references, ground-link reversal and nontrivial joint-frame placements. Exact PR head `3da8c733895baab939548e0ba2e81670ca0c6359`, run #404 / `42193562931`: both jobs PASS, 452 tests in 1.35s; merge `22bbf1714224095cfd652d6887130d26facef087`; post-merge run #405 / `42193654653`: both jobs PASS, 452 tests in 1.33s. PR #56 now implements explicit 2D PLANAR plane-frame mobility; exact-head and post-merge CI both pass.  
**Scope:** Dependency-light offline engineering core, normalized stable-ID mechanism schema v1.2, explicit placements and generalized-coordinate parameterization, generated joint pose-consistency residuals and finite-difference Jacobians, geometry-aware loop-closure evaluation for supplied configurations, bounded generalized-coordinate fitting for fixed body poses, generated spatial local mobility analysis, rigid transforms/frame graph, narrow planar adapters, general loop topology, caller-driven mobility/kinematics and cross-discipline reference validation. No general spatial dynamics solver or physical control is claimed.

## Implemented in the merged baseline

- Typed SI-backed quantities and dimensional checks for a deliberately limited unit registry.
- Evidence/provenance records with FACT / ASSUMPTION / SIMULATION / UNKNOWN distinctions and PASS / FAIL / SKIPPED / UNKNOWN statuses.
- Fail-closed safety gate that rejects physical execution actions.
- Small dense linear solver with partial pivoting and residual calculation.
- Bounded Levenberg–Marquardt solver for scalar nonlinear equality residuals, with forward finite differences as the default, opt-in central differences and validated analytic Jacobian callbacks; residual scaling, per-equation tolerances, optional projected variable bounds, explicit CONVERGED / NOT_CONVERGED semantics and per-constraint PASS/FAIL.
- Jacobian result diagnostics: selected derivative strategy, scalar residual callback evaluations, Jacobian builds and analytic Jacobian callback evaluations.
- Threshold-dependent numerical Jacobian rank diagnostics using modified Gram–Schmidt with column pivoting; reports rank, maximum rank, threshold, matrix shape and FULL_RANK / RANK_DEFICIENT / INDETERMINATE. This is an estimate, not a proof.
- Optional variable scaling in normalized LM coordinates, recorded in results; residual acceptance remains in original units. A column-norm ratio flags scale disparity but is not a matrix condition number.
- Versioned JSON-compatible solver result snapshots via `NonlinearSolveResult.to_dict()`; not-computed rank/scale diagnostics are represented as null.
- Hard/soft scalar constraint evaluation with explicit UNKNOWN for missing variables.
- Analytic Box/Cylinder geometry primitives and bounds; not a CAD kernel.
- Straight-sided polygon profile extrusion with optional through-hole loops, strict topology validation, net area/perimeter, SI volume/surface area including inner walls, deterministic backward-compatible v1.0 snapshots and public package exports (PR #52 merged).
- Assembly occurrence/joint data contracts, identity/reference checks, normalized axes, finite/ordered limits and nominal joint DOF bookkeeping.
- Versioned normalized mechanism schema v1.2: stable-ID links, eight joint kinds, frame/geometry references, explicit placements and generalized-coordinate/joint parameterization records. Joint schema capability remains SCHEMA_ONLY; no general solver support is implied.
- Dependency-free rigid coordinate transforms with frame-checked composition, inversion, point/vector transforms and transformed axis-aligned bounds.
- Coordinate-frame forest with one parent per child, cycle rejection, inverse traversal and path resolution.
- Tree-only forward kinematics for FIXED, REVOLUTE and PRISMATIC joints with explicit placements, topology/frame validation and joint-limit enforcement.
- Narrow analytic planar two-link (2R) inverse kinematics for elbow-up and elbow-down branches, with workspace, joint-limit, finite-input and forward-reconstruction residual checks.
- Narrow planar four-link/four-revolute (4R) loop closure by circle intersection, left/right branches, reachability checks and closure residual validation.
- Planar Kutzbach/Gruebler mobility estimate; a nominal count, not a proof of actual mobility.
- Linear algebra simulation adapter with declared limitations and evidence.
- Versioned module request/response envelopes.
- Starter mechanics, DC electrical calculations, linear thermal expansion and traceable material property records (initial equations only).

## PR #27 — Joint/Link normalization (implementation)

- PR: https://github.com/phakphum12345/universal-platform/pull/27
- Adds `mechanism_model.py` with versioned `MechanismModel`, `LinkModel`, `JointModel`, `FrameReference`, `GeometryReference` and structural validation.
- Schema joint kinds: FIXED, REVOLUTE, PRISMATIC, CYLINDRICAL, HELICAL, SPHERICAL, PLANAR and UNIVERSAL. Stable IDs, dangling references, frame-parent cycles, axis normalization, scalar limits and selected radian/metre conventions are validated.
- Joint nominal DOF is bookkeeping only. All normalized joint records report `SCHEMA_ONLY`; the existing planar 4R adapter remains unchanged and is not generalized by this PR.
- Exact tested PR head: `320962c80551d5e68d2e392166a7bd6b46b3326c`.
- GitHub Actions run #210 (run ID `42149832552`): `workflow-sanity` PASS; `python-tests` PASS, **172 passed in 0.37s**. The documentation-only marker was SKIPPED, not PASS.
- Squash merge commit: `2d99717da12974434d71c686dc18dff48271d617`.
- Post-merge workflow/status lookup returned no runs or status entries; post-merge CI remains **UNKNOWN**, not PASS.

## PR #24 — Mechanism constraint adapter contract (design only)

- PR: https://github.com/phakphum12345/universal-platform/pull/24
- Base: `docs/phase-0-complete-requirements` at `8084ccf9375245b7e7eaa1812628703292746c67`.
- Tested PR head: `ef4330d1e7aa424df8cd58f4ff46ba572beaf975`.
- GitHub Actions run #170 (run ID `42146444943`): `workflow-sanity` PASS; `python-tests` PASS, **141 passed in 0.32s**. The documentation-only marker was SKIPPED, not PASS.
- Merge commit: `7aead53ac5af9dd3a82999c823a413db0e2f4ead`.
- Post-merge workflow/status lookup returned no runs or status entries; post-merge CI remains **UNKNOWN**, not PASS.
- Adds a proposed mechanism-to-solver contract covering immutable snapshots, deterministic IDs/order, units/frames/topology/ground validation, residual mapping, branch/gauge/redundancy handling and acceptance tests.
- **No general mechanism adapter implementation is claimed.** Existing assembly contracts, tree kinematics and planar four-bar utility remain narrow capabilities.

## PR #23 — Versioned nonlinear solver result schema

- PR: https://github.com/phakphum12345/universal-platform/pull/23
- Base: `docs/phase-0-complete-requirements` at `b561247ff933ea3d5d9fa6c32d4224341e5f2be1`.
- Tested PR head: `207d38d9959764756c703625e13d4122b82e0151`.
- GitHub Actions run #159 (run ID `42146051451`): `workflow-sanity` PASS; `python-tests` PASS. The Python job ran `python -m pytest -q`: **141 passed in 0.23s**. The documentation-only marker was SKIPPED, not PASS.
- Merge commit: `870a3f634d7a7fbd47e838f85aff4dc2f1b76162`.
- Post-merge workflow/status lookup returned no runs or status entries; post-merge CI remains **UNKNOWN**, not PASS.
- Adds `NonlinearSolveResult.to_dict()` with schema version 1.0, ordered variables/residuals, status, iteration and objective data, derivative/evaluation diagnostics, rank/scale metadata, limitations and explicit nulls for diagnostics not computed.
- This is a Python result snapshot, not a full evidence ledger, signed record or cross-language API.

## PR #22 — Nonlinear solver reliability regression matrix

- PR: https://github.com/phakphum12345/universal-platform/pull/22
- Base: `docs/phase-0-complete-requirements` at `4ed0fcd094606f21fdc704ed5e19fc1cda594e1e`.
- Initial tested head `9a4e6520553dc1ab0bfe54c780340a1c428ee0d3`: run #146 failed (138 passed, 1 failed). The failure showed the test's step tolerance was too loose for the requested original-unit residual tolerance.
- Corrected tested head: `265a7420edbb21da977dd357affaec61fa63f701`.
- GitHub Actions run #147 (run ID `42145747842`): `workflow-sanity` PASS; `python-tests` PASS. The Python job ran `python -m pytest -q`: **139 passed in 0.18s**. The documentation-only marker was SKIPPED, not PASS.
- Merge commit: `1a3f05b5f99fa330cf0fd79e64f7ff3934211265`.
- Post-merge workflow/status lookup returned no runs or status entries; post-merge CI remains **UNKNOWN**, not PASS.
- Adds a dedicated deterministic reliability suite for consistent/inconsistent overdetermined systems, active lower/upper bounds, finite-difference step sensitivity, analytic/central agreement and original-unit residual acceptance.

## PR #21 — Variable scaling and Jacobian scale-disparity indicator

- PR: https://github.com/phakphum12345/universal-platform/pull/21
- Base: `docs/phase-0-complete-requirements` at `4f4865474adb76f59a78c6cf85725b3081d48f16`.
- Tested PR head: `8f5c1ad54e42dd40f585c7860e37a6ac37b9dc78`.
- GitHub Actions run #142 (run ID `42145350391`): `workflow-sanity` PASS; `python-tests` PASS. The Python job ran `python -m pytest -q`: **130 passed in 0.21s**. The documentation-only marker was SKIPPED, not PASS.
- Merge commit: `0ce6774aac48d822ef4a0d373ada36af6e3e2d3c`.
- Post-merge workflow/status lookup returned no runs or status entries; post-merge CI remains **UNKNOWN**, not PASS.
- Adds optional positive finite variable scales, normalized LM coordinates, scale metadata, and a column-norm ratio indicator. The indicator is not a formal condition number and does not identify every near-dependent system.
- Residual acceptance and per-constraint PASS/FAIL remain evaluated in original residual units.

## PR #20 — Jacobian rank and system-shape diagnostics

- PR: https://github.com/phakphum12345/universal-platform/pull/20
- Base: `docs/phase-0-complete-requirements` at `0e2f45f6a2f151c55b0e05e882467def9659095e`.
- Tested PR head: `43dbe1cb76eff112b6c4ea4bd348cd72f596da69`.
- GitHub Actions run #131 (run ID `42144874541`): `workflow-sanity` PASS; `python-tests` PASS. The Python job ran `python -m pytest -q`: **127 passed in 0.28s**. The documentation-only marker was SKIPPED, not PASS.
- Merge commit: `6651b5985391679daba15abb6bdf2f78b9ff894b`.
- Post-merge workflow/status lookup returned no runs or status entries; post-merge CI remains **UNKNOWN**, not PASS.
- The rank estimator is threshold-dependent modified Gram–Schmidt with column pivoting over the scaled Jacobian. It reports system shape separately from estimated rank and does not prove exact mathematical rank, uniqueness, identifiability or physical feasibility.

## PR #19 — Jacobian strategies and evaluation diagnostics

- PR: https://github.com/phakphum12345/universal-platform/pull/19
- Base: `docs/phase-0-complete-requirements` at `23ca284ca95be223d4a426c344a48bc21afc1953`.
- Tested PR head: `db18dc115a55a2ba2aa648e7665e2d111a52e572`.
- GitHub Actions run #118 (run ID `42144312008`): `workflow-sanity` PASS; `python-tests` PASS. The Python job ran `python -m pytest -q`: **120 passed in 0.31s**. The documentation-only marker was SKIPPED, not PASS.
- The PR job checked out synthetic merge candidate `5e246963da9a4722c121e5224b8a179aef48dfe2` for its test run.
- Merge commit: `9676bdb00f3ffb1c8a2b0929fd27481b47368d43`; integration branch comparison reports identical at this SHA.
- Post-merge workflow/status lookup returned no runs or status entries; post-merge CI remains **UNKNOWN**, not PASS.
- Added forward (default), central and analytic Jacobian strategies, analytic shape/finiteness/error validation, residual-scale normalization, and evaluation counters.
- No rank/conditioning proof, global convergence, uniqueness or physical-feasibility guarantee is provided.

## PR #16 — Bounded nonlinear equality-constraint solver

- PR: https://github.com/phakphum12345/universal-platform/pull/16
- Base: docs/phase-0-complete-requirements at 4a5bf5b2a63c0192dbb5f2ab60b4e3f62df74a44.
- Tested PR head: 26730dba8ea3199e9576fa071a7207ed6c59c38d.
- Merge commit: 77dd2de9b49773fe24324cb9732b7db5e2623ecf.
- [PR Actions run #98](https://github.com/phakphum12345/universal-platform/actions/runs/42140506796): workflow-sanity PASS; python-tests PASS. Documentation-only marker SKIPPED, not PASS.
- [Push run #97](https://github.com/phakphum12345/universal-platform/actions/runs/42140488356) on the same tested head: workflow-sanity PASS; python-tests PASS. Documentation-only marker SKIPPED, not PASS.
- Post-merge [push run #99](https://github.com/phakphum12345/universal-platform/actions/runs/42140562726) on merge SHA 77dd2de9b49773fe24324cb9732b7db5e2623ecf: workflow-sanity PASS; python-tests PASS. Documentation-only marker SKIPPED, not PASS.
- Tests cover scalar and coupled nonlinear systems, an overdetermined consistent system, bounds, unsatisfied stationary points, zero-iteration convergence, malformed inputs and callback errors.
- Limitations: local small dense equality least squares only; no global guarantee, exact/sparse Jacobian, robust rank/conditioning analysis, inequalities/contact, complementarity, continuation, branch enumeration, gauge fixing or automatic dimensional analysis.

## PR #14 — Planar four-bar loop closure

- PR: https://github.com/phakphum12345/universal-platform/pull/14
- Base: docs/phase-0-complete-requirements at c384492b058ec9dee3599feb60bb7475de298181.
- Tested PR head: 31e104bf476aaccb751dac2329ab6d16455650b0.
- Merge commit: c33ef005896b71aa2ff0721efb87245781526ca7.
- [PR Actions run #90](https://github.com/phakphum12345/universal-platform/actions/runs/42137524286): workflow-sanity PASS; python-tests PASS. Documentation-only marker SKIPPED, not PASS.
- [Push run #89](https://github.com/phakphum12345/universal-platform/actions/runs/42137510261) on the same tested head: workflow-sanity PASS; python-tests PASS. Documentation-only marker SKIPPED, not PASS.
- Post-merge [push run #91](https://github.com/phakphum12345/universal-platform/actions/runs/42137584363) on merge SHA c33ef005896b71aa2ff0721efb87245781526ca7: workflow-sanity PASS; python-tests PASS. Documentation-only marker SKIPPED, not PASS.

## PR #12 — Planar two-link inverse kinematics

- PR #12 merged at 0379c8613c7668a56b681a91d01882c66f1c812c; tested PR head e5f8511b14cd72ecb930ffd08ccb7f916cb71056.
- [PR run #82](https://github.com/phakphum12345/universal-platform/actions/runs/42136840495) and [push run #81](https://github.com/phakphum12345/universal-platform/actions/runs/42136834146): workflow-sanity and python-tests PASS.
- [Post-merge run #83](https://github.com/phakphum12345/universal-platform/actions/runs/42136914390): workflow-sanity and python-tests PASS.
- Documentation-only markers were SKIPPED, not PASS. Initial run #80 failure (83 passed, 1 faulty limit-test expectation) is retained in PR #13 evidence reconciliation.

## PR #13 — Evidence reconciliation

- PR #13 merged at c384492b058ec9dee3599feb60bb7475de298181.
- Tested PR head 757d036e190a426cb3b9a6615b13d73dd0e6f31c.
- [PR run #86](https://github.com/phakphum12345/universal-platform/actions/runs/42137072600) and [push run #85](https://github.com/phakphum12345/universal-platform/actions/runs/42137057985): workflow-sanity and python-tests PASS.
- Post-merge [push run #87](https://github.com/phakphum12345/universal-platform/actions/runs/42137139200): workflow-sanity and python-tests PASS. Documentation-only marker SKIPPED, not PASS.

## Historical evidence

- PR #10 merged at 8db7010872d69635963a982f4f09ec3cda0913a8; [run #72](https://github.com/phakphum12345/universal-platform/actions/runs/42092868218) passed workflow-sanity and python-tests.
- PR #11 merged at 06334b68e7ce084e99df70a7651face34d3a3ec0.
- Post-merge push evidence for PR #8–#11 was not returned by the earlier status interface; those historical post-merge statuses remain UNKNOWN, not PASS.
- PR #1 post-merge [run #19](https://github.com/phakphum12345/universal-platform/actions/runs/42086568425) passed on merge SHA 647956be574ffc0055d2613be5a7a4781d660542.
- PR #4 [run #34](https://github.com/phakphum12345/universal-platform/actions/runs/42090211506), PR #6 [run #44](https://github.com/phakphum12345/universal-platform/actions/runs/42090605011), PR #8 [run #57](https://github.com/phakphum12345/universal-platform/actions/runs/42091837580), and PR #9 [run #68](https://github.com/phakphum12345/universal-platform/actions/runs/42092666100) passed on their exact PR heads.

## Explicitly not implemented or not verified

- General inverse kinematics for arbitrary chains, 3D robots or redundant mechanisms.
- General mechanism-level closed-loop solving, multi-loop coupling, inequality/contact/complementarity, robust rank/conditioning analysis, continuation, branch enumeration, automatic gauge fixing, full mobility/over-constraint analysis and singularity classification. PR #16 supplies a local equality least-squares numerical core, not a general mechanism solver.
- Dynamics, acceleration, torque, friction, backlash, compliance, collision, contact, tolerance stack-up and singularity conditioning analysis.
- General symbolic mathematics, nonlinear/multiphysics solvers, FEA, CFD, FEM meshing or convergence studies.
- B-rep/parametric CAD kernel, STEP/STL/3MF import/export, Boolean operations, sketch constraints or manufacturing drawings.
- Coordinate-frame unit conversion, uncertainty propagation, frame inference or dynamic localization.
- Universal hardware driver generation; EFI/Kext candidate code is not a generic driver compiler.
- Datasheet ingestion, schematic/PCB parsing, circuit simulation or hardware runtime.
- Production UI, API server, database, agent orchestration, plugin runtime or packaging.
- Qualified engineering certification, regulatory compliance, fabrication or physical operation.

## Scope interpretation

Passing tests validate only the code and contracts present at the exact tested SHA. They do not validate the broader proposed UEIC, CAD, CAE, hardware or manufacturing capabilities. Each later change requires fresh tests and evidence.


## PR #25 — Stable-ID planar four-bar model adapter (implementation)

- PR: https://github.com/phakphum12345/universal-platform/pull/25
- Base: `docs/phase-0-complete-requirements` at `68b4d0dc12e36b7cfdea4c24666d77b067164bc8`.
- Corrected tested PR head: `f3f4b2031ccad797fad3a803f77c43e5f14d95e8`.
- GitHub Actions run #188 (run ID `42148672902`) on exact PR head `7bf230bb73040565a1a143dd2846349d8220e4f4`: `workflow-sanity` PASS; `python-tests` PASS; `python -m pytest -q`: **155 passed in 0.26s**. The documentation-only marker was SKIPPED, not PASS.
- Earlier run #181 failed due an escaped-newline syntax error in package exports; run #183 then exposed a test fixture using unsupported `dm`. Both were corrected; only run #185 is the current exact-head passing evidence.
- Adds `PlanarFourBarModelSnapshot`, `PlanarFourBarAdapterResult` and `solve_planar_four_bar_model`. Length quantities are dimension-checked and normalized to SI metres; branch and stable model/link/joint IDs are explicit; result mapping and JSON snapshot are deterministic.
- **Scope remains one planar four-link/four-revolute loop.** This is not a general mechanism-to-solver adapter, arbitrary assembly graph solver, multi-loop/3D solver or physical feasibility certification.
- - Merge commit: `6198529d0e816898ad84e20efa153d54c6e0c61d`. Post-merge workflow/status lookup returned no runs or status entries; post-merge CI remains **UNKNOWN**, not PASS.


## PR #26 — Complete stable-ID planar four-bar residual mapping

- PR: https://github.com/phakphum12345/universal-platform/pull/26
- Base: `docs/phase-0-complete-requirements` at `5e989e0ab96ada23aec0bce85f0075fbb43d591c`.
- Tested PR head: `839691467dfe9fc2bc9b55baab1a9580ee8f9201`.
- GitHub Actions run #193 (run ID `42148977388`): `workflow-sanity` PASS; `python-tests` PASS; `python -m pytest -q`: **156 passed in 0.35s**. Documentation-only marker SKIPPED, not PASS.
- Adds explicit ground, input-crank, coupler and output-rocker length residuals mapped to stable link IDs; checks the mapped residual set against the declared SI tolerance; rejects boolean input angles.
- Merge commit: `129a5f7867147b32d5582695b68d365db2b0c497`.
- Post-merge workflow/status lookup returned no runs or status entries; post-merge CI remains **UNKNOWN**, not PASS.


## PR #28 — General mechanism loop topology and explicit closure residual bridge

- PR: https://github.com/phakphum12345/universal-platform/pull/28
- Base integration branch: `docs/phase-0-complete-requirements` at `6e57ff1ae1c33560f0bc9d1a2fec46ef4fd3404f`.
- Adds deterministic spanning-forest and fundamental-cycle analysis over normalized stable-ID links and joints. Reports connected components, tree edges, loop-closing edges and ordered cycle paths; handles disconnected components, isolated links and parallel joints.
- Adds caller-supplied scalar residual records associated with every loop-closing edge and bridges them to the existing nonlinear equality solver. Each closing edge must be covered; residual IDs, tolerance and scale flow into the existing solver.
- Status semantics: CONVERGED only when supplied residuals pass; UNDERCONSTRAINED only when the solver diagnostics explicitly show an underdetermined Jacobian with estimated rank below variable count; otherwise UNKNOWN. SINGULAR and UNREACHABLE are not inferred from local solver failure.
- Corrected tested code head: `5318f93d1964e81e3dfc11c7a11fd0061e0d47b2`; PR run #218 (run ID `42150595977`): `workflow-sanity` PASS; `python-tests` PASS, **181 passed in 0.41s**.
- Final tested PR head including evidence documentation: `ebd545ef4a47770b13878d5261966c50a5807939`; PR run #220 (run ID `42150727013`): `workflow-sanity` PASS; `python-tests` PASS, **181 passed in 0.35s**. Documentation-only markers were SKIPPED, not PASS.
- Initial push run #216 (run ID `42150470866`) failed at the first test head `a4e41c9ce33586bb15e74d5a5dc664169706ac9e` (179 passed, 2 failed). Both were test-fixture expectation defects; corrected on the exact tested head above. The earlier failure is retained as evidence, not overwritten.
- Squash merge commit: `0b1370460dd37afc685d5b7f2ec64cdeb77659b8`.
- Post-merge push run #221 (run ID `42150851188`) on exact merge SHA `0b1370460dd37afc685d5b7f2ec64cdeb77659b8`: `workflow-sanity` PASS; `python-tests` PASS, **181 passed in 0.40s**. Documentation-only marker SKIPPED, not PASS.
- Explicit limits: normalized JointModel does not contain enough complete placement/coordinate/geometry information to generate general joint equations. This PR provides topology and an explicit residual bridge, not automatic arbitrary-mechanism or spatial geometry solving.


## PR #29 — Nominal and local mechanism mobility diagnostics

- Adds explicit PLANAR and SPATIAL nominal mobility formulations over normalized stable-ID mechanism models. The caller must identify the grounded link; nominal counts use free rigid-body coordinates minus ideal lower-pair constraint counts derived from each joint's declared nominal relative DOF.
- Adds a caller-supplied constraint Jacobian contract with named constraints, the complete free-body generalized-coordinate set for the selected ground link, a configuration ID and a source/provenance label. Local mobility is estimated as coordinate count minus the numerical Jacobian rank at that configuration.
- Reports redundant Jacobian rows separately from negative nominal DOF. These are distinct diagnostics; redundant rows alone do not prove physical overconstraint.
- Singularity status remains UNKNOWN unless the caller supplies a regular-configuration reference rank. A lower rank is reported only as POSSIBLE_SINGULARITY, not a proof.
- Rank uses the existing threshold-dependent modified Gram–Schmidt estimator; results retain rank method and threshold. Caller is responsible for consistent units/scaling and geometric Jacobian derivation.
- The normalized JointModel schema still does not provide complete placements/parameterizations to generate geometric joint equations automatically. Higher pairs, automatic Jacobian construction, dynamics, contact, physical feasibility and certification remain out of scope.
- PR #29 final tested PR head `4034e47557c2154c122e96cb348666d6d32dad78`; run #233 (run ID `42152768589`) on that exact head: `workflow-sanity` PASS; `python-tests` PASS, **196 passed in 0.45s**. Documentation-only marker SKIPPED, not PASS. Earlier code head `ce2f1dd7e46279f58a6d6572efebe0c62e1c98ba` passed run #231 (196 tests in 0.23s); preceding revisions and their test counts are retained in the PR body.
- Squash merge commit: `a20e83314abb735448c6ebebf755b8b50cf7635e`. Post-merge push run #234 (run ID `42152843277`) on that exact merge SHA: `workflow-sanity` PASS; `python-tests` PASS, **196 passed in 0.32s**. Documentation-only marker SKIPPED, not PASS.


## PR #30 — Integrated mechanism kinematics pipeline

- Adds one versioned orchestration result that runs normalized-model loop topology/position closure, PR #29 local mobility diagnostics, then velocity and acceleration equality solves.
- Position uses the existing explicit loop-closing residual callback contract. Mobility uses a caller-supplied configuration-specific constraint Jacobian whose stable constraint/coordinate ordering is checked against the position input.
- Velocity solves J*qdot + b_v = 0; acceleration solves J*qddot + b_a = 0. The time-derivative bias vectors and their provenance labels are caller-supplied; the pipeline does not synthesize derivatives from missing joint placements.
- Derivative outputs report UNIQUE / NON_UNIQUE / NOT_ESTABLISHED from the Jacobian rank and solve status; rank-deficient results are not presented as unique.
- Configuration IDs, branch IDs, prior configuration, continuation status, model revision, Jacobian source and bias sources are preserved in the versioned result snapshot. Same-branch continuation seeds from the prior solved coordinates; branch changes use the new caller-supplied seed and are explicit.
- Regression fixtures cover one planar 4R loop, two independent loops, branch continuity/switch, invalid cross-revision continuation and deterministic result/provenance serialization.
- Explicit limits: no automatic geometric joint equation/Jacobian generation, branch discovery, symbolic differentiation, dynamics, forces, collision/contact, physical feasibility or certification.
- PR #30 validation evidence pending exact final head CI.


- PR #30 initial push run #237 (run ID `42153434281`) on head `bd3eb302a64854218fdca8d0c83b4bdf94283f6e`: `workflow-sanity` PASS; `python-tests` FAIL (202 passed, 1 failed). The log identifies a test-fixture defect: the test accessed `MechanismKinematicsInput.__dict__`, but the dataclass uses slots. Production code was not implicated by this failure; the fixture is corrected with `dataclasses.replace` in the next head.

- PR #30 final tested PR head `4a7edd3865f9cbd02bcea753bf5c036150380e07`; run #242 (run ID `42153688904`) on that exact head: `workflow-sanity` PASS; `python-tests` PASS, **203 passed in 0.42s**. Initial run #237 on `bd3eb302a64854218fdca8d0c83b4bdf94283f6e` failed only in a slotted-dataclass test fixture (202 passed, 1 failed); corrected with `dataclasses.replace`.
- Squash merge commit: `b670f0c8f4d60f1c6006d1c836c1d2ff4cb728bb`. Post-merge push run #243 (run ID `42153753500`) on that exact merge SHA: `workflow-sanity` PASS; `python-tests` PASS, **203 passed in 0.51s**. Documentation-only marker SKIPPED, not PASS.

## PR #29 — Nominal and local mechanism mobility diagnostics

- Adds separate PLANAR/SPATIAL nominal mobility estimates and configuration-specific local mobility from caller-supplied constraint Jacobians.
- Separates redundant rows, negative nominal DOF and possible singularity; singularity remains UNKNOWN without a regular-rank reference.
- Final PR head `4034e47557c2154c122e96cb348666d6d32dad78`; run #233 (`42152768589`): workflow-sanity PASS; python-tests PASS, 196 passed.
- Merge `a20e83314abb735448c6ebebf755b8b50cf7635e`; post-merge run #234 (`42152843277`) on exact merge SHA: workflow-sanity PASS; python-tests PASS, 196 passed.

## PR #30 — Integrated mechanism kinematics pipeline

- Connects normalized topology, explicit loop residuals, mobility diagnostics, velocity and acceleration equality solves.
- Position residuals, constraint Jacobian and derivative bias vectors remain caller-supplied; the pipeline does not generate them from geometry.
- Final tested PR head `4a7edd3865f9cbd02bcea753bf5c036150380e07`; run #242 (`42153688904`): workflow-sanity PASS; python-tests PASS, 203 passed.
- Merge `b670f0c8f4d60f1c6006d1c836c1d2ff4cb728bb`; post-merge run #243 (`42153753500`) on exact merge SHA: workflow-sanity PASS; python-tests PASS, 203 passed.

## PR #31 — Joint and geometry placement contracts

- Adds schema v1.1 `JointFramePlacement` and `GeometryPlacement` records, reusing the existing `RigidTransform` convention.
- Joint placement maps parent link body frame → joint frame → child link body frame. Geometry placement maps a geometry-local frame into the declared geometry reference frame.
- Placement translations are metres; no implicit unit conversion or placement inference occurs.
- Legacy schema v1.0 topology-only models remain valid; placement records require schema v1.1.
- Missing placement IDs are reported as coverage gaps rather than assumed identity.
- Regression tests cover valid placement chains, missing coverage, legacy compatibility, schema rejection, duplicate/dangling IDs, frame endpoint/ownership mismatch, units and deterministic snapshots.
- Branch `feat/joint-geometry-placement-contract`; base SHA `213b07e1ea362bf3fe6b460d5495bd505b2232e4`; tested PR head `1807a623c11655c2d80662cb0a75ca093a3e39f7`. Push run #247 (`42155058023`) and PR run #248 (`42155131491`) on that exact head: workflow-sanity PASS; python-tests PASS, 212 passed (0.40s / 0.43s). Squash merge `26c8d15dcf0e97e1dca1f13cc5da702e758b96d9`; post-merge run #249 (`42155225252`) on exact merge SHA: workflow-sanity PASS; python-tests PASS, 212 passed in 0.50s. Documentation-only marker SKIPPED, not PASS.
- Explicit non-goals: CAD inference, automatic joint residual equations, automatic Jacobians, time-derivative bias generation, general spatial solving, dynamics or physical validation.


## PR #32 — Generalized coordinates and joint parameterization

- Adds schema v1.2 GeneralizedCoordinate and JointCoordinateParameterization records with stable IDs, ordered mappings, explicit rotational/rad units and translational/m units, joint-frame axes, finite coordinate limits and positive numerical scales.
- Validates coordinate ownership, duplicate/dangling/orphan references, family-specific coordinate count and kind, axis alignment, universal-axis non-parallelism, planar basis handedness, helical pitch and explicit spherical Euler convention.
- Existing schema v1.0/v1.1 topology and placement records remain readable. New coordinate records require v1.2; legacy scalar fields are not silently migrated.
- Missing parameterization coverage is reported for non-fixed joints. No automatic solver-variable generation, geometric residual/Jacobian generation or physical feasibility is claimed.
- PR branch: feat/generalized-coordinate-joint-parameterization; base SHA: 844c5187a7b6a61d4f38ac66ed8826fc18bef3d5.
- Initial exact PR head `07ae6ba0c0acceb7891b9deb5de953ab72b94fe9` passed pull_request run #255 (ID `42157210760`): `workflow-sanity` PASS; `python-tests` PASS; **225 passed in 0.54s**. The documentation-only marker was SKIPPED. The PR head is mergeable, with no review submissions or unresolved review threads at this inspection. Final documentation-head validation and post-merge evidence remain pending.


## PR #33 — Automatic joint constraint generation (merged)

- Adds deterministic six-component pose-consistency residual definitions for each normalized joint: translation x/y/z in metres and rotation-log x/y/z in radians.
- Uses explicit parent/joint/child placements, caller-supplied body-to-world rigid poses and exact generalized-coordinate values. Generates expected joint motion for FIXED, REVOLUTE, PRISMATIC, CYLINDRICAL, HELICAL, SPHERICAL, PLANAR and UNIVERSAL families.
- Fails closed for missing joint placements, missing non-fixed parameterizations, incomplete pose/coordinate coverage, invalid units/frames and invalid tolerances.
- Does not create solver variables, Jacobians, branch selection, dynamics, contact/collision or physical feasibility. Six pose residual components are kinematic consistency checks; they are not six independent mobility constraints in every formulation.
- PR branch: feat/automatic-joint-constraint-generation; base SHA: b658fa385851ccc3eeb1e598e1b587fea8e6266e.
- Initial PR head `6c25ec2ffdd368605dc90ff67b29bc4abeaeea8b`: run #263 (`42158183347`) exposed a fixture mismatch (237 passed, 1 failed); the PRISMATIC fixture declared a Z joint axis while its coordinate used X. Production validation correctly rejected it. Fixture corrected in `be3b27627d0c71a2b3d232da93f7e37cd2729798`; run #265 (`42158275371`) passed 238 tests.
- Expanded test head `e701a149592778ae8aab036d79baf49091a03012`: run #267 (`42158394515`) exposed an extrinsic Euler composition-order defect (240 passed, 1 failed). Corrected implementation in `0ac3c4be51b1f5940e5d530fcbe4e9394dcc66ff` and added explicit regression coverage.
- Corrected code head `0ac3c4be51b1f5940e5d530fcbe4e9394dcc66ff`: push run #268 (`42158471339`) and PR run #269 (`42158477297`) both passed workflow-sanity and python-tests; 241 passed (0.60s / 0.35s). Documentation-only marker SKIPPED. Final documentation-head and post-merge evidence pending.


## PR #34 — Automatic joint constraint Jacobian (merged)

- Adds deterministic finite-difference Jacobian construction for generated joint residuals with columns for stable-ID generalized coordinates and body-pose tangent variables.
- Translation pose variables use world-frame metres; rotation variables use world-frame left perturbations at fixed body origins in radians. Matrix entries retain the row-residual-unit / column-variable-unit convention.
- Supports forward and central finite differences, coordinate characteristic scales, bound-aware one-sided fallback and BOUND_LOCKED columns for coordinates fixed at both bounds.
- Does not claim symbolic/exact derivatives, solver convergence, rank proof or physical validation. Jacobian rank remains a separate numerical diagnostic.
- PR branch: feat/automatic-joint-constraint-jacobian; base SHA: 74a5fed138d9dc2bdf543da9263397c095de7514.
- Exact PR head `c0a69866ceaf318b5e05ae4689ba018085e6363f`: push run #276 (`42159087591`) and PR run #277 (`42159114452`) both passed workflow-sanity and python-tests; **248 passed** (0.51s / 0.35s). Documentation-only marker SKIPPED. Mergeability/review/thread inspection and post-merge evidence pending.


## PR #35 — Geometry-aware loop-closure evaluation (merged)

- Connects deterministic fundamental-cycle topology with automatic six-component joint pose-consistency residuals.
- Evaluates and retains every joint residual, then groups the six residuals associated with each loop-closing joint; spanning-tree failures remain visible and prevent an overall PASS.
- Requires explicit placements, complete generalized-coordinate parameterization, body-to-world poses, finite in-limit coordinate values and SI tolerances.
- Reports PASS/FAIL only for the supplied configuration. It does not search for a configuration or claim global reachability, physical feasibility or certification.
- Base integration SHA: `d8523bffa58a0c7a5ed8a34433c939d70c225d42`.
- Exact PR head `9c5b5f43aa6af44da59f7b33cfa5db3448fd4d44`: run #283 (ID `42161855276`) passed `workflow-sanity` and `python-tests`; **253 passed in 0.35s**. Documentation-only marker SKIPPED.
- Squash merge commit: `223740381b81fc06a292eb90ba0653b27cbe8e7a`.
- Post-merge run #284 (ID `42161983634`) on the exact merge SHA passed `workflow-sanity` and `python-tests`; **253 passed in 0.65s**.


## PR #36 — Geometric loop coordinate solver (merged)

- Adds bounded local nonlinear fitting of generalized-coordinate values against generated six-component joint residuals while body poses remain fixed caller inputs.
- Includes every joint residual, including spanning-tree joints; normalizes residual rows by their declared tolerances and forwards coordinate bounds and characteristic scales.
- Returns CONVERGED only when the solver and final geometric evaluation both pass; local failure remains NOT_CONVERGED and is not interpreted as UNREACHABLE.
- Does not solve body poses, discover branches, prove global reachability or physical feasibility. Exact PR-head and post-merge evidence pending.


## PR #37 — Generated spatial Jacobian mobility (merged)

- Builds on PR #33 generated joint pose-consistency residuals and PR #34 finite-difference Jacobians.
- Selects six body-pose tangent variables per non-ground link plus every independent generalized joint coordinate; ground pose variables are excluded.
- Computes local mobility as combined variable count minus estimated Jacobian rank and retains the nominal joint-count estimate separately.
- The generated adapter supports SPATIAL and an explicit PLANAR formulation. PLANAR requires a plane-to-world frame, validates coplanarity/axes and projects to three pose variables per non-ground link; PR #56 exact-head and post-merge CI pass.
- Singularity status remains UNKNOWN unless a regular-configuration reference rank is supplied; rank is numerical and tolerance-dependent.
- Base integration SHA: `775ee8bbd9169b9d2def3c1abdc6d01e52487013`.
- Exact PR head `64927a329dcaa2f53f59f2b05d3b0e59619471d3`: push run #293 (`42163424217`) and PR run #294 (`42163431321`) passed `workflow-sanity` and `python-tests`; **265 passed** on both (0.56s / 0.41s). Documentation-only marker SKIPPED.
- Squash merge commit: `41d81818385dd82497840ce93ce5aac60e3216da`.
- Post-merge run #295 (`42163519632`) on the exact merge SHA passed both checks; **265 passed in 0.78s**.


## PR #38 — Cross-discipline engineering reference validation (merged)

- Adds a versioned JSON registry of independently derived reference cases with stable IDs, operation names, explicit inputs, expected outputs, tolerances and reference equations.
- Exercises dimensional conversion, mechanics, DC electrical, thermal expansion, analytic geometry, rigid transforms, linear algebra, static algebraic simulation, planar inverse kinematics, four-bar closure, material records, assembly metadata, constraints and the physical-execution safety gate.
- The pack validates implemented analytical contracts only; illustrative material values are not certified allowables, and the static solver is not FEA.


- Exact PR head: `bfe0857bb1844c2f022dfcdc2890853ad8570d1f`.
- PR run #297 (ID `42164123611`): workflow-sanity PASS; python-tests PASS; 285 passed in 0.81s.
- Squash merge: `587bd503dad3f6d4f66c99fe08e39e20a65c5265`.
- Post-merge run #298 (ID `42164204886`) on exact merge SHA: workflow-sanity PASS; python-tests PASS; 285 passed in 0.81s.
- Documentation/evidence commit: `b9aba3d82396494c005accf948fa9e992473044d`; run #299 (ID `42164335487`): workflow-sanity PASS; python-tests PASS; 285 passed in 0.82s.


## PR #39 — Offline module metadata registry (merged)

- Base integration branch: `docs/phase-0-complete-requirements`, exact base SHA `22c71b610b3af4e2707389f0b62e039135ef76a0`.
- Final PR head: `4c07fb980afa19a36f3696d5ceed7eb35105fcc3`.
- PR run #311 (ID `42167103639`): `workflow-sanity` PASS; `python-tests` PASS; **308 passed in 0.57s**. Documentation-only marker SKIPPED.
- Squash merge commit: `cd552e5fa96fa21ab21a437b0103b3a195542dbc`.
- Post-merge run #312 (ID `42167199845`) on the exact merge SHA: `workflow-sanity` PASS; `python-tests` PASS; **308 passed in 0.85s**.
- Scope: immutable module manifests/operations, metadata-only registry, deterministic snapshots and dependency ordering.
- Boundary: no dynamic loading/invocation, sandboxing, permission enforcement, physical control, firmware writes or external writes.
- Metadata-only scope; runtime loading/invocation, sandboxing and permission enforcement remain NOT IMPLEMENTED.


## PR #40 — Module registry evidence reconciliation (merged documentation)

- Base integration SHA: `cd552e5fa96fa21ab21a437b0103b3a195542dbc`.
- Exact PR head: `4216c89464d7941d4f4bb893f98d9bac750363bf`.
- PR run #315 (ID `42167437979`): workflow-sanity PASS; python-tests PASS; **308 passed in 0.82s**.
- Squash merge: `818a1150fe2536c53371a878b5f1cbf5524bed7d`.
- Post-merge run #316 (ID `42167521401`) on exact merge SHA: workflow-sanity PASS; python-tests PASS; **308 passed in 0.72s**.
- Documentation reconciliation only; no runtime capability was added.


## PR #41 — Validated module request/response envelopes (merged)

- Base integration SHA: `818a1150fe2536c53371a878b5f1cbf5524bed7d`.
- Adds immutable, JSON-compatible ModuleRequest/ModuleResponse envelopes with identifier/schema validation, finite resource limits, explicit operational statuses, and deterministic snapshots.
- Final PR head: `f669efefd7d96c9ef6041af0d9095111638ee789`; PR run #319 (`42168026105`): both jobs PASS; 338 passed in 0.94s.
- Squash merge: `a9053b02312d1319fa13f0079465fb3fc92afafd`; post-merge run #320 (`42168116830`): both jobs PASS; 338 passed in 0.81s.
- Boundary: data contracts only; no module execution, permission enforcement or runtime plugin loading.


## PR #41 — Validated module request/response envelopes (merged)

- Base integration SHA: `818a1150fe2536c53371a878b5f1cbf5524bed7d`.
- Final PR head `f669efefd7d96c9ef6041af0d9095111638ee789`; run #319 (`42168026105`): workflow-sanity PASS; python-tests PASS; **338 passed in 0.94s**.
- Squash merge `a9053b02312d1319fa13f0079465fb3fc92afafd`; post-merge run #320 (`42168116830`) on exact merge SHA: both jobs PASS; **338 passed in 0.81s**.
- Runtime invocation, permission enforcement, sandboxing, typed unit/frame maps and cancellation remain NOT IMPLEMENTED.


## PR #43 — Versioned coordinate-frame exchange (merged)

- Base integration SHA: `5781f3bd017b5e12f55e463934f7e34a933c6dc3`.
- Adds versioned deterministic serialization for RigidTransform and FrameGraph, explicit length units, strict schema validation and round-trip tests.
- FrameGraph requires one length unit for all transforms; mixed-unit frame graphs remain unsupported and require explicit conversion before composition.
- Final PR head: `0a1460f3910ca00f385dd52f58cd06f5f52ddee8`; PR run #327 (`42169448334`): both jobs PASS; 366 passed in 0.56s.
- Squash merge: `a3884853fa039d27f0427d2ab6198fffb8e00bc8`; post-merge run #328 (`42169547658`): both jobs PASS; 366 passed in 0.92s.


## PR #43 — Versioned coordinate-frame exchange (merged)

- Base integration SHA: `5781f3bd017b5e12f55e463934f7e34a933c6dc3`.
- Final PR head `0a1460f3910ca00f385dd52f58cd06f5f52ddee8`; run #327 (`42169448334`): workflow-sanity PASS; python-tests PASS; **366 passed in 0.56s**.
- Squash merge `a3884853fa039d27f0427d2ab6198fffb8e00bc8`; post-merge run #328 (`42169547658`) on exact merge SHA: both jobs PASS; **366 passed in 0.92s**.
- Scope: RigidTransform/FrameGraph v1.0 JSON snapshots, explicit length units and deterministic serialization.
- Limitation: one common length unit per graph; no implicit mixed-unit conversion.


## PR #44 — Versioned Quantity exchange (merged)

- Base integration SHA: `a3884853fa039d27f0427d2ab6198fffb8e00bc8`.
- Adds Quantity v1.0 JSON snapshots with SI value, five-exponent dimension and source-unit lineage; strict schema and round-trip tests.
- Final PR head: `130f37216afbcc753e2311bdee114b2e5a0289f2`; PR run #331 (`42169954337`): both jobs PASS; 377 passed in 0.71s.
- Squash merge: `40edecde06b966327ea09d84d911e8959f698b71`; post-merge run #332 (`42170030517`): both jobs PASS; 377 passed in 0.85s.


## PR #44 — Versioned Quantity exchange (merged)

- Base integration SHA: `a3884853fa039d27f0427d2ab6198fffb8e00bc8`.
- Final PR head `130f37216afbcc753e2311bdee114b2e5a0289f2`; run #331 (`42169954337`): workflow-sanity PASS; python-tests PASS; **377 passed in 0.71s**.
- Squash merge `40edecde06b966327ea09d84d911e8959f698b71`; post-merge run #332 (`42170030517`) on exact merge SHA: both jobs PASS; **377 passed in 0.85s**.
- Scope: Quantity v1.0 serialization with SI value, dimensional signature and source-unit lineage.


## PR #45 — Frame-bound spatial values (merged)

- Base integration SHA: `40edecde06b966327ea09d84d911e8959f698b71`.
- Adds immutable FramedPoint3 and FramedVector3 records, v1.0 schemas and FrameGraph transformation helpers.
- Point transforms apply rotation and translation; vector transforms apply rotation only.
- Final PR head: `73d009e0f0e8c82f205a0c686da9190ec377a6e5`; PR run #335 (`42170469268`): both jobs PASS; 387 passed in 0.71s.
- Squash merge: `59b47c6730a0ab9f5d9512733e400483ecdb3eec`; post-merge run #336 (`42170545630`): both jobs PASS; 387 passed in 0.72s.


## PR #45 — Frame-bound spatial values (merged)

- Base integration SHA: `40edecde06b966327ea09d84d911e8959f698b71`.
- Final PR head `73d009e0f0e8c82f205a0c686da9190ec377a6e5`; run #335 (`42170469268`): workflow-sanity PASS; python-tests PASS; **387 passed in 0.71s**.
- Squash merge `59b47c6730a0ab9f5d9512733e400483ecdb3eec`; post-merge run #336 (`42170545630`) on exact merge SHA: both jobs PASS; **387 passed in 0.72s**.
- Scope: frame-bound spatial points and displacement vectors with explicit frame and length-unit semantics.


## PR #46 — Hardware schematic connectivity model (merged)

- Base integration SHA: `59b47c6730a0ab9f5d9512733e400483ecdb3eec`.
- Adds a normalized, offline SchematicModel for components, pins, electrical pin types, nets and terminal references; strict schema and topology validation.
- Does not render schematics, perform electrical rule checking, simulate circuits or map components to drivers.
- Final PR head: `2975a54d5d12e1bead98457e8ad89cd8620ae39e`; PR run #341 (`42171427481`): both jobs PASS; 395 passed in 0.51s.
- Squash merge: `9b9308eb3dac378866b2ff08e9d901e6bd6ab5fb`; post-merge run #342 (`42171498370`): both jobs PASS; 395 passed in 0.53s.


## PR #46 — Hardware schematic connectivity model (merged)

- Base integration SHA: `59b47c6730a0ab9f5d9512733e400483ecdb3eec`.
- Final PR head `2975a54d5d12e1bead98457e8ad89cd8620ae39e`; run #341 (`42171427481`): workflow-sanity PASS; python-tests PASS; **395 passed in 0.51s**.
- Squash merge `9b9308eb3dac378866b2ff08e9d901e6bd6ab5fb`; post-merge run #342 (`42171498370`) on exact merge SHA: both jobs PASS; **395 passed in 0.53s**.
- Scope: normalized component/pin/net connectivity metadata; no EDA rendering, ERC or circuit simulation.


## PR #47 — Hardware driver interface bindings (merged)

- Base integration SHA: `9b9308eb3dac378866b2ff08e9d901e6bd6ab5fb`.
- Adds driver/protocol/signal declarations and explicit schematic-pin bindings with endpoint and direction compatibility checks.
- Optional metadata validation against ModuleRegistry; no driver loading, bus configuration, firmware writes or hardware actuation.
- Final PR head: `d10f83804bc95e9896cdbf457fb30194b8e395d3`; PR run #345 (`42171976796`): both jobs PASS; 403 passed in 1.01s.
- Squash merge: `e2a66b4425e971c58fb88b14cf6fb3479f4df935`; post-merge run #346 (`42172082271`): both jobs PASS; 403 passed.


## PR #47 — Hardware driver interface bindings (merged)

- Base integration SHA: `9b9308eb3dac378866b2ff08e9d901e6bd6ab5fb`.
- Final PR head `d10f83804bc95e9896cdbf457fb30194b8e395d3`; run #345 (`42171976796`): workflow-sanity PASS; python-tests PASS; **403 passed in 1.01s**.
- Squash merge `e2a66b4425e971c58fb88b14cf6fb3479f4df935`; post-merge run #346 (`42172082271`) on exact merge SHA: both jobs PASS; **403 passed**.
- Scope: driver interface/protocol/signal declarations and metadata-only schematic pin bindings.


## PR #48 — CAD-neutral analytic primitive geometry (merged)

- Base integration SHA: `e2a66b4425e971c58fb88b14cf6fb3479f4df935`.
- Adds versioned Box/Cylinder primitive solids, SI volume/surface-area calculations, frame-aware AABBs and deterministic model serialization.
- Does not implement B-rep, mesh export, Boolean operations, feature history, CAD kernel integration or manufacturability validation.
- Final PR head: `fda9e42f9a57a35e302516ea1454f1277d73f5bd`; PR run #349 (`42172938440`): both jobs PASS; 412 passed in 1.07s.
- Squash merge: `8c4d5a4277a63e71c10492595bd8431ec684cbe6`; post-merge run #350 (`42173099340`): both jobs PASS; 412 passed in 0.62s.


## PR #48 — CAD-neutral analytic primitive geometry (merged)

- Base integration SHA: `e2a66b4425e971c58fb88b14cf6fb3479f4df935`.
- Final PR head `fda9e42f9a57a35e302516ea1454f1277d73f5bd`; run #349 (`42172938440`): workflow-sanity PASS; python-tests PASS; **412 passed in 1.07s**.
- Squash merge `8c4d5a4277a63e71c10492595bd8431ec684cbe6`; post-merge run #350 (`42173099340`) on exact merge SHA: both jobs PASS; **412 passed in 0.62s**.
- Scope: Box/Cylinder analytic primitives, SI properties and frame-aware bounds.


## PR #49 — Profile extrusion primitive (merged)

- Base integration SHA: `8c4d5a4277a63e71c10492595bd8431ec684cbe6`.
- Final PR head: `38a800d033ebbba19e1120c8cd3a47ade4088526`; run #356 (`42178039043`): workflow-sanity PASS; python-tests PASS; **416 passed in 1.06s**.
- Squash merge: `bfc3e6585106c73b29297cbda2ab9ec9d50340db`; post-merge run #381 (`42186896757`): both jobs PASS; **416 passed in 0.84s**.
- Scope: simple polygon profile extrusion with analytic properties and transformed bounds; no curved sketches, Boolean features, B-rep or mesh output.


## PR #52 — Through-hole profile integration and public exports (merged)

- Base integration SHA: `bfc3e6585106c73b29297cbda2ab9ec9d50340db`.
- Final PR head: `bf093db34c7a7900d3d0924bccadfb40c33a30f0`; PR run #384 (`42191597715`): workflow-sanity PASS; python-tests PASS; **425 passed in 0.78s**.
- Squash merge: `1d1628175dafca3f5d4d3d6b5cf01e241ec75afa`; post-merge run #385 (`42191666816`) on the exact merge SHA: both jobs PASS; **425 passed in 0.87s**.
- Adds optional through-hole loops, strict inner-loop topology, net area/perimeter, SI volume/surface area including inner walls, backward-compatible optional serialization and JSON Schema support.
- Fixes missing package-level imports for `Vec2` and `ExtrudedProfileSolid`; regression tests now import both from `universal_platform.engineering`.
- Reviews: 0; unresolved threads: 0; mergeability clean before merge.
- Limitations: straight-sided analytic extrusion only; no curved sketches, Boolean kernel, B-rep, mesh or physical/manufacturing validation.


## PR #54 — Spatial joint reference validation (merged)

- Base integration SHA: `1db066915c4993e544b386c0311e332874ef4aed`.
- Final PR head: `3da8c733895baab939548e0ba2e81670ca0c6359`; run #404 (`42193562931`): workflow-sanity PASS; python-tests PASS; **452 passed in 1.35s**.
- Squash merge: `22bbf1714224095cfd652d6887130d26facef087`; post-merge run #405 (`42193654653`) on exact merge SHA: both jobs PASS; **452 passed in 1.33s**.
- Run #403 (`42193476702`) initially failed eight test assertions because the test expected the reduced mobility Jacobian width rather than the full generated Jacobian with six pose columns per link. The expectation was corrected; no code or test gates were weakened. The corrected exact head passed.
- Scope: all eight joint families have deterministic six-row residual, Jacobian component/sign/pitch, local mobility/rank and ground-reversal reference coverage; nontrivial joint-frame placement composition is tested.
- Limitations: one-joint local references only; no general global solver, dynamics or physical validation. PLANAR analysis is a local estimate and depends on finite-difference step, scaling and rank tolerance.


## PR #53 — Documentation index restoration and evidence reconciliation (merged)

- Base SHA: `1d1628175dafca3f5d4d3d6b5cf01e241ec75afa`.
- Final head: `e9ef961e750aaa270c1f6d32d31d7c7763ab90f3`; run #401 (`42192288446`): both jobs PASS, 425 tests in 0.96s.
- Merge: `1db066915c4993e544b386c0311e332874ef4aed`; post-merge run #402 (`42192465566`): both jobs PASS, 425 tests in 0.83s.
- Restores `DOCUMENTATION_INDEX.md`, reconciles PR #49/#52 evidence and documents the integration-vs-main branch boundary.


## PR #56 — Explicit planar plane-frame mobility (merged)

- PR #56 merged at `8335515b31a89efc4cacb70cf9c2e3aeb4ae16d4`. Exact PR head `8b76f89687c4685c66fee5f8bc9cd045bd589abe`; run #459 (`42197011073`) passed `workflow-sanity` and `python-tests` with 462 tests. Exact post-merge run #461 (`42197156442`) on the merge SHA passed both jobs with 462 tests.
- Scope: explicit plane-to-world `RigidTransform`; body-origin, body-axis, joint-anchor and generalized-coordinate-axis coplanarity validation; deterministic projection to two in-plane translations and one plane-normal rotation per non-ground link.
- Supported 2D joint kinds: FIXED, REVOLUTE, PRISMATIC and PLANAR. CYLINDRICAL, HELICAL, SPHERICAL and UNIVERSAL fail closed in the PLANAR formulation.
- Numerical stability: geometric-mobility default central finite-difference step is `1e-5` to reduce round-off amplification from composed frames; callers may explicitly supply another positive step. Rank tolerance was not relaxed.
- Limitations: local mobility only; not a global mobility proof, general closed-loop configuration solver, dynamics, collision/contact, physical feasibility, certification or machine control.


## PR #59 — Versioned schematic layout and deterministic SVG renderer (merged)

- Integration base: `docs/phase-0-complete-requirements` at `977f42bbcb0deedfbe2f013fbdf75bf99cfc4b84`.
- Implementation commit: `6785cd685b9fb879ffea69eedcc04a56a2290f11`; branch: `feat/schematic-layout-svg-renderer`.
- Scope: immutable `SchematicLayout` v1.0 with explicit millimetre page coordinates, stable IDs, symbol definitions (LINE/POLYLINE/RECTANGLE/CIRCLE), pin anchors, component placement/rotation, explicit net routes and strict JSON Schema.
- Renderer: pure-Python deterministic SVG; validates component/symbol/pin references, page bounds and route endpoints; reports incomplete net connectivity separately and never labels an incomplete route as rendered.
- Tests at implementation commit `6785cd6`: run `42201375975`, `workflow-sanity` PASS, `python-tests` PASS; **477 passed in 2.00s**. PR-triggered checks on the documentation-updated candidate must be recorded separately before merge.
- PR #59: https://github.com/phakphum12345/universal-platform/pull/59; review submissions 0 and unresolved threads 0 at initial review.
- Limitations: no automatic placement/autorouting, EDA import/export, ERC, SPICE/circuit simulation, power analysis, manufacturing validation, certification, physical validation or hardware actuation. SVG is a drawing artifact, not electrical proof.


## PR #59 — Versioned schematic layout and deterministic SVG renderer (merged)

- Base integration SHA: `977f42bbcb0deedfbe2f013fbdf75bf99cfc4b84`.
- Final PR head: `70003c5ec985fe487471bd68996cfb60e501f7a7`; PR push run #42203791191 and PR run #42203797877 passed both required jobs.
- Merge commit: `2fd7b3144ed38491f11c6dfefa8bb793f1a2cc21`; post-merge run #42205768788 passed `workflow-sanity` and `python-tests`.
- Scope: SchematicLayout v1.0, explicit page units, symbols, placements, pin anchors, routes and deterministic offline SVG with incomplete-net reporting.
- Limitations: no automatic placement/routing, EDA exchange, ERC (tracked separately by PR #60), circuit simulation, power analysis or physical verification.


## PR #60 — Static electrical rule checking (merged)

- Adds pure offline ERC over validated SchematicModel v1.0; versioned result schema and ruleset v1.0.
- Six rules cover unconnected pins, multiple push-pull outputs, multiple power outputs, power inputs without a declared source, power/signal-driver mixing and open-drain/collector source visibility.
- Results include canonical input SHA-256, stable finding IDs, severity, object references, evidence, recommendations and limitations. Warnings produce FAIL; PASS means only no findings under this ruleset.
- Exact PR-head run #42206594529 and push run #42206646922 passed both jobs with **485 tests**; merge `e641ca19b4f28bb2e2077cf475b371125ebf237a`; post-merge run #42206719188 passed both jobs with **485 tests**. No electrical standards, voltage/current/thermal/timing verification, passive pull-up inference, simulation, physical validation or hardware actuation is claimed.


## PR #61 — Convex 2D profile Boolean operations (MERGED)

- Merge commit: `5f1612ec40a4e6d0f89ee7b419e5add02120f5dc`; base: `docs/phase-0-complete-requirements`.
- Exact PR head: `29e846f513f489196ff742ed464c983a8a771225`; both PR and push workflows passed both required checks; **496 passed**.
- Exact post-merge run #42217655332 passed `workflow-sanity` and `python-tests`; **496 passed in 1.19s**.
- Implements convex-loop UNION/INTERSECTION/DIFFERENCE with deterministic convex-cell decomposition, strict v1.0 result snapshots and area accounting.
- Limitations: concave loops, holes, arcs, exact arithmetic, general planar arrangements, region dissolution, 3D B-rep and mesh Booleans are not implemented.

## PR #62 — General planar region topology contract (DESIGN CANDIDATE)

- Branch: `docs/cad-general-planar-topology-contract`; base SHA: `5f1612ec40a4e6d0f89ee7b419e5add02120f5dc`.
- Adds `docs/design-3d/CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT.md` defining CAD-neutral regions with outer boundaries and holes, explicit frames/units, topology invariants, contact semantics, numerical robustness tiers, result/evidence requirements and kernel decision gate.
- Design only: no general planar Boolean implementation, precision policy selection, kernel selection or third-party dependency is claimed.
- Next gate: select and document a precision policy and independent adversarial reference corpus before implementation.


## PR #62 — General planar region topology contract (MERGED; DESIGN ONLY)

- PR: https://github.com/phakphum12345/universal-platform/pull/62
- Base SHA: `5f1612ec40a4e6d0f89ee7b419e5add02120f5dc`; exact head SHA: `d03928bbe3472fae4f5890f6a9f481c0049b7f35`.
- Merge commit / current integration HEAD: `213b1b52ef78ae3297a88892b4cc0c6539159160`.
- Exact PR-head runs #42217964997 (pull_request) and #42217937596 (push): both `workflow-sanity` and `python-tests` PASS; **496 passed**.
- Exact post-merge run #42218707816 on the merge SHA: both jobs PASS; **496 passed in 1.08s**.
- Adds `docs/design-3d/CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT.md`; defines a CAD-neutral region/hole topology and numerical/kernel decision gate.
- Documentation/design only. No general polygon Boolean implementation, precision policy selection, geometry kernel selection, or third-party dependency is claimed.
- Current working tree is UNKNOWN because no local checkout was inspected. Default branch `main` remains at `96e75010716226037893155b9fd4b13410fb0d6f`; integration has not been merged to main.


## PR #64 — Deterministic primitive triangle mesh (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/64
- Base SHA: `342c3c43ae6b4561da42a4839f042054f3198a4d`; exact PR head SHA: `8fe9db48cd07a66ea39d61e386ee8f362b968104`.
- Merge commit / integration HEAD: `f0bfd8ad9958af9bfe678e923d52726b12eee73a`.
- Exact PR-head run #42219983207 and push run #42219977049: both required jobs PASS; **506 passed**.
- Exact post-merge run #42220119818 on the merge SHA: both jobs PASS; **506 passed in 1.93s**.
- Adds `TriangleMesh` v1.0, deterministic BoxSolid/CylinderSolid tessellation, source SHA-256 provenance, explicit local frame/unit, cylinder chordal tolerance, structural edge/winding validation, signed volume and surface area.
- Explicit limitations: no extruded-profile or hole meshing, arbitrary triangle self-intersection detection/repair, B-rep, 3D Boolean, STEP/STL/3MF exchange or manufacturing validation.


## PR #66 — Straight extruded-profile triangle mesh (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/66
- Base SHA: `51e8227e2be50caccebce7ee307eaabb4d74292b`; exact corrected PR head SHA: `1179fb69114bc76b3155d0c3e6edf50223050846`.
- Merge commit / integration HEAD: `1ead537afa34d2637fdb08f91b2d2bb823d411a0`.
- Exact PR workflow run #42221102000 and push run #42221092727: both required jobs PASS; **511 passed**.
- Exact post-merge run #42221247498 on the merge SHA: both jobs PASS; **511 passed in 1.20s**.
- Adds deterministic ear-clipped cap triangulation and outward side walls for straight-edged, hole-free concave/convex `ExtrudedProfileSolid`; retains source SHA-256, local frame and unit.
- The initial head `48b3124f89a3e97dc9ce529d811aa0ee2503107b` failed the CW profile orientation reference; the final head corrected side-wall winding to normalized CCW traversal and passed all tests.
- Limitations: no profile holes or arcs, arbitrary mesh self-intersection/repair, B-rep, 3D Boolean or neutral CAD interchange.


## PR #68 — Polygonal through-hole extrusion mesh (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/68
- Base SHA: `f9d8f51b01fb41afec311b8b72ffd0e9231c631b`; exact corrected PR head SHA: `da5c8a292dacf8c300fcb48b9e92b506f1172bd8`.
- Merge commit / integration HEAD: `6ec9ba1367c22c0a14d293e57ed2d538ebfc654b`.
- Exact PR workflow run #42222216690 and push run #42222207986: both required jobs PASS; **514 passed**.
- Exact post-merge run #42222360177 on the merge SHA: both jobs PASS; **514 passed in 1.53s**.
- Adds deterministic visible-bridge selection and ear clipping for straight polygonal extrusion regions with one or more strictly-contained holes; inner walls use CW hole boundaries to face the void.
- First tested head had two inner-wall winding/volume failures; final exact head corrected orientation and added reversed-hole-winding regression coverage.
- Limitations: curved outer/hole boundaries, arbitrary mesh self-intersection/repair, B-rep, 3D Boolean and neutral CAD interchange remain unsupported.


## PR #70 — Circular-arc profile triangle mesh (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/70
- Base SHA: `c1056671b7ad8a8ca1415a449d830db0057f5034`; exact corrected PR head: `0e7d7233069e2fafb8850a15d1f1e1539bf6c883`.
- Merge commit: `98440851b0b75216ea89013d9d2eea07b42c4416`.
- Exact PR workflow run #42223197118 and push run #42223188816 passed both required jobs with 515 tests; exact post-merge run #42223460020 passed both jobs with **515 tests in 2.01s**.
- Adds deterministic circular-arc boundary tessellation for extruded profiles and polygonal holes under explicit positive chordal tolerance; stores tolerance in TriangleMesh v1.0 and preserves source geometry digest/frame/unit.
- Limits: non-circular curves/splines, general geometric self-intersection detection/repair, B-rep, 3D Boolean and neutral CAD interchange remain NOT IMPLEMENTED.

## PR #71 — Circular-arc through-hole reference coverage (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/71
- Base SHA: `98440851b0b75216ea89013d9d2eea07b42c4416`; exact PR head: `d94d9c3b974e3ceea70ddf4a8a1b18da92b8c845`.
- Merge commit / integration HEAD: `8aba562a1df6c0691c855f95ef16a9ba94089556`.
- Exact PR workflow run #42225768304 passed both jobs with **516 tests in 1.74s**; exact post-merge run #42225830931 passed both jobs with **516 tests in 1.45s**.
- Adds a curved polygonal-hole reference validating watertightness, manifold edge incidence, winding, positive volume, chordal-area bound, endpoint retention, deterministic output and strict snapshot round trip.
- Test-only change; production API/schema unchanged. This closes the reference-coverage gap for the hole-arc path.



## PR #73 — Binary STL interchange contract (DESIGN ONLY)

- Branch: `docs/stl-interchange-contract`; base integration SHA: `6cdfffc8d9fffadb7162977c77efd54445bb9471`.
- Adds `docs/design-3d/STL_INTERCHANGE_CONTRACT.md` defining deterministic binary STL export and a mandatory sidecar manifest with frame, unit, source provenance, chordal tolerance, payload digest, counts and float32 quantization error.
- First implementation slice is export-only with an independent test-only reader; arbitrary external STL import and external CAD application reopen are not implemented.
- No STL exporter, manifest schema, STEP/3MF support, external toolchain selection or third-party dependency is claimed.


## PR #73 — Binary STL interchange contract (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/73
- Exact PR head: `39f3325260baa084d8e817554a9c9fd1702922c0`; base: `6cdfffc8d9fffadb7162977c77efd54445bb9471`.
- Merge commit / integration HEAD: `24f0b7083d95fb5582e26f4614a227250e0a2de0`.
- Exact PR workflow #42226759918 and push workflow #42226749519 passed both jobs with 516 tests; post-merge run #42226889599 passed both jobs with **516 tests in 1.11s**.
- Adds a design contract only. STL export/import, schema and external CAD reopen are not implemented.

## PR #74 — Deterministic binary STL export (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/74
- Base SHA: `24f0b7083d95fb5582e26f4614a227250e0a2de0`; exact PR head: `e7491d976177a51933f62e5eefcab90d11dcc19f`.
- Merge commit / integration HEAD: `1503266c18c5ed74c5756391c033437b05ae6f13`.
- Exact PR run #42227530004: both jobs PASS, 523 tests in 1.61s; push run #42227459289: both jobs PASS, 523 tests in 1.12s; post-merge run #42227796004: both jobs PASS, **523 tests in 1.31s**.
- Adds pure-Python binary STL export and strict sidecar metadata, public API exports, source-specific tolerance rules, binary32 quantization checks, caller-approved frame/unit validation and independent test-only facet reader.
- Limitations: no arbitrary STL import, ASCII STL, external CAD reopen, STEP/3MF, B-rep or mesh repair.

## PR #75 — Independent STL geometric reopen references (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/75
- Base SHA: `1503266c18c5ed74c5756391c033437b05ae6f13`; exact PR head: `0d17638b6c361abfed7d0501576b0bc7de277809`.
- Merge commit / integration HEAD: `a8a7e6b28650a90665a465e7373d8ad6582f7832`.
- Exact PR workflow #42228344477 passed both jobs with 524 tests in 2.09s; exact post-merge run #42228462537 passed both jobs with **524 tests in 2.20s**.
- Adds independent facet-record bounding-box and signed-volume comparison, coordinate-error-derived tolerance and non-finite/normal corruption tests.
- This is test-only; production STL API/schema is unchanged.

## PR #76 — Mesh geometric topology analysis contract (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/76
- Exact PR head: `526a2cb0632154e52596e3322a107ee8dddc4d4d`; merge commit / integration HEAD: `ff486f8ae4569ca8122f0294f55d18b21b32d10c`.
- Exact PR run #42229095708 passed both required jobs with 524 tests in 2.25s; exact post-merge run #42229207672 passed both jobs with **524 tests in 1.60s**.
- Design contract only; no topology-analysis implementation was introduced by #76.

## PR #77 — Mesh geometric topology analysis implementation (MERGED)

- PR: https://github.com/phakphum12345/universal-platform/pull/77
- Exact PR head: `66593ebb6658f0e0fc43d17f90b6c8360e5969d2`; merge commit / integration HEAD: `20e34933087a7276d0acc08e0d17b872c3973949`.
- Exact PR workflow #42230501005 and push workflow #42230490785 passed both jobs with 533 tests in 2.08s; exact post-merge run #42230654227 passed both jobs with **533 tests in 1.98s**.
- Adds additive MeshTopologyAnalysis v1.0 and analyze_mesh_topology, strict schema, provenance/digests, edge-connected components, vertex-link manifoldness, duplicate/near-coincident groups and unused-vertex diagnostics.
- No self-intersection claim; self_intersection_status remains UNKNOWN.

## PR #78 — Triangle-mesh self-intersection contract (DESIGN ONLY)

- Branch: `docs/mesh-triangle-intersection-contract`; base SHA: `20e34933087a7276d0acc08e0d17b872c3973949`.
- Adds a separate contract for triangle-pair classification, conservative broad-phase candidate generation, exact represented-input predicates, adjacency exclusions, resource limits and independent reference tests.
- No implementation or self-intersection PASS is claimed.


## PR #78 — Triangle-mesh self-intersection contract (MERGED; DESIGN ONLY)

- Integration branch HEAD: `502d49baf58e43938d2746859e10817badd43f6e`; PR #77 predecessor: `20e34933087a7276d0acc08e0d17b872c3973949`.
- Exact PR head: `08f6aade1d928b9d2e2d7a065aa448ef9065bed1`; PR #78 base SHA: `20e34933087a7276d0acc08e0d17b872c3973949`.
- PR workflow #42231152061: workflow-sanity PASS; python-tests PASS; PR evidence reports 533 tests passed. Documentation-only marker SKIPPED.
- Reviews: 0; unresolved review threads: 0.
- Adds only the separate MeshIntersectionAnalysis design contract. No self-intersection implementation or geometric PASS is claimed. `MeshTopologyAnalysis v1.0` remains backward compatible and self-intersection remains UNKNOWN.
- Post-merge CI on integration HEAD `502d49baf58e43938d2746859e10817badd43f6e`: UNKNOWN; no status entries or workflow runs were returned.
- Full capability gaps and next work packages: [Repository Audit 2026-11-06](../audit/REPOSITORY_AUDIT_2026-11-06.md).


## PR #80 — Exact triangle-mesh intersection analysis (MERGED)

- Base integration SHA: `f0d52ecf8dee44c4984badf3fb0e902f3f47b57f`.
- Exact PR head: `009ab1b24578579c0f6c6bbf3d4f8e3ee42fc181`; merge SHA / integration HEAD: `cb91c7c49406fd02324be6b30d5570e821b4d503`.
- PR workflow #42238370626: workflow-sanity PASS; python-tests PASS; **550 passed in 2.63s**. Push workflow #42238360081 passed both jobs. Documentation-only marker step SKIPPED.
- Reviews: 0; unresolved review threads: 0.
- Adds `MeshIntersectionAnalysis v1.0`, `analyze_mesh_intersections`, schema, exact rational narrow-phase predicates over binary64 inputs, deterministic conservative sweep, stable pair classifications, strict provenance-bound snapshots and resource-limit UNKNOWN behavior.
- Structural validation is a precondition. Input mesh is not mutated. No welding, snapping, repair, B-rep, Boolean, collision, manufacturing, physical or certification claim is made.
- `MeshTopologyAnalysis v1.0` remains backward compatible and keeps `self_intersection_status=UNKNOWN`; the new intersection result is independent.
- Post-merge CI for `cb91c7c49406fd02324be6b30d5570e821b4d503`: UNKNOWN; no run/status evidence was returned.
- Next work is general planar-region Boolean topology after a precision-policy decision and independent adversarial references. Full gaps: [post-PR #80 Repository Audit](../audit/REPOSITORY_AUDIT_2026-11-06_POST_PR80.md).


## PR #82 — PlanarRegion v1 input model (IN REVIEW; not yet implemented on integration)

- Base integration SHA: `1eceffbbdabd0d40f508a26dd14f99b70bc3dd53`.
- Candidate branch: `feat/planar-region-model-v1`; exact candidate head will be recorded after PR creation.
- Adds separate PlanarRegion v1.0 input model, exact rational represented-binary64 boundary predicates, strict hole checks, canonical orientation/start point, explicit frame/unit, canonical digest, schema and tests.
- Does not implement Boolean operations and does not change convex ProfileLoop v1.0.
- Status remains IN REVIEW until exact-head CI, merge and post-merge checks are verified.


## PR #82 — PlanarRegion v1.0 input model (MERGED)

- Base integration SHA: `1eceffbbdabd0d40f508a26dd14f99b70bc3dd53`; exact PR head: `a2df003b7dfe66c6ccaf605cfb8ee83d0780668e`; merge SHA / integration HEAD: `114bf8dd84831d7d4080922ed7069cadda380ba3`.
- PR workflow #42240159979 and push workflow #42240149518 passed both required jobs; 563 tests in 1.54s on the PR head.
- Post-merge workflow #42240292055 passed workflow-sanity and python-tests; 563 tests in 2.47s.
- Adds PlanarRegion v1.0, exact represented-binary64 rational predicates, canonical winding/start, strict simple boundary and hole validation, explicit frame/unit, digest, schema and 2,048-edge bound.
- No Boolean operation is implemented. ProfileLoop/ProfileBooleanResult v1.0 remain convex-only.
- Next work: exact planar-region Boolean arrangement with multi-component/hole support, independent references, deterministic graph traversal and output rounding/error bounds.


## PR #84 — Pairwise PlanarRegion Boolean engine (MERGED)

- Integration HEAD / merge SHA: `1b75e2dab5b64d2d089e410bba02187d28772193`; `main` remains `96e75010716226037893155b9fd4b13410fb0d6f`.
- Exact PR head `999235de2627f948a6fba8c4c9a038cea7cf8857`; PR workflow #42250468895 passed workflow-sanity and python-tests, **580 passed in 2.14s**.
- Exact post-merge workflow #42250583756 on the merge SHA passed both jobs, **580 passed in 2.96s**.
- New API: `PlanarRegionBooleanOperation`, `PlanarRegionBooleanResult`, `boolean_planar_regions`; pairwise operations UNION, INTERSECTION, DIFFERENCE and SYMMETRIC_DIFFERENCE. Supports multiple output components and holes, exact rational arrangement decisions over represented binary64 inputs, deterministic cycles, output rounding-error metrics and strict snapshot validation.
- Limits: 256 total input boundary edges / 32,640 pair checks; same frame/unit required; point-touching or branching output fails closed. No implicit conversion, snapping, quantization or repair. Existing convex ProfileLoop v1.0 contract unchanged.
- Still not implemented: general region-set aggregation, robust point-contact traversal, arcs/splines, parametric sketch constraints, feature history, B-rep/3D Booleans, STEP/3MF round-trip, physical/manufacturing validation. No local working-tree test is claimed.
