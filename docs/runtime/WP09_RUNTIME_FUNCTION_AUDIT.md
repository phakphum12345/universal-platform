# WP-09 Runtime Function-by-Function Audit

**Repository:** `phakphum12345/universal-platform`  
**Audit baseline:** `c3d9800ebb46caff38bf18c13142e218ee2c6c63`  
**Implementation branch:** `feat/wp-09-windows-job-object`  
**Evidence status:** WP-09C merged at `b6e02988b009754fbf0ccdfc032c33174355e5c6`; WP-09D framing primitive and tests authored on `feat/wp-09d-versioned-worker-ipc`; exact-head CI pending.  
**Scope:** Windows process-tree lifecycle, current in-process ModuleRuntime, and in-memory resource lease behavior.

## 1. Worker specification and result

| Function / type | Current behavior | Validation / remaining concern |
|---|---|---|
| `WorkerSpec.__post_init__` | Validates worker ID, executable, immutable argument tuple, working directory, finite positive timeout, finite non-negative termination grace, and string environment mapping. Rejects NULs and invalid environment names/values. | It validates structure, not whether environment variables are safe or whether the executable is trustworthy; executable allow-list is enforced by supervisor. |
| `WorkerResult` | Immutable result containing exit code, timeout/cancel flags, duration, captured output and truncation flag. | It does not claim process-tree termination evidence. Supervisor cleanup must complete before returning normally. |

## 2. Windows Job Object adapter — `runtime/windows_job.py`

| Function | Responsibility | Failure behavior |
|---|---|---|
| `_windows_api` | Loads Kernel32 and declares ctypes signatures for Job Object, thread snapshot, thread open/resume and handle APIs. | Refuses non-Windows use; API calls use last-error reporting. |
| `_raise_last_error` | Converts the Win32 last-error code into an `OSError`. | Raises rather than silently weakening containment. |
| `_resume_only_suspended_primary_thread` | Takes a Toolhelp thread snapshot while the new process is still suspended; requires exactly one thread owned by the process; opens that thread and requires `ResumeThread` to report a previous suspend count of exactly one. | Fails closed if enumeration, thread open, or resume invariant fails. The process remains in the assigned Job Object and is terminated by the caller. This relies on the suspended primary thread not having executed user code and therefore not having created another thread. |
| `WindowsJob.__init__` | Creates a private Job Object and sets `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` before worker creation. | Creation/configuration failure raises; the handle is closed on configuration failure. |
| `assign_suspended` | Assigns the still-suspended Popen process handle to the Job Object, then resumes the sole primary thread. | Assignment failure does not resume the process. Resume failure terminates the Job Object and raises. |
| `terminate` | Calls `TerminateJobObject` for the whole process tree. An already-empty job is treated as complete only after querying active-process count. | Propagates API failures if active processes remain. |
| `active_processes` | Queries Job Object basic accounting information and returns the OS-reported active process count. | Query failure raises; it is not converted to zero. |
| `wait_empty` | Polls the OS active-process count to a bounded deadline. | Returns false on deadline; does not assert that the tree is gone. |
| `close` | Closes the Job Object handle; kill-on-close is the final backstop. | Preserves the handle state if CloseHandle fails so cleanup can be retried. |
| `__enter__ / __exit__` | Context-manager convenience; terminates a non-empty job and closes it. | The supervisor uses explicit lifecycle handling so it can verify emptiness and report failure. |

### Startup ordering

1. Create/configure Job Object.
2. Start `Popen` with `CREATE_SUSPENDED` and `CREATE_NEW_PROCESS_GROUP`.
3. Assign process to Job Object.
4. Enumerate exactly one suspended primary thread and resume it.
5. Keep the Job Object handle until the root and all descendants exit, or terminate the job.
6. Confirm the OS-reported active-process count is zero before normal completion.
7. Close the Job Object; kill-on-close is a final fail-safe.

