# UEIC and 3D Engineering — Vertical Slice Specification

**Status:** PROPOSED candidate; owner selection required  
**Implementation:** NOT STARTED / NOT VERIFIED  
**Safety tier:** Draft design and offline simulation only  
**Depends on:** Full source inventory, architecture and technology decisions

## 1. Purpose

Prove the smallest end-to-end workflow that exercises the shared UEIC layer and a 3D design capability without attempting to implement every discipline or a full CAD suite at once.

## 2. Candidate workflow

**Candidate:** Design and verify an adjustable mechanical fixture with a simple moving clamp or pivoting arm.

This is a test candidate, not an owner-approved final product requirement. It is chosen because it can exercise:
- Requirements intake and explicit assumptions.
- Parametric geometry and editable CAD.
- Parts, assembly hierarchy and joints.
- Basic kinematics and motion envelope.
- Static load and torque calculations.
- Material property lookup with source lineage.
- Dimensional analysis and uncertainty.
- Basic manufacturing constraints and BOM.
- Geometry and independent output validation.

A simpler static bracket may be substituted if the candidate mechanism requires unavailable CAD/solver capabilities.

## 3. Inputs

- Functional description and intended use.
- Reference dimensions and interfaces.
- Load case and operating envelope.
- Material candidates and authoritative property sources.
- Manufacturing process preference or explicitly OPEN process.
- Tolerance and fit requirements.
- CAD/solver tool availability and versions.
- Safety classification and prohibited uses.

Missing critical inputs must be requested or explicitly modeled as assumptions with sensitivity analysis. They must not be invented as facts.

## 4. Workflow

1. Create a versioned EngineeringCase from requirements.
2. Identify applicable disciplines and explain module selection.
3. Normalize quantities, units and coordinate frames.
4. Build a dependency/constraint graph.
5. Create parametric parts and assembly relationships.
6. Calculate basic loads, force, torque and kinematics using a declared model.
7. Compare candidate materials using cited data and stated validity ranges.
8. Check geometry, joints, motion, interference and clearances.
9. Evaluate process constraints and prepare a draft BOM.
10. Export a neutral CAD artifact if supported.
11. Reopen the export independently and compare geometry, scale and units.
12. Produce an evidence package and human-review report.

## 5. Expected artifacts

- Requirements and assumptions record.
- EngineeringCase and variable dictionary.
- Discipline/module selection explanation.
- Parametric CAD source project.
- Part and assembly manifest.
- Calculation/model records.
- Solver logs and numerical checks, if a solver is used.
- Geometry/assembly validation report.
- BOM and draft manufacturing notes.
- Export file and independent reopen report.
- Evidence manifest tied to exact source/model/tool versions.

## 6. Acceptance criteria

- [ ] Every requirement maps to one or more model parameters or explicit unresolved items.
- [ ] Units and coordinate frames are validated.
- [ ] Every calculation records equations, inputs, assumptions and sources.
- [ ] Every CAD artifact has a revision and reproducible inputs.
- [ ] Assembly joints and degrees of freedom are explicit.
- [ ] Motion and collision checks are executed or marked UNKNOWN/SKIPPED.
- [ ] Solver numerical health and validity are checked.
- [ ] Export is reopened independently; scale and orientation are checked.
- [ ] BOM reconciles with assembly occurrences.
- [ ] Critical unknowns and risks remain visible.
- [ ] No overall PASS while critical evidence is FAIL or UNKNOWN.
- [ ] No physical fabrication, purchase, actuation or machine operation occurs.

## 7. Non-goals

Full CFD, nonlinear fracture, fatigue life certification, advanced multiphysics, autonomous CAD feature planning, production-ready tooling, structural certification, physical prototyping and machine execution are outside this first slice unless separately approved.

## 8. Gate to implementation

Before code begins, the owner must approve:
- The selected vertical-slice object/use case.
- Required CAD and solver toolchain after comparison.
- The source repository and Driver Generation reuse boundary.
- Minimum target OS/platform.
- Test fixtures, acceptance tolerances and resource budget.

Until these are approved, this document remains a candidate specification.
