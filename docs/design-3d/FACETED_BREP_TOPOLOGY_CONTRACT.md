# Faceted B-rep Topology Contract v1.0

**Status:** Initial bounded topology model; PR candidate on `feat/faceted-brep-topology-v1`.  
**Profile:** `FACETED_TRIANGULAR_PLANAR_SHELL_V1`.

## 1. Purpose

Provide an explicit topological boundary representation for one closed, connected, consistently oriented shell composed only of triangular planar faces. The first adapter converts an already validated `TriangleMesh` into this representation and back again.

This is a foundation for future B-rep work. It is not a general CAD boundary-representation kernel and does not implement 3D Boolean operations.

## 2. Topology records

- `BRepVertex`: stable vertex ID and frame-local 3D position.
- `BRepEdge`: stable edge ID and canonical start/end vertex IDs.
- `BRepEdgeUse`: an edge reference plus a forward/reverse orientation.
- `BRepLoop`: exactly three ordered edge uses forming a closed triangle cycle.
- `BRepFace`: one outer triangular loop; the implied surface is planar.
- `BRepShell`: one connected set of faces.
- `BRepSolid`: shell topology, frame/unit, stable identity and source geometry digest.

Schema: `schemas/geometry/faceted-brep-solid.schema.json`.

## 3. Validation invariants

- IDs are stable and unique within each entity family.
- Every reference resolves; every loop is a closed directed cycle.
- Each face is a non-degenerate triangle under exact-rational predicates over the represented binary64 coordinates.
- Every vertex and loop is used.
- Every shell edge is used by exactly two faces, with opposite edge-use directions.
- The face adjacency graph is connected.
- The Euler characteristic is consistent with a connected orientable closed surface; genus is reported.
- The oriented shell must have positive signed volume.
- Conversion from mesh requires the existing mesh validator to report valid, watertight and consistently oriented.

## 4. Mesh bridge

`brep_from_triangle_mesh` creates deterministic IDs from mesh array order and canonical edge endpoint ordering. `triangle_mesh_from_brep` reconstructs the triangular mesh and re-runs the existing mesh validation. The source geometry digest, solid ID, frame and length unit are preserved. Reconstructed meshes use `source_kind=IMPORTED_BREP`.

## 5. Explicit limits

- Triangular planar faces only; no polygonal n-gons, face holes, analytic curved surfaces, NURBS, trims, wires or shells with multiple disconnected components.
- One closed orientable shell per solid.
- Topological manifold checks do not prove geometric non-self-intersection; use the separate mesh intersection analysis.
- No 3D UNION / INTERSECTION / DIFFERENCE / XOR, no shell healing, no tolerance-based vertex welding, no feature history integration and no manufacturing/certification claim.
- STEP AP214 faceted-BREP interchange remains a separate serialization boundary.

## 6. Next gates

1. Add polygonal planar faces and face-loop holes with exact loop containment and orientation checks.
2. Add shell/solid aggregation and multiple-shell semantics.
3. Define exact geometric intersection and classification contracts for 3D Boolean operations.
4. Implement bounded Boolean operations only after independent reference cases, manifold checks and failure injection.
5. Add curved-edge/surface representations and neutral-format interoperability only with explicit tolerance and provenance contracts.
