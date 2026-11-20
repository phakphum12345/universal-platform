# Engineering Hazard Register

**Status:** PROPOSED starter register; project-specific risk assessment is mandatory.

## Purpose
Identify recurring hazards across engineering analysis, 3D design, simulation and manufacturing preparation. This register is not a complete hazard analysis or safety certification.

## Starter hazards
| ID | Hazard | Example cause | Minimum control / evidence |
|---|---|---|---|
| HAZ-001 | Incorrect physical input | Wrong units, stale datasheet, transcription error | Source lineage, unit validation, independent input review |
| HAZ-002 | Model invalidity | Assumptions outside validity range | Validity declaration, sensitivity, UNKNOWN outside range |
| HAZ-003 | Numerical failure | Singular/ill-conditioned system, non-convergence | Residual/conditioning checks, solver diagnostics |
| HAZ-004 | Geometry/interchange defect | Scale, orientation, topology loss | Independent reopen and geometric comparison |
| HAZ-005 | Material misuse | Typical value treated as guaranteed allowable | Source type, temperature/range, qualified review |
| HAZ-006 | Electrical incompatibility | Voltage/current/timing mismatch | Datasheet limits, margin checks, no physical energization |
| HAZ-007 | Structural failure | Incorrect loads, boundary conditions or code basis | Qualified professional review and jurisdiction-specific standards |
| HAZ-008 | Manufacturing injury/damage | Unreviewed machine/tooling file | Human release gate; no automatic machine execution |
| HAZ-009 | Physical actuation | Generated workflow reaches hardware controls | No physical-control adapter in initial scope; deny by default |
| HAZ-010 | Supply-chain/security | Malicious CAD/plugin/solver/dependency | Provenance, license/security review, sandbox and least privilege |
| HAZ-011 | Data disclosure | Proprietary drawings/datasheets sent externally | Data classification, minimization and explicit external-sharing approval |
| HAZ-012 | False assurance | SKIPPED/UNKNOWN or simulation presented as PASS/measurement | Evidence semantics, exact SHA, audit and independent review |

## Project hazard assessment
For each use case record intended use, affected people/assets, foreseeable misuse, severity, likelihood, exposure, detectability, safeguards, residual risk, owner, reviewer, approval and reassessment trigger. Select an established risk method appropriate to the domain; do not invent numeric risk scores without a defined scale.

## Release gate
Tier 2/3 outputs require appropriate independent qualified review. Tier 4 physical execution, procurement, fabrication release or deployment requires a separate scoped authorization and execution system. Initial platform scope remains offline analysis/simulation.

## Acceptance
Hazards map to requirements and tests; controls have owners and evidence; residual risks remain visible; changes trigger reassessment.
