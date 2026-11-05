# 3D Motion and Mechanism Reference Cases

**Status:** Partially implemented assembly/joint data contract; no general kinematics solver is implemented.

## Purpose
Define deterministic fixtures for assembly joints, degrees of freedom, motion limits and mechanism validation before selecting a solver.

## Case definitions
| ID | Fixture | Expected contract |
|---|---|---|
| MOT-001 | Two rigid bodies connected by a fixed joint | Relative nominal DOF = 0 |
| MOT-002 | Two rigid bodies connected by an ideal revolute joint | Relative nominal DOF = 1; normalized rotation axis and limits explicit |
| MOT-003 | Two rigid bodies connected by an ideal prismatic joint | Relative nominal DOF = 1; normalized translation axis and limits explicit |
| MOT-004 | Two rigid bodies connected by an ideal cylindrical joint | Relative nominal DOF = 2 where the selected convention defines rotation plus translation on one axis |
| MOT-005 | Joint references unknown occurrence | Validation FAIL |
| MOT-006 | Lower limit exceeds upper limit | Validation FAIL |
| MOT-007 | Revolute/prismatic/cylindrical joint lacks required axis | Validation FAIL |
| MOT-008 | Requested position outside declared limits | Motion check FAIL |
| MOT-009 | Mechanism has redundant/conflicting constraints | Solver must report over-constraint or UNKNOWN; no silent relaxation |
| MOT-010 | Collision/clearance capability unavailable | SKIPPED or UNKNOWN, never PASS |
| MOT-011 | Duplicate occurrence or joint identifiers | Assembly validation FAIL |
| MOT-012 | Empty assembly, occurrence, part or revision identity | Assembly validation FAIL |
| MOT-013 | Zero-length or non-unit joint axis | Assembly validation FAIL |
| MOT-014 | Non-finite or inverted joint limits | Assembly validation FAIL |

## Implemented contract behavior
`Assembly.validate()` checks non-empty assembly/occurrence/joint identity, duplicate occurrence and joint IDs, part/revision metadata, known parent/child occurrences, self-joints, supported joint types, required axes, unit-length axes and finite/ordered limits.

`nominal_joint_dof` remains a simple sum of the declared joint DOFs. It is not the mobility of a constrained mechanism and does not account for closed loops, redundant constraints, grounding, singularities or dependent constraints. Axis vectors are normalized and interpreted in the parent occurrence's local frame by convention.

## Required motion evidence
Record part and assembly revisions, joint definitions, coordinate frames, units, input motion profile, solver/version, initial conditions, limits, convergence/numerical health, collision model fidelity, outputs and limitations.

## Explicit limitations
These fixtures define expected data-contract behavior. They do not define a complete spatial constraint solver or guarantee physically realizable motion. No frame graph, automatic joint-frame placement, inverse kinematics, dynamics, friction, backlash, flexible-body analysis or collision detection is implemented.

## Acceptance
- Joint types and DOF conventions are versioned.
- Limits and normalized axes are explicit.
- Unsupported collision, dynamics, friction, backlash or flexible-body effects remain UNKNOWN/SKIPPED.
- Test results are tied to exact fixtures and solver versions.