The implementation uses the Popen process handle (`process._handle`) and Toolhelp enumeration to obtain the primary thread. The former is a private CPython attribute; the Windows CI is pinned to Python 3.12. A future hardening slice should replace this dependency with a dedicated `CreateProcessW` adapter that owns both process and primary-thread handles directly, unless compatibility tests establish the current adapter as acceptable across supported Python versions.

## 3. Process supervisor — `runtime/supervisor.py`

| Function | Responsibility | Validation / remaining concern |
|---|---|---|
| `PythonProcessSupervisor.__init__` | Resolves a strict working root and existing executable allow-list; validates output cap; initializes worker/job registries and lock. | Allow-list is path-based and applies to executable path, not binary signature or publisher identity. |
| `active_worker_ids` | Returns a sorted snapshot under the registry lock. | In-memory observation only; OS job accounting is the termination authority. |
| `run` — admission | Resolves executable and working directory, checks allow-list and root confinement, rejects duplicate worker IDs before spawn. | Path checks do not establish a general filesystem sandbox. |
| `run` — spawn | POSIX uses a new session. Windows creates a private Job Object, creates the process suspended, assigns it, then resumes it. | Windows assignment or resume errors roll back and fail closed. |
| `run` — output | Drains stdout/stderr concurrently and retains no more than the configured bytes per stream. | Truncation is explicit. |
| `run` — timeout | Waits only for the configured timeout; timeout terminates the Job Object on Windows or process group on POSIX. | Windows termination waits for OS job emptiness. |
| `run` — normal exit | On Windows, waits briefly for descendants; if any remain after grace, terminates the job. Reader joins are bounded. | This intentionally treats descendants as part of the worker lifetime, even after root exit. |
| `run` — cleanup | Keeps the Job Object alive through termination verification, closes it, and clears process/job/cancellation registries in a finally path. | If OS termination cannot be confirmed, raises instead of returning a successful result. |
| `cancel` | Marks a registered worker cancelled and targets its whole Job Object on Windows or process group on POSIX. | Cancellation racing with completion is covered by shared registry/job lifecycle; broader stress testing remains open. |
| `_terminate_process` | Windows terminates and waits for Job Object emptiness; POSIX sends TERM then KILL to the process group, including when the leader has exited. | Does not enforce CPU/memory/network/filesystem limits. |

## 4. ModuleRuntime — `engineering/module_runtime.py`

| Function | Current behavior | WP-09 implication |
|---|---|---|
| `ModuleRuntime.__init__` | Accepts a registry and optional in-memory ResourceAllocator; stores trusted Python handlers, grants and invocation counters. | No process supervisor is injected or called. |
| `grant` | Grants only permissions declared by a registered module; uses immutable permission sets. | This is application-level host policy for in-process handlers, not an OS token or sandbox boundary. |
| `revoke` | Removes a grant, blocks new admissions and waits for admitted invocations to drain. | It waits for Python handler completion, not an external worker process. |
| `_finish_invocation` | Decrements per-module active count and wakes waiters. | Must ultimately run only after any worker tree is terminated and leases are resolved in a future integration. |
| `register_handler` | Registers one callable per declared operation. | Handler remains trusted in-process Python code. |
| `_reserve_resources` | Maps request resource names to host-configured metric units and allocates a non-expiring lease. | Reservation is quota accounting only; not OS resource enforcement. |
| `invoke` | Validates request/operation/schema/grant/handler, increments admission count, reserves resources, calls handler synchronously, validates output, releases lease in finally and finishes invocation. | No IPC, worker protocol, module loading, process isolation or worker-owned lease lifecycle exists yet. |

## 5. ResourceAllocator — `runtime/resources/allocator.py`

