# Universal Platform — Universal Requirements

**Status:** Phase 0 requirements baseline  
**Normative labels:** CONFIRMED = directly established by the owner; PROPOSED = detailed design/acceptance item pending review; OPEN = unresolved; DEFERRED = outside the initial implementation boundary.

## 1. Product intent
Build a cross-platform, cross-disciplinary environment for learning, research, understanding systems, engineering, calculation, simulation, creation, adaptation, and governed capability growth. The platform is not restricted to a single industry, programming language, operating system, or device family.

## 2. Confirmed requirements
- R-001 [CONFIRMED] Support broad and extensible disciplines rather than a fixed narrow domain.
- R-002 [CONFIRMED] Support multiple operating systems and interaction surfaces.
- R-003 [CONFIRMED] Include computing, software, hardware, electronics, communications, mathematics, science, and engineering.
- R-004 [CONFIRMED] Understand authorized existing applications and systems.
- R-005 [CONFIRMED] Support adapting existing systems and creating new applications/systems.
- R-006 [CONFIRMED] Include IC/chip, board, sensor, and module intelligence.
- R-007 [CONFIRMED] Initial device scope is analysis and simulation, not physical control.
- R-008 [CONFIRMED] Support calculations across hardware, software, electronics, and engineering.
- R-009 [CONFIRMED] Learn, improve, and extend platform capabilities under governance.
- R-010 [CONFIRMED] Avoid unnecessary spending; prefer learning, open tools, local execution, and reuse when suitable.
- R-011 [CONFIRMED] Consolidate requirements and review documentation before implementation.
- R-012 [CONFIRMED] Existing projects remain separate until explicitly assessed and approved for integration.
- R-013 [CONFIRMED] Use multiple scientific and engineering disciplines together through a reusable central module, not isolated one-off logic.
- R-014 [CONFIRMED] Scope includes 3D design and generation of tools, machines, moving mechanisms, structures/buildings, electronic equipment and general products.
- R-015 [CONFIRMED] Existing Driver Generation is to be reused/inventoried; do not create a duplicate driver generator.

## 3. Functional requirement groups

### Knowledge and research
- Discover, ingest, index, cite, version, and retrieve authorized documents, source code, APIs, datasets, standards, datasheets, and user-provided materials.
- Preserve provenance, licenses, timestamps, source identity, confidence, and uncertainty.
- Distinguish observed facts, derived results, assumptions, hypotheses, and unknowns.

### System intelligence
- Inspect authorized repositories, applications, APIs, configuration, dependencies, data models, workflows, interfaces, and runtime evidence.
- Produce architecture and dependency maps, inventories, risk reports, and change-impact analysis.
- Never imply access to hidden internals when only black-box observations are available.

### Universal command and orchestration
- Accept user goals through a common task model independent of UI.
- Convert intent into explicit plans, prerequisites, permissions, steps, expected outputs, and verification criteria.
- Support preview, approval, cancellation, pause/resume, rollback planning, and audit.
- The exact command syntax and interaction model remain OPEN.

### Calculation and multidisciplinary engineering
- Provide unit-aware calculations, symbolic/numeric methods, estimation, optimization, and reproducible result records.
- Coordinate physics, mathematics, mechanics, materials science, thermodynamics, fluid dynamics, electrical/electronic engineering, control theory, chemistry, manufacturing, geometry, computing and other reviewed disciplines.
- Support cross-domain constraint solving and explicit handling of conflicting models.
- Separate calculation, estimate, simulation, and physical measurement.
- Detailed UEIC and solver requirements are PROPOSED in the engineering specifications.

### 3D design, tools, machines and structures
- Support parametric 3D design from requirements, sketches, dimensions and supported existing models.
- Support tools, fixtures, machine components, assemblies, moving mechanisms, structures/buildings, electronic equipment and general products.
- Represent parts, materials, interfaces, assemblies, joints, degrees of freedom, motion envelopes and tolerances where supported.
- Connect CAD models to engineering calculations, simulation, validation, drawings, BOM and manufacturing planning.
- Detailed CAD kernel, formats, solver choices and capability maturity remain OPEN pending repository inventory and technology review.

