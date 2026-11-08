# FeatureHistory Suppression Contract — Proposed Schema v1.1

**Status:** Backend model/editor/regeneration IMPLEMENTED by PR #163; revision-safe service/API operations are in PR #165 pending CI/merge; workbench integration remains open.  
**Depends on:** FeatureHistory v1.0, immutable revision store, revision-safe edit API, local workbench and real-browser E2E gate.  
**Purpose:** Define suppression and unsuppression semantics before changing source schemas, persistence, regeneration or UI behavior.

## 1. Goals and non-goals

Suppression temporarily excludes a feature and its computed artifact from a regenerated document without deleting the source node or rewriting prior revisions. Unsuppression restores the node only when its dependencies are active and the resulting graph remains valid.

This contract does not implement arbitrary feature reordering, feature renaming, branch/merge history, undo/redo UI, new geometry operations, user code, plugins or physical-device actions.

## 2. Versioned source representation

FeatureHistory v1.1 adds a history-level `suppressed_feature_ids` array. It is a canonical, duplicate-free, lexicographically sorted set of existing feature IDs.

Compatibility requirements:

- Continue accepting strict v1.0 snapshots with the original exact field set.
- A v1.0 snapshot round-trips byte-for-byte at the canonical JSON value level as v1.0; loading it must not silently rewrite old revision content or invalidate its stored SHA-256 revision digest.
- New histories created by existing v1.0 callers remain v1.0 unless an explicit migration or suppression edit upgrades the returned document.
- Suppression/unsuppression edits produce v1.1 snapshots. A v1.1 snapshot includes `suppressed_feature_ids`, including an empty array when nothing is suppressed.
- Strict import rejects unknown fields, duplicate IDs, unsorted/non-canonical suppression IDs, references to missing nodes and unsupported schema versions.
- The SQLite revision-store envelope and database schema do not need to change solely for this document-schema increment. Old immutable revisions remain readable and retain their original digest; the first v1.1 edit appends a new revision whose parent digest points to the old revision.
- Provide an explicit, deterministic v1.0 → v1.1 migration helper. Migration must preserve node IDs, node order, dependencies, parameters and outputs, adding only an empty suppression set.

Do not silently change the existing v1.0 serializer or reinterpret old stored JSON as v1.1.

## 3. Graph invariants

For a history with node set N, dependency edges E, outputs O and suppressed set S:

1. S must be a subset of N.
2. At least one output must remain active: O − S is non-empty.
3. An active node must not depend directly or transitively on a suppressed node. The suppression edit operation must suppress the target's transitive dependents when cascade is explicitly requested; otherwise it must reject suppression if active dependents exist.
4. A suppressed node remains in the source DAG and retains its stable ID, kind, inputs and parameters.
5. Suppression does not rewrite or reorder the graph. Deterministic topological ordering remains unchanged.
6. Cycles, dangling references, duplicate node IDs and invalid outputs remain rejected by the existing FeatureHistory validator.

A suppressed output is allowed only when another declared output remains active. Suppressing the last active output is rejected. No implicit output reassignment is permitted.

## 4. Edit semantics

### Suppress

- `suppress_feature(history, feature_id, cascade=False)` returns a new immutable history.
- Reject unknown feature IDs and invalid cascade types.
- Without cascade, reject if any active transitive dependent exists.
- With cascade, add the target and every transitive dependent to the suppressed set.
- Reject the operation if it would suppress every output.
- Repeated suppression is idempotent and does not mutate the input object.
- Suppression never deletes nodes or artifacts from prior immutable revisions.

### Unsuppress

- `unsuppress_feature(history, feature_id)` returns a new immutable history.
- Reject unknown IDs and invalid state.
- Reject unsuppression while any direct dependency remains suppressed.
- Unsuppress only the requested feature; never implicitly unsuppress descendants.
- A caller can restore a suppressed chain in dependency order, one revision at a time.
- The active-output invariant must remain satisfied.

All edits pass through the existing expected-revision compare-and-swap path. A stale expected revision returns the existing revision-conflict result and creates no revision.

## 5. Regeneration semantics

- Suppressed nodes are skipped and produce no artifact in the returned run.
- Active nodes execute in the existing deterministic topological order.
- Because active nodes cannot depend on suppressed nodes, every active dependency artifact must exist before its consumer executes.
- The result reports the suppressed feature IDs separately from active execution order, artifacts, reused IDs and recomputed IDs.
- At least one active declared output must be regenerated successfully for the run to be successful.
- Any active-feature failure retains the existing fail-closed behavior: status FAILED and no partial artifact list.
- Suppression state is source-document state and therefore changes the source revision digest. It is not executable code and never expands the built-in feature allow-list.

