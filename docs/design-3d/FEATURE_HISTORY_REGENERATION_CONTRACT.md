# Feature History and Regeneration Contract v1.0

**Status:** Bounded implementation — PR #93 merged to integration.  
**Merge SHA:** `0983de4c8839070e2a27cd7b8e704f975d176abf`.  
**Exact PR-head CI:** run #42263173745 — both required jobs PASS, 636 tests.  
**Post-merge CI:** run #42263296016 — both required jobs PASS, 636 tests.  
**Main:** unchanged at `96e75010716226037893155b9fd4b13410fb0d6f`.

## 1. Purpose

Represent a parametric design as a versioned directed acyclic graph (DAG) of immutable feature records and regenerate its supported outputs deterministically from source parameters.

This is a bounded, offline feature evaluator. It is not yet a full commercial CAD history editor, persistent document service or general geometry kernel.

## 2. Graph model

- `FeatureHistory` has a stable history ID, immutable feature-node sequence and one or more output feature IDs.
- `FeatureNode` has a stable ID, allow-listed kind, ordered dependency IDs and canonical JSON parameters.
- Feature IDs must be unique; all dependencies and outputs must resolve.
- Self-dependencies, duplicate references and dependency cycles are rejected.
- Topological order is deterministic: among currently ready nodes, feature IDs are processed lexicographically.
- Snapshots are schema-versioned and strict; unknown fields and unsupported kinds are rejected.
- Schema: `schemas/geometry/feature-history.schema.json`.

## 3. Executable built-in features

| Kind | Inputs | Parameters | Output |
|---|---|---|---|
| SKETCH_PROFILE | none | ParametricSketch v1.0 snapshot | solved sketch → canonical PlanarRegion set |
| PLANAR_BOOLEAN | 2+ region-producing features | operation | PlanarRegion set |
| EXTRUSION | one region-producing feature | solid_id, height, optional region_index | analytic ExtrudedProfileSolid |
| MESH | one extrusion feature | none | TriangleMesh plus validation report |

The complete tested vertical slice is:

`ParametricSketch → SKETCH_PROFILE → PLANAR_BOOLEAN (optional) → EXTRUSION → MESH`

## 4. Regeneration and evidence

- All built-in operations execute in deterministic topological order.
- Feature parameter snapshots are canonical JSON; generated payloads receive SHA-256 content digests.
- A successful run exposes each artifact, execution order and digest.
- A failed feature aborts regeneration and returns no partial artifacts. The failed feature ID and reason are explicit.
- Sketch constraints must converge before a region can be generated.
- Mesh output must pass validity, watertightness and consistent-orientation checks.
- Repeated regeneration of the same history produces identical artifact digests; changing a source dimension changes downstream digests.

## 5. Security boundary

Only hard-coded, allow-listed operations execute. Feature parameters are data, not executable code. The engine does not invoke user Python, plugins, shell commands, network calls, firmware writes, device control or physical actuation.

## 6. Explicit limitations

Not yet implemented: persistent document storage, incremental recomputation/cache invalidation, feature suppression, rollback/branch/merge editing, interactive GUI, constraints/parameter expression language, feature migration tooling, generalized B-rep, arbitrary 3D Boolean, STEP/3MF, assembly-level feature contexts, or manufacturing/certification validation.

The current sketch-to-region converter accepts only closed straight-edge loops. The current planar Boolean engine remains bounded and fails closed on point-touching/branching outputs. The current extrusion and mesh operations retain their documented straight-edged limits.

## 7. Acceptance evidence

- DAG missing-reference, duplicate-ID, self-reference and cycle rejection.
- Strict FeatureHistory and ParametricSketch snapshot round trips.
- Deterministic topological order and stable per-feature hashes.
- Sketch → extrusion → mesh end-to-end regeneration.
- Two sketches → planar UNION → extrusion → mesh end-to-end regeneration.
- Failed extrusion returns FAILED and no partial artifacts.
- Exact PR-head and post-merge CI each pass 636 tests.
