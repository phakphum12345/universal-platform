# Binary STL Interchange Contract

**Status:** Contract implemented for binary STL export by PR #74 candidate; exact-SHA CI evidence is pending. Arbitrary STL import and external CAD toolchain integration are not implemented. The existing TriangleMesh v1.0 remains the canonical in-memory representation.

## 1. Purpose and delivery boundary

Define a deterministic, dependency-free binary STL export format for an already validated `TriangleMesh`, with a required JSON sidecar that preserves the metadata STL cannot represent.

The first implementation increment is **export-only**. It must produce a binary STL byte artifact and a strict metadata manifest. A separate test-only reader must reopen the bytes independently of the production writer and verify facet count, coordinates, winding and geometric bounds.

Importing arbitrary third-party STL files, editing/re-importing files after external CAD changes, ASCII STL, color/material extensions, STEP, 3MF, B-rep and CAD-kernel integration are not part of this first increment. These remain explicit roadmap items.

## 2. Artifact pair and identity

An export consists of two artifacts:

1. Binary STL payload.
2. JSON manifest with schema `STLInterchangeManifest` v1.0.

The manifest must contain:
- `schema_version`, `format` = `BINARY_STL`, and coordinate encoding `IEEE754_BINARY32_LE`.
- Stable `solid_id`, source `source_kind`, source mesh schema version and source geometry SHA-256.
- Explicit `frame_id` and `length_unit`; no frame or unit is embedded in STL itself.
- Optional source `chordal_tolerance` in the same length unit.
- Exact STL byte length, facet count and SHA-256 of the complete payload.
- Maximum absolute coordinate-rounding error measured between source float64 coordinates and the serialized float32 coordinates.
- A declared normal policy: recompute unit normals from the quantized facet coordinates.

The sidecar is mandatory for platform round-trip provenance. A bare STL file is not sufficient evidence of units, frame, source identity or tessellation tolerance. The caller must treat the sidecar as trusted metadata and verify the expected frame/unit before using the artifact. A byte digest detects payload changes, not malicious sidecar substitution; authenticity/signatures are a separate future requirement.

## 3. Binary STL byte contract

- Header: exactly 80 bytes, deterministic for identical input, beginning with an implementation identifier that does not begin with the ASCII token `solid`.
- Facet count: unsigned 32-bit little-endian integer.
- Each facet: 12-byte normal (three little-endian float32 values), 36-byte vertices (three XYZ float32 triples), and a 2-byte attribute count.
- Attribute count must be zero; color/vendor extensions are rejected.
- Exact payload length is `84 + 50 * facet_count`; trailing bytes and truncation are rejected.
- The v1 exporter emits one record for every source triangle in source order. No welding, simplification, reordering, unit conversion, coordinate transform or topology repair occurs.
- Facet normals are recomputed from the quantized triangle vertices and normalized. Degenerate quantized facets fail closed.

## 4. Precision and numerical policy

STL v1 stores IEEE-754 binary32 coordinates. The exporter must:
- Reject non-finite source coordinates, binary32 overflow and any triangle that becomes degenerate after quantization.
- Measure and record the maximum per-coordinate absolute rounding error across all vertices.
- Preserve the source frame and unit in the sidecar; it must not silently convert coordinates.
- Recompute normals from the quantized coordinates, not from the higher-precision source values.
- Reject a source mesh that fails `validate_triangle_mesh` before serialization.
- Enforce a documented maximum facet count (initial default: 1,000,000) before allocating the output buffer.
- Validate the quantized facet soup using an independent test reader; compare triangle count, oriented facets, bounding box and signed volume within a bound derived from the recorded coordinate error and mesh scale.

The coordinate error field is a measured export property, not a global manufacturing tolerance. It does not bound all downstream geometric operations or prove physical accuracy.

## 5. Manifest schema and validation

The manifest schema must use `additionalProperties: false`, require all identity/digest/count fields, reject non-finite or negative error bounds, and constrain digest strings to lowercase 64-character SHA-256 values.

Import of the manifest for a platform-produced artifact must reject:
- Unknown/missing fields or unsupported schema/format/encoding.
- Invalid length units or blank frame/solid IDs.
- Non-zero or inconsistent facet count, byte length or digest.
- A manifest whose expected frame/unit does not match caller-supplied context.
- A chordal tolerance that is non-finite or non-positive when present.

The first increment does not reconstruct a TriangleMesh from arbitrary STL. A future import contract must explicitly decide vertex welding/deduplication, tolerance, source-kind identity, external provenance and how to represent imported geometry without fabricating an analytic source SHA.

## 6. Determinism and offline behavior

The exporter must be pure Python, offline-capable and dependency-free. Identical TriangleMesh snapshots must produce byte-identical STL payloads and manifest dictionaries. Output ordering follows the source triangle order. No timestamps, random identifiers, host paths or environment-dependent metadata are serialized.

## 7. Independent reopen validation

The test suite must contain a separately implemented binary STL reader that does not call production export helpers or reuse their facet-packing code. It must parse the 80-byte header, count and 50-byte records directly, then verify:
- Exact byte length and facet count.
- Finite float32 normals/vertices and zero attribute bytes.
- Source triangle order, winding and quantized coordinate correspondence.
- Manifest digest, frame/unit, provenance and coordinate error.
- Bounding box and signed volume within the precision-derived reference bound.
- Rejection of truncation, trailing bytes, malformed count, non-finite values, non-zero attributes, digest mismatch and metadata mismatch.

An external CAD application reopen test remains UNKNOWN until a tool is selected through TECH-001/TECH-002 evaluation. The independent test reader is not a substitute for that future external interoperability gate.

## 8. Acceptance criteria for implementation

- Versioned manifest schema and strict serializer/validator.
- Public API export with documented byte and manifest return types.
- Validated input mesh required; unsupported or invalid meshes fail closed.
- Deterministic binary STL bytes with exact count/length and zero attributes.
- Float32 quantization and degenerate-facet rejection are tested.
- Independent test-only reader validates payload and reference metrics.
- Tests cover Box, Cylinder, straight profile, polygonal holes and circular-arc profiles.
- Unit/frame/provenance/tolerance survive in the sidecar and expected-context checks.
- No third-party runtime dependency or claim of STEP/3MF/B-rep support.

## 9. Explicit non-claims and follow-up gates

This contract does not implement STL export or import, STEP/3MF exchange, external CAD reopen, B-rep, mesh self-intersection detection/repair, mesh Boolean operations, manufacturing checks, physical validation or certification. STEP support remains gated on a CAD-kernel/toolchain decision and independent interoperability evidence.
