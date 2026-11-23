# Shared API Contract

## Purpose
Define inter-service compatibility without imposing a new gateway or replacing existing APIs. Existing routes remain authoritative until individually reconciled.

## Versioning
Use explicit versioned contracts for new cross-service interfaces. Do not rename or break existing Calendar or Engineering endpoints as part of documentation work.

## Proposed response envelope
Success:
```json
{"success":true,"data":{},"meta":{"request_id":"opaque-id","contract_version":"1"}}
```
Error:
```json
{"success":false,"error":{"code":"VALIDATION_ERROR","message":"Request validation failed"},"meta":{"request_id":"opaque-id","contract_version":"1"}}
```
These are proposed examples, not claims about current API responses.

## Conventions
- JSON UTF-8; explicit nullability and timestamp/time-zone semantics.
- Stable machine-readable error codes.
- Bounded pagination and request sizes.
- Correlation ID propagated across trusted internal calls.
- Idempotency keys only for operations whose semantics support them.
- Validate input at every trust boundary.
- Never return credentials, raw tokens, stack traces, or internal filesystem paths.

## Ownership
Calendar routes and schemas are owned by Laravel. Engineering routes and schemas are owned by Python. Shared schemas describe only agreed integration messages. OpenAPI/JSON Schema should be generated or checked against actual implementations before being treated as authoritative.
