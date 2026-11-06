# CAD-neutral Primitive Geometry Contract

**Status:** PR #61 implements dependency-free convex 2D profile Boolean operations v1.0; PR #62 adds a general planar topology design contract only; PR #64 implements deterministic Box/Cylinder triangle tessellation and structural validation; PR #66 adds straight-edged profile meshing; PR #68 implements polygonal through-hole meshing; PR #70 adds circular-arc tessellation with a caller-specified chordal tolerance. This remains an analytic primitive layer plus a narrow mesh adapter, not a B-rep CAD kernel.

## 1. Model

- `BoxSolid`: stable solid ID, frame ID, positive x/y/z dimensions and explicit length unit.
- `CylinderSolid`: stable solid ID, frame ID, positive radius/height and explicit length unit.
- `ExtrudedProfileSolid`: immutable 2D profile loop in local XY using straight edges or signed circular-arc sweeps in radians, positive extrusion height along local +Z, and zero or more through-hole loops that may also use circular arcs. Curved edges carry stable segment IDs.
- `Vec2`: finite 2D profile vertex.
- `PrimitiveGeometryModel`: versioned FrameGraph plus primitive solid collection.
- `FramedBounds3`: axis-aligned bounds expressed in a named target frame and length unit.

## 2. Computation

Volume and surface area are computed analytically and returned as SI-valued Quantity records with dimensional signatures. Box bounds transform all eight corners. Cylinder bounds use the transformed local cylinder axis and analytic radial/axial extents. Extruded-profile bounds transform every outer-profile vertex at both extrusion planes.

For an extruded profile, net area and perimeter are computed analytically from line and circular-arc segments. Net area is outer area minus the sum of hole areas. Boundary perimeter includes the outer loop and every hole loop; therefore analytic surface area includes the inner through-hole walls. Volume is net profile area multiplied by extrusion height. Arc sweep angles are signed radians; zero denotes a straight edge. Curved profiles serialize as schema v1.1, while legacy straight-only snapshots remain v1.0.

All transforms in a connected FrameGraph use one length unit; solids must match that unit. No implicit conversion occurs.

## 3. Validation and compatibility

- Stable unique solid IDs and declared frame IDs.
- Positive finite dimensions and supported length units.
- Outer and hole loops require at least three immutable finite Vec2 vertices, no duplicate vertices, non-degenerate area and unique stable segment IDs for curved edges. Arc sweeps must be finite, non-zero when curved, and have magnitude below 2*pi radians.
- Every hole must lie strictly inside the outer profile and cannot touch/intersect its boundary.
- Hole loops cannot touch, intersect, overlap or nest.
- The optional `holes` property is omitted when empty. Older v1.0 snapshots without `holes` remain readable and round-trip without adding the optional field.
- Strict v1.0 JSON snapshots, JSON Schema coverage, deterministic solid ordering and reference-value tests.
- Public package exports include `Vec2` and `ExtrudedProfileSolid`.

## 4. Acceptance criteria for through-holes

1. Single- and multiple-hole profiles produce the expected net area, perimeter, SI volume and surface area.
2. Inner wall area is included in surface area.
3. Invalid, touching, outside, overlapping and nested loops fail closed.
4. Serialization is deterministic; empty holes remain omitted.
5. Existing no-hole profile snapshots remain backward compatible.
6. The public package-level imports resolve to the canonical primitive types.
7. Existing Box/Cylinder and mechanism regression tests remain unchanged and pass.

## 5. Limitations

Curved-profile topology checks use deterministic 1-degree arc tessellation; area, perimeter and local arc bounds are analytic, but topology validation is not an exact B-rep operation. This is not a B-rep or mesh CAD kernel. It does not implement splines, draft angles, general concave/hole-bearing Boolean operations, 3D Boolean/B-rep operations, feature history, fillets, tolerances, materials/density, collision/contact, meshing, STEP/STL export, toolpath generation or manufacturability/certification checks. Analytic PASS does not validate a physical design.


## 6. Convex 2D Boolean operations (PR #61 merged)

See [2D Convex Profile Boolean Topology Contract](../design-3d/CAD_2D_BOOLEAN_TOPOLOGY_CONTRACT.md). The new operation set accepts convex simple polygon loops and returns deterministic convex-cell decompositions for UNION, INTERSECTION and DIFFERENCE. It intentionally does not dissolve adjacent cells. Concave loops, arcs, holes, exact arithmetic and general planar arrangements remain unsupported.


## 7. Deterministic primitive triangle meshes (PR #64 merged)

See [Deterministic Primitive Triangle Mesh Contract](../design-3d/TRIANGLE_MESH_GENERATION_CONTRACT.md). BoxSolid emits an exact 8-vertex/12-triangle closed surface. CylinderSolid emits deterministic polygonal rings and cap fans under an explicit radial chordal tolerance. PR #66 adds ear-clipped caps and side walls for straight-edged concave/convex ExtrudedProfileSolid inputs; PR #68 adds ear-clipped cap regions with bridged polygonal holes and correctly oriented inner walls (514-test post-merge CI PASS). Meshes retain source-local frame/unit and a SHA-256 source geometry digest; validation checks face indices, degenerate triangles, edge manifold counts, directed winding and positive signed volume.

Non-circular/spline ExtrudedProfileSolid meshes, general mesh self-intersection, mesh repair, B-rep, 3D Booleans and STEP/STL/3MF interchange remain unsupported.
