# FeatureHistory Branch and Merge Contract

**Status:** Design contract — implementation not yet claimed.  
**Scope:** First bounded branch/fork and three-way merge workflow for immutable FeatureHistory revisions.

## 1. Goals

- Allow an engineer to isolate experimental edits from a stable FeatureHistory line.
- Preserve the existing append-only, per-history SHA-256 revision chain.
- Merge compatible changes without rewriting or deleting any source revision.
- Detect semantic conflicts and fail closed rather than silently choosing a winner.
- Keep execution deterministic and dependency-safe after a merge.

## 2. Non-goals

This contract does not introduce collaborative real-time editing, distributed replication, remote synchronization, arbitrary cherry-picking, rebase, squash history rewriting, binary geometry conflict resolution, automatic conflict resolution, plugin execution, or deployment.

## 3. Branch identity and storage model

The current store has one linear revision chain and one mutable head per `history_id`. A branch MUST therefore be represented as a distinct history identity, not as a second head inside the existing linear chain.

- The caller supplies a stable, unique branch history ID and a non-empty branch name.
- Branch creation copies a selected immutable source snapshot into a new history whose `history_id` is the branch history ID. The fork starts at branch revision 1.
- A branch-origin record binds the branch ID/name to the exact source history ID, source revision number and source content SHA-256. It also records creation time and schema version.
- The source history and all its revisions remain unchanged.
- Version 1 permits branching only from a root history, not from another branch. This gives every branch an unambiguous common base and avoids ambiguous merge-base discovery.
- Branch names are unique within the source history; branch IDs are globally unique in the local store.
- Branch-origin metadata is append-only. Renaming, deleting or force-resetting a branch is out of scope.

The branch snapshot MUST preserve feature IDs, node kinds, parameters, dependencies, outputs, suppression state and presentation order. Only the history identity changes.

## 4. Merge eligibility

A merge request names source branch, target history, expected source head revision and expected target head revision.

The target MUST be either:
1. the exact root history from which the source branch was created; or
2. another branch created from the same root history at the same base revision and base digest.

The source and target MUST both be loaded and integrity-verified. The recorded base revision MUST be loaded from the root history and its digest MUST match branch-origin metadata. Missing, corrupt, incompatible or mismatched ancestry blocks the merge.

A merge MUST NOT mutate the source branch. It appends one new immutable revision to the target using target expected-revision compare-and-swap. A stale source or target head MUST be rejected before writing.

## 5. Three-way content merge

The merge base is the exact FeatureHistory snapshot captured when the branches were forked. For each feature ID, compare its complete node value (existence, kind, dependency IDs and canonical parameters) in base, source and target:

| Source vs base | Target vs base | Result |
|---|---|---|
| unchanged | unchanged | Keep base |
| changed | unchanged | Take source |
| unchanged | changed | Keep target |
| same change | same change | Keep the shared change |
| different changes | different changes | Conflict |

Deletion is a node value. Delete-vs-edit and incompatible same-ID additions are conflicts. No implicit rename detection is attempted.

Output membership and suppression membership use the same three-way rule as boolean set membership. A divergent change to the same membership item is a conflict.

## 6. Presentation order and graph validity

- If only one side changed the relative order of base feature IDs, retain that side's relative order.
- If both sides changed the relative order of the same base feature IDs incompatibly, report an order conflict.
- New nodes from both sides are combined without changing their node content. The resulting order MUST be a complete topological presentation order.
- The merge implementation MUST reject missing dependencies, cycles, duplicate IDs, invalid outputs, invalid suppression relationships or any final FeatureHistory that fails normal model validation.
- A deterministic tie-breaker MUST be specified and tested for independent new nodes; it MUST NOT be mistaken for execution priority.
- `FeatureHistory.topological_order()` remains the sole deterministic execution-order authority.

The first implementation MUST report conflicts with stable feature IDs and conflict categories. It MUST NOT pick a side, drop a node or mutate dependency edges to make a merge pass.

## 7. Revision and audit semantics

