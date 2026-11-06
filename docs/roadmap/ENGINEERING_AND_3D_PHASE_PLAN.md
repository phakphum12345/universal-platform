# Engineering Intelligence and 3D Design Project Plan

**Planning status:** PROPOSED for owner review  
**Scope direction:** CONFIRMED by owner  
**Current code baseline:** Initial engineering-core slice merged at `647956be574ffc0055d2613be5a7a4781d660542`.

## 1. Objective
Specify a reusable multidisciplinary engineering core and 3D design/tool-generation system. UEIC is the shared middle layer. Existing Driver Generation is treated as an existing capability to locate and reuse; this project must not create a duplicate driver generator.

## 2. Scope
- Multidisciplinary knowledge modules and domain registry.
- Physics and first-principles models.
- Mathematics, units, uncertainty and provenance.
- Solver/model adapter contracts.
- Cross-domain constraint planning and verification.
- Parametric 3D design and existing-model analysis.
- Tool, fixture and mechanism generation.
- Assembly, joints, kinematics and motion envelopes.
- Structural/civil, mechanical, thermal, fluid and electronic design support.
- Simulation and model validation.
- CAD-to-manufacturing preparation.
- Safety, review and evidence governance.

## 3. Explicit exclusions for the initial phase
No physical device control, GPIO writes, live bus transactions, register writes, power switching, actuator/motor operation, firmware flashing, machine operation, production release, automatic purchasing or deployment. No duplicate driver-generation implementation. No automatic integration of separate projects.

## 4. Work phases and gates
### Phase 0 — Requirements and documentation baseline
Deliver scope, requirements, architecture, module catalogue, data/API contracts, safety policy, acceptance criteria, traceability, decision register and open questions. Documentation is a specification, not implementation evidence.

### Phase 1 — Repository and capability inventory
Inspect existing code/docs, especially Driver Generation, calculation engine, device intelligence, simulation, CAD-related work and adapters. Record exact paths, SHA, tests and actual maturity.
**Current result:** Universal Platform has a merged initial Python engineering foundation and 66-blob recursive tree at the baseline SHA. The initial engineering slice is verified by PR #1 checks and post-merge run #19. Broader capabilities remain not implemented or unverified. The external Driver Generation canonical source remains UNKNOWN; the inspected EFI/OpenCore candidate is not a universal driver generator.
Gate: complete source inventory; canonical Driver Generation location or explicit owner acceptance of UNKNOWN; reuse/extension/create decisions.

### Phase 2 — Architecture and technology decision
Compare candidate CAD kernels, file formats, solvers, simulation tools and data stores using license, cost, offline support, platform support, interoperability and validation evidence.
Gate: architecture decision records approved. No vendor/tool selected by assumption.

### Phase 3 — Minimal vertical-slice design
Choose one representative workflow, define test dataset, requirements, interfaces, expected outputs and verification method.
Gate: owner approves acceptance tests and safety boundary.

### Phase 4 — Core implementation
Extend only approved UEIC contracts, module registry, units/provenance, solver adapters and evidence records. Isolate components and add tests.
Gate: tests and security review pass.

### Phase 5 — 3D design integration
Integrate a selected CAD tool/kernel, parametric geometry, assemblies and export validation. Do not imply full simulation support unless independently proven.
Gate: repeatable model build and export tests.

### Phase 6 — Multidisciplinary analysis
Add validated physics/material/mechanical/electrical/thermal modules incrementally. Validate each against reference cases.
Gate: per-module evidence and expert review where required.

### Phase 7 — Tool generation and manufacturing preparation
Add tooling templates, DFM checks, drawings, BOM and process planning.
Gate: human design review; no automatic fabrication.

### Phase 8 — Controlled release
Only after owner authorization, security review, evidence completeness, documentation and rollback planning. Physical operation remains a separately governed future decision.

## 5. Required deliverables before broader implementation
- Approved scope and requirements baseline.
- Repository capability inventory and reuse map.
- Engineering master file plan.
- Vertical-slice specification and owner-selected use case.
- UEIC architecture, module contracts and schemas.
- Discipline/model reference cases and failure taxonomy.
- CAD/3D interchange and simulation architecture.
- Data/API schemas and evidence model.
- Safety/hazard and approval policy.
- Technology comparison and decision records.
- Traceability matrix and unresolved decision list.

## 6. Documentation completion rule
Every requirement maps to an architecture owner, document, acceptance criterion, evidence plan and status. Documentation completeness is not implementation readiness. Owner decisions remain OPEN until explicitly resolved.

## 7. Current status
Initial engineering-core implementation: PASS at the merged baseline SHA.  
Repository capability inventory: PARTIAL; the initial tree is enumerated, but external candidate runtime/license/security audit remains open.  
Canonical generic Driver Generation source: UNKNOWN.  
CAD kernel / solver / schema / database decisions: OPEN.  
Vertical slice selection: OPEN.  
Full UEIC/3D implementation: NOT IMPLEMENTED / NOT VERIFIED.


## PR #32 — Generalized coordinate foundation

Implemented and merged as PR #32 at `e6a6a4c58fb43ad9a837e4f38558cb53ab6eb598`. Exact PR head `c2b768b8f3a75a010614c1cd8a874b63f32f7ca0` passed run #257 (225 tests); post-merge run #258 on the exact merge SHA passed (225 tests). The v1.2 extension defines independent coordinate records, ordered joint mappings, explicit units/axes/bounds/scales, family-specific validation and legacy compatibility. This remains a structural parameterization layer; automatic joint constraint equations and Jacobian generation remain subsequent dependency steps.


## PR #33 — Automatic joint constraint generation

PR #33 merged at `62c71e4ca1f60eff5b496305429e6d141a81d268`. Final PR head `68fb6a6d0c268b67786183211734a66db0a4b27c` passed push run #270 and PR run #271 (241 tests each); post-merge run #272 on the exact merge SHA passed 241 tests. The implementation adds deterministic six-component pose-consistency residuals per joint using explicit body poses, joint placements and generalized coordinates. It covers all eight declared joint families and rejects missing placement/parameterization inputs. Automatic Jacobian generation and solver integration remain separate follow-on work.


## PR #34 — Automatic constraint Jacobian

Implementation in review adds a numerical Jacobian for generated joint residuals with deterministic stable-ID columns for generalized coordinates and body poses. Forward/central finite differences, characteristic coordinate scales, physical row/column units and bound-aware one-sided differences are represented explicitly. Symbolic derivatives and solver convergence claims remain out of scope.
