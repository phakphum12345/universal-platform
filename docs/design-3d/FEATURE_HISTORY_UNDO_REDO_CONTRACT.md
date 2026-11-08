# FeatureHistory Undo/Redo Contract — Revision Restore Model

**Status:** Store layer implemented by PR #169, merged at `93744335f3e50a07dde2f78a18f9a307308b73ef`; service/API implementation is in PR #170 pending CI/merge; workbench integration remains open.  
**Scope:** One linear editing session per FeatureHistory, with persistent undo/redo state backed by immutable source revisions.  
**Depends on:** FeatureHistory revision store, expected-revision compare-and-swap, authenticated loopback API, workbench current-head gating and audit log.

## 1. Goal

Provide reliable Undo and Redo without mutating or deleting any previously committed FeatureHistory revision. Undo/Redo must survive page reload, remain safe under concurrent writers and preserve the existing immutable SHA-256 revision chain.

Undo/Redo is not branch/merge. It is a linear sequence of new revisions whose content restores a prior immutable snapshot.

## 2. Core invariants

1. Existing revisions remain append-only and immutable.
2. Undo and Redo never delete revisions, snapshots, audit entries or artifact-cache records.
3. Every Undo/Redo appends a new revision with the current head digest as its parent digest.
4. The restored snapshot is copied from an existing revision of the same history ID and is revalidated through the current strict FeatureHistory parser before saving.
5. Every mutation requires the exact current `expected_revision`; stale writers receive the existing revision-conflict response and do not alter either stack.
6. Undo/Redo are available only on the current head. Historical revision views remain read-only.
7. A normal edit after an Undo clears the Redo stack. This prevents replaying a redo path that no longer follows the current edit sequence.
8. Navigation state is persisted in the same database and transaction as the appended revision. A crash cannot append a revision without updating its undo/redo stacks, or update stacks without appending the revision.

## 3. Persistent navigation state

Add a non-destructive SQLite table, for example `feature_history_navigation`:

- `history_id` — primary key, references the owning history logically.
- `undo_stack_json` — ordered array of immutable revision numbers; the last element is the next Undo target.
- `redo_stack_json` — ordered array of immutable revision numbers; the last element is the next Redo target.
- `updated_at` — UTC timestamp.

The table is created with `CREATE TABLE IF NOT EXISTS`. Existing revision tables and rows are not rewritten.

### Existing-history initialization

For a history with revisions 1..N and no navigation row, initialize the Undo stack to [1..N-1] and Redo to []. This gives existing histories a deterministic undo path. Revision N remains the current head.

The implementation must validate that every stack entry belongs to the same history and refers to an existing revision. Invalid or corrupt navigation metadata fails closed; it must not guess or silently repair the stacks.

## 4. State transitions

### Normal edit

When a normal edit appends revision N+1:

- Push the previous current head N onto the Undo stack.
- Clear the Redo stack.
- Append the new snapshot as revision N+1.
- Commit the new revision and navigation state atomically.

### Undo

Given current head N:

- Reject with `NO_UNDO` when the Undo stack is empty.
- Pop target revision U from the Undo stack.
- Push current head N onto the Redo stack.
- Load and validate immutable snapshot U.
- Append a new revision N+1 containing the exact canonical snapshot content from U.
- Parent digest is the previous current head N digest.
- Record operation metadata `undo`, target revision U and source head N.

### Redo

Given current head N:

- Reject with `NO_REDO` when the Redo stack is empty.
- Pop target revision R from the Redo stack.
- Push current head N onto the Undo stack.
- Load and validate immutable snapshot R.
- Append a new revision N+1 containing the exact canonical snapshot content from R.
- Parent digest is the previous current head N digest.
- Record operation metadata `redo`, target revision R and source head N.

All stack transitions and revision appends must be one SQLite transaction.

## 5. Worked sequence

Starting with revision 1:

| Action | New head | Undo stack (next at right) | Redo stack (next at right) |
|---|---:|---|---|
| Initial | 1 | [] | [] |
| Edit A | 2 | [1] | [] |
| Edit B | 3 | [1, 2] | [] |
| Undo | 4 (content of 2) | [1] | [3] |
| Undo | 5 (content of 1) | [] | [3, 4] |
| Redo | 6 (content of 2) | [5] | [3] |
| Redo | 7 (content of 3) | [5, 6] | [] |
| New edit C | 8 | [5, 6, 7] | [] |

The sequence demonstrates that Undo/Redo append new revisions; they never move the head pointer backwards or rewrite existing revisions.

## 6. Store and service contract

