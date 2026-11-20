# Electrical Rule Checking Contract

**Status:** Static ERC ruleset v1.0 implementation candidate (PR #60). This is conservative offline design linting, not a circuit simulator, standards-compliance engine, or safety certification.

## 1. Purpose and inputs

The checker consumes a validated SchematicModel v1.0. It does not modify the source model. All results are deterministic for equivalent normalized inputs and include a SHA-256 digest of the canonical model snapshot.

## 2. Versioned rules

| Rule | Severity | Condition | Interpretation |
|---|---|---|---|
| ERC-PIN-001 | WARNING | A declared pin is absent from every net and is not typed NO_CONNECT | Review whether it is intentionally unused |
| ERC-NET-001 | ERROR | More than one OUTPUT pin is assigned to a net | Potential push-pull driver contention |
| ERC-NET-002 | ERROR | More than one POWER_OUT pin is assigned to a net | Potentially paralleled power sources |
| ERC-NET-003 | WARNING | A net has POWER_IN pins but no POWER_OUT pin | Source may be off-sheet, implicit, or absent |
| ERC-NET-004 | ERROR | A net combines POWER_IN with signal-driver types | Likely pin classification or connectivity conflict |
| ERC-NET-005 | WARNING | A net has OPEN_DRAIN/OPEN_COLLECTOR pins but no POWER_OUT pin | Pull-up path is not represented as a declared power source |

All rules are version 1.0. Findings have stable IDs derived from rule ID and sorted object references. Finding order is deterministic.

## 3. Result contract

ElectricalRuleCheckResult schema v1.0 records:
- ruleset version and canonical input SHA-256;
- PASS or FAIL status;
- evaluated and skipped rule IDs;
- deterministic findings with severity, affected object references, evidence and recommendations;
- a severity summary and explicit limitations.

PASS means only that this ruleset found no modeled violations. WARNING findings still produce an overall FAIL so they cannot be mistaken for a clean design. No unsupported rule is silently reported as passed.

## 4. Deliberate limits

The v1.0 model has no declared voltage domains, current limits, logic thresholds, net classes, passive pull-up semantics, datasheet provenance, standards profile, or approved-waiver ledger. Therefore this ruleset does not infer:
- voltage/logic-level compatibility or absolute maximum ratings;
- current, power, thermal, timing, impedance, sequencing or decoupling compliance;
- whether multiple supplies are safe to parallel;
- whether a passive pull-up exists or has the correct value;
- whether a schematic matches a manufactured board.

Such checks require explicit versioned inputs and authoritative source evidence. Missing data must remain UNKNOWN/SKIPPED in later extensions, not be treated as PASS.

## 5. Safety boundary

The checker is pure offline analysis. It performs no EDA import, network access, simulation, device communication, power switching, GPIO access, firmware writes, physical probing, manufacturing release, certification or safety approval.
