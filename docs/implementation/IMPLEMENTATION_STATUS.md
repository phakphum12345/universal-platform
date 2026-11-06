# Implementation Status — UEIC Foundation

**Integration branch:** docs/phase-0-complete-requirements  
**Latest merged baseline:** c384492b058ec9dee3599feb60bb7475de298181 (PR #13)  
**Current feature work:** feat/planar-four-bar-loop-closure — planar 4R loop closure and mobility estimate; pending exact-SHA CI.  
**Scope:** Dependency-light engineering core, rigid transforms, coordinate-frame forest, limited rooted-tree forward kinematics, planar 2R inverse kinematics and a narrow planar 4R loop-closure adapter.

## Implemented in the merged baseline

- Typed SI-backed quantities and dimensional checks for a deliberately limited unit registry.
- Evidence/provenance records with FACT / ASSUMPTION / SIMULATION / UNKNOWN distinctions and PASS / FAIL / SKIPPED / UNKNOWN statuses.
- Fail-closed safety gate that rejects physical execution actions.
- Small dense linear solver with partial pivoting and residual calculation.
- Hard/soft scalar constraint evaluation with explicit UNKNOWN for missing variables.
- Analytic Box/Cylinder geometry primitives and bounds; not a CAD kernel.
- Assembly occurrence/joint data contracts, identity/reference checks, normalized axes, finite/ordered limits and nominal joint DOF bookkeeping.
- Dependency-free rigid coordinate transforms with frame-checked composition, inversion, point/vector transforms and transformed axis-aligned bounds.
- Coordinate-frame forest with one parent per child, cycle rejection, inverse traversal and path resolution.
- Tree-only forward kinematics for FIXED, REVOLUTE and PRISMATIC joints with explicit placements, topology/frame validation and joint-limit enforcement.
- Narrow analytic planar two-link (2R) inverse kinematics for elbow-up and elbow-down branches, with workspace, joint-limit, finite-input and forward-reconstruction residual checks.
- Linear algebra simulation adapter with declared limitations and evidence.
- Versioned module request/response envelopes.
- Starter mechanics, DC electrical calculations, linear thermal expansion and traceable material property records (initial equations only).

## Current feature slice — planar four-bar loop closure and mobility estimate

The feature branch adds one planar four-link/four-revolute (4R) loop closure adapter. It solves the coupler endpoint as the intersection of two circles, returns left/right assembly branches and verifies the link-length closure residual. It also adds the planar Kutzbach/Gruebler mobility count, explicitly labeled as an estimate.

This is not a general nonlinear constraint solver. It does not solve arbitrary topologies, multiple loops, 3D constraints, redundant systems or physical mechanisms. Its implementation status remains PENDING CI until the exact PR head SHA has passing workflow evidence.

## PR #12 — Planar two-link inverse kinematics

- PR #12 merged at 0379c8613c7668a56b681a91d01882c66f1c812c; tested PR head e5f8511b14cd72ecb930ffd08ccb7f916cb71056.
- [PR run #82](https://github.com/phakphum12345/universal-platform/actions/runs/42136840495) and [push run #81](https://github.com/phakphum12345/universal-platform/actions/runs/42136834146): workflow-sanity and python-tests PASS.
- [Post-merge run #83](https://github.com/phakphum12345/universal-platform/actions/runs/42136914390): workflow-sanity and python-tests PASS.
- Documentation-only markers were SKIPPED, not PASS. Initial run #80 failure remains recorded in the PR #13 reconciliation.

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
- General closed-loop constraint solving, multi-loop coupling, arbitrary nonlinear constraints, full mechanism mobility/over-constraint analysis and singularity classification.
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
