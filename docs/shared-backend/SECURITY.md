# Security Architecture

## Identity boundaries
Calendar identity and organization membership remain owned by the Calendar backend. Universal Platform local bearer-token/workspace controls remain owned by the Engineering backend. A credential from one domain does not grant access to the other.

## Network
- Bind local services to loopback by default.
- Do not expose a local API through a tunnel, reverse proxy, LAN interface, or public host without a separately reviewed threat model and explicit approval.
- Avoid fixed ports; use controlled discovery/configuration and communicate the selected endpoint safely.
- Apply request size, timeout, and rate limits appropriate to the service.

## Secrets
- Never commit credentials or embed backend secrets in Flutter.
- Never log passwords, access tokens, refresh tokens, API keys, or authorization headers.
- Use environment configuration with restrictive file permissions.
- Rotate credentials if exposure is suspected.

## Authorization
Enforce least privilege at the domain API, including organization/workspace scoping. Reject requests when identity or scope cannot be established. Validate cross-domain calls through explicit service identity and narrowly scoped permissions.

## Audit and threat tests
Test unauthenticated access, cross-organization/workspace access, token expiry/replay, injection, path traversal, oversized payloads, and accidental network exposure. Audit metadata must avoid unnecessary personal data.
