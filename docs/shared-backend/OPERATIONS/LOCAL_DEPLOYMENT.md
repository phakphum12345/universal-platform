# Local Deployment

## Goal
Run the required services on existing hardware without a newly purchased cloud host.

## Requirements
- Independently start and stop each backend.
- Resolve endpoints dynamically or through explicit local configuration.
- Bind to loopback by default.
- Expose safe health/readiness status.
- Handle service shutdown and restart predictably.
- Keep logs and data in documented locations.
- Avoid embedding secrets in scripts or client applications.

## Deployment gate
Validate network binding, auth, recovery, backup/restore, and resource usage before real-data use. Docker is optional, not a requirement.
