# Implementation Status — UEIC Foundation

**Integration branch:** docs/phase-0-complete-requirements  
**Latest merged baseline before PR #31:** b670f0c8f4d60f1c6006d1c836c1d2ff4cb728bb (PR #30; integrated mechanism position, mobility, velocity and acceleration pipeline)  
**Scope:** Dependency-light offline engineering core; normalized stable-ID mechanism schema v1.1; rigid transforms and frame graph; explicit joint/geometry placements; narrow planar kinematics and caller-supplied loop/Jacobian contracts.

## PR #31 — Joint and geometry placement contracts

- Adds schema v1.1 records `JointFramePlacement` and `GeometryPlacement`.
- Joint placements explicitly map parent link body frame → joint frame → child link body frame. Geometry placements map a geometry-local frame into its declared reference frame.
- Reuses `RigidTransform`; transform endpoint frame IDs are validated exactly. Placement translations are declared in metres; no implicit unit conversion occurs.
- Legacy schema v1.0 topology-only models remain valid. Placement records require schema v1.1.
- Validation reports missing placement IDs as coverage gaps rather than assuming identity transforms.
- Adds deterministic placement snapshots and regression tests for valid placements, missing coverage, schema compatibility, duplicate/dangling IDs, endpoint mismatch, frame ownership and unit mismatch.
- **Not implemented by PR #31:** CAD placement inference, automatic joint residual equations, automatic Jacobian generation, velocity/acceleration bias generation, general spatial solving, dynamics or physical validation.
- PR #31 branch: `feat/joint-geometry-placement-contract`; base SHA: `213b07e1ea362bf3fe6b460d5495bd505b2232e4`. CI evidence pending until exact final PR head is tested.

## Existing integrated mechanism capabilities

- PR #27: normalized stable-ID model topology and structural validation; joint kinds remain schema-only.
- PR #28: deterministic fundamental-cycle topology and explicit caller-supplied loop residual bridge.
- PR #29: nominal/local mobility and Jacobian rank diagnostics; Jacobian is caller-supplied.
- PR #30: position/mobility/velocity/acceleration orchestration; loop residuals, Jacobian and derivative biases remain caller-supplied.
- PR #31 supplies the missing explicit rigid placements but does not yet generate the residual/Jacobian functions from those placements.

## Evidence policy

A feature is implemented only to the extent source exists. PASS requires executed tests tied to an exact SHA. SKIPPED and UNKNOWN are never PASS. These offline checks do not imply physical feasibility, safety certification, actuation or manufacturing readiness.
