# WP-09G — Durable Worker Lease and Crash-Recovery Contract

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

A platform adapter must expose three-valued liveness: `PRESENT`, `ABSENT`, or `UNKNOWN`. It must return `ABSENT` only when it has verified the exact process identity and the entire supervised process tree is gone. Unsupported platforms and ambiguous identity return `UNKNOWN`, which quarantines the lease.

### 3.3 Append-only lease events

Use a versioned event journal with at least:

- `LEASE_ACQUIRED`
- `WORKER_IDENTITY_RECORDED`
- `LEASE_QUARANTINED`
- `LEASE_RELEASED`
- `LEASE_RECOVERED_RELEASED`
- `LEASE_FORCE_RELEASED`
- `LEASE_RENEWED` (ordinary leases only, if renewal is supported)

Every event contains a unique event ID, monotonically increasing sequence, UTC timestamp, pool ID, lease ID, host instance ID, event payload, previous hash and record hash. Canonical JSON encoding and SHA-256 hash chaining must make event ordering and tampering detectable.

Do not reuse `RecoveryEvidenceRecord` as this journal: its record grain and fields describe completed recovery outcomes, not the live state transitions needed to rebuild a resource pool. Prefer extracting a small reusable, tested hash-chain/locking primitive from the existing evidence store rather than copying a second subtly different implementation.

## 4. Journal and allocator transaction rules

### 4.1 Store integrity and locking

- Use a cross-process exclusive lock for every read-modify-write transaction.
- Reject symlink/non-regular journal and lock targets; use no-follow flags where available.
- Bound record and total-store sizes.
- Verify the complete hash chain before every append and before allocator restoration.
- Append one complete newline-terminated event and call `fsync` before reporting success.
- Treat an incomplete final line, sequence gap, invalid hash, unsupported schema version, or lock/write/fsync failure as a hard store error.
- Never silently truncate, skip, or reset a corrupt journal. Recovery requires an explicit, separately audited repair/export procedure.

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
