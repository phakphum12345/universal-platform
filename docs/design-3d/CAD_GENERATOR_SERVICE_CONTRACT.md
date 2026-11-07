# CAD Generator Service Contract v1.0

**Status:** In-process, transport-neutral service implementation.  
**Implementation:** `engineering/cad_generator_service.py`; public exports from `universal_platform.engineering`.  
**Scope:** Local revisioned FeatureHistory persistence and allow-listed deterministic regeneration.

## 1. Purpose

Provide one stable application-service boundary that joins the immutable FeatureHistory revision store, validated FeatureArtifact cache and bounded regeneration engine. A caller should not need to orchestrate SQLite stores or compute cache keys directly.

This is not an HTTP server, network listener, plugin host, CAD GUI or general geometry kernel.

## 2. Dependencies

`CADGeneratorService` requires explicit instances of:

- `SQLiteFeatureHistoryStore` — append-only source document revisions with optimistic concurrency and SHA-256 revision-chain verification.
- `SQLiteFeatureArtifactCache` — optional-to-use-by-direct-library-call but required by this service; local immutable artifact snapshots with strict rehydration and exact computation-signature matching.

Both stores use caller-supplied filesystem database paths. The service does not create a default global database path or bind a network port.

## 3. Operations

### Save a typed history

```python
revision = service.save_history(history, expected_revision=0)
```

The expected revision is 0 for initial creation or the current head revision for an append. A stale writer receives `FeatureHistoryRevisionConflict`; existing revisions are never overwritten.

### Save a JSON-compatible snapshot

```python
revision = service.save_snapshot(snapshot, expected_revision=revision_number)
```

The snapshot is parsed by strict `FeatureHistory.from_dict` validation before persistence. Unknown fields, malformed IDs, invalid DAG references and non-finite data are rejected.

### Read a revision

```python
revision = service.get_revision(history_id, revision=revision_number)
numbers = service.list_revisions(history_id)
```

Omitting the revision selects the current durable head. An explicit revision selects that immutable source snapshot.

### Regenerate

```python
run = service.regenerate(history_id, revision=revision_number)
response = run.to_dict()
```

The service loads and verifies the exact source revision, invokes `regenerate_feature_history` with the configured artifact cache, and binds the result to the source revision metadata. Cache hits require exact history ID, feature ID, computation SHA-256 and per-feature algorithm version. Missing cache entries are computed and saved.

## 4. Response envelope

`CADGeneratorRun.to_dict()` returns:

- `schema_version`
- `history_id`
- `source_revision`: revision number, parent digest, content digest and creation timestamp
- `regeneration`: status, execution order, artifacts, failed feature, error, reused IDs and recomputed IDs
- `limitations`: explicit authority and deployment boundaries

The source revision digest is the durable revision-envelope digest, not the raw FeatureHistory snapshot digest. Artifact content digests identify canonical output payloads; computation digests identify the exact input/algorithm signature.

A successful service operation means regeneration completed. Engineering PASS still depends on each artifact's geometry/mesh validation; operational status must not be interpreted as certification.

## 5. Failure semantics

- Invalid snapshots/dependencies: `InvalidModelError`.
- Stale source revision writes: `FeatureHistoryRevisionConflict`.
- Unknown source history/revision: `KeyError` from the underlying revision store.
- Source store corruption: `FeatureHistoryStoreIntegrityError`.
- Artifact cache corruption: regeneration returns FAILED with no partial artifacts.
- Feature/model/solver validation failure: regeneration returns FAILED with no partial artifacts.
- No fallback to a different source revision is performed after an explicit revision is requested.

## 6. Security and authority

- Only built-in allow-listed `SKETCH_PROFILE`, `PLANAR_BOOLEAN`, `EXTRUSION` and `MESH` operations execute.
- Feature parameters are data; no user Python, shell, plugin or dynamic import is executed.
- No network calls, HTTP listener, public bind, firmware write, device control, physical actuation or deployment is performed.
- SQLite paths are explicit inputs. No implicit default path or port is selected.
- SHA-256 checks detect corruption but are not keyed signatures and do not protect against an attacker who can rewrite the entire local database.

## 7. Transport boundary — future work

A future HTTP/CLI/UI adapter must be a separate reviewed increment. Before any network listener is enabled, define authentication, authorization, request-size and time limits, loopback-only default binding, explicit opt-in for remote access, audit evidence, cancellation semantics, structured error mapping and tests proving no public/SSH exposure. This service alone does not grant network authority.

## 8. Acceptance evidence

- Save a source revision and load it by exact revision number.
- Regenerate the exact revision and return source revision provenance.
- Reuse matching cached artifacts and report reused/recomputed feature IDs.
- Preserve stale-write conflict behavior and reject malformed snapshots.
- Verify the complete two-store fresh-process workflow in `tests/test_feature_history_durable_e2e.py`.
- Exact PR-head and post-merge CI must pass before promotion.
