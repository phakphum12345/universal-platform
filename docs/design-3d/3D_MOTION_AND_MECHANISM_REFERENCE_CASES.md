# 3D Motion and Mechanism Reference Cases

**Status:** PROPOSED; no general kinematics solver is implemented by this specification.

## Purpose
Define deterministic fixtures for assembly joints, degrees of freedom, motion limits and mechanism validation before selecting a solver.

## Case definitions
| ID | Fixture | Expected contract |
|---|---|---|
| MOT-001 | Two rigid bodies connected by a fixed joint | Relative DOF = 0 |
| MOT-002 | Two rigid bodies connected by an ideal revolute joint | Relative DOF = 1; rotation axis and limits explicit |
| MOT-003 | Two rigid bodies connected by an ideal prismatic joint | Relative DOF = 1; translation axis and limits explicit |
| MOT-004 | Two rigid bodies connected by an ideal cylindrical joint | Relative DOF = 2 where the selected convention defines rotation plus translation on one axis |
| MOT-005 | Joint references unknown occurrence | Validation FAIL |
| MOT-006 | Lower limit exceeds upper limit | Validation FAIL |
| MOT-007 | Revolute/prismatic joint lacks required axis | Validation FAIL |
| MOT-008 | Requested position outside declared limits | Motion check FAIL |
| MOT-009 | Mechanism has redundant/conflicting constraints | Solver must report over-constraint or UNKNOWN; no silent relaxation |
| MOT-010 | Collision/clearance capability unavailable | SKIPPED or UNKNOWN, never PASS |

These fixtures define expected data-contract behavior. They do not define a complete spatial constraint solver or guarantee physically realizable motion.

## Required motion evidence
Record part and assembly revisions, joint definitions, coordinate frames, units, input motion profile, solver/version, initial conditions, limits, convergence/numerical health, collision model fidelity, outputs and limitations.

## Acceptance
- Joint types and DOF conventions are versioned.
- Limits and axes are explicit.
- Unsupported collision, dynamics, friction, backlash or flexible-body effects remain UNKNOWN/SKIPPED.
- Test results are tied to exact fixtures and solver versions.
