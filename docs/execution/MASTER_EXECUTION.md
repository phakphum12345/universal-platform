# Documentation-Driven Continuous Execution

**Repository:** phakphum12345/universal-platform  
**Control document:** This file  
**Evidence rule:** Source code, executed tests and exact Git revisions outrank prose status claims.

## 1. Operating model

Use the existing domain contracts and implementation records as the authoritative specifications. Do not create parallel documents for capabilities already covered. Each implementation slice must update its relevant contract, this execution register, the implementation status and requirements traceability when those records are affected.

Execution loop:

1. Audit the current integration branch, main, open PRs, exact SHAs, reviews, threads and CI.
2. Inspect the relevant source, tests, schemas and existing contracts.
3. Select the smallest dependency-ready vertical slice with explicit acceptance criteria.
4. Implement source and tests together.
5. Run targeted tests and all relevant CI checks.
6. Open a focused PR against the approved integration branch.
7. Verify exact head SHA, reviews, unresolved threads, mergeability and required checks.
8. Merge only into the integration branch when all merge conditions pass.
9. Verify post-merge CI on the exact merge SHA.
10. Reconcile documentation and select the next task.

## 2. Existing documentation is reused

The repository already contains domain specifications under:

- docs/architecture/ — platform, data, module and system contracts.
- docs/engineering/ — UEIC, physics, quantities, solvers and cross-domain constraints.
- docs/design-3d/ — CAD, B-rep, geometry, FeatureHistory, assembly and kinematics.
- docs/hardware/ — hardware, schematic, ERC and driver contracts.
- docs/requirements/ — confirmed and proposed product requirements.
- docs/roadmap/ — engineering delivery and vertical-slice plans.
- docs/testing/ — test strategy.
- docs/governance/ and docs/operations/ — approval, hazards, resources, release and rollback.
- docs/implementation/ and docs/traceability/ — implementation maturity and evidence mapping.
- docs/audit/ — dated repository and capability inventories.

The proposed file tree in a command is not authority to duplicate these files. Extend existing specifications unless a genuinely missing contract is identified.

## 3. Work package map

| WP | Domain | Canonical specification / evidence |
|---|---|---|
| 01 | Core architecture and governance | docs/architecture/, docs/governance/ |
| 02 | CAD geometry and topology | docs/design-3d/CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT.md, docs/design-3d/FACETED_BREP_TOPOLOGY_CONTRACT.md |
| 03 | Parametric CAD and FeatureHistory | docs/design-3d/FEATURE_HISTORY_REGENERATION_CONTRACT.md, docs/design-3d/FEATURE_HISTORY_EDITING_CONTRACT.md |
| 04 | Mechanics and kinematics | docs/design-3d/GENERAL_LOOP_CLOSURE_CONTRACT.md, docs/engineering/MECHANISM_CONSTRAINT_ADAPTER_CONTRACT.md |
| 05 | Central physics and solvers | docs/engineering/PHYSICS_AND_FIRST_PRINCIPLES.md, docs/engineering/ENGINEERING_SOLVER_AND_MODEL_CONTRACT.md |
| 06–08 | Hardware, schematic, drivers | docs/hardware/ |
| 09 | Module runtime and adapters | docs/architecture/ENGINEERING_MODULE_API_CONTRACT.md, docs/operations/ |
| 10 | System understanding and governed evolution | docs/architecture/SYSTEM_INTELLIGENCE.md, docs/evolution/ |
| 11–12 | API, UI and platform integration | docs/architecture/PLATFORM_ARCHITECTURE.md, docs/integration/ |
| 13–14 | Security, quality and final verification | docs/testing/, docs/governance/, docs/audit/ |

## 4. Status vocabulary

- PASS: implemented behavior has reproducible evidence tied to an exact revision.
- FAIL: a required behavior or check is not satisfied.
- SKIPPED: not executed; never a pass.
- UNKNOWN: evidence unavailable or insufficient.
- BLOCKED: a dependency or external constraint prevents progress.
- OWNER APPROVAL REQUIRED: a protected action requires owner authorization.

Documentation presence alone does not establish implementation. A green workflow does not establish untested browser, security, physical or engineering validity.

## 5. Safety and merge policy

- Work against the verified integration branch, not main.
- Do not merge into main without explicit owner approval.
- Do not deploy production, activate paid services, delete files/data/branches/history, force-push, alter protections, permissions or secrets without explicit approval.
- Prefer local-first and cost-aware dependencies.
- Preserve existing source and history; use additive, reviewable changes.
- When one task is blocked, continue independent tasks only when their prerequisites and safety conditions are satisfied.

## 6. Completion rule

The repository remains INCOMPLETE while any approved requirement lacks implementation or evidence, or while required security, integration, numerical, browser, compatibility or post-merge gates remain unverified. Report limitations and owner decisions explicitly.
