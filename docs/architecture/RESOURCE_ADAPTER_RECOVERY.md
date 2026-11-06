# Runtime Resource Adapter and Log-Driven Recovery

**Status:** Initial bounded implementation; not a production process supervisor.

## Purpose

Provide a central typed registry for runtime components and a fail-closed recovery coordinator. The first vertical slice targets Python worker-like components through a replaceable adapter contract. It does not manage physical devices, host operating-system resources, or arbitrary Python processes.

## Resource model

Each registered resource has a stable resource ID, resource kind, adapter ID, required capabilities, lifecycle state and generation counter. Unit-bearing ResourceMetric values are grouped into timestamped, sequenced ResourceSnapshot records. The registry serializes updates under a lock, rejects stale lifecycle transitions and non-monotonic measurement snapshots, and exposes the latest snapshot per resource. Metrics can represent CPU utilization, memory/GPU/disk bytes, network byte counters, worker counts and other adapter-defined measurements. It is process-local; durable persistence and distributed leases are future work.

## Log-driven detection

The analyze_logs function accepts caller-supplied text or structured JSON lines. It extracts error/critical/fatal/exception evidence, associates explicit component/resource IDs, caps lines and message length, and redacts common credential patterns. It does not execute commands, interpret log content as instructions, or autonomously decide that a source-code patch is correct. FileLogSource reads UTF-8 files only beneath a configured root, rejects traversal/out-of-root paths, and enforces a byte ceiling. The configured root must not be writable by untrusted actors. Stream ingestion, rotation/cursors and retention policy remain future work.

## Recovery lifecycle

ACTIVE or SUSPECT -> QUIESCING -> SLEEP -> DIAGNOSING -> REPAIRING -> VALIDATING -> CANARY -> ACTIVE

Any repair, health, canary or adapter exception fails closed to QUARANTINED. Quiescing stops new scheduling and drains/cancels work via the adapter. The component is resumed only after the repair executor reports success, health checks pass and canary checks pass.

## Repair and replacement safeguards

- A repair executor must explicitly declare sandboxed = True; otherwise repair is not invoked and the resource is quarantined.
- Log messages are evidence only, never executable instructions.
- Replacement adapters must match the resource kind and provide every required capability. The registry permits replacement only while the resource is asleep.
- A production repair executor must use an isolated workspace/process/container with explicit permissions, quotas, timeout, cancellation, artifact capture and rollback. This slice defines the contract; it does not provide a sandbox implementation.
- A failed validation must not resume the component. Recovery exceptions trigger rollback and quarantine.

## Known limitations and next gates

1. Structured event envelope and persistent append-only recovery evidence.
2. Permissioned file/stream log-source adapters with cursoring, rotation and bounded retention.
3. Real Python worker adapter with process isolation, checkpoints, graceful shutdown and cancellation.
4. Sandboxed repair executor with explicit human approval for source changes.
5. Atomic adapter switchover, canary traffic policy, durable leases and concurrency tests.
6. Integration with the existing module registry and permission/evidence contracts.
7. Exact-PR-head CI and adversarial tests before merge.

No arbitrary self-modification, privilege escalation, automatic production code patching or physical hardware control is enabled.
\n\n## Log-source and evidence increment\n\nFileLogSource provides bounded, read-only UTF-8 ingestion from an operator-configured root. JsonlRecoveryEvidenceStore appends structured recovery records with SHA-256 event fingerprints and fsync; it does not persist raw logs. The store uses a process-local lock and is not yet wired automatically into RecoveryCoordinator. Configure its directory with owner-only access; distributed locking and tamper-evident chaining are future work.\n