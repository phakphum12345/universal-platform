# Generalized Coordinate and Joint Parameterization Contract

**Status:** Implemented schema v1.2 structural contract. PR #33 adds generated six-component pose-consistency residuals for all eight declared joint kinds; PR #34 adds finite-difference Jacobians; PR #37 adds SPATIAL local mobility analysis for supplied configurations. PR #54 adds missing all-family Jacobian/mobility reference coverage. General time derivatives and a general mechanism solver remain unimplemented.

## Purpose

Give every independent mechanism degree of freedom a stable identity, explicit physical kind/unit, local axis, bounds and numerical scale. Map those generalized coordinates to a specific normalized joint in a deterministic order. This is a model/schema contract used by the generated joint residual and finite-difference Jacobian layers. It does not imply a general global mechanism solver or physical feasibility.

## Records

- GeneralizedCoordinate: stable coordinate_id, ROTATIONAL or TRANSLATIONAL kind, unit (rad or m), normalized axis in the associated joint frame, optional finite ordered limits and positive characteristic scale.
- JointCoordinateParameterization: stable joint_id, ordered coordinate IDs, and joint-family-specific metadata.
- MechanismModel generalized_coordinates and joint_parameterizations: immutable tuples appended to the model record.
- ModelValidationResult joints_without_parameterization: explicit coverage gaps for non-fixed joints; omission is not silently treated as zero DOF.

## Joint coordinate ordering

| Joint kind | Ordered coordinate kinds | Additional rule |
|---|---|---|
| FIXED | none | Must not declare coordinates |
| REVOLUTE | ROTATIONAL | Coordinate axis aligns with declared joint axis |
| PRISMATIC | TRANSLATIONAL | Coordinate axis aligns with declared joint axis |
| CYLINDRICAL | ROTATIONAL, TRANSLATIONAL | Both axes align with joint axis |
| HELICAL | ROTATIONAL | Requires finite non-zero pitch in m/rad |
| SPHERICAL | ROTATIONAL × 3 | Requires explicit supported Euler convention |
| PLANAR | TRANSLATIONAL, TRANSLATIONAL, ROTATIONAL | Axes form a right-handed orthonormal basis |
| UNIVERSAL | ROTATIONAL × 2 | Axes must not be parallel |

Spherical conventions: EULER_INTRINSIC_XYZ, EULER_INTRINSIC_ZYX, EULER_EXTRINSIC_XYZ and EULER_EXTRINSIC_ZYX. The generated joint residual builder applies the declared sequence when composing spherical-joint orientation. Euler singularities are not removed; no quaternion parameterization is claimed.

## Validation and determinism

- Coordinate IDs and parameterization joint IDs are non-empty and unique.
- Every coordinate has exactly one owning joint parameterization; unknown, duplicate, reused and orphan coordinates fail validation.
- Coordinate kind, unit, axis normalization, finite limits and positive finite scale are checked.
- Parameterization arity and ordered coordinate kinds must match the declared joint family.
- Joint-axis alignment, universal-axis non-parallelism, planar basis handedness and helical pitch are checked.
- Coordinate and parameterization snapshots are deterministic and JSON-compatible.
- Existing topology-only models remain valid without parameterizations; their missing coverage is reported.

## Versioning and compatibility

- Schema v1.0 and v1.1 remain readable with existing placement compatibility rules.
- Schema v1.2 is the default and is required when generalized coordinates or joint parameterizations are present.
- Existing JointModel fields and constructors remain available. Legacy coordinate_unit and scalar limits are not silently expanded into generalized-coordinate records.
- No migration is forced: callers can add v1.2 coordinate records explicitly while retaining stable model/link/joint IDs.

## Explicit non-goals

- No symbolic differentiation, exact analytic Jacobian or general time-derivative engine.
- No general global configuration search, branch discovery, arbitrary loop solver or uniqueness proof.
- No dynamics, contact/collision, physical feasibility, machine control or certification.
- Coordinate scales are normalization metadata, not a claim of a well-conditioned system.
