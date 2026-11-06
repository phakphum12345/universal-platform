# Engineering Data Model

**Status:** PROPOSED conceptual schema

## 1. Core entities

Project; Requirement; EngineeringCase; Discipline; KnowledgeModule; SourceArtifact; Quantity; Unit; CoordinateFrame; Parameter; Constraint; Equation/Model; Solver; SimulationRun; CADModel; Part; Assembly; Joint; Material; LoadCase; Result; VerificationCheck; EvidenceRecord; Risk; ReviewDecision; and ManufacturingArtifact.

## 2. Identity and revision

Every durable entity has a stable identifier, schema version, revision, created/updated metadata and provenance. CAD parts and assemblies use explicit revision relationships. A changed input invalidates dependent results according to a declared dependency graph.

## 3. Quantity representation

Store value, unit, dimension, uncertainty, source, coordinate frame if relevant, semantic role and transformation lineage. Avoid storing unit-bearing values as untyped strings.

## 4. Source and evidence

Source artifacts include origin, author/publisher, license, revision, date, content hash, location within source and retrieval method. Evidence records include procedure, expected criterion, actual result, status, environment, tool versions, logs and reviewer.

## 5. Relationships

EngineeringCase links requirements, selected disciplines, modules, models, constraints, CAD revisions, simulation runs and evidence. Derived quantities link to all input quantities and transformations. Assemblies link occurrences to part revisions and joints.

## 6. Data governance

Support export, retention policy, access control, data classification and deletion rules. Proprietary or personal data must not be ingested into external services without explicit authorization.

## 7. Acceptance criteria

- [ ] Entity identities and revisions are stable.
- [ ] Units and coordinate frames are typed.
- [ ] Provenance survives transformations.
- [ ] Dependencies support invalidation of stale results.
- [ ] Evidence is linked to exact artifacts and tool versions.


## Implemented coordinate-frame interchange

The v1.0 coordinate-frame graph snapshot stores sorted stable frame IDs and sorted rigid-transform edges. Each transform carries an explicit length unit. The current graph contract requires one common length unit per graph; mixed-unit transforms must be converted before insertion.


## Quantity interchange

The implemented Quantity v1.0 snapshot contains SI base value, a five-integer dimensional signature and original source unit. This preserves dimensional identity and source-unit lineage in JSON data exchange. The current unit catalogue is limited and does not represent arbitrary user-defined units.


## Frame-bound coordinate values

FramedPoint3 and FramedVector3 preserve frame identity and length units through JSON exchange. Transformations require a connected FrameGraph and matching graph/value units. Point/vector semantics are separate: only points receive translation.
