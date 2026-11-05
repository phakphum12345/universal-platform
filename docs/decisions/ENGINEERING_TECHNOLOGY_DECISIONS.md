# Engineering Technology Decisions

Status: OPEN. No CAD kernel, solver, schema, database, or vendor has been selected.

## Decision rules

Evaluate each candidate against the approved first workflow. Record the exact version, official source, license, cost, offline behavior, supported operating systems, automation API, import/export formats, validation evidence, security, resource use, maintenance outlook, and replacement path.

Prefer local-first, portable, documented, replaceable, free or open tools when they meet the requirements. Do not adopt a paid or hosted dependency without an explicit cost and benefit review and owner approval.

## Open decisions

| ID | Decision | Status |
|---|---|---|
| TECH-001 | CAD application and geometry kernel | OPEN |
| TECH-002 | CAD interchange formats and round-trip requirements | OPEN |
| TECH-003 | Solver stack for each discipline | OPEN |
| TECH-004 | Module manifest and schema format | OPEN |
| TECH-005 | Engineering data persistence | OPEN |
| TECH-006 | Evidence record and artifact storage | OPEN |
| TECH-007 | Supported operating systems and minimum hardware | OPEN |
| TECH-008 | Local runtime and isolation strategy | OPEN |
| TECH-009 | Authoritative standards and material data sources | OPEN |
| TECH-010 | Existing Driver Generation adapter | BLOCKED: canonical source location unknown |

## Evaluation record template

For every candidate, record name and version, official source, license and dependency licenses, supported platforms, offline behavior, required capabilities, unsupported capabilities, API and automation support, data formats, benchmark/reference-case results, numerical tolerances, resource measurements, security review, maintenance status, decision (SELECT/REJECT/DEFER/EXPERIMENT), reviewer and date.

## Approval gate

No candidate becomes a platform dependency until its license and security have been reviewed, the relevant reference cases have been executed, limitations are documented, and the owner has approved the decision. All selected tools must remain behind replaceable adapters where practical.