## 6. Artifact-cache behavior

The cache remains keyed by history ID, feature ID and computation signature. Suppression does not alter a feature's geometry computation signature because it does not alter that feature's inputs or parameters.

- Suppressed features are not loaded or emitted during that regeneration.
- Existing immutable cache entries are retained; suppression is not a cache deletion or invalidation command.
- After unsuppression, an artifact may be reused only if the exact algorithm-version-aware computation signature still matches.
- Downstream features whose inputs changed must continue to recompute through the existing digest propagation.
- No cache pruning, cleanup or database mutation is implied.

## 7. Service, API and workbench behavior

- Extend the service edit allow-list with `suppress` and `unsuppress`; preserve exact operation-specific request fields. PR #165 adds this service/API slice, pending exact-head and post-merge CI.
- Suppress accepts `feature_id`, `cascade` and `expected_revision`; unsuppress accepts `feature_id` and `expected_revision`.
- The HTTP API continues to require bearer authentication, same-origin loopback access, strict JSON parsing and current-head optimistic concurrency.
- Historical revisions remain read-only.
- The UI must display suppressed state explicitly, keep suppressed nodes visible in the feature tree, and distinguish suppression from deletion.
- Cascading suppression requires an explicit user confirmation. No implicit cascade is allowed.
- Unsuppress controls are disabled or rejected until dependencies are active; server-side validation remains authoritative.
- UI state is not persisted outside the revisioned FeatureHistory document.

## 8. Acceptance matrix

| Area | Required evidence |
|---|---|
| Compatibility | v1.0 strict load/round-trip; v1.0 revision digest remains valid after reopen; explicit v1.0 → v1.1 migration |
| Validation | Unknown IDs, duplicate/unsorted suppression IDs, missing nodes, invalid outputs and unsupported versions reject |
| Suppress | Leaf suppression; active-dependent rejection; explicit transitive cascade; repeated idempotent suppression |
| Outputs | Multiple outputs; suppress one output while another remains active; reject suppressing the final active output |
| Unsuppress | Restore in dependency order; reject when a dependency remains suppressed; never unsuppress descendants implicitly |
| Regeneration | Suppressed nodes skipped; active execution order deterministic; no active consumer may read a suppressed artifact |
| Cache | Suppressed cache entries are not emitted; exact matching artifacts can be reused after unsuppression; changed inputs invalidate descendants |
| Persistence | New v1.1 edit appends a revision; old revisions remain immutable; stale writer receives conflict |
| API/UI | Strict request parsing, authenticated loopback, historical read-only behavior, explicit cascade confirmation |
| Browser | Chromium tests for suppress, cascade confirmation, unsuppress dependency order, stale revision conflict and safe text rendering |
| Regression | Full Python suite, workflow sanity and browser E2E all pass on exact PR head and post-merge SHA |

## 9. Rollout sequence

1. Implement and test v1.0/v1.1 compatibility and explicit migration in the FeatureHistory model.
2. Add pure immutable suppress/unsuppress transformations and graph invariants.
3. Add regeneration skip/report behavior and cache acceptance tests.
4. Add revision-safe service and strict HTTP API operations.
5. Add workbench state, explicit cascade confirmation and browser E2E.
6. Update implementation status and traceability only after exact-head and post-merge evidence.

Each step is a separate reviewable change. Do not combine schema migration, editor behavior and UI work into one untestable change.

## 10. Implementation status and non-claims

PR #163 merged the first backend slice at `e6a6196aeaa84fca2eff8ce2f0417cc0a4014c2b`:

- FeatureHistory v1.0/v1.1 strict parsing and serialization, with explicit v1.0 → v1.1 migration.
- Preservation of v1.0 snapshots and immutable revision digests across store reopen; a suppression edit appends a v1.1 revision.
- Immutable suppress/unsuppress transformations with explicit cascade, active-output validation and dependency-order restoration.
- Regeneration skips suppressed nodes and reports suppressed IDs; the artifact cache is not deleted or cleaned.
- JSON Schema and public package exports for the new model/helper operations.

PR #165 adds revision-safe service/API mutation operations with strict request fields and expected-revision compare-and-swap; it remains pending validation. Workbench controls, cascade confirmation UI and suppression-specific browser E2E remain open. Those are required before claiming end-to-end suppression capability. Exact PR-head and post-merge evidence for PR #163: 851 Python tests, 4 Chromium E2E tests and workflow-sanity all PASS.
