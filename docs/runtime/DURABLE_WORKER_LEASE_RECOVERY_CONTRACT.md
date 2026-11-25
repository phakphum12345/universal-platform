# WP-09G — Durable Worker Lease and Crash-Recovery Contract

## Live implementation reconciliation — 2026-11-25

- **Current Main baseline:** `24dbf3851cb64e7827234675a832e5abf1876b38` (PR #291 merge).
- **WP-09G-A through D:** integrated on `main` through PR #272 (merge SHA `bb5d016a48bf8329136629dd0d7835e56fa0ece0`); implementation includes the shared append-only journal, durable resource allocator, process identity binding/start gate, liveness inspection and startup lease reconciliation.
- **WP-09G-E implementation slice:** integrated by PR #277 (merge SHA `87c19a9752e43ea051dac0aa302fb85323d130ce`); it provides a host-injected `authenticate_and_authorize` port, freshness-bounded operator authentication and process-liveness evidence, identity-bound `ABSENT` proof, durable `LEASE_FORCE_RELEASED` journal event and chain-hash audit reference.
- **WP-09G-E acceptance remains OPEN:** production host identity-provider and trusted authorization wiring, operator-facing API integration and owner acceptance are not established by the in-process port alone.
- **Security boundary remains PARTIAL:** process supervision/Job Objects are not a general sandbox; privilege, filesystem/network isolation and OS CPU/RAM/I/O enforcement are not established.
- **CI:** exact-SHA post-merge CI for the current Main baseline `24dbf385...` is **UNKNOWN** in this reconciliation. Do not reuse PR #286 CI as evidence for the newer Main SHA.

## Historical implementation reconciliation — 2026-11-22 (superseded)

- **Main baseline:** `2c8a1542f8d051a42348feeb7dd0ce55fc6b4607` (PR #278 merge; includes PR #279).
- **WP-09G-A through D:** integrated on `main` through the durable runtime chain and PR #272 (merge commit `bb5d016a48bf8329136629dd0d7835e56fa0ece0`). The implementation includes the shared append-only journal, durable resource allocator, process identity binding/start gate, liveness inspection and startup lease reconciliation.
- **WP-09G-E implementation slice:** integrated by PR #277 (merge commit `87c19a9752e43ea051dac0aa302fb85323d130ce`). The service provides a host-injected `authenticate_and_authorize` port, freshness-bounded operator authentication and process-liveness evidence, identity-bound `ABSENT` proof, durable `LEASE_FORCE_RELEASED` journal event and chain-hash audit reference. PRESENT, UNKNOWN, stale/mismatched evidence, authorization denial and journal-write failure retain quarantine.
- **WP-09G-E production acceptance remains OPEN:** the repository does not yet provide a trusted production identity-provider adapter or host/API wiring. No mock authorizer is a production default; the recovery service is not an exposed operator login or production recovery endpoint.
- **CI evidence:** PR #277 merge SHA passed Repository Quality, Workflow Sanity, Python Tests and Windows Process Supervisor. PR #279 enabled Cross-Shell validation; PR #278 then merged the local CAD Generator launcher. Verify post-merge CI on the current Main SHA before claiming Main CI acceptance.
- **Non-claims:** No general OS sandbox, privilege separation, filesystem/network isolation, or OS CPU/memory/I/O enforcement is established.
- **Next slice:** integrate a real host identity-provider adapter and authorization decision into the trusted host/API boundary. Keep recovery unavailable when no trusted adapter is configured. Add API authorization, audit read-back and failure-injection tests. Preserve quarantine and capacity accounting if authorization, liveness evidence or durable audit persistence fails.

The 2026-11-20 checkpoint below is retained as historical candidate evidence and is superseded by this live reconciliation.

## Historical implementation checkpoint — 2026-11-20 (superseded)

This section records candidate implementation state without changing the acceptance requirements below.

- **WP-09G-A — journal primitive:** integrated on the development branch by PR #257 at `2eff621e4ff24e98250bc085b2c652cd366a5e2e`.
- **WP-09G-B — durable allocator:** implemented and exact-head verified on PR #258 at `43aac3cbb3a42e8dd822ee5d56efcab1d1e01719`. A stacked integration candidate adds the `ResourceAllocatorPort` contract so `ModuleRuntime` can accept either the existing in-memory allocator or an explicitly host-injected `DurableResourceAllocator`. The durable allocator exposes its host-configured capacity through the same port.
- The stacked ModuleRuntime integration candidate PR #260 is exact-head verified at `47d2ac49eab69d9dd8c260d8803a73070c25aad1` (Python 1,166 passed / 4 skipped; Windows supervisor and workflow-sanity PASS). It preserves default in-memory behavior and does not automatically select a durable storage root. It records worker/host logical identity as a non-expiring `supervised_worker` lease and quarantines unconfirmed termination; it is not merged or accepted.
- PR #258 concurrency tests exercise multiple allocator instances with threads; PR #260 adds a subprocess-based capacity-race regression using a shared journal. Platform-specific skips remain SKIPPED.
- **WP-09G-C — process identity snapshot primitive:** candidate implementation in PR #261 at `3e8af697ead9050dd531f27ce8bbaef358145261` adds immutable Linux PID/start-time/boot/process-group/session identity and Windows PID/process-creation-time identity capture, with focused validation tests. Exact-head CI passed; the PR remains a draft and is not integrated.
- **WP-09G-C — durable identity binding:** PR #262 at `30c61a6715ac47b9bb583ee2de9603802ee7d2c3` passed exact-head CI (Python 1,176 passed / 4 skipped; Windows supervisor and workflow-sanity PASS). It adds an append-only `LEASE_PROCESS_BOUND` event, host/worker identity matching, idempotent binding, replacement/quarantine rejection and journal replay. It is still Draft and not integrated.
- **WP-09G-C — supervisor start-gate candidate:** Draft PR #263 at `077edafe5c1e750be6270b28f98fd42430348a98` passed exact-head CI: Python 1,179 passed / 5 skipped; Windows process supervisor 22 passed / 5 skipped; Windows journal 20 passed / 1 skipped; Windows durable allocator/ModuleRuntime 18 passed; workflow-sanity PASS. Linux holds an isolated bootstrap on an inherited gate until the persistence callback returns; Windows assigns the suspended process to a named Job Object, captures creation identity, then resumes only after callback success.
- **WP-09G-C — WorkerIPC/ModuleRuntime integration candidate:** Draft PR #264 at `2b4ff7f014d8ee17e7f84bd623ca6d3322d7c6f9` has Windows supervisor, journal, durable allocator/ModuleRuntime and workflow-sanity checks PASS; its full Python suite is still IN_PROGRESS. It routes the callback through WorkerIPC and ModuleRuntime, creates an identity-only durable worker lease even when no resource metrics were requested, and binds the OS identity before the payload is released. The E2E worker reads the journal and asserts its own PID/worker/host identity is already durably recorded before processing its request. Failure to persist identity blocks payload execution; unconfirmed cleanup quarantines the lease. Windows CI now also runs the WorkerIPC/ModuleRuntime identity integration tests.
- **WP-09G-D — liveness adapter candidate:** Draft PR #265 adds `ProcessIdentityInspector` with Linux boot-ID/start-time/process-group/session inspection and Windows named Job Object active-process inspection. Linux PID reuse is not accepted as a match; ambiguous reused group IDs return UNKNOWN. It returns explicit PRESENT/ABSENT/UNKNOWN evidence and does not release leases. Exact-head CI is pending.
- **WP-09G-D — allocator startup reconciliation candidate:** Draft PR #266 adds `startup_reconciliation_required` readiness gating, blocks new allocations until reconciliation, appends `LEASE_RECOVERED_RELEASED` only with matching timestamped ABSENT evidence, quarantines UNKNOWN and PRESENT workers from a different host instance, retains same-host PRESENT leases, and never clears an existing quarantine during startup. `ModuleRuntime` invokes reconciliation before becoming available when a durable pool reports pending startup work. Tests cover absent, present, unknown, missing/mismatched identity, quarantine retention and ModuleRuntime startup. Exact-head CI is pending.
- **WP-09G-D remaining work:** exact-head CI/review and fault-injection around reconciliation journal writes remain open. **WP-09G-E** (authenticated/audited operator recovery, force release and audit durability) remains not implemented.
- No sandbox, privilege separation, filesystem/network isolation, or OS CPU/memory/I/O enforcement is claimed.

The lifecycle remains IMPLEMENTED → VERIFIED → INTEGRATED → ACCEPTED. PR-head verification does not establish integration or acceptance.

---

**Status:** Design contract / implementation not yet accepted  
**Scope:** Durable resource reservations used by supervised workers, process identity hand-off, restart reconciliation, and operator-controlled recovery  
**Dependencies:** WP-09E-A bounded stdin, WP-09E-B one-shot WorkerIPCClient, WP-09F ModuleRuntime worker dispatch, Windows Job Object containment, POSIX process-group supervision  
**Non-goal:** This contract does not claim a security sandbox or OS-enforced CPU, memory, filesystem, or network limits.

## 1. Current baseline and gap

The current `ResourceAllocator` is an in-memory, process-local quota pool. It supports finite or non-expiring leases and an in-memory quarantine state. Its reservations are atomic only within one allocator instance; active leases and quarantine metadata disappear when the host process exits.

`JsonlRecoveryEvidenceStore` is a separate append-only recovery-outcome store. It provides cross-process file locking, bounded JSONL records, a SHA-256 hash chain, file-type/symlink checks and `fsync`. It records recovery evidence; it is not a source of truth for live worker leases and cannot reconstruct allocator capacity or identify orphaned worker processes.

WP-09G must close that gap without treating an evidence record as a live reservation or assuming that a missing host process means its worker process tree has exited.

## 2. Required safety invariants

1. **No double allocation:** all processes sharing a durable pool must serialize lease admission against the same persisted state.
2. **Write before publish:** a lease is not returned to a caller until its acquisition event is durably appended and flushed.
3. **Release after proof:** a worker lease is not released until the supervisor has confirmed process-tree termination and the release event is durable.
4. **Fail closed:** journal corruption, incomplete records, lock failures, write failures, or unknown process liveness must never increase available capacity.
5. **Worker leases do not expire by TTL:** a worker lease remains active across host restart until reconciliation proves the worker process tree is gone or an authorized operator resolves it.
6. **Quarantine survives restart:** quarantine status and reason are persisted and restored before the allocator accepts new reservations.
7. **Identity is not PID alone:** process identity must include an OS-specific creation/start token to protect against PID reuse.
8. **Cancellation is identity-bound:** cancellation targets the immutable worker identity reserved for that invocation, never a new lookup that can bind to a later request reusing the same request ID.
9. **No silent repair:** malformed or tampered journal data is not truncated, skipped, or automatically rewritten.
10. **Audited operator action:** any manual force release requires an authenticated operator identity, a non-empty reason, and a durable audit event.
11. **Pinned pool capacity:** every process using the same pool ID must verify the same canonical capacity-and-unit configuration before admission.
12. **Safe compaction:** journal rotation must preserve a verifiable state checkpoint and an explicit archive-retention policy; never discard history needed to reconstruct active or quarantined leases.
13. **Honest integrity guarantee:** an unkeyed SHA-256 chain detects accidental corruption but is not proof against an actor who can rewrite the journal and recompute the chain. Strong tamper evidence requires a separately protected checkpoint/signing key.

## 3. Durable data model

### 3.1 Lease record

A persisted lease record must contain:

- `schema_version` and `pool_id`
- `lease_id`, `owner_id`, and immutable allocation metrics (name, value, unit)
- UTC `acquired_at` and optional `expires_at`
- `lease_kind`: `ordinary` or `supervised_worker`
- `host_instance_id` and, for workers, `worker_id`
- Optional `process_identity` captured by the supervisor before the worker is allowed to execute
- `status`: `ACTIVE`, `QUARANTINED`, or terminal `RELEASED`
- Quarantine reason and reconciliation provenance where applicable

A `supervised_worker` lease must use no automatic TTL. An ordinary lease may expire only under the existing documented TTL policy and only after the durable store has serialized the expiry transition.

### 3.2 Process identity contract

Persist a platform-specific identity object, not a raw process handle:

- Platform and host boot/session identity
- PID and a process creation/start token (not PID alone)
- Process group/session identity on POSIX
- Job Object identity and process creation identity on Windows
- Supervisor-generated `worker_id` and host instance ID

A platform adapter must expose three-valued liveness: `PRESENT`, `ABSENT`, or `UNKNOWN`. It must return `ABSENT` only when it has verified the exact process identity and the entire supervised process tree is gone. Unsupported platforms and ambiguous identity return `UNKNOWN`, which quarantines the lease. On Linux, the supervisor creates a new session/process group so its PID, PGID and SID anchor the worker tree; the liveness adapter refuses non-leader identities and does not count a reused leader PID as the original worker. On Windows, the named kill-on-close Job Object is the process-tree anchor. `host_instance_id` is generated once per host process and shared by its `ModuleRuntime` instances; it must change after a host process restart.

### 3.3 Append-only lease events

Use a versioned event journal with at least:

- `LEASE_ACQUIRED`
- `LEASE_PROCESS_BOUND`
- `LEASE_QUARANTINED`
- `LEASE_RELEASED`
- `LEASE_RECOVERED_RELEASED`
- `LEASE_FORCE_RELEASED`
- `LEASE_RENEWED` (ordinary leases only, if renewal is supported)

Every event contains a unique event ID, monotonically increasing sequence, UTC timestamp, pool ID, lease ID, host instance ID, event payload, previous hash and record hash. Canonical JSON encoding and SHA-256 hash chaining must make event ordering and tampering detectable.

Do not reuse `RecoveryEvidenceRecord` as this journal: its record grain and fields describe completed recovery outcomes, not the live state transitions needed to rebuild a resource pool. Prefer extracting a small reusable, tested hash-chain/locking primitive from the existing evidence store rather than copying a second subtly different implementation.

## 3.4 Trusted-storage boundary and tamper evidence

The SHA-256 hash chain detects accidental corruption, record modification, reordering, truncation and incomplete writes when the previously trusted chain head is known. An unkeyed hash chain does **not** authenticate the writer and cannot detect a malicious actor who can rewrite the entire journal or restore an older valid copy and recompute every hash.

The default local mode therefore assumes the journal directory, lock file and host account are protected by operating-system access controls and that untrusted principals cannot write or restore the journal. It must not be described as tamper-proof against a privileged host administrator or compromised host.

If the threat model includes an actor with journal write/restore access, use a separately protected trust anchor:
- Sign periodic checkpoints with a key held outside the journal directory (for example, an OS-protected keystore/TPM-backed key) or publish the checkpoint digest to a separate operator-controlled trust domain.
- A checkpoint contains pool ID, covered sequence, chain-head hash, snapshot digest, key ID, timestamp and signature.
- Startup verifies the signature and compares the latest locally stored checkpoint with the trusted external anchor before replay.
- Never store the signing key beside the journal. If the required key/anchor is unavailable or does not match, the pool remains unavailable for new admissions.
- If this stronger mode is not configured, report the narrower accidental-corruption guarantee explicitly.

## 4. Journal and allocator transaction rules

### 4.1 Store integrity and locking

- Use a cross-process exclusive lock for every read-modify-write transaction.
- Reject symlink/non-regular journal and lock targets; use no-follow flags where available.
- Bound record and total-store sizes.
- Verify the complete hash chain before every append and before allocator restoration.
- Append one complete newline-terminated event and call `fsync` before reporting success.
- Treat an incomplete final line, sequence gap, invalid hash, unsupported schema version, or lock/write/fsync failure as a hard store error.
- Never silently truncate, skip, or reset a corrupt journal. Recovery requires an explicit, separately audited repair/export procedure.

### 4.1.1 Pool capacity configuration pinning

A pool ID has one canonical, versioned capacity configuration. The initial durable state records a POOL_INITIALIZED event containing a sorted list of metric names, values and units plus a deterministic configuration fingerprint. Every process opening that pool must compare its requested configuration with the persisted fingerprint before accepting reservations. A mismatch fails closed; it must not let one process enforce a larger capacity than another.

A capacity change is a separate POOL_CAPACITY_UPDATED transition. It requires an authorized operator identity, reason, expected prior configuration version and a check that the new capacity does not invalidate active reservations. The event is appended and fsynced before any process uses the new capacity. All processes must refresh the pinned configuration while holding the shared pool lock. Ordinary worker requests cannot change pool capacity.

### 4.2 Acquire

1. Acquire the cross-process pool lock.
2. Reload and verify the journal; reconstruct current leases.
3. Apply only eligible ordinary-lease expiry transitions and persist them.
4. Check capacity against the reconstructed state.
5. Append and fsync `LEASE_ACQUIRED`.
6. Only then publish the lease to the caller and update the local cache.
7. Release the pool lock.

If any persistence step fails, reject the acquisition and do not expose additional capacity.

### 4.3 Worker start hand-off

A crash between process creation and durable process-identity recording must not create an untracked executable worker.

- **Windows:** preserve suspended process creation; assign the process to its Job Object; durably record PID, process creation token, Job Object identity and worker ID; only then resume the primary thread.
- **POSIX:** use a start-gated launcher that cannot execute the configured worker payload until the host has durably recorded PID, process-group/session identity, boot ID/start token and worker ID. If the host exits before releasing the gate, the launcher must fail closed and exit without executing the worker payload.
- If identity persistence fails, terminate the not-yet-authorized process tree and confirm cleanup. If cleanup cannot be confirmed, retain/quarantine the lease and report the condition.

The exact Windows and POSIX mechanisms must be implemented and tested by their owning supervisor adapters; this document does not assume they already exist.

### 4.4 Release and quarantine

- On confirmed process-tree termination, append and fsync `LEASE_RELEASED` before removing the lease from durable or in-memory accounting.
- On unconfirmed termination, append and fsync `LEASE_QUARANTINED`; keep the allocation charged and exclude it from ordinary TTL expiry.
- If quarantine persistence fails, keep the active lease charged in memory, stop new admissions for the affected pool, and surface a critical recovery-store error. Do not claim the quarantine is durable.
- A release-event persistence failure leaves the lease charged and retryable; it must not be optimistically removed from memory.

### 4.5 Journal checkpointing, rotation and compaction

A hard total-store cap without compaction would eventually block all future worker admissions even after leases are released. Rotation must therefore be part of the durable-store design, not an operational afterthought.

- Keep the active journal segment bounded. Before it reaches its configured limit, acquire the exclusive pool lock, verify the entire active chain and reconstruct the canonical pool state.
- Create a checkpoint snapshot containing the pool ID, schema version, pinned capacity configuration/fingerprint, all active and quarantined lease records, the last covered sequence, the last chain-head hash, snapshot timestamp and snapshot digest.
- Write the snapshot to a new temporary file in the same protected directory, fsync the file, atomically rename it into place, and fsync the containing directory before treating the checkpoint as committed.
- Start the next journal segment with a SEGMENT_STARTED record that references the checkpoint digest, covered sequence and covered chain-head hash. Replay verifies the checkpoint and segment anchor before applying later events.
- Preserve the prior segment as a read-only archive. Archive rotation has its own size/retention policy; delete an archived segment only after its checkpoint is verified and, where strong tamper evidence is required, anchored by the external signature/trust domain described in §3.4.
- Never remove events required to reconstruct active or quarantined leases. Terminal history may be compacted into the checkpoint only when the snapshot contains the complete resulting state and the covered history remains verifiable through the checkpoint anchor.
- If archival retention or checkpoint persistence cannot complete within the configured storage budget, stop new admissions before the active journal reaches its hard limit. Do not discard records, clear quarantine, or silently reset the journal to regain capacity.

The exact snapshot schema, segment naming, atomic replacement semantics and archive retention limits must be covered by fault-injection tests on every supported OS. A local unkeyed snapshot is still only accidental-corruption protection, not protection against a privileged actor who can replace both snapshot and journal.

## 5. Host restart and orphan reconciliation

Allocator initialization must complete reconciliation before accepting new reservations:

1. Acquire the pool lock and verify the complete journal.
2. Replay events in sequence and rebuild active, quarantined and released leases.
3. For each non-terminal supervised-worker lease, inspect its exact persisted process identity through the platform liveness adapter.
4. If `ABSENT`, append and fsync `LEASE_RECOVERED_RELEASED`, then free the reservation.
5. If `PRESENT`, keep the reservation charged. Adopt/monitor it only if a separately reviewed policy supports safe adoption; otherwise quarantine it.
6. If `UNKNOWN`, keep the reservation charged and quarantine it.
7. Restore previously quarantined leases as quarantined; never clear quarantine solely because a new host instance started.
8. Mark the pool ready only after reconciliation is complete. If verification or reconciliation persistence fails, keep the pool unavailable for new admissions.

Ordinary leases may be expired during replay only when their lease type and policy permit it. A worker lease with `expires_at = null` is never freed by wall-clock age alone.

## 6. Operator recovery

A force release is a control-plane action, not a normal allocator method exposed to worker code. It must require:

- Authenticated operator identity and an authorization check
- Explicit lease ID and a non-empty reason
- A fresh liveness result; `UNKNOWN` must be shown explicitly
- A durable `LEASE_FORCE_RELEASED` event before capacity is returned
- An immutable audit reference in the result

If the journal cannot durably record the operator action, the lease remains charged. No default, timeout, or background cleanup may silently force-release quarantined worker capacity.

## 7. Crash and fault-injection matrix

| Failure point | Required post-restart behavior |
|---|---|
| Before `LEASE_ACQUIRED` is fsynced | No lease was committed; no worker payload may have started |
| After lease commit, before process creation | Restore the charged lease; reconcile missing worker identity conservatively |
| After process creation, before identity persistence | Start gate prevents payload execution; verify launcher exit, otherwise quarantine |
| After identity persistence, before worker resume | Restore lease; prove process tree absent or quarantine |
| During worker execution | Restore lease and inspect exact process identity; never free by TTL |
| After process-tree exit, before release event | Restore charged lease; liveness `ABSENT` permits a durable recovered-release event |
| During quarantine append/fsync | Keep lease charged; pool fails closed until journal integrity is re-established |
| During release append/fsync | Keep lease charged; retry only after journal verification |
| Partial final line or hash mismatch | Refuse allocation; preserve journal for explicit repair |
| PID reused by another process | Creation token mismatch means the old worker is `ABSENT`; never signal the unrelated process |
| Cross-process concurrent allocation | Lock + journal replay prevents overcommit |
| Operator force-release audit write fails | Keep lease charged; return an explicit failure |

## 8. Required tests and acceptance evidence

- Deterministic replay of every event type and supported schema version
- Concurrent cross-process acquisition with a capacity race; no overcommit
- Same pool ID opened with different capacity/units; mismatch must block admission
- Authorized capacity update with active leases; reject unsafe changes and audit accepted changes
- Journal approaching active-segment cap; checkpoint/rotation preserves replay state and all active/quarantined leases
- Snapshot, archive or external checkpoint write failure; previous verified state remains authoritative and admissions fail closed
- Old segment/snapshot replacement or replay; trusted checkpoint anchor mismatch blocks admission in strong-integrity mode
- Crash injection before/after every durable append, fsync and worker-start gate transition
- Tampered hash, sequence gap, malformed JSON, incomplete tail, symlink and non-regular-file rejection
- Lock contention, lock timeout, write failure, disk-full and fsync failure behavior
- Restart with worker definitely absent, definitely present, PID reused, and liveness unknown
- Windows Job Object identity and process-tree reconciliation tests on Windows CI
- POSIX process-group/start-token reconciliation tests on supported POSIX CI
- Quarantine and force-release audit durability tests
- Exact-head Python, workflow-sanity, Windows supervisor and platform-specific recovery CI
- Post-merge checks on the exact merge SHA

A skipped platform-specific test is recorded as `SKIPPED`, never as `PASS`. Unsupported process-liveness adapters must produce `UNKNOWN` and preserve the lease.

## 9. Implementation slices

1. **WP-09G-A — journal primitive:** extract/reuse a bounded, locked, hash-chained append journal; preserve current recovery-evidence compatibility and tests.
2. **WP-09G-B — durable allocator:** add journal-backed acquire/release/quarantine and cross-process capacity accounting.
3. **WP-09G-C — supervisor identity hand-off:** expose immutable OS process identity and add the Windows/POSIX start gate before worker payload execution.
4. **WP-09G-D — startup reconciliation:** replay leases and reconcile orphaned worker process trees before opening admission.
5. **WP-09G-E — operator recovery and acceptance:** audited force release, fault injection, platform CI and exact merge-SHA verification.

Do not combine all slices into one unreviewable change. Each slice must preserve the fail-closed invariants and update the completion matrix and requirements traceability.

## 10. Explicit non-claims

Until the relevant implementation and evidence exist, do not claim durable leases, cross-process quota enforcement, orphan-worker recovery, automatic worker adoption, PID-reuse-safe cleanup, persistent quarantine, sandboxing, or OS resource enforcement. This document is a proposed contract; implementation, verification, integration and owner acceptance remain separate maturity states.
