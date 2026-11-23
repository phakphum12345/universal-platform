# Monitoring and Observability

## Local-first baseline
Use service health/readiness endpoints and structured local logs before considering external monitoring products.

## Log fields
Timestamp, service, severity, request/correlation ID, operation, duration, outcome, and stable error code.

## Never log
Passwords, access/refresh tokens, API keys, authorization headers, or unnecessary personal data.

## Alerts and recovery
Document what constitutes unavailable/degraded, safe restart steps, data integrity checks, and escalation. External alert delivery may introduce provider quotas or costs and requires separate review.
