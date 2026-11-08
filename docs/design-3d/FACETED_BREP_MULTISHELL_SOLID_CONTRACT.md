# Faceted B-rep Multi-Shell Solid Contract v1.0

**Status:** IMPLEMENTED — PR #184 merged to the integration branch.  
**Profile:** `FACETED_MULTI_SHELL_SOLID_V1`.  
**Component profile:** `FACETED_POLYGONAL_PLANAR_SHELL_V2`.

## 1. Purpose and compatibility

Represent one material region using one independently validated outer B-rep shell and zero or more independently validated cavity shells. This aggregate deliberately avoids changing the established `BRepSolid` v2.0 snapshot or constructor. Existing v1.0 triangular and v2.0 polygonal single-shell snapshots remain importable through `BRepSolid.from_dict`.

The aggregate is a separate immutable type, `BRepMultiShellSolid`. Every component remains a normal `BRepSolid` and retains its own stable component ID, topology, source digest, frame and unit.

## 2. Orientation semantics

- The outer component is stored as a normal outward-oriented, positive-volume B-rep.
- Each cavity component is also stored as a normal outward-oriented, positive-volume B-rep.
- Aggregate conversion applies subtractive orientation to cavity triangles by reversing each cavity triangle's winding.
- The resulting aggregate mesh must pass the existing watertight, manifold-edge and consistent-winding validator and have strictly positive net signed volume.
- Cavity orientation is an aggregate semantic; source component snapshots are never mutated.

## 3. Topology and geometry invariants

- Exactly one outer shell is required.
- Zero or more cavity shells are permitted.
- Each component must independently pass `validate_brep_solid`: one closed, connected, orientable shell with valid planar polygonal faces and positive signed volume.
- All component IDs must be unique and every component must use the same frame and length unit.
- Every cavity vertex must be strictly inside the outer shell. The point-in-shell test uses exact rational predicates over represented binary64 coordinates and deterministic ray directions; unresolved ray classifications fail closed.
- The complete combined boundary mesh is checked with `analyze_mesh_intersections`. Only `NO_INTERSECTIONS_FOUND` is accepted. `INTERSECTIONS_FOUND` and `UNKNOWN` both fail closed.
- Cavity shells must be pairwise disjoint and non-nested. Nested cavities would imply material islands and are explicitly unsupported in this profile.
- The combined mesh must pass `validate_triangle_mesh`; net signed volume must be positive.
- No geometry is healed, welded, snapped, or silently reoriented in source snapshots.

## 4. Serialization

Schema: `schemas/geometry/faceted-brep-multishell-solid.schema.json`.

The aggregate snapshot contains:
- schema version and profile;
- aggregate solid ID, frame, unit and computed SHA-256;
- one complete v2 single-shell snapshot in `outer_shell`;
- zero or more complete v2 single-shell snapshots in `cavity_shells`.

The aggregate digest is SHA-256 over canonical JSON containing the aggregate ID and the ordered outer/cavity component snapshots. Import validates metadata and recomputes the digest. Unknown or missing fields are rejected.

## 5. Mesh conversion

`BRepMultiShellSolid.to_mesh()` concatenates component vertices in deterministic component order (outer first, then cavity order). It preserves the exact per-component coordinates and reverses cavity triangle winding. The output is an `IMPORTED_BREP` TriangleMesh whose source digest identifies the complete aggregate snapshot.

No Boolean surface reconstruction is performed. This operation composes already valid closed shell boundaries.

## 6. Explicit limits

- Planar polygonal single-shell components only; curved surfaces, NURBS and trimmed surfaces are not supported.
- One outer shell plus disjoint, non-nested cavity shells only; nested cavity islands, multiple material regions and arbitrary shell nesting are unsupported.
- The existing mesh intersection analysis has a finite candidate-pair budget. A resource-limit `UNKNOWN` result is a rejection, not a pass.
- Existing mesh validation does not prove every geometric property of the source components; the aggregate additionally requires complete mesh-intersection analysis.
- No general 3D Boolean operations, shell healing, tolerance-based welding, STEP/AP242 multi-shell exchange, manufacturing certification or physical execution are claimed.

## 7. Acceptance tests

- One nested cavity: net volume and watertight oriented mesh.
- Multiple disjoint cavities: deterministic output and subtractive net volume.
- Rotated non-axis-aligned cavity and concave polygonal-prism cavity reference cases.
- Outside, touching, intersecting and nested cavity rejection.
- Frame/unit mismatch rejection.
- Strict snapshot round-trip, digest verification and schema contract.
- Existing single-shell v1/v2 tests remain unchanged.

## 8. Follow-up gates

1. Independent reference fixtures beyond axis-aligned boxes (rotated and concave planar shells).
2. Explicit cavity classification and shell hierarchy if material islands become a requirement.
3. STEP/AP242 multi-shell serialization and round-trip conformance.
4. General 3D Boolean operations only after independent geometric reference cases and failure injection.


## 9. PR #184 implementation evidence

- Exact PR head: `850e521cd3499ede4e8a00a5cb1698cee32347d0`.
- Merge SHA: `db7ce54efe3d9334b87b3902a14b089b6ce67ebd`.
- Exact-head PR workflow #42461224579: workflow-sanity PASS; Python 902 PASS (15.63s).
- Exact-head push workflow #42461220462: workflow-sanity PASS; Python 902 PASS (15.53s).
- Post-merge workflow #42461294867: workflow-sanity PASS; Python 902 PASS (14.17s).
- Browser E2E was not triggered because no browser UI changed; it is not counted as PASS.
- See [post-PR #184 repository audit](../audit/REPOSITORY_AUDIT_2026-11-08_POST_PR184.md).
