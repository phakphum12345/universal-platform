# Windows Job Object Process-Tree Containment Contract

**Status:** WP-09C merged to integration at `b6e02988b009754fbf0ccdfc032c33174355e5c6`; post-merge CI is running. WP-09D IPC framing is in progress.  
**Work package:** WP-09, Windows process supervision.  
**Baseline:** integration commit `c3d9800ebb46caff38bf18c13142e218ee2c6c63`.  
**Scope:** containment and deterministic cleanup for explicitly trusted worker processes on Windows.

## 1. Existing behavior and boundary

`PythonProcessSupervisor` currently starts Windows workers with `CREATE_NEW_PROCESS_GROUP` and terminates only the direct child. POSIX uses a new session and process-group cleanup. The supervisor is an allow-listed process-management facility, not a sandbox.

A Windows Job Object implementation must not claim descendant cleanup merely because a Job Object can be assigned to a process. Assignment after an ordinary `Popen` launch leaves a race in which the worker can create descendants before assignment.

## 2. Required startup invariant

The implementation MUST guarantee that no worker instruction executes before the process is assigned to its Job Object:

1. Create a Job Object and configure `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` before creating the worker.
2. Create the worker suspended (`CREATE_SUSPENDED`) with an explicit, minimal handle-inheritance policy.
3. Assign the suspended process to the Job Object.
4. Verify assignment succeeded; on failure, terminate the still-suspended process, close all owned handles and fail closed. Never resume an uncontained worker.
5. Resume the primary thread only after successful assignment.
6. Retain the Job Object handle for the entire worker lifetime. Closing it is a final cleanup backstop, not a substitute for waiting for termination.

Current implementation uses a suspended Popen process and a Toolhelp thread snapshot. Because the primary thread has not executed, it cannot have created another thread; the adapter requires exactly one thread owned by the suspended process, opens that thread, and resumes it only when the prior suspend count is exactly one. Any deviation fails closed. The implementation currently relies on CPython's private `Popen._handle`; a dedicated `CreateProcessW` adapter that owns both handles remains a hardening follow-up.

## 3. Job Object policy

- Use a private Job Object per worker unless a documented host policy requires a shared job.
- Set kill-on-job-close and verify the configuration call succeeds.
- Do not enable breakaway flags by default.
- Do not silently weaken containment when the host process itself is already inside a restrictive Job Object. Detect and report unsupported nested-job/assignment conditions.
- Do not claim CPU, memory, I/O, network, filesystem, token, or privilege isolation unless each corresponding OS control is separately implemented and tested.
- Close thread, process, pipe and Job Object handles exactly once on every path.

## 4. Lifecycle and race semantics

- Timeout, external cancellation, reader failure, and supervisor shutdown must converge on one idempotent termination path.
- Cancellation racing with normal exit must not report successful containment cleanup until process termination has been observed.
- A worker is not complete while descendants remain in its Job Object, even if the root process has exited.
- Drain stdout/stderr with bounded retained output. A descendant retaining inherited pipe handles must not cause an unbounded wait.
- Do not release any future worker-owned resource lease until Job Object termination is confirmed (or a separately documented terminal failure is returned and the lease remains held/quarantined).
- Preserve the current POSIX process-group behavior; Windows-specific changes must not regress it.

## 5. Required Windows acceptance tests

Run on `windows-latest` and test at minimum:

1. Normal worker success: output and exit code are preserved; all handles and active-worker registrations are cleared.
2. Descendant containment: a worker starts a child which starts a grandchild; normal root exit cleans the remaining tree.
3. Parent-exits-first: root exits while a grandchild remains alive; supervisor returns within a bounded deadline and descendants are gone.
4. Assignment failure: a fault-injected assignment failure never resumes the worker and closes/terminates all resources.
5. Timeout: root and descendants are terminated; result reports timeout.
6. Cancellation: cancellation targets the whole tree and does not leak the worker registry.
7. Cancellation races with normal exit and timeout without double-close, leaked worker registration, or false success.
8. Job handle closure and reader-startup failure cleanup.
9. Duplicate worker ID and concurrent invocations remain correctly serialized.
10. Existing POSIX descendant cleanup and full Python suite continue to pass.

Tests must assert process/job termination using OS-observable evidence, not only a returned exit code or an empty in-memory registry.

## 6. Evidence and merge gates

- Exact PR-head Windows job MUST pass all Windows supervisor acceptance tests.
- Exact PR-head full Python suite and workflow-sanity MUST pass.
- Post-merge integration-branch CI must be checked separately; a skipped or missing job is UNKNOWN, never PASS.
- Review submissions and inline threads must be inspected at the exact PR head. No automated-review quota failure may be represented as an approval.
- Do not merge to `main` or deploy without explicit human approval.

## 7. Worker IPC envelope requirements\n\nThe first transport slice uses a 4-byte unsigned network-order length prefix followed by one UTF-8 JSON envelope. The envelope is exactly `{ protocol_version, message_type, request_id, payload }`. Version `1.0` supports only `REQUEST`, `RESPONSE`, and `CANCEL`; request IDs are non-empty and bounded. Frame size is bounded (default 1 MiB). Decoders must reject partial headers/bodies, unknown versions/types/fields, duplicate object keys, invalid UTF-8/JSON, non-finite numbers, and oversized lengths before reading the body. Clean EOF is distinct from a truncated frame. Host authorization and schema validation remain outside the transport layer and must be applied before handler dispatch.\n\nThis framing implementation is not yet integrated into ModuleRuntime or the process supervisor; do not treat it as an end-to-end worker IPC channel until process dispatch, correlation, timeout/cancel, crash handling and lease lifecycle tests exist.\n\n## 8. Non-goals

This contract does not implement a general security sandbox, module loading, worker IPC, durable resource leases, OS resource quotas, network isolation, or production execution of untrusted plugins. Those remain separate WP-09 gates.
