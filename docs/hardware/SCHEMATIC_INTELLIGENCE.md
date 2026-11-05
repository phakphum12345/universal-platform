# Schematic Intelligence

**Status:** PROPOSED  
**Requirement:** HWR-001  
**Implementation:** NOT IMPLEMENTED / NOT VERIFIED

## 1. Purpose

Specify a capability to interpret electronic schematics as structured engineering information. It should inventory components, pins, nets, connectivity, power domains, and interfaces, then provide reliable inputs to hardware/software mapping, driver analysis, compatibility review, and simulation.

This is a requirements proposal, not authorization to alter source designs or operate physical hardware.

## 2. Inputs and format support

Candidate inputs, subject to parser/version validation:
- Native EDA projects and schematics, with KiCad as a candidate first format.
- Netlists, BOM exports, PCB layout exports, and revision metadata.
- PDF, SVG, and raster diagrams as lower-confidence visual sources.
- Datasheets, component specifications, connector pinouts, and design notes.

Prefer native structured sources over visual extraction. OCR/vision-derived connectivity must be labelled uncertain and must not be treated as electrically authoritative without review.

## 3. Normalized design model

Represent at least:
- Design identity, revision, source files, EDA tool/version, and provenance.
- Components: reference designator, part number, value, manufacturer, symbol, footprint, attributes, and sheet/location.
- Pins: component reference, pin number/name, electrical type, and metadata.
- Nets: stable identifier, connected pins, labels, aliases, and net class.
- Connections: explicit pin-to-net relationships and source evidence.
- Power domains: rail name, polarity, nominal/min/max voltage when documented, and source.
- Interfaces: candidate protocol/bus with confidence and evidence.
- Revision changes: added, removed, renamed, or modified objects.

Unknown values remain unknown. Inferences require rationale and confidence.

## 4. Required capabilities

1. Parse project structure and source metadata.
2. Inventory components, pins, nets, and explicit connectivity.
3. Trace signals between documented source and destination pins.
4. Identify power/ground distribution from explicit labels and connections.
5. Flag unconnected pins, duplicate references, unresolved symbols, and incomplete metadata when detectable.
6. Compare revisions and report topology/component changes.
7. Cross-reference components with supplied datasheets and BOM entries.
8. Export normalized machine-readable data and human-readable reports.

## 5. Evidence and confidence

Every extracted fact records source file/revision, sheet and object reference, extraction method, confidence (HIGH/MEDIUM/LOW/UNKNOWN), and whether it is explicit, inferred, or manually confirmed.

A schematic parse does not prove that a physical board matches the schematic. Physical inspection and measurement are separate evidence classes.

## 6. Safety boundary

Initial phase is offline analysis only. No GPIO writes, bus transactions, register access, power switching, actuator operation, firmware flashing, or physical probing. Original EDA files are read-only; proposed edits must be separate reviewable artifacts.

## 7. Acceptance criteria

- [ ] Supported native schematics can be inventoried with provenance and revision.
- [ ] Components, pins, nets, and explicit connections can be exported.
- [ ] Signal paths include source references.
- [ ] Explicit facts are distinguished from inferred/visual facts.
- [ ] Unsupported formats and parser failures return UNKNOWN or SKIPPED, not success.
- [ ] Revision comparison identifies changed objects and preserves source revisions.
- [ ] Analysis does not modify original design files.
- [ ] No physical device operation is initiated.

## 8. Traceability and dependencies

Related: DEVICE_INTELLIGENCE.md, HARDWARE_TO_SOFTWARE_MAPPING.md, SCHEMATIC_DRIVER_TRACEABILITY.md, HARDWARE_DESIGN_VERIFICATION.md.

HWR-001 — Schematic interpretation and connectivity extraction (PROPOSED). Supports HR-007 through HR-011.

## 9. Open questions

- Which EDA formats and minimum versions are mandatory for the first milestone?
- Is KiCad the first native format?
- Which normalized schema/versioning policy should be adopted?
- What review promotes low-confidence visual extraction to confirmed engineering data?
