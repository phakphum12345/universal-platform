# Policy-Gated Module Runtime

**Status:** Host-grant-gated trusted-handler and supervised-worker dispatch; not a sandbox and not production isolation.

## Current behavior

`ModuleRegistry` remains a metadata-only declaration store. `ModuleRuntime` adds a narrow host-controlled dispatch boundary over explicitly registered trusted Python callables or host-configured one-shot supervised workers:

1. Host code registers either a trusted in-process callable or a WorkerIPCClient backed by a host-configured WorkerSpec for an already-declared module operation.
2. Host code grants a module an immutable subset of permissions declared by its manifest.
3. Invocation validates the request envelope, resolves the declared operation and checks its input schema version; worker-backed operations additionally require a declared versioned input schema and validate inputs before process launch.
4. Required operation permissions are checked against the host-side grant. `ModuleRequest.permissions` is untrusted descriptive input and cannot grant authority.
5. Only then is the pre-registered handler called or the host-configured worker process started. Worker request data cannot select executable, arguments, environment or working directory.
6. Unknown operations, schema mismatch, missing handlers and insufficient permissions are rejected. Worker-backed operations must declare at least one host permission. Handler/worker failures return stable sanitized errors without exception text.

Grants can be revoked. Handler registration does not import modules, download code, or execute code supplied by a request.

## Security boundary and limitations

This is application-level authorization for trusted in-process handlers and host-configured worker dispatch. It does **not** provide a security sandbox, privilege separation, filesystem/network restrictions, OS-enforced CPU/memory/I/O limits, code signing, durable grant storage, human approval, or safe execution of untrusted plugins. In-process handlers run with host-process privileges; supervised workers run with the host account's privileges unless an independently reviewed OS policy is added. Do not register untrusted callables or executables.

The process supervisor is integrated for one-shot trusted-worker dispatch, but it is not a sandbox. Any future isolated worker adapter must enforce OS/container policy independently and must not weaken the host-grant permission check.

## Acceptance evidence

Focused tests cover allowed invocation, request self-grant rejection, missing/revoked grants, manifest grant ceiling, missing handlers, unknown operations, schema mismatch, sanitized handler failures and duplicate registration. Completion status is operational only; it does not imply engineering evidence PASS.


## Host quota reservation integration

ModuleRuntime may be constructed with a host-configured ResourceAllocator. When a validated ModuleRequest.resource_limits mapping is non-empty, the runtime maps each metric name to the unit declared by the allocator capacity and atomically reserves that amount before invoking the handler. Unknown metrics, missing allocators and exhausted capacity fail closed before handler execution. The lease is released in a finally path after both successful and failed handler execution.

This is a reservation/lease lifecycle, not enforcement of actual CPU time, resident memory, I/O, network use or execution deadlines. The request supplies an amount to reserve, but cannot define capacity or units. Capacity and units are controlled by host configuration. Runtime invocation leases use explicit release rather than TTL expiry. In-process handlers retain the reservation until the handler and validation path finish. Worker-backed handlers retain the reservation until supervisor cleanup is confirmed; an unconfirmed worker termination quarantines the lease and blocks ordinary release/TTL expiry. If quarantine metadata cannot be written, ModuleRuntime still withholds release and reports the retained active lease for manual inspection. General allocator callers may continue using finite TTL leases. The allocator and leases are in-memory and process-local; they are not durable or coordinated across processes. A host crash discards the in-memory pool and does not provide cross-process accounting.


## Output schema enforcement — WP-09A

Each executable ModuleOperation must carry an immutable output JSON Schema subset whose `x-schema-version` exactly matches `output_schema_version`. The runtime rejects an operation with no output schema before handler dispatch. After a handler returns, the runtime validates the output structure before constructing a COMPLETED response. Missing required properties, forbidden additional properties, primitive/nested type mismatches, invalid array items and numeric bounds fail closed with the stable `module.output_validation_failed` error. Handler output and validator internals are not returned to callers.

The in-process validator intentionally supports a documented subset of JSON Schema: object, array, string, boolean, integer, number and null types; required/properties/additionalProperties; items; enum/const; and basic length, item-count, property-count and numeric bounds. Unsupported validation keywords fail closed rather than being silently ignored. This is not a claim of full Draft 2020-12 conformance.

Output validation is distinct from JSON-compatibility validation in ModuleResponse. The latter remains a final serialization-safety check. Neither validation establishes engineering evidence PASS or isolates handler code.


## Grant/revoke concurrency lifecycle — WP-09B

Grant admission and revoke initiation are serialized by one runtime condition lock. An invocation is admitted only when its required permissions are currently granted and the module is not in the revoking state; the in-flight count is incremented in that same critical section. This is the invocation admission linearization point.

Revocation removes the grant before waiting for admitted invocations to drain. Consequently, new invocations are rejected immediately after revoke begins, while already-admitted invocations are allowed to finish. The drain covers the complete invocation lifecycle, including host quota reservation, handler execution, output validation and lease release. Repeated revoke calls are idempotent; a concurrent caller waits for the active revoke and then observes that the grant is already absent. A new grant is rejected while draining and may be installed after revoke completes.

The revoke operation is synchronous and can wait indefinitely if an in-process handler never returns. Call it from a control-plane thread, not from the module's own handler. It does not forcibly cancel or terminate handlers. Timeout, cancellation and untrusted-handler process isolation remain separate follow-up work under WP-09C; this lifecycle is not OS-level enforcement.


## Trusted process-supervisor lifecycle hardening — WP-09C (partial)

The allow-listed process supervisor is still separate from ModuleRuntime and remains restricted to trusted executables. The current lifecycle hardening serializes worker-ID reservation with process creation, rejects duplicate IDs before spawning a second process, tracks cancellation until run cleanup, and makes registry removal unconditional. On POSIX, workers start in a new session and termination signals the process group even if its leader has exited; this closes the inherited-pipe case where a descendant outlives the parent and keeps stdout/stderr open.

The supervisor bounds retained output per stream and does not invoke a shell. Tests cover timeout, external cancellation, duplicate worker IDs, and POSIX descendants that retain inherited pipes after the parent exits.

**Windows containment status:** PR #244 integrated Windows Job Object containment: the process is created suspended, assigned to a kill-on-close Job Object before resume, and timeout/cancellation/normal-root-exit cleanup checks the Job Object process count. Windows-specific supervisor tests run on a Windows CI job. Job Objects provide process-tree containment, not a full security sandbox or OS resource quota.

**Current worker integration boundary (WP-09E-B/WP-09F):** ModuleRuntime can register a WorkerIPCClient for a declared operation, validate versioned input/output schemas, require an explicit host permission, send one correlated REQUEST frame and accept exactly one RESPONSE frame. Each request receives a unique host-generated worker ID; cancellation maps request_id to that worker ID and retries through startup registration. Resource leases remain held until supervisor cleanup is confirmed and are quarantined when termination is unconfirmed. This is one process per request, not a persistent worker pool. Durable lease recovery, cross-process accounting, worker restart/replay semantics, privilege separation, filesystem/network isolation and full OS sandbox acceptance remain open. Do not run untrusted plugin code.