PR #169 merged the store exposes transactional methods such as:

- `undo(history_id, expected_revision)`
- `redo(history_id, expected_revision)`
- `get_navigation_state(history_id, expected_revision)`

The service maps empty stacks to explicit domain errors (`NO_UNDO`, `NO_REDO`) and stale heads to the existing revision-conflict error.

Normal save/edit operations update the navigation stacks atomically. Direct database manipulation, stack edits from the browser and arbitrary target revision restore requests are not allowed.

## 7. HTTP API contract

- `POST /v1/histories/{id}/undo` — exact body: `{ "expected_revision": N }`.
- `POST /v1/histories/{id}/redo` — exact body: `{ "expected_revision": N }`.
- `GET /v1/histories/{id}/navigation` — returns current revision, `can_undo`, `can_redo`, stack depths and the expected revision.
- Undo/Redo require the existing bearer token, same-origin loopback request, request-size limits, strict JSON fields and append-only audit logging.
- Unknown fields, wrong types, invalid history IDs and stale revisions are rejected.
- No arbitrary `target_revision` is accepted from the client.

## 8. Workbench behavior

- Undo/Redo buttons are visible but enabled only when connected to the current head and the API reports availability.
- Buttons are disabled while a mutation is in progress.
- After success, refresh current revision, navigation state and feature tree from the server.
- Historical revision browsing never enables Undo/Redo.
- After a new edit following Undo, the Redo button becomes disabled because the server cleared the redo stack.
- The UI does not keep the authoritative stack in memory or browser storage.

## 9. Audit and observability

Each Undo/Redo request is recorded through the existing append-only API audit log with operation, history ID, expected revision, resulting revision, target revision, status and request/response digests. Do not log bearer tokens or sensitive request payloads.

Navigation state responses must not expose raw SQLite paths, tokens or unrelated history records.

## 10. Acceptance matrix

| Area | Required evidence |
|---|---|
| Existing data | Existing histories initialize deterministic Undo stacks without rewriting revisions |
| Immutability | Undo/Redo append revisions; prior snapshot JSON and digests remain unchanged |
| State machine | Multi-step Undo/Redo sequence matches the worked table |
| Persistence | Close/reopen store and server; Undo/Redo state remains correct |
| New edit | New edit after Undo clears Redo atomically |
| Concurrency | Stale expected revision changes neither stack nor revision count |
| Integrity | Missing/cross-history stack targets, invalid JSON and corrupted state fail closed |
| Audit | Every successful and rejected operation is auditable without token leakage |
| API | Strict body parsing, auth, loopback, status codes and navigation endpoint |
| UI | Current-head gating, historical read-only, availability, disabled-while-busy |
| Browser | Chromium tests for multi-step Undo/Redo, reload persistence, redo invalidation and stale-writer conflict |
| Regression | Full Python suite, workflow sanity and Chromium E2E pass on exact PR head and post-merge SHA |

## 11. Rollout sequence

1. Add SQLite navigation-state table and deterministic legacy initialization.
2. Implement atomic store Undo/Redo transactions and migration/corruption tests.
3. Add service operations and domain errors.
4. Add strict HTTP endpoints and navigation-state read endpoint.
5. Add workbench controls and browser E2E.
6. Update requirements traceability and implementation status after exact-head and post-merge CI.

Each stage is reviewable and may be merged independently. No branch/merge history is implied.

## 12. Implementation status and non-claims

PR #169 merged the store-level slice at `93744335f3e50a07dde2f78a18f9a307308b73ef`:

- Additive SQLite navigation and revision-action metadata tables.
- Deterministic legacy initialization from existing immutable revision chains.
- Persistent Undo/Redo stacks with atomic append-only restore revisions.
- Expected-revision compare-and-swap, explicit `NO_UNDO`/`NO_REDO` results and fail-closed stack integrity checks.
- Operation/source/target revision metadata and navigation-state reads.
- Store tests for multi-step transitions, restart persistence, redo invalidation after new edits, legacy backfill, stale writers and corrupted state.

Exact PR-head and post-merge CI for PR #169 passed 860 Python tests and workflow-sanity. PR #170 adds the service/API layer: persistent navigation-state reads, strict undo/redo endpoints, expected-revision checks and explicit NO_UNDO/NO_REDO responses; exact-head CI is pending. Workbench controls and Chromium navigation E2E remain open. Undo/Redo is not end-to-end complete until those layers pass exact-head and post-merge evidence.

This does not claim graph branching/merging, collaborative editing, arbitrary revision selection as a mutation, or whole-repository completion.
