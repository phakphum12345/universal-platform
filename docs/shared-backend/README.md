# Shared Zero-Cost Hybrid Backend

**Status:** Proposed architecture; not an implementation or production-readiness claim.

## Scope
A shared integration architecture for:
- `phakphum12345/phakphum-calendar`: Laravel Calendar domain backend and Flutter client.
- `phakphum12345/universal-platform`: Python Engineering domain backend and platform tooling.

## Architecture principles
1. Preserve each repository's existing domain backend.
2. Share API contracts, schemas, correlation conventions, and integration guidance—not databases or credentials.
3. Keep Calendar and Engineering persistence isolated.
4. Prefer local-first/self-hosted operation and existing open-source components.
5. Do not introduce paid SaaS, cloud hosting, or billable infrastructure without explicit approval.
6. Keep local services loopback-only by default and avoid fixed-port assumptions.
7. Treat all unverified implementation claims as UNKNOWN.

## Documents
- [Architecture](ARCHITECTURE.md)
- [Requirements](REQUIREMENTS.md)
- [API contract](API_CONTRACT.md)
- [Security](SECURITY.md)
- [Data architecture](DATA_ARCHITECTURE.md)
- [Implementation plan](IMPLEMENTATION_PLAN.md)
- [Test strategy](TEST_STRATEGY.md)
- [Zero-cost policy](ZERO_COST_POLICY.md)
- [Traceability](REQUIREMENTS_TRACEABILITY.md)
- [Implementation status](IMPLEMENTATION_STATUS.md)
- [Decision records](DECISIONS.md)
- [Flutter integration](INTEGRATION/FLUTTER_INTEGRATION.md)
- [Laravel integration](INTEGRATION/LARAVEL_INTEGRATION.md)
- [Python integration](INTEGRATION/PYTHON_INTEGRATION.md)
- [Local deployment](OPERATIONS/LOCAL_DEPLOYMENT.md)
- [Backup and restore](OPERATIONS/BACKUP_RESTORE.md)
- [Monitoring](OPERATIONS/MONITORING.md)
- [System overview](diagrams/SYSTEM_OVERVIEW.md)
- [Request flow](diagrams/REQUEST_FLOW.md)

## Important
This documentation is a design baseline. It does not prove that the proposed shared layer exists, that integrations are complete, or that external authentication works offline.
