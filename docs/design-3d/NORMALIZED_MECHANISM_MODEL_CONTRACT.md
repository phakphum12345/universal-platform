# Normalized Mechanism Model Contract

**Status:** Implemented schema and structural validator; general solver integration remains out of scope.

## Purpose

Provide a common, versioned data vocabulary for mechanism links, joints, coordinate frames and geometry references. Stable identifiers connect the records without embedding solver-specific state in the model.

## Records

- `MechanismModel`: model ID, revision, schema version and ordered link/joint/frame/geometry collections.
- `LinkModel`: stable link ID, part revision, body frame ID and geometry IDs.
- `JointModel`: stable joint ID, joint kind, parent/child link IDs, joint frame, optional axis and scalar coordinate limits.
- `FrameReference`: frame ID, optional parent frame and optional owning link.
- `GeometryReference`: geometry ID, owning link, frame and kind (analytic, mesh, CAD reference or external).

Joint kinds in schema v1.0: FIXED, REVOLUTE, PRISMATIC, CYLINDRICAL, HELICAL, SPHERICAL, PLANAR and UNIVERSAL. Nominal relative DOF is metadata only. Rotational scalar coordinates use radians and translational scalar coordinates use metres. Coupled/mixed-coordinate conventions are not inferred.

## Validation guarantees

The validator checks non-empty and unique stable IDs, dangling link/frame/geometry references, self-joints, frame-parent cycles, axis finiteness and normalization, finite/ordered limits, supported schema version and selected coordinate-unit consistency.

## Explicit non-guarantees

- Schema support is not solver support. Every normalized joint currently reports `SCHEMA_ONLY`.
- Existing planar four-bar adapter remains a separate narrow API; this PR does not automatically convert arbitrary MechanismModel instances into solver inputs.
- No arbitrary-topology loop closure, spatial solver, mobility proof, collision/contact, dynamics, CAD-kernel integration, physical feasibility or safety certification is added.
- The nominal joint DOF count is not assembled mechanism mobility and says nothing about singularity.

## Compatibility

Existing `Assembly`, `Joint`, frame graph and planar 4R adapter APIs remain unchanged. The normalized model is additive and versioned at schema `1.0`.
