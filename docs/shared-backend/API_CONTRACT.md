# Shared API Contract

## Purpose
Define inter-service compatibility without imposing a new gateway or replacing existing APIs. Existing routes remain authoritative until individually reconciled.

## Versioning
Use explicit versioned contracts for new cross-service interfaces. Do not rename or break existing Calendar or Engineering endpoints as part of documentation work.

## Current cross-service correlation contract

- `X-Request-ID` is the canonical request-correlation header.
- A caller may supply an ID matching `[A-Za-z0-9._-]{8,128}`; services must reject malformed values and generate a new opaque ID.
- The canonical machine-readable definition is `schemas/shared/request-id.schema.json`; implementation validators and client tests must remain compatible with this schema.
- Every JSON response must return the effective ID in the `X-Request-ID` response header.
- A JSON body may also include `request_id` for compatibility and diagnostics. It is not required on every endpoint.
- Laravel currently echoes the effective ID in the response header; its health and diagnostics responses also include `request_id` in the body.
- The Python CAD Generator API includes `request_id` in JSON bodies and now echoes the same ID in the response header.
- Existing success payloads remain domain-specific. Do not wrap or rename them as part of correlation support.
- Errors should expose a stable machine-readable `error.code` and user-safe `error.message` where the endpoint currently supports that shape. Laravel validation responses retain Laravel's established validation format until a versioned migration is designed.

This contract is additive and does not change authentication, authorization, route paths, payload ownership, or persistence.

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
