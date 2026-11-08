# FeatureHistory Presentation Reordering Contract

**Status:** Backend editor, revision-safe service and strict loopback API implementation submitted in PR #173; workbench controls and browser acceptance remain a separate slice.  
**Scope:** Reorder the FeatureHistory tree's stored presentation sequence without changing dependency edges or regeneration execution order.

## Invariants

1. Reordering is a complete permutation of every existing feature ID.
2. Duplicate, missing and unknown IDs are rejected.
3. Every direct dependency must appear before its dependent in the requested sequence.
4. Feature IDs, kinds, parameters, dependencies, outputs and suppression metadata are unchanged.
5. The source document is immutable; a successful reorder appends a new revision using the current expected revision.
6. Execution remains governed by `FeatureHistory.topological_order()`; it does not adopt presentation order as an execution priority.
7. Reordering does not invoke feature operations, run regeneration, delete revisions or mutate artifact-cache records.
8. Historical revisions remain read-only; stale writers receive the existing revision conflict.

## API

`POST /v1/histories/{history_id}/edit`

Exact body:
```json
{
  "expected_revision": 1,
  "operation": "reorder",
  "ordered_feature_ids": ["base", "independent", "dependent"]
}
```

Unknown fields are rejected. The ID array must be a complete valid topological presentation order.

## Explicit non-claims

This contract does not define execution reprioritization, dependency rewiring, feature suppression, graph branch/merge, geometry-kernel editing, recompute propagation or a complete CAD editor. Browser presentation controls and real-browser acceptance are separate follow-up work.
