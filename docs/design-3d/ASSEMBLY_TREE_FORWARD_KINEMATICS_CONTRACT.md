# Assembly Tree Forward-Kinematics Contract

**Status:** Deterministic tree-only forward kinematics is an initial executable adapter. It is not a general mechanism solver.

## Inputs
- A validated Assembly with unique occurrence and joint identifiers.
- One root occurrence.
- Exactly one JointPlacement for every joint.
- Optional scalar coordinates keyed by joint ID; omitted coordinates default to zero.
- Joint axis vectors are expressed in the parent occurrence frame, consistent with the assembly contract.

Each JointPlacement contains:
- parent_to_joint: transform from the parent occurrence frame into a joint-local frame.
- joint_to_child: transform from that same joint-local frame into the child occurrence frame.

## Supported motion
| Joint type | Coordinate | Behavior |
|---|---|---|
| FIXED | omitted or zero | No relative motion |
| REVOLUTE | radians | Right-handed rotation about the declared axis |
| PRISMATIC | model length unit | Translation along the declared axis |

Other declared joint types (CYLINDRICAL, SPHERICAL and PLANAR) remain unsupported by this adapter and fail explicitly.

## Output convention
The result maps each occurrence frame into the selected root occurrence frame. The root pose is identity. A revolute coordinate is in radians; a prismatic coordinate uses the model length unit. Joint lower and upper limits are enforced before calculating the pose.

## Topology and fail-closed behavior
- Exactly one root is selected by the caller; the root cannot have a parent joint.
- Every other occurrence must have exactly one parent joint and be reachable from the root.
- Missing/extra placements, unknown coordinate keys, invalid transform frame names, multiple parents, cycles, disconnected occurrences, unsupported joint types, non-finite coordinates and limit violations raise InvalidModelError.
- No implicit unit conversion or coordinate inference is performed.

## Reference cases
- Fixed link preserves the static child pose.
- Revolute link rotates a basis vector by the requested angle around the declared axis.
- Prismatic link translates the child pose by the requested displacement.
- Joint limits reject out-of-range coordinates.
- Frame mismatches, disconnected parts and cyclic topology fail closed.
- Unsupported joint types are not silently approximated.

## Explicit limitations
This is forward evaluation of a rooted tree only. It does not solve inverse kinematics, closed-loop closure, over/under-constraint, mobility, redundant constraints, dynamics, acceleration, torque, friction, backlash, compliance, singularity handling, collision, tolerance stack-up, contact or flexible bodies. It does not establish physical feasibility or manufacturing readiness.

## Acceptance evidence
Every run should record assembly revision, occurrence and joint IDs, root occurrence, joint placements, input coordinates and units, software revision, returned poses, validation errors and unsupported effects. Tests validate only this adapter and its declared inputs.