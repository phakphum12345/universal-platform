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
