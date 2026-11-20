# 3D Motion and Mechanism Reference Cases

**Status:** Assembly/joint contracts and a limited rooted-tree forward-kinematics adapter are implemented. No general constraint or mechanism solver is implemented.

## Purpose
Define deterministic fixtures for assembly joints, degrees of freedom, motion limits and mechanism validation.

## Case definitions
| ID | Fixture | Expected contract |
|---|---|---|
| MOT-001 | Two rigid bodies connected by a fixed joint | Relative nominal DOF = 0 |
| MOT-002 | Two rigid bodies connected by an ideal revolute joint | Relative nominal DOF = 1; normalized rotation axis and limits explicit |
| MOT-003 | Two rigid bodies connected by an ideal prismatic joint | Relative nominal DOF = 1; normalized translation axis and limits explicit |
| MOT-004 | Two rigid bodies connected by an ideal cylindrical joint | Relative nominal DOF = 2; data contract only, not solved by current kinematics adapter |
| MOT-005 | Joint references unknown occurrence | Validation FAIL |
| MOT-006 | Lower limit exceeds upper limit | Validation FAIL |
| MOT-007 | Revolute/prismatic/cylindrical joint lacks required axis | Validation FAIL |
| MOT-008 | Requested position outside declared limits | Forward-kinematics evaluation FAIL |
| MOT-009 | Mechanism has redundant/conflicting constraints | Solver must report over-constraint or UNKNOWN; no silent relaxation |
| MOT-010 | Collision/clearance capability unavailable | SKIPPED or UNKNOWN, never PASS |
| MOT-011 | Duplicate occurrence or joint identifiers | Assembly validation FAIL |
| MOT-012 | Empty assembly, occurrence, part or revision identity | Assembly validation FAIL |
| MOT-013 | Zero-length or non-unit joint axis | Assembly validation FAIL |
| MOT-014 | Non-finite or inverted joint limits | Assembly validation FAIL |
| MOT-015 | Fixed joint in a rooted tree | Child-to-root pose preserves static placement |
| MOT-016 | Revolute joint at a requested angle | Child-to-root pose rotates around declared axis; angle is radians |
| MOT-017 | Prismatic joint at a requested displacement | Child-to-root pose translates along declared axis; value uses model length unit |
| MOT-018 | Tree contains an occurrence with no parent path to root | Evaluation FAIL |
| MOT-019 | Root occurrence is also a joint child | Evaluation FAIL |
| MOT-020 | Placement frames do not match joint endpoints | Evaluation FAIL |
| MOT-021 | Cylindrical, spherical or planar joint requested from current adapter | Explicit unsupported-type FAIL; never approximated silently |

## Implemented contract behavior
`Assembly.validate()` checks non-empty assembly/occurrence/joint identity, duplicate occurrence and joint IDs, part/revision metadata, known parent/child occurrences, self-joints, supported joint types, required axes, unit-length axes and finite/ordered limits.

`nominal_joint_dof` remains a simple sum of declared joint DOFs. It is not the mobility of a constrained mechanism and does not account for closed loops, redundant constraints, grounding, singularities or dependent constraints. Joint axis vectors are interpreted in the parent occurrence's local frame.

`FrameGraph` provides a forest of rigid coordinate frames with one parent per child, cycle rejection, reverse traversal and transform path resolution between connected frames.

`solve_tree_forward_kinematics()` evaluates fixed, revolute and prismatic joints in a connected rooted tree. Joint placements are explicit; revolute coordinates are radians and prismatic coordinates use the model length unit. The result maps each occurrence frame into the selected root frame. Missing placements, topology errors, frame mismatches, unsupported joint types and limit violations fail explicitly.

## Required motion evidence
Record part and assembly revisions, joint definitions, coordinate frames, units, input motion profile, solver/version, initial conditions, limits, numerical health, outputs and limitations.

## Explicit limitations
No inverse kinematics, closed-loop constraint solving, mobility analysis, dynamics, friction, backlash, flexible-body analysis, collision detection, contact, tolerance stack-up or automatic joint-frame inference is implemented. The tree adapter does not guarantee physically realizable motion.

## Acceptance
- Joint types and DOF conventions are versioned.
- Limits and normalized axes are explicit.
- Unsupported collision, dynamics, friction, backlash or flexible-body effects remain UNKNOWN/SKIPPED.
- Test results are tied to exact fixtures and software revisions.
