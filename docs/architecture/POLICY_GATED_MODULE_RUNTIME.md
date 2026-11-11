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

The process supervisor remains a separate trusted-worker facility and is not a sandbox. A future isolated worker adapter must enforce OS/container policy independently and should not weaken this in-process permission check.

## Acceptance evidence

Focused tests cover allowed invocation, request self-grant rejection, missing/revoked grants, manifest grant ceiling, missing handlers, unknown operations, schema mismatch, sanitized handler failures and duplicate registration. Completion status is operational only; it does not imply engineering evidence PASS.


## Host quota reservation integration

ModuleRuntime may be constructed with a host-configured ResourceAllocator. When a validated ModuleRequest.resource_limits mapping is non-empty, the runtime maps each metric name to the unit declared by the allocator capacity and atomically reserves that amount before invoking the handler. Unknown metrics, missing allocators and exhausted capacity fail closed before handler execution. The lease is released in a finally path after both successful and failed handler execution.

This is a reservation/lease lifecycle, not enforcement of actual CPU time, resident memory, I/O, network use or execution deadlines. The request supplies an amount to reserve, but cannot define capacity or units. Capacity and units are controlled by host configuration. Runtime invocation leases use explicit release rather than TTL expiry, so an active handler retains its reservation until the finally path releases it. General allocator callers may continue using finite TTL leases. The allocator and leases are in-memory and process-local; they are not durable or coordinated across processes. A process crash discards the in-memory pool and does not provide cross-process accounting.


## Output schema enforcement — WP-09A

Each executable ModuleOperation must carry an immutable output JSON Schema subset whose `x-schema-version` exactly matches `output_schema_version`. The runtime rejects an operation with no output schema before handler dispatch. After a handler returns, the runtime validates the output structure before constructing a COMPLETED response. Missing required properties, forbidden additional properties, primitive/nested type mismatches, invalid array items and numeric bounds fail closed with the stable `module.output_validation_failed` error. Handler output and validator internals are not returned to callers.

The in-process validator intentionally supports a documented subset of JSON Schema: object, array, string, boolean, integer, number and null types; required/properties/additionalProperties; items; enum/const; and basic length, item-count, property-count and numeric bounds. Unsupported validation keywords fail closed rather than being silently ignored. This is not a claim of full Draft 2020-12 conformance.

Output validation is distinct from JSON-compatibility validation in ModuleResponse. The latter remains a final serialization-safety check. Neither validation establishes engineering evidence PASS or isolates handler code.
