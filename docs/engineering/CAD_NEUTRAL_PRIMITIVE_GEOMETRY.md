# CAD-neutral Primitive Geometry Contract

**Status:** Analytic Box/Cylinder subset implemented under PR #48.

## 1. Model

- `BoxSolid`: stable solid ID, frame ID, positive x/y/z dimensions and explicit length unit.
- `CylinderSolid`: stable solid ID, frame ID, positive radius/height and explicit length unit.
- `PrimitiveGeometryModel`: versioned FrameGraph plus primitive solid collection.
- `FramedBounds3`: axis-aligned bounds expressed in a named target frame and length unit.

## 2. Computation

Volume and surface area are computed analytically and returned as SI-valued Quantity records with dimensional signatures. Box bounds transform all eight corners. Cylinder bounds use the transformed local cylinder axis and analytic radial/axial extents to produce a tight axis-aligned bounding box.

All transforms in a connected FrameGraph use one length unit; solids must match that unit. No implicit conversion occurs.

## 3. Validation

- Stable unique solid IDs and declared frame IDs.
- Positive finite dimensions and supported length units.
- Strict v1.0 JSON snapshots and unknown-kind rejection.
- Deterministic solid ordering.
- Reference tests for SI volume/surface area and transformed bounds.

## 4. Limitations

This is not a B-rep or mesh CAD kernel. It does not implement Boolean operations, sketches, feature history, fillets, tolerances, materials/density, collision/contact, meshing, STEP/STL export, toolpath generation or manufacturability/certification checks. Analytic PASS does not validate a physical design.


## 5. Simple polygon extrusion (PR #49)

`ExtrudedProfileSolid` adds a 2D simple polygon profile in local XY, extruded along local +Z by a positive height. It validates immutable unique vertices, non-self-intersection and non-zero area. Volume is profile area × height; surface area is 2 × profile area + perimeter × height. Bounds transform all profile vertices at both extrusion planes.

This supports straight-sided plates/brackets as a CAD-neutral analytic primitive. PR #50 extends the profile with zero or more disjoint through-hole loops. Hole loops must be simple, strictly inside the outer loop, and may not touch, overlap or nest. Net profile area subtracts hole areas; perimeter includes every boundary loop; analytic extrusion surface area includes the inner hole walls. Snapshots without a `holes` field remain readable and empty-hole snapshots omit the field for compatibility. Arcs/splines, draft angles, Boolean features, sketch constraints, B-rep and mesh export remain unsupported.
