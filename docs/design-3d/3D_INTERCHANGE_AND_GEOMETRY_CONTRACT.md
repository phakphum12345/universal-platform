# 3D Interchange and Geometry Contract

**Status:** Partially implemented software geometry contract; CAD format/kernel decisions remain OPEN.

## Purpose
Define minimum invariants for geometry, coordinate frames and neutral CAD exchange. File extension alone does not establish semantic fidelity or manufacturability.

## Canonical geometry metadata
Every model records model ID/revision, source project and hash, units, coordinate convention, origin, handedness, component/assembly identity, material references, tolerance assumptions, authoring tool/kernel and version, export adapter/version, and provenance.

## Coordinate frames
A frame declares stable ID, parent frame, origin, axis orientation, handedness, unit and transform convention. The dependency-free `RigidTransform` contract is implemented in [Coordinate Frames and Rigid Transforms](COORDINATE_FRAMES_AND_RIGID_TRANSFORMS.md). It uses:

`p_to = R_to_from p_from + t_to_from`

The implementation validates right-handed orthonormal rotations, frame-compatible composition, inverse transforms, point/vector semantics and transformed axis-aligned bounds. Both frames are required to use the same length unit. A frame graph, automatic path resolution, unit conversion, and uncertainty propagation are not implemented.

## Geometry classes
Distinguish analytic primitives, boundary representation (B-rep), parametric feature history, polygon meshes, point clouds and 2D drawings. Do not claim a mesh preserves parametric design intent. Unsupported entities must be listed in an export report.

## Candidate formats
- STEP: candidate for solid/assembly interchange; exact application protocol and metadata mapping remain to be selected.
- STL: tessellated surface; generally does not preserve units, materials or feature history reliably.
- 3MF: additive manufacturing package candidate; validate units, materials and build metadata.
- OBJ: mesh interchange candidate; assembly/material semantics vary by implementation.
- DXF/SVG: 2D geometry/document exchange; not a substitute for a 3D solid model.

No format is selected by this document. Evaluate tool support, license, version, round-trip fidelity, assembly semantics, units, metadata, security and offline behavior.

## Export/import validation
1. Pin source model revision and tool versions.
2. Record export options and supported/unsupported entities.
3. Export to a separate artifact; never overwrite the source.
4. Reopen using an independent supported reader where possible.
5. Compare units, scale, orientation, component count, topology/mesh metrics and bounding dimensions.
6. Record deviations and tolerance; fail on unexplained scale or orientation changes.
7. Hash source and exported artifacts and attach the validation report.

## Acceptance
- Units and coordinate frames are explicit.
- Unsupported geometry is reported, not silently discarded.
- Export/import tests use fixtures and documented tolerances.
- Source models remain immutable.
- A valid file is not described as structurally safe or manufacturing-ready without separate checks.


## Current analytic geometry implementation boundary — 2026-11-06

- PR #48 (merged) provides analytic Box/Cylinder primitives, SI properties and frame-aware bounds.
- PR #49 (open review candidate; head `38a800d033ebbba19e1120c8cd3a47ade4088526`) adds straight-sided polygon profile extrusion.
- PR #50 (open review candidate; head `9507b9fab758465763c60d02f8da83d7d8131d2d`), stacked on PR #49, adds optional through-hole loops and backward-compatible snapshots.
- Exact-head CI for PR #49 and PR #50 is UNKNOWN at this audit. Neither PR is merged.
- Curves/splines, draft, Boolean features, B-rep/mesh kernels and STEP/STL/3MF interchange are not established by these analytic primitives.
