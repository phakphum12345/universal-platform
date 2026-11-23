# Laravel Integration

## Ownership
Laravel remains the Calendar domain backend.

## Preserve
- Existing API version and route compatibility.
- Google identity verification and existing session/token semantics.
- Organization authorization and data scoping.
- Roster, shift transaction, and calendar domain logic.
- Existing migrations and queue behavior unless separately reviewed.

## Integration approach
Inspect routes, middleware, controllers, services, migrations, and tests before proposing changes. Add an adapter only for a documented use case. Do not expose Calendar database tables to Python.

## Verification
API regression, identity validation, organization isolation, migration safety, contract compatibility, and failure-path tests.