A successful merge appends a target revision with action metadata that identifies:
- operation = `merge`;
- target's prior revision and new revision;
- source branch ID and exact source revision/digest;
- root merge-base history ID, revision and digest;
- merge algorithm/schema version.

The target's prior revisions and source branch revisions remain immutable. The merge result's parent digest is the target's previous head digest. Merge provenance MUST be included in the revision-action record and exposed by revision inspection.

A merge failure MUST leave target head, source head, revision chains and navigation stacks unchanged. Undo/Redo MUST treat a successful merge as a new target edit; it MUST NOT rewind or mutate the source branch.

## 8. Transaction and concurrency requirements

Branch creation and merge metadata writes MUST be transactional with their corresponding initial/target revision writes. The store MUST use SQLite write transactions and verify expected revisions while holding the write lock. A crash or constraint failure MUST roll back all related writes.

No migration may drop or rewrite existing tables, rows, snapshots, hashes or navigation state. Schema migration MUST be additive and tested against databases created by every supported prior schema version.

## 9. Required acceptance tests

### Branch creation
- Fork from root head and from a historical root revision.
- Verify exact base ID/revision/digest provenance.
- Verify the source root remains byte-for-byte unchanged.
- Reject duplicate branch ID/name, malformed IDs/names and invalid source revision.
- Verify branch revision 1 has a valid independent hash chain and correct copied content.

### Merge success
- Source-only add, replace, remove, output change and suppression change.
- Target-only changes are retained.
- Same identical changes on both sides are accepted.
- Independent additions produce deterministic, dependency-safe presentation order.
- Execution topological order remains valid and deterministic.
- Successful merge appends exactly one target revision and preserves all source revisions.

### Merge conflicts and safety
- Same-node divergent parameter/kind/dependency changes.
- Delete-vs-edit and incompatible same-ID additions.
- Divergent output/suppression membership and conflicting presentation order.
- Missing/corrupt merge base, source revision, target revision or provenance.
- Stale source and target expected revisions.
- Cycles, missing dependencies, invalid outputs and invalid suppression dependencies.
- Every failure leaves all heads, revision rows, action metadata and navigation stacks unchanged.

### Regression
- Existing v1.0/v1.1 snapshots, revision hashes, Undo/Redo and reorder behavior remain compatible.
- Full Python suite, workflow sanity and Chromium E2E pass on exact PR head and post-merge SHA.
- No external service, paid dependency, user code execution, network access or physical device action is introduced.

## 10. Implementation sequence

1. Add additive branch-origin metadata and transactional branch creation.
2. Add deterministic three-way merge analysis as a pure function with conflict results.
3. Add transactional target merge append with exact source/target/base provenance and expected-revision checks.
4. Add service and strict loopback API routes.
5. Add branch/merge workbench controls only after backend contracts and tests pass.
6. Add browser acceptance and reconcile requirements, implementation status, roadmap and audit.

Each stage is independently reviewable. The whole FeatureHistory branching/merging requirement remains **OPEN** until all stages and exact-SHA gates pass.


## 11. Branch creation implementation status — PR #176

- PR #176 merged at `2bc96a79c9c341dc896da980c1117d37928023ba`; exact PR head `aa4a24c71242c861fdff387475e711d3e22756c6`.
- Adds additive SQLite schema v2 table `feature_history_branches` for branch ID, root history ID, branch name, exact fork revision/digest and creation timestamp.
- `SQLiteFeatureHistoryStore.create_branch` verifies the source revision, rejects nested forks and duplicate IDs/names, and commits branch revision 1, head, empty navigation stacks and origin metadata in one transaction.
- `get_branch` and `list_branches` expose local branch provenance; `CADGeneratorService.fork_history` is the transport-neutral service entry point.
- Existing revision digest envelope remains v1; migration is additive and preserves existing revision hashes. Regression tests cover historical fork, source independence, suppression preservation and migration.
- Exact PR-head and post-merge CI: workflow-sanity PASS; Python tests PASS (875); Chromium E2E PASS (7).
- **Still OPEN:** three-way merge analysis and append, conflict resolution/reporting, merge provenance, API routes, workbench controls and branch/merge browser acceptance.