| Function | Current behavior | Limitation |
|---|---|---|
| `ResourceAllocator.__init__` | Validates pool ID and unique non-empty capacities; stores in-memory lease map and lock. | Process-local and non-durable. |
| `capacity` | Returns sorted configured capacity metrics. | Does not measure live OS capacity. |
| `allocate` | Validates owner, TTL, timezone, non-empty unique requests and units; expires old leases; checks capacity atomically; creates a lease. | No OS scheduler, cgroup, Job Object CPU/memory, disk or network enforcement. |
| `release` | Removes a lease by ID. | Idempotent boolean result; caller owns lifecycle correctness. |
| `active_leases` | Expires eligible leases and returns sorted active records. | Reads in-memory records only. |
| `available` | Computes configured capacity minus active reservations. | Represents quota ledger availability, not measured host resources. |
| `_expire` | Removes leases whose expiry is at or before the supplied time. | WP-09 worker leases use `ttl_seconds=None` today, but ModuleRuntime currently releases them when the in-process handler returns. |

## 6. Windows Job Object acceptance coverage (merged in PR #244)

- Existing cross-platform tests still cover allow-listing, working-root escape rejection, bounded output, timeout, cancellation, malformed limits and duplicate worker IDs.
- Windows-only tests added for root-exits-first child/grandchild cleanup, injected Job Object assignment failure (worker must not execute), timeout of a process tree, and cancellation of a process tree.
- The workflow now includes a dedicated `windows-latest` supervisor job using Python 3.12.
- POSIX descendant-pipe cleanup remains POSIX-only.
- **Exact-head CI is pending.** Tests skipped on non-Windows are not counted as Windows PASS; the Windows runner must execute them.

## 7. WP-09D versioned worker IPC framing (merged in PR #245; historical checkpoint)

- Added `runtime/worker_protocol.py` with a versioned 1.0 envelope and 4-byte network-order length prefix.
- Message types are restricted to REQUEST, RESPONSE and CANCEL; request IDs are bounded to 128 characters.
- Frames are bounded to 1 MiB by default, with caller-configurable positive limits.
- Decoder rejects truncated frames, unsupported versions/types, duplicate JSON keys, unknown envelope fields, invalid UTF-8/JSON, non-finite numbers and oversized lengths before body allocation.
- `read_frame` distinguishes clean EOF from truncated input; `write_frame` handles partial writes and flushes.
- Added `tests/test_runtime_worker_protocol.py` for round-trip, framing, size limits, malformed input, duplicate keys, NaN/Infinity and EOF behavior.
- Boundary: this is a transport primitive only. It is not yet connected to `ModuleRuntime` or `PythonProcessSupervisor`; no worker is launched and no permission is delegated by the frame.

## 8. Remaining WP-09 implementation work at the WP-09D checkpoint (historical)

1. Verify this Windows Job Object slice on the exact PR head and repair every CI failure.
2. Add fault-injection coverage for Job Object creation/configuration, thread enumeration/open/resume, query/terminate/close, reader startup and cleanup failures.
3. Replace or explicitly support the private `Popen._handle` dependency with a dedicated process-creation adapter.
4. Define a versioned worker IPC protocol with bounded frames, request identity, schema validation, cancellation, timeout and crash semantics.
5. Integrate ModuleRuntime with process supervision; do not execute module-supplied code in the host process.
6. Keep resource leases until the worker process tree is confirmed empty; quarantine the lease if termination cannot be confirmed.
7. Add crash recovery and supervisor shutdown semantics.
8. Perform security review before claiming any untrusted-code isolation. Job Objects alone are not a sandbox.

## 9. Explicit non-claims

No general sandbox, privilege separation, token restriction, filesystem/network isolation, CPU/memory/I/O enforcement, dynamic module loading, durable leases, or production-safe untrusted plugin execution is claimed by this slice.

## 10. WP-09E-A bounded one-shot worker stdin transport (merged in PR #248; historical candidate notes)

Historical pre-merge note: the bounded stdin transport described below is now integrated through PR #248. The current integrated state and evidence are recorded in section 11. The earlier candidate branch was `feat/wp-09e-bounded-worker-stdin`.

