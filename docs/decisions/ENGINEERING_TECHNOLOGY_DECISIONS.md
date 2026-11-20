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
| TECH-010 | Existing Driver Generation adapter | PARTIAL: `research_os_efi_platform` contains EFI/OpenCore Kext selection and candidate generation; generic Driver Generation remains UNKNOWN |

## Evaluation record template

For every candidate, record name and version, official source, license and dependency licenses, supported platforms, offline behavior, required capabilities, unsupported capabilities, API and automation support, data formats, benchmark/reference-case results, numerical tolerances, resource measurements, security review, maintenance status, decision (SELECT/REJECT/DEFER/EXPERIMENT), reviewer and date.

## Approval gate

No candidate becomes a platform dependency until its license and security have been reviewed, the relevant reference cases have been executed, limitations are documented, and the owner has approved the decision. All selected tools must remain behind replaceable adapters where practical.

## External source audit — `research_os_efi_platform`

Targeted source inspection found an Apache-2.0 licensed repository with read-only Windows/Linux/macOS hardware discovery, normalized hardware snapshots, deterministic identity hashes, OS-specific observation adapters, and an EFI/OpenCore candidate pipeline. The EFI pipeline's `resolve_kexts(profile)` selects a small set of macOS kext names based on evidence flags; it does not demonstrate compiling, packaging, signing, installing, or generating arbitrary drivers for other operating systems/devices. The config generator itself describes its output as a schema-safe starting point, not proof of bootability.

**Decision:** classify as `REUSE-CANDIDATE` for hardware discovery, identity/normalization and EFI-specific research. Keep the universal Driver Generation capability `UNKNOWN` until its intended scope and canonical source are confirmed. No dependency adoption or code copying is approved by this record. Before adapter implementation, pin repository HEAD, enumerate the full tree, execute tests, inspect dependency/license/security posture, and define versioned input/output contracts.


## Binary STL interchange evaluation candidate — PR #73

The staged interchange contract proposes dependency-free binary STL export paired with a required JSON sidecar. STL itself cannot preserve units, coordinate frames, source identity or chordal tolerance, so these remain explicit manifest fields and caller-verified context. IEEE-754 binary32 quantization, exact byte digest, facet limits and an independent test-only reader are required.

**Decision:** PR #73 contract merged; PR #74 implements dependency-free binary STL export behind the platform mesh API. No external STL importer, CAD application or library has been selected. TECH-002 remains OPEN. An external reopen tool must be evaluated for license, offline operation, supported platforms, deterministic import/export behavior and independent geometry comparison before it can be used as interoperability evidence. STEP remains gated on TECH-001 CAD-kernel evaluation.
