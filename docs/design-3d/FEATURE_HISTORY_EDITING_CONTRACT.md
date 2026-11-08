# FeatureHistory Editing Contract

**Status:** Backend graph editing and local workbench controls implemented in bounded slices (PRs #152, #154 and current UI slice).  
**Scope:** Source FeatureHistory document editing; not geometry-kernel editing or a complete interactive CAD editor.

## 1. Purpose

Provide validated, immutable operations for adding, replacing and removing nodes in a FeatureHistory DAG. Editing produces a new in-memory source document. Persistence remains the responsibility of the existing revisioned CAD Generator service.

## 2. Operations

| Operation | Behavior | Safety rule |
|---|---|---|
| Add | Append a new node and optionally make it an output | Reject duplicate IDs; validate all references and graph acyclicity |
| Replace | Replace an existing node without changing its ID | Preserve stable identity; validate dependencies and cycles |
| Remove | Remove one node | Reject removal when dependents exist unless cascade is explicitly requested |
| Cascade remove | Remove a node and all transitive dependents | Remove affected outputs and reject a result with no output |
| Reorder | Change the stored feature-tree presentation sequence | Must be a complete permutation and preserve dependency-before-dependent order; execution order remains dependency-derived and unchanged |

The operations are pure transformations: the input FeatureHistory is never mutated. Every returned document is reconstructed through the strict FeatureHistory validator.

## 3. Persistence and regeneration

- The service exposes revision-checked add/replace/remove operations and appends the returned document using the existing SQLite compare-and-swap store.
- The loopback API exposes POST /v1/histories/{history_id}/edit with strict operation-specific request fields.
- Revision conflicts return HTTP 409; editing does not bypass optimistic concurrency.
- Regeneration is a separate operation and must run against the persisted revision.
- Existing content-addressed artifact caching remains keyed by computation signatures.
- Stable feature IDs are not silently renamed. A future rename operation must update all dependency references and be specified as a separate graph migration.

## 4. Explicit limitations

This slice does not implement branch/merge history, expression parameters, arbitrary B-rep editing, face/edge/vertex selection, or new geometry operations. Reordering is presentation-only: the stored node sequence must be a complete topological presentation order, while execution remains deterministic and dependency-derived. PR #174 adds current-head-gated Move Up/Move Down controls and real-browser acceptance. Browser controls provide basic add/replace/remove operations only. Real Chromium browser automation/E2E interaction coverage is implemented and passing (PR #158); it does not expand the feature-editing capability boundary. Feature order for execution remains deterministic topological order, not the stored tuple order.

## 5. Acceptance criteria

- Add, replace and remove return new immutable histories.
- Duplicate IDs, missing references and cycles fail closed.
- Replacement preserves feature identity.
- Removal refuses downstream breakage unless cascade is explicit.
- Cascade removal removes all transitive dependents.
- At least one valid output remains.
- Unit tests cover success and failure paths.
- Service/API tests verify append-only revision creation, stale-writer conflicts and strict request parsing.
- Browser UI exposes parameter replacement, feature add and feature removal through the revision-safe local API.
- Historical revisions are read-only in the UI; edits are allowed only when the selected revision equals the current head.
- Cascade removal requires an explicit confirmation checkbox.
- Browser E2E interaction tests remain a separate quality gate.


## 6. Real-browser verification — PR #158

- Dedicated GitHub Actions workflow: `.github/workflows/cad-browser-e2e.yml`.
- Four Chromium tests cover workbench startup and uncaught page errors, current-head versus historical-revision editing gates, parameter replacement/add/remove with explicit cascade confirmation, stale-writer HTTP 409 behavior, and safe text-only rendering.
- Exact PR head `9aa96157eb6e5ebbf324aa6614178ffd8af17495`: browser E2E PASS (4 tests); Python suite PASS (843 tests); workflow sanity PASS.
- Exact merge SHA `9d899f70a97372f689ba07a8e90b479bf14494b4`: post-merge browser E2E PASS (4 tests), Python suite PASS (843 tests), workflow sanity PASS.
- Browser coverage is a distinct verification gate; it does not imply feature suppression, reordering, undo/redo, or broader CAD editing support.


## 7. Feature-tree presentation reordering — bounded semantics

- A reorder request supplies the complete ordered feature-ID tuple; partial moves and duplicate/unknown IDs are rejected.
- Every dependency must appear before its dependent. A reorder cannot change dependency edges, feature IDs, parameters, outputs or suppression metadata.
- Reordering creates a new immutable source revision through the existing expected-revision compare-and-swap path.
- `FeatureHistory.topological_order()` remains unchanged and determines execution order independently of stored presentation order. No geometry recomputation semantics are changed by this operation.
- Reordering is not graph editing, dependency rewiring, feature execution reprioritization, branch/merge or a general CAD history editor.
