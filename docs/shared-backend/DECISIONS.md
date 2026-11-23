# Architecture Decision Records

## ADR-001 — Preserve domain backends
**Status:** PROPOSED  
Keep Laravel as Calendar domain owner and Python as Engineering domain owner. Avoid rewrite without measured justification.

## ADR-002 — Share contracts, not databases
**Status:** PROPOSED  
Share versioned schemas and integration conventions; retain independent persistence and migrations.

## ADR-003 — Local-first deployment
**Status:** PROPOSED  
Use existing hardware for initial deployment; no new hosted infrastructure without approval.

## ADR-004 — No forced FastAPI migration
**Status:** PROPOSED  
Assess the current Python HTTP server first. Adopt FastAPI only if a concrete concurrency, async, maintainability, or compatibility requirement warrants it.

## ADR-005 — Dynamic endpoint configuration
**Status:** PROPOSED  
Avoid fixed-port dependencies. Discover or configure service endpoints at runtime without exposing secrets.

## ADR-006 — Separate identity domains
**Status:** PROPOSED  
Do not implicitly reuse Calendar identity tokens for Engineering authorization or vice versa.
