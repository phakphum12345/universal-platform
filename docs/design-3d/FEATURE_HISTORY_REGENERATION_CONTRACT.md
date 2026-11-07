# Feature History and Regeneration Contract v1.0

**Status:** Bounded implementation — PR #93 merged to integration.  
**Merge SHA:** `0983de4c8839070e2a27cd7b8e704f975d176abf`.  
**Exact PR-head CI:** run #42263173745 — both required jobs PASS, 636 tests.  
**Post-merge CI:** run #42263296016 — both required jobs PASS, 636 tests.  
**Main:** unchanged at `96e75010716226037893155b9fd4b13410fb0d6f`.

## 1. Purpose

Represent a parametric design as a versioned directed acyclic graph (DAG) of immutable feature records and regenerate its supported outputs deterministically from source parameters. An optional prior successful in-memory result enables fingerprint-checked reuse of unchanged artifacts.

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
- Incremental regeneration compares a SHA-256 computation signature over feature kind, canonical parameters, ordered input artifact digests and (for sketch features only) solver options. An exact match reuses the prior immutable artifact; a changed source invalidates only that node and descendants whose input artifact digest changes.
- Results report `reused_feature_ids` and `recomputed_feature_ids` in deterministic execution order. Failure still returns no partial artifacts, even if earlier nodes were reused.

## 5. Security boundary

Only hard-coded, allow-listed operations execute. Feature parameters are data, not executable code. The engine does not invoke user Python, plugins, shell commands, network calls, firmware writes, device control or physical actuation.

## 6. Explicit limitations

Not yet implemented: durable computed-artifact cache or geometry rehydration, feature suppression, rollback/branch/merge editing, interactive GUI, constraints/parameter expression language, feature migration tooling, generalized B-rep, arbitrary 3D Boolean, STEP/3MF, assembly-level feature contexts, or manufacturing/certification validation. Incremental recomputation remains an in-memory cache: the caller must retain and explicitly pass a prior successful `FeatureRegenerationResult`. The durable document store described below does not persist or reconstruct computed artifact objects.

The current sketch-to-region converter accepts only closed straight-edge loops. The bounded planar Boolean engine preserves unambiguous point-only contacts as separate simple regions under PR #95; ambiguous branching, coincident outgoing directions and invalid hole topology remain fail-closed. The current extrusion and mesh operations retain their documented straight-edged limits.

## 7. Acceptance evidence

- DAG missing-reference, duplicate-ID, self-reference and cycle rejection.
- Strict FeatureHistory and ParametricSketch snapshot round trips.
- Deterministic topological order and stable per-feature hashes.
- Sketch → extrusion → mesh end-to-end regeneration.
- Two sketches → planar UNION → extrusion → mesh end-to-end regeneration.
- Failed extrusion returns FAILED and no partial artifacts.
- Exact PR-head and post-merge CI each pass 636 tests.


## 8. Durable revisioned source documents

The implementation branch `feat/cad-feature-history-durable-revisions-v1` adds
`SQLiteFeatureHistoryStore` as a local-first persistence layer for source
`FeatureHistory` documents. It is intentionally separate from regeneration
and computed-artifact caching.

- Each save appends an immutable, monotonically numbered revision; prior
  snapshots are retained.
- Callers supply `expected_revision` (0 for initial creation). A SQLite
  `BEGIN IMMEDIATE` transaction checks the current head and appends the new
  revision atomically. A stale writer receives
  `FeatureHistoryRevisionConflict`; it cannot silently overwrite another
  writer's update.
- Each revision stores canonical JSON, a SHA-256 digest over the revision
  envelope, and the preceding revision digest. Reads verify canonical encoding,
  schema round-trip, contiguous revision numbering, parent links, every
  revision digest, and the latest head pointer.
- The database uses SQLite WAL mode, a full synchronous durability setting,
  a busy timeout, and the standard library only. The caller chooses the local
  filesystem database path; in-memory/URI modes are rejected.
- History identifiers are data keys, never filesystem paths. Stored snapshots
  are parsed as data and never executed.
- `load(history_id, revision=...)` can read an earlier immutable revision;
  `list_revisions(history_id)` lists retained revision numbers.

**Boundary:** this persists the source feature DAG only. It does not persist
`FeatureArtifact.value`, solver state, mesh objects, or a durable computation
cache. Those values require explicit versioned serializers and trusted
rehydration contracts before cross-process artifact reuse can be claimed.
There is no suppression, rollback mutation, branch/merge model, replication,
encryption-at-rest, backup scheduler, or distributed consensus in this slice.

## 9. Durable-store acceptance evidence

- Source document round-trip after reopening the SQLite database.
- Append-only revision history and retrieval of earlier revisions.
- Optimistic compare-and-swap conflict across independent store instances.
- Concurrent writer serialization through SQLite transactions.
- Detection of modified snapshot bytes, missing revision links, and a tampered
  latest-head digest.
- Rejection of invalid identifiers, in-memory/URI database modes, invalid
  expected revisions, and unknown documents.
- Exact-head CI must pass before this branch can be considered integrated.
