# Joint and Geometry Placement Contract

**Status:** Implemented schema contract in mechanism model v1.1. Automatic joint equations and Jacobians are not part of this change.

## Coordinate convention

Every placement stores a rigid transform using the existing convention:

`p_to = R_to_from p_from + t_to_from`

The transform source and destination frame IDs are explicit. Rotations must be proper right-handed orthonormal matrices, as enforced by `RigidTransform`. Translation components in these placement records are metres; coordinate conversion must happen before constructing the record. The schema does not infer or silently convert units.

## Records

- `JointFramePlacement`: one record per placed joint, containing `parent_to_joint` (parent link body frame → `JointModel.frame_id`) and `joint_to_child` (`JointModel.frame_id` → child link body frame).
- `GeometryPlacement`: one record per placed geometry, containing `geometry_to_frame` (geometry-local frame → `GeometryReference.frame_id`).
- Each record has a stable parent object ID and a deterministic `to_dict()` snapshot.
- `MechanismModel.joint_placements` and `geometry_placements` are optional tuples. Omission is preserved as missing placement coverage, not silently replaced with identity transforms.

## Schema compatibility

- Schema v1.0 remains accepted for existing topology-only models.
- Schema v1.1 is the default and supports the new optional placement records.
- v1.0 models containing placement records fail validation.
- Existing field order and prior constructors remain compatible; new collections are appended as optional fields.

## Validation

The structural validator checks unique placement IDs, known joint/geometry references, transform types, exact source/destination frame endpoints, local geometry frame ownership where declared, and metre translation units. It reports placement counts and explicit joint/geometry IDs that still lack placements.

## Explicit non-goals

- No automatic placement inference from CAD geometry, mesh, external references or topology.
- No automatic revolute/prismatic/fixed constraint equations or residual generation.
- No automatic Jacobian, velocity or acceleration bias generation.
- No spatial loop solver, contact/collision, dynamics, physical feasibility or safety certification.
- Geometry references remain metadata; this contract does not create a B-rep or CAD kernel.
