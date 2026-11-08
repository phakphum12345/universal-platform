# Faceted B-rep Topology Contract v2.0

**Status:** Polygonal planar faces with inner loops; one connected orientable shell.  
**Profile:** `FACETED_POLYGONAL_PLANAR_SHELL_V2`.

## 1. Purpose

Provide an explicit topological boundary representation for one closed, connected, consistently oriented shell composed of planar polygonal faces, including strictly contained face inner loops. TriangleMesh conversion is a separate deterministic polygonal-face triangulation adapter.

This is a foundation for future B-rep work. It is not a general CAD boundary-representation kernel and does not implement 3D Boolean operations.

## 2. Topology records

- `BRepVertex`: stable vertex ID and frame-local 3D position.
- `BRepEdge`: stable edge ID and canonical start/end vertex IDs.
- `BRepEdgeUse`: an edge reference plus a forward/reverse orientation.
- `BRepLoop`: at least three ordered edge uses forming a closed polygon cycle.
- `BRepFace`: one outer polygon loop and zero or more strictly-contained inner polygon loops; the implied surface is planar.
- `BRepShell`: one connected set of faces.
- `BRepSolid`: shell topology, frame/unit, stable identity and source geometry digest.

Schema: `schemas/geometry/faceted-brep-solid.schema.json`.

## 3. Validation invariants

- IDs are stable and unique within each entity family.
- Every reference resolves; every loop is a closed directed cycle.
- Each face is a non-degenerate planar simple polygon under exact-rational predicates over the represented binary64 coordinates.
- Every vertex and loop is used.
- Every shell edge is used by exactly two faces, with opposite edge-use directions.
- The face adjacency graph is connected.
- The Euler characteristic is consistent with a connected orientable closed surface; genus is reported.
- The oriented shell must have positive signed volume.
- Conversion from mesh requires the existing mesh validator to report valid, watertight and consistently oriented.

## 4. Mesh bridge

`brep_from_triangle_mesh` creates deterministic IDs from mesh array order and canonical edge endpoint ordering. `triangle_mesh_from_brep` deterministically triangulates polygonal faces and inner loops using the existing bridge-and-ear-clipping profile helper, maps the result to the unchanged B-rep vertices and re-runs the existing mesh validation. The source geometry digest, solid ID, frame and length unit are preserved. Reconstructed meshes use `source_kind=IMPORTED_BREP`.

## 5. Explicit limits

- Planar polygonal faces only; no analytic curved surfaces, NURBS, trims or non-linear wires.
- One closed orientable connected shell per solid; multiple disconnected shells are not supported.
- Exact represented-binary64 predicates validate face planarity, simple loops, strict inner-loop containment, non-contact and opposite hole orientation.
- TriangleMesh conversion supports planar polygonal faces and inner loops through bounded triangulation (10,000 boundary vertices per face; 200,000 output triangles per solid); triangulation or mesh-validation failures fail closed.
- Topological manifold checks do not prove geometric non-self-intersection; use the separate mesh intersection analysis.
- No 3D UNION / INTERSECTION / DIFFERENCE / XOR, no shell healing, no tolerance-based vertex welding, no feature history integration and no manufacturing/certification claim.
- STEP AP214 faceted-BREP interchange remains a separate serialization boundary.

## 6. Next gates

1. Add shell/solid aggregation and multiple-shell semantics.
2. Define exact geometric intersection and classification contracts for 3D Boolean operations.
3. Implement bounded Boolean operations only after independent reference cases, manifold checks and failure injection.
4. Add multiple-shell solid aggregation and explicit shell/cavity semantics.
5. Define exact geometric intersection and classification contracts for arbitrary 3D Boolean operations.
6. Add curved-edge/surface representations and neutral-format interoperability only with explicit tolerance and provenance contracts.


## 7. v2.0 implementation evidence

PR #181 implements arbitrary simple planar polygon loops and face inner loops. Exact rational predicates validate coplanarity, non-degenerate/simple boundaries, strict containment, non-touching/non-overlapping holes and opposite inner-loop orientation. The Euler characteristic accounts for face holes, allowing a valid single-shell genus-1 through-hole solid. v1.0 triangular snapshots remain importable and normalize to v2.0. Mesh conversion deliberately remains triangular/no-hole only and fails closed for the new topology.


## PR #181 implementation verification

- Exact PR head `70be8fb3c091fd391d994da01c0fb6b4cb912dfd`; merge SHA `ea9dfc13503c5d41739804e0ab5b68fe87e74d1b`.
- Exact PR-head and post-merge: workflow-sanity PASS; Python tests PASS (892). Chromium E2E SKIPPED/not triggered (no UI surface changed).
- Supports planar polygonal n-gon loops and explicit inner loops, exact coplanarity/simple-loop/containment/orientation validation, and Euler/genus accounting for face holes.
- Imports v1.0 triangular snapshots and normalizes to v2.0. Mesh adapter remains triangular/no-hole only.
- Multi-shell aggregation and general 3D Boolean remain the next topology gates.


## 8. Polygonal B-rep mesh triangulation — PR #182

The v2.0 mesh bridge triangulates validated planar n-gon faces and one or more inner loops without adding geometric vertices. It reuses the deterministic profile-region bridge-and-ear-clipping helper, restores each outer-loop orientation, preserves source identity/frame/unit/digest, and validates the completed mesh as valid, watertight and consistently oriented. Resource limits are 10,000 boundary vertices per face and 200,000 output triangles per solid. See [Faceted B-rep Polygonal Mesh Triangulation Contract](FACETED_BREP_MESH_TRIANGULATION_CONTRACT.md). Exact-head and post-merge evidence must be recorded after CI; this adapter does not add multiple shells or general 3D Boolean operations.