- `WorkerSpec.stdin_data`: optional immutable bytes; omitted input preserves the existing closed-stdin behavior.
- `PythonProcessSupervisor.max_input_bytes`: host-configured positive bound, default 1 MiB; oversized input is rejected before process creation.
- A dedicated writer thread sends the exact payload while stdout/stderr reader threads drain output concurrently, then closes stdin so the child observes EOF.
- The supervisor joins the writer under the same timeout/cancellation lifecycle. If a worker/descendant does not read input, process-tree termination must unblock the writer; a writer that cannot be joined is a hard failure.
- Early child stdin closure before the payload is fully sent raises a supervisor error rather than returning a successful WorkerResult.
- New tests cover echo/EOF, input bound, early exit, blocked-writer timeout, invalid type and invalid supervisor limit.

This is not yet a complete IPC channel: no versioned frame decode/encode is invoked here, no RESPONSE is validated, no request correlation exists, and ModuleRuntime/resource leases are not yet integrated. Latest exact-head workflow #44567047096 on `5a6a8ffe4cec8a3eba1a325a260875c16d53837b` passed workflow-sanity and Windows process supervisor; Python 1,080 passed / 4 skipped. This includes the bytes-subclass input-cap regression and verifies the candidate on its PR branch only, not after integration.

## 11. Current integration reconciliation — 2026-11-20

The earlier sections describe historical WP-09 implementation slices. The current Development Branch has since integrated:
- PR #244: Windows Job Object process-tree containment.
- PR #245: versioned WorkerFrame protocol and bounded framing.
- PR #248: bounded one-shot stdin transport with writer lifecycle and byte-accurate input-cap enforcement.

### WP-09E-B rebased WorkerIPCClient candidate

Branch feat/wp-09e-worker-ipc-client-rebased builds on those integrated dependencies.

- WorkerIPCClient runs one host-configured WorkerSpec per REQUEST and accepts exactly one correlated RESPONSE frame.
- The client accounts for the 4-byte framing header when constraining the frame body to the supervisor's configured max_input_bytes.
- The supervisor exposes its input cap. Raw bounded stdout bytes are retained separately from the backward-compatible decoded stdout string.
- Each invocation receives a host-generated unique worker ID. The protocol request ID is used only for response correlation and host cancellation mapping; duplicate active IDs are rejected before a second launch.
- Request IDs are bounded and NUL-free. Cancellation validates its grace period and retries through the process-start race.
- Linux process-group detection ignores zombie-only groups when /proc confirms no live group member; inaccessible process metadata falls back to a conservative liveness result.
- A process-tree cleanup failure raises WorkerTerminationError; the client reports termination_confirmed=False. This is the required signal for the later ModuleRuntime layer to quarantine capacity safely.

### Current validation boundary

- Exact-head CI for this rebased candidate is pending. Do not reuse earlier PR #250 CI or PR #248 CI as evidence for this new head.
- This candidate is still transport-only. It does not yet register worker-backed operations in ModuleRuntime, validate worker input schemas against module contracts, bind host grants to worker dispatch, retain/quarantine ResourceAllocator leases, or provide durable recovery.
- The supervisor is process-tree management, not a security sandbox. No arbitrary/untrusted plugin code execution is supported or claimed.

### Next WP-09 gates

1. Pass exact-head Python, workflow-sanity and Windows supervisor CI for the rebased WorkerIPCClient.
2. Review and integrate the one-shot client without treating skipped platform tests as passing.
3. Implement ModuleRuntime worker dispatch using host-owned process configuration and validated input/output schemas.
4. Bind request identity, cancellation, deadlines and ResourceAllocator lease lifecycle to the supervised worker; quarantine a lease if termination is unconfirmed.
5. Add durable crash recovery and explicit supervisor shutdown semantics.
6. Complete threat-model-driven OS isolation and platform acceptance before any untrusted-code execution claim.

## 12. WP-09F ModuleRuntime supervised worker dispatch (candidate, 2026-11-20)

