# Coordinate Frames and Rigid Transforms

**Status:** Implemented software contract slice; tested independently at the repository's current feature branch head.  
**Scope:** Offline coordinate mathematics only. This is not a CAD kernel, assembly solver, or export implementation.

## 1. Transform convention

A transform maps coordinates from a source frame into a destination frame:

`p_to = R_to_from p_from + t_to_from`

- `R_to_from` is a 3×3 rotation matrix mapping vector components from the source basis to the destination basis.
- `t_to_from` is the source-frame origin expressed in destination-frame coordinates.
- Points receive rotation and translation.
- Direction vectors receive rotation only.
- Both frames must use the same length unit. Unit conversion is a separate, explicit operation.
- Only right-handed proper rotations are accepted: `R Rᵀ = I` and `det(R) = +1`.

Scale, shear, reflection, non-finite entries and ambiguous frame composition are rejected.

## 2. Composition and inversion

If `T_A_to_B` maps A to B and `T_B_to_C` maps B to C, then:

`R_C_from_A = R_C_from_B R_B_from_A`

`t_C_from_A = R_C_from_B t_B_from_A + t_C_from_B`

The API expresses this as `T_A_to_B.then(T_B_to_C)`. The intermediate frame identifiers must match exactly.

The inverse uses the orthonormal rotation property:

`R_from_to = R_to_fromᵀ`

`t_from_to = -R_to_fromᵀ t_to_from`

## 3. Implemented API

`universal_platform.engineering.transforms.RigidTransform` provides:

- `identity(frame_id)`
- `apply_point(Vec3)`
- `apply_vector(Vec3)`
- `apply_bounds(BoundingBox)`, transforming all eight corners and rebuilding an axis-aligned bounding box
- `inverse()`
- `then(next_transform)`

Rotation validation uses a fixed absolute tolerance of `1e-9`. It is intended for normalized rigid transforms, not noisy measured orientation estimates or large-scale numerical optimization.

## 4. Verification cases

The unit tests cover identity, a 90-degree Z rotation plus translation, point/vector distinction, inverse round-trip, composition equivalence, frame mismatch rejection, transformed bounding-box enclosure, and rejection of scale, shear, reflection, non-finite rotation and empty frame identifiers.

## 5. Explicit limitations

- No coordinate-frame tree/graph or automatic path resolution.
- No unit conversion inside a transform.
- No affine scale, shear, reflection, deformation or projective transforms.
- No quaternion/Euler-angle import/export or convention guessing.
- No uncertainty propagation or tolerance analysis.
- No CAD B-rep, mesh, STEP/STL/3MF, assembly constraint or collision implementation.
- A transformed bounding box is a conservative axis-aligned enclosure, not exact transformed solid geometry.

## 6. Safety and evidence

The module is dependency-free and performs local mathematical operations. It does not access files, networks, hardware or external solvers. Passing these tests validates this transform contract only; it does not validate any physical design or manufacturing outcome.
