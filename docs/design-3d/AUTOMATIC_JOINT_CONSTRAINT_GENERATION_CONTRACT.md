# Automatic Joint Constraint Generation Contract

**Status:** Implemented candidate in PR #33; merge and exact-SHA CI evidence pending.

## Purpose and boundary

Generate deterministic geometric pose-consistency residuals from the normalized mechanism schema, explicit joint placements, generalized-coordinate parameterizations and caller-supplied rigid body poses. The generator is offline and non-actuating. It does not infer geometry or silently invent missing placements.

## Inputs

- A structurally valid MechanismModel.
- One body-to-world RigidTransform per link. Each transform source must equal the link body frame and all transforms must target the same world frame.
- One finite value per generalized coordinate, keyed by stable coordinate ID.
- Explicit JointFramePlacement records for every joint.
- Explicit JointCoordinateParameterization records for every non-fixed joint.

## Frame convention

The body poses map link-body coordinates into one shared world frame. The parent-side joint pose is resolved through inverse(parent_to_joint) then parent-body-to-world. The child-side joint pose is resolved through joint_to_child then child-body-to-world. The relative transform is child-joint-to-parent-joint and is compared with the declared coordinate-driven joint motion.

All placement translations and translational residuals are metres. Rotational coordinates and rotation-log residuals are radians. No implicit unit conversion occurs.

## Generated residuals

Each joint produces six stable-ID residuals in fixed order:
- translation_x, translation_y, translation_z (m)
- rotation_x, rotation_y, rotation_z (rad)

The expected relative motion is generated from the parameterization:
- FIXED: identity
- REVOLUTE / PRISMATIC: one axis rotation / translation
- CYLINDRICAL: independent rotation and translation along the declared axis
- HELICAL: axis rotation coupled to translation by pitch in m/rad
- SPHERICAL: three ordered rotations with an explicit supported Euler convention
- PLANAR: two in-plane translations and one normal-axis rotation
- UNIVERSAL: ordered two-axis rotation sequence

A six-component pose comparison is a residual representation, not a claim that every component is an independent scalar constraint or that the mechanism has six fewer DOF. The coordinate variables remain explicit inputs.

## Validation and failure behavior

- Invalid mechanism models fail before generation.
- Missing placement on any joint or missing parameterization on any non-fixed joint fails closed.
- Pose and coordinate maps must cover exactly the model link and coordinate IDs.
- Body pose frame IDs and shared world target must be consistent.
- Non-finite coordinate values and non-positive tolerances are rejected.
- Residuals retain stable IDs, units, tolerances, values and PASS/FAIL status.

## Limitations

- No automatic Jacobian, derivative bias, solver variable construction or loop branch discovery.
- No collision/contact, dynamics, force/torque, structural analysis, physical feasibility or certification.
- Caller-supplied body poses and generalized coordinates are not discovered or simulated by this generator.
