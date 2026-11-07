# FeatureHistory Editing Contract

**Status:** Initial implementation slice — immutable graph-edit operations.  
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

The operations are pure transformations: the input FeatureHistory is never mutated. Every returned document is reconstructed through the strict FeatureHistory validator.

## 3. Persistence and regeneration

- The service exposes revision-checked add/replace/remove operations and appends the returned document using the existing SQLite compare-and-swap store.
- The loopback API exposes POST /v1/histories/{history_id}/edit with strict operation-specific request fields.
- Revision conflicts return HTTP 409; editing does not bypass optimistic concurrency.
- Regeneration is a separate operation and must run against the persisted revision.
- Existing content-addressed artifact caching remains keyed by computation signatures.
- Stable feature IDs are not silently renamed. A future rename operation must update all dependency references and be specified as a separate graph migration.

## 4. Explicit limitations

This slice does not implement feature suppression, reordering semantics, undo/redo, branch/merge history, browser GUI edit controls, expression parameters, arbitrary B-rep editing, face/edge/vertex selection, or new geometry operations. Feature order for execution remains deterministic topological order, not the stored tuple order.

## 5. Acceptance criteria

- Add, replace and remove return new immutable histories.
- Duplicate IDs, missing references and cycles fail closed.
- Replacement preserves feature identity.
- Removal refuses downstream breakage unless cascade is explicit.
- Cascade removal removes all transitive dependents.
- At least one valid output remains.
- Unit tests cover success and failure paths.
- Service/API tests verify append-only revision creation, stale-writer conflicts and strict request parsing.
- Browser UI remains read-only; interactive edit controls are a separate follow-on.
