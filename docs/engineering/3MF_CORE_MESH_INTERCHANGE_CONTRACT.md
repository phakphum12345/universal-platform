# 3MF Core Mesh Interchange Contract v1.0

**Status:** Bounded single-mesh solid import/export implemented by PR #97.  
**Merge SHA:** `9b415f7c6be0f537feb67cbe86a911dc0ef5f662`.  
**Exact PR-head CI:** run #42265918058 — both required jobs PASS, 650 tests.  
**Post-merge CI:** run #42266044427 — both required jobs PASS, 650 tests.

## 1. Purpose and standard basis

Provide a dependency-free, bounded 3MF Core package profile for exchanging validated triangle-mesh solids. The package uses the 3MF OPC/ZIP model, a 3D Model part, the 3MF Core namespace and the StartPart relationship. See the [3MF Core Specification](https://github.com/3MFConsortium/spec_core) and [3MF Consortium specification index](https://3mf.io/spec/).

## 2. Supported profile

- One model object containing one triangle mesh.
- One build item referencing that object, with no transform.
- Supported length units: metre, millimetre, centimetre and inch, mapped to the platform's registered units.
- Mesh vertices and triangles, plus platform metadata for solid ID, frame ID and source geometry SHA-256.
- Imported meshes use source kind `IMPORTED_3MF`; the source file package digest is reported separately.
- Export requires a valid, watertight, consistently oriented mesh.
- Import requires finite vertices, in-range triangle indices and a valid, watertight, consistently oriented mesh.
- Schema update: `schemas/geometry/triangle-mesh.schema.json`.

## 3. Package and parser safety

- Exact three-part profile: `[Content_Types].xml`, `_rels/.rels`, `3D/3dmodel.model`.
- Validate content types, one StartPart relationship, root namespace, model/resources/build structure and object references.
- Reject duplicate names, path traversal, backslashes, symlinks, encrypted entries, excessive package/XML sizes, excessive compression ratio, DTD/entity declarations and unsupported package parts.
- Bound vertex and triangle counts.
- Reject transforms, components, extra resources, materials, colors, textures, extensions, multiple objects and unsupported units.
- Uses Python standard library only; no external runtime dependency.

## 4. Determinism and provenance

- ZIP entries have fixed timestamps, stable ordering and fixed compression settings.
- XML numeric coordinates use round-trip-safe decimal formatting.
- Exported package SHA-256 and source geometry SHA-256 are both recorded.
- Round-trip preserves solid ID, frame ID, unit, vertex order, triangle order and source geometry digest.
- Imported TriangleMesh snapshots round-trip under the versioned schema.

## 5. Explicit limitations

This is not a complete 3MF Core consumer/producer. It does not support multiple models, assemblies/components, transforms, build items, materials, colors, textures, thumbnails, extensions, custom parts, OPC signatures, arbitrary external 3MF packages or preservation of unknown package parts. It does not provide STEP, B-rep, analytic surfaces, parametric feature history exchange, manufacturing suitability or certification.

STEP import/export remains OPEN and must be handled by a separate versioned adapter and reference corpus.

## 6. Acceptance evidence

- Deterministic package bytes across repeated exports.
- Round-trip of a watertight box mesh with source provenance and unit preservation.
- Inch unit mapping.
- Reject non-watertight export, unsupported units, extra package parts, unsafe paths, DTD/entity declarations, invalid triangle indices, non-finite coordinates, invalid relationship targets and unsupported model units.
- Exact PR-head and post-merge CI both pass 650 tests.
