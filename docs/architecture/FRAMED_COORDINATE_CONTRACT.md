# Frame-bound Coordinate Contract

**Status:** Implemented v1.0 subset under PR #45; spatial displacement vectors only.

## 1. Types

- `FramedPoint3`: a point expressed in one named coordinate frame.
- `FramedVector3`: a spatial displacement vector expressed in one named frame.

Each record carries a stable non-empty `frame_id`, a finite Vec3 value and an explicit length unit. The v1.0 snapshot carries `schema_version`, `kind` (POINT or VECTOR), `frame_id`, and x/y/z coordinates with unit.

## 2. Transform semantics

Both types resolve a transform through FrameGraph. A point uses `RigidTransform.apply_point()` (rotation plus translation). A displacement vector uses `apply_vector()` (rotation only). The result is bound to the target frame.

The graph and value must use the same length unit. Mixed-unit conversion is explicit and outside this contract.

## 3. Validation

- Unknown or disconnected frames fail.
- Mismatched units fail.
- Non-finite coordinates fail through Vec3.
- Unknown fields, wrong kind and unsupported schema versions fail.
- Same-frame transformation is identity and preserves the original unit.

## 4. Limitations

FramedVector3 is specifically a spatial displacement vector with length components. It is not a generic vector for force, velocity, acceleration, magnetic field or other physical dimensions. No frame-bound tensor, rigid-body pose, uncertainty propagation or automatic unit conversion is implemented.
