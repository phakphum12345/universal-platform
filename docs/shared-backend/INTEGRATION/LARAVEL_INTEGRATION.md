# Laravel Integration

## Ownership

Laravel remains the Calendar domain backend.

## Preserve

- Existing API version and route compatibility.
- Google identity verification and existing session/token semantics.
- Organization authorization and data scoping.
- Roster, shift transaction, and calendar domain logic.
- Existing migrations and queue behavior unless separately reviewed.

## Request correlation and browser access

- The API middleware validates or generates `X-Request-ID` and returns the effective ID in the response header.
- Health and client-diagnostics responses may also include `request_id` in the JSON body; other domain response payloads remain unchanged.
- CORS allows the correlation header and exposes it to browser clients.
- Membership `PATCH` and `DELETE` methods are allowed for configured origins; CORS does not bypass Google bearer authentication or organization authorization.
- Keep `FRONTEND_ALLOWED_ORIGINS` explicit. Do not replace it with a wildcard as a shortcut.

## Integration approach

Inspect routes, middleware, controllers, services, migrations, and tests before proposing changes. Add an adapter only for a documented use case. Do not expose Calendar database tables to Python.

## Verification

API regression, identity validation, organization isolation, migration safety, contract compatibility, CORS preflight, correlation-header and failure-path tests.
