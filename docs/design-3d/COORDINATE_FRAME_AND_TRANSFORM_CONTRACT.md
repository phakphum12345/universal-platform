# Coordinate Frame and Transform Contract

**Status:** Implemented v1.0 serialization subset; mixed-unit frame graphs are not supported.

## 1. Conventions

A rigid transform maps coordinates from a source frame to a destination frame:

`x_to = R_to_from × x_from + t_to_from`.

The rotation is a proper right-handed orthonormal 3×3 matrix. Translation is expressed in the destination frame. Coordinates and translation use the explicitly declared `length_unit`.

## 2. RigidTransform v1.0

The JSON-compatible record contains:
- `schema_version`: exactly `1.0`.
- `from_frame` and `to_frame`: non-empty stable frame identifiers.
- `rotation`: immutable 3×3 numeric matrix; scale, shear, reflection and non-finite entries are rejected.
- `translation`: x/y/z values and an explicit length unit (m, mm, cm, km or in).

`to_dict()` emits the v1.0 snapshot. `from_dict()` rejects unknown/missing fields, unsupported versions and invalid values. Inverse transforms preserve units. Composition requires matching intermediate frame IDs and identical length units.

## 3. FrameGraph v1.0

A graph snapshot contains:
- `schema_version`: exactly `1.0`.
- `frames`: unique, non-empty frame IDs sorted lexicographically.
- `transforms`: parent-to-child RigidTransform records sorted by child frame ID.

The graph is a forest: each child has at most one parent; cycles and undeclared edge endpoints are rejected. Isolated frames are permitted. Serialization order is deterministic.

## 4. Unit policy and limitations

All transforms within one FrameGraph must use the same length unit. The graph does not perform implicit unit conversion or store per-frame unit systems. Convert translations and coordinate data explicitly before inserting mixed-unit transforms. Angular coordinates and general physical quantities use their own domain contracts.

This is a coordinate utility, not an assembly constraint solver, CAD kernel, collision detector, motion solver or physical validation system.

## 5. Validation

- JSON round-trip for RigidTransform and FrameGraph.
- Explicit length-unit preservation through inverse, composition and graph resolution.
- Strict version/field checks.
- Duplicate frame, duplicate parent, undeclared endpoint and cycle rejection.
- Deterministic serialization independent of insertion order.
- Mixed-unit composition and graph edges fail closed.
