# Flutter Integration

## Responsibilities

- Maintain a typed API client per backend/domain.
- Reuse existing Dart networking and authentication components where appropriate.
- Configure base endpoints at runtime; do not assume fixed ports.
- Apply explicit timeout, cancellation, and error mapping.
- Keep backend secrets out of the application.

## Calendar API client

- Configure the Calendar API origin through `ORGANIZATION_API_BASE_URL`.
- Use HTTPS for every non-loopback origin. HTTP is allowed only for `localhost`, `127.0.0.1`, or `::1` local development.
- Generate a fresh opaque correlation ID for each request and send it as `X-Request-ID`.
- Read the response `X-Request-ID` header and retain it on API exceptions for support and diagnostics.
- Browser clients require Laravel CORS to allow `X-Request-ID` and expose it to JavaScript. Membership clients also require PATCH/DELETE preflight support.
- Google ID tokens are sent only to the Laravel Calendar API. Never forward them to the Python CAD API.

## Engineering API boundary

The Python CAD Generator API is local-only, binds to loopback, uses a separate local bearer token, and selects an available port dynamically. A remote or mobile Flutter client must not assume that `127.0.0.1` points to the Windows host or that the local token can be reused as a Calendar credential.

Any future remote Engineering client requires a separately approved secure transport and runtime service discovery. Do not introduce a fixed port, public listener, or automatic credential forwarding.

## Domain separation

Calendar requests use Calendar authentication and organization scope. Engineering requests use Engineering authentication and workspace scope. No automatic token forwarding across domains.

## Verification

Test serialization, malformed responses, auth failure, timeout, unavailable service, correlation header propagation, response correlation capture, HTTPS enforcement, and browser CORS preflight using local/mock transports.