### Creation and adaptation
- Generate designs, source code, applications, system components, documentation, tests, and deployment plans.
- Adapt existing systems only with authorization, license/security review, isolated changes, tests, and human approval where consequential.
- Preserve original sources and provide diffs, provenance, and rollback paths.
- Existing Driver Generation is not to be duplicated; its implementation and interfaces must be inspected during Phase 1.

### Device intelligence
- Identify and classify ICs/chips, boards, sensors, and modules.
- Interpret datasheets, pinouts, electrical limits, interfaces, timing, power, thermal behavior, footprints, and constraints.
- Analyze schematics, PCB layouts, BOMs, netlists, and compatibility.
- Initial scope excludes physical device control, GPIO operation, real sensor acquisition, actuator control, firmware flashing, and machine operation.

### Virtual laboratories
- Provide reproducible software, OS, network, circuit, hardware-emulation, scientific, and engineering simulation environments as supported.
- Isolate untrusted workloads and label simulated results clearly.

### Governed evolution
- Detect capability gaps, propose extensions, evaluate them, and add capabilities through reviewable modules.
- Platform self-modification, privilege escalation, production changes, and autonomous deployment are not implicitly authorized.

## 4. Non-functional requirements
- NFR-001 Security by default; least privilege and explicit trust boundaries.
- NFR-002 Local-first and offline-capable where practical.
- NFR-003 Cost transparency; no paid service without a justified benefit and approval.
- NFR-004 Modular, replaceable components and open interfaces.
- NFR-005 Cross-platform behavior with declared support matrices.
- NFR-006 Reproducibility, versioning, provenance, and auditability.
- NFR-007 Accessibility, understandable errors, and user control.
- NFR-008 Graceful degradation when models, networks, or tools are unavailable.
- NFR-009 No fabricated capability, test, measurement, or success claim.
- NFR-010 Data minimization, exportability, and explicit retention rules.
- NFR-011 Engineering models expose validity ranges, assumptions, units and uncertainty.
- NFR-012 Domain modules and solver adapters are replaceable and independently versioned.
- NFR-013 3D and manufacturing artifacts preserve revision, units, provenance and human release control.

## 5. Evidence and acceptance
Every capability must state: purpose, inputs, outputs, prerequisites, permissions, supported platforms, limitations, risks, cost, tests, and evidence. Results use PASS / FAIL / SKIPPED / UNKNOWN. PASS requires executed evidence tied to a version/SHA and reproducible command or procedure. A plan or mock is not proof of implementation. Engineering validation is specific to a model version and stated validity range.

## 6. Authority and safety boundaries
Read-only inspection is the default. Writes, external communication, purchases, account changes, deployment, physical actuation, and self-modification require explicit scoped authorization. Initial physical hardware control is DEFERRED. Untrusted code/data must be sandboxed and treated as untrusted instructions. Engineering and manufacturing outputs do not certify safety or authorize fabrication/operation.

## 7. Completeness rule
A requirement is not complete merely because it appears in a roadmap. It must be mapped to architecture, an owner/module, acceptance criteria, tests, and evidence—or explicitly marked OPEN, PROPOSED, DEFERRED, or OUT OF SCOPE.

## 8. Open questions
- Exact command vocabulary and interaction contract.
- First end-to-end use case and acceptance target.
- Supported OS/platform priority and minimum hardware.
- AI model/provider strategy and offline model requirements.
- Data governance, retention, identity, and multi-user model.
- Boundaries between core platform and future OS/language/compiler/database/model research.
- Future physical hardware integration and safety certification.
- Initial CAD kernel, native file formats, solver stack and simulation tools.
- First discipline modules and their validation datasets.
- Applicable standards, jurisdictions and reviewer qualifications by engineering domain.
- Unresolved phrase from earlier discussion: “ยังเก็บคำสั่งไม่หนดครับ” — preserved verbatim; meaning requires owner clarification.
