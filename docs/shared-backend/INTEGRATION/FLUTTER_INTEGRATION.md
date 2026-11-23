# Flutter Integration

## Responsibilities
- Maintain a typed API client per backend/domain.
- Reuse existing Dart networking and authentication components where appropriate.
- Configure base endpoints at runtime; do not assume fixed ports.
- Apply explicit timeout, cancellation, and error mapping.
- Keep backend secrets out of the application.

## Domain separation
Calendar requests use Calendar authentication and organization scope. Engineering requests use Engineering authentication and workspace scope. No automatic token forwarding across domains.

## Verification
Inventory current clients first. Test serialization, malformed responses, auth failure, timeout, unavailable service, and both supported integration paths.