Branch feat/wp-09f-module-runtime-worker-dispatch-rebased is stacked on the rebased one-shot WorkerIPCClient.

- ModuleOperation supports an optional versioned input_schema. Existing trusted in-process handlers remain compatible; worker-backed registration requires input and output schemas plus at least one explicitly declared host permission.
- ModuleRuntime checks host-granted permissions before admission. Request.permissions remains descriptive and cannot grant authority.
- Worker process configuration remains in the host-supplied WorkerSpec. The worker receives only the operation identity, schema version, validated inputs, assumptions, source references and quota request; it does not receive host permission grants or executable configuration.
- Input schema validation occurs before process creation. The returned outputs are validated against the host-declared output schema after response correlation.
- ModuleRuntime reserves a `WorkerInvocationHandle` before worker startup and stores request_id → (WorkerIPCClient, immutable handle). Cancellation uses that exact handle/worker ID, not a fresh lookup by request_id; stale cancellation cannot target a later invocation even if the same request_id is reused. WorkerIPCClient cancellation retries only against the captured worker ID through process startup and converts supervisor exceptions to `False`. Invalid/NUL-containing IDs are rejected before supervisor calls.
- Resource leases are retained through worker execution. Normal completion, timeout and cancellation release only after supervisor cleanup is confirmed. An unconfirmed termination quarantines the lease; ordinary release and TTL expiry cannot reclaim it. If quarantine metadata recording itself fails, ModuleRuntime still withholds release and reports the active lease for manual inspection. Explicit force release is required after a recorded quarantine.
- Tests cover success, input/schema rejection, permission denial, output validation, timeout, cancellation startup race, duplicate active request rejection, stale-handle isolation after request_id reuse, supervisor cancellation exceptions, unconfirmed termination and lease quarantine.

### Current gaps and safety limits

- Latest WP-09F exact-head CI is pending on the live PR head; no tests are claimed PASS until all required jobs complete.
- ResourceAllocator remains an in-memory quota ledger. It does not enforce OS CPU, memory, I/O, network or wall-clock limits.
- Quarantine is process-local and not durable across host restart. Durable lease recovery and reconciliation remain open.
- This is not a security sandbox. No arbitrary/untrusted plugin execution, privilege separation, filesystem/network isolation or production-safe plugin runtime is claimed.
- Worker-backed dispatch is one process per request, not a persistent pool or long-lived bidirectional channel.

### Next work

1. Pass exact-head Python, workflow-sanity and Windows supervisor CI for WP-09E-B and WP-09F.
2. Add fault-injection tests for lease allocation/release exceptions, concurrent revoke/cancel, worker response schema failures and supervisor shutdown.
3. Design durable quarantine/recovery records and safe operator reconciliation.
4. Define and validate a threat-model-backed OS isolation boundary before any untrusted-code capability.


## 14. Authoritative WP-09F integration — 2026-11-20

PR #254 merged at f2ee9045c6316b2ff9026ea5196fedf1232f71a3. Exact-head run #44606596004 and exact merge-SHA run #44607892946 both passed: Python 1,142 passed / 4 skipped, Windows process-supervisor PASS, workflow-sanity PASS.

- ModuleRuntime registers WorkerIPCClient only for operations with declared versioned input/output schemas and explicit host permissions.
- An immutable WorkerInvocationHandle is reserved before process startup. Cancellation snapshots the handle and targets its unique worker ID; stale cancellation cannot target a later invocation after request_id reuse.
- Worker executable configuration remains host-owned. Resource leases are released only after confirmed process-tree cleanup and are quarantined on uncertainty.
- Quarantine and allocator state are still in-memory and do not survive host restart. This is not durable lease recovery, cross-process quota enforcement, a sandbox or OS resource enforcement.

WP-09G is design-only. See DURABLE_WORKER_LEASE_RECOVERY_CONTRACT.md for WP-09G-A through WP-09G-E.
