# Policy-Gated Module Runtime

**Status:** Initial in-process execution boundary; not a sandbox and not production isolation.

## Current behavior

`ModuleRegistry` remains a metadata-only declaration store. `ModuleRuntime` adds a narrow host-controlled dispatch boundary over explicitly registered Python callables:

1. Host code registers a handler for an already-declared module operation.
2. Host code grants a module an immutable subset of permissions declared by its manifest.
3. Invocation validates the request envelope, resolves the declared operation and checks its input schema version.
4. Required operation permissions are checked against the host-side grant. `ModuleRequest.permissions` is untrusted descriptive input and cannot grant authority.
5. Only then is the pre-registered handler called.
6. Unknown operations, schema mismatch, missing handlers and insufficient permissions are rejected. Handler exceptions return a stable sanitized error without exception text.

Grants can be revoked. Handler registration does not import modules, download code, or execute code supplied by a request.

## Security boundary and limitations

This is application-level authorization for trusted in-process handlers. It does **not** provide OS process isolation, filesystem/network restrictions, resource quotas, code signing, durable grant storage, human approval, or safe execution of untrusted plugins. A handler runs with the host process's privileges. Do not register untrusted callables.

The process supervisor is a separate trusted-worker facility and is not a sandbox. A future isolated worker adapter must enforce OS/container policy independently and should not weaken this in-process permission check.

## Acceptance evidence

Focused tests cover allowed invocation, request self-grant rejection, missing/revoked grants, manifest grant ceiling, missing handlers, unknown operations, schema mismatch, sanitized handler failures and duplicate registration. Completion status is operational only; it does not imply engineering evidence PASS.


## Host quota reservation integration

ModuleRuntime may be constructed with a host-configured ResourceAllocator. When a validated ModuleRequest.resource_limits mapping is non-empty, the runtime maps each metric name to the unit declared by the allocator capacity and atomically reserves that amount before invoking the handler. Unknown metrics, missing allocators and exhausted capacity fail closed before handler execution. The lease is released in a finally path after both successful and failed handler execution.

This is a reservation/lease lifecycle, not enforcement of actual CPU time, resident memory, I/O, network use or execution deadlines. The request supplies an amount to reserve, but cannot define capacity or units. Capacity and units are controlled by host configuration. Runtime invocation leases use explicit release rather than TTL expiry, so an active handler retains its reservation until the finally path releases it. The allocator and leases are in-memory and process-local; they are not durable or coordinated across processes. A process crash discards the in-memory pool and does not provide cross-process accounting.


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

**Known platform limitation:** Windows currently terminates only the direct child. CREATE_NEW_PROCESS_GROUP is not a process-tree containment boundary. Windows descendant cleanup requires Job Object assignment and lifecycle handling; until implemented and tested on Windows, descendant termination and reader-thread cleanup on Windows are UNKNOWN and must not be claimed as PASS.

**Integration limitation:** ModuleRuntime still invokes trusted Python callables in-process. It does not automatically route module operations through the process supervisor, and it cannot forcibly stop a blocked Python thread. ResourceAllocator leases are released when the in-process invocation exits, not when a timed-out worker process is forcibly stopped. End-to-end worker protocol, request/worker identity mapping, host-owned deadlines, cancellation races, lease release after worker termination, and OS-enforced isolation remain open acceptance work. This supervisor is not a sandbox and must not run untrusted plugin code.
