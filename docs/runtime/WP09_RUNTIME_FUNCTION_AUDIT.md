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

## 6. Added acceptance coverage on this branch

- Existing cross-platform tests still cover allow-listing, working-root escape rejection, bounded output, timeout, cancellation, malformed limits and duplicate worker IDs.
- Windows-only tests added for root-exits-first child/grandchild cleanup, injected Job Object assignment failure (worker must not execute), timeout of a process tree, and cancellation of a process tree.
- The workflow now includes a dedicated `windows-latest` supervisor job using Python 3.12.
- POSIX descendant-pipe cleanup remains POSIX-only.
- **Exact-head CI is pending.** Tests skipped on non-Windows are not counted as Windows PASS; the Windows runner must execute them.

## 7. WP-09D versioned worker IPC framing (in progress)\n\n- Added `runtime/worker_protocol.py` with a versioned 1.0 envelope and 4-byte network-order length prefix.\n- Message types are restricted to REQUEST, RESPONSE and CANCEL; request IDs are bounded to 128 characters.\n- Frames are bounded to 1 MiB by default, with caller-configurable positive limits.\n- Decoder rejects truncated frames, unsupported versions/types, duplicate JSON keys, unknown envelope fields, invalid UTF-8/JSON, non-finite numbers and oversized lengths before body allocation.\n- `read_frame` distinguishes clean EOF from truncated input; `write_frame` handles partial writes and flushes.\n- Added `tests/test_runtime_worker_protocol.py` for round-trip, framing, size limits, malformed input, duplicate keys, NaN/Infinity and EOF behavior.\n- Boundary: this is a transport primitive only. It is not yet connected to `ModuleRuntime` or `PythonProcessSupervisor`; no worker is launched and no permission is delegated by the frame.\n\n## 8. Remaining WP-09 implementation work

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
