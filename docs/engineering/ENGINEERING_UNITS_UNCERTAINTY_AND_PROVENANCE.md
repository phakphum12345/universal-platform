# Engineering Units, Uncertainty, and Provenance

**Status:** PROPOSED cross-cutting contract

## 1. Units and dimensions

Use explicit quantities with magnitude, unit, dimension and source. Preserve original source units and show conversions. Reject dimensionally invalid equations. Support SI as the preferred internal basis while allowing domain-specific units where required. Unit conversions must be versioned and tested.

## 2. Coordinate systems

Every geometric or vector quantity declares coordinate frame, origin, orientation, handedness and unit. Transformations must identify source and destination frames. Do not combine values from unrelated frames without a valid transform.

## 3. Uncertainty classes

Distinguish measurement uncertainty, source tolerance, manufacturing tolerance, numerical error, model-form uncertainty, estimation uncertainty and unknown uncertainty. Do not collapse these into one unexplained confidence score.

## 4. Propagation and sensitivity

Use an appropriate method: analytical propagation, interval arithmetic, Monte Carlo, sensitivity derivatives or domain-specific methods. State distribution assumptions, correlations, sample count and convergence where applicable. Report dominant contributors.

## 5. Provenance

Each input and derived value records source, revision/date, location (page/section/table/object), extraction method, transformation history, confidence and reviewer state. Derived values retain lineage to all material inputs.

## 6. Evidence types

FACT, INFERENCE, ASSUMPTION, HYPOTHESIS, ESTIMATE, SIMULATION, MEASUREMENT and UNKNOWN must remain distinct. A simulation is not a physical measurement; a datasheet typical value is not a guaranteed limit.

## 7. Acceptance criteria

- [ ] Every engineering quantity has a unit and dimension.
- [ ] Coordinate frames are explicit where relevant.
- [ ] Source values preserve revision and location.
- [ ] Uncertainty type and method are declared.
- [ ] Derived quantities retain lineage.
- [ ] Unsupported precision is not displayed.


## Implemented evidence record and gate subset (PR #42)

SourceRef and EvidenceRecord are immutable, validated and JSON-serializable. Content hashes use SHA-256; evidence timestamps must be timezone-aware ISO-8601; nested metadata is detached/frozen and rejects non-finite or non-JSON values.

The conservative evidence gate treats all supplied records as required and uses FAIL > UNKNOWN > SKIPPED > PASS precedence. An empty evidence set is UNKNOWN. This is software evidence aggregation only, not engineering certification or physical validation.


## Implemented coordinate-frame exchange subset (PR #43)

RigidTransform and FrameGraph provide deterministic v1.0 serialization with explicit length units. A FrameGraph currently enforces one length unit across all edges; it does not perform implicit mixed-unit conversion. This does not replace typed uncertainty propagation or full frame-aware quantity algebra.
