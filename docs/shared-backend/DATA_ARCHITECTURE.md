# Data Architecture

## Ownership
- Calendar database: Calendar domain records, organization, roster, transactions, and Calendar-specific state.
- Universal Platform database: engineering workspaces, CAD artifacts/history, physics and local audit state.

## Isolation
No direct cross-repository database reads/writes and no shared schema coupling. Use a documented API adapter for any justified exchange.

## Storage choices
Retain existing storage initially. SQLite is suitable for bounded local-first deployments when write concurrency and backup semantics are understood. PostgreSQL is a possible later option, not a required migration or hosted dependency.

## Migration safety
Use versioned migrations, backup before migration, test against a disposable copy, and define rollback/recovery. Do not run destructive migrations as part of architecture documentation work.

## Backup and retention
Define data owners, backup frequency, retention, encryption/access controls, restore objectives, and restore-test evidence before production use. A backup file existing is not proof that restore works.
