# Runtime Resource Adapter and Log-Driven Recovery

**Status:** Incremental implementation; process supervision is available for explicitly trusted, allow-listed workers. This is not a production security sandbox or a complete self-healing platform.

## Resource model

Each registered resource has a stable resource ID, kind, adapter ID, required capabilities, lifecycle state and generation counter. Unit-bearing metrics are grouped into timestamped, sequenced snapshots. The in-process registry serializes updates, rejects stale lifecycle transitions and non-monotonic snapshots. Durable resource persistence and distributed leases are not implemented.

## Resource quota allocation and leases

ResourceAllocator provides an in-memory quota pool with typed, unit-bearing capacity metrics. Allocation is atomic within one process, validates metric names and units, rejects overcommit, and returns an owner-bound lease with an expiry timestamp. Leases can be released explicitly or reclaimed when a later operation observes their expiry. The implementation is process-local; it does not discover host capacity, enforce OS-level CPU/memory limits, coordinate multiple processes/machines or persist leases across restarts.

## Log-driven diagnosis

The log analyzer accepts bounded caller-supplied text or structured JSON lines, extracts error/critical/fatal/exception evidence, correlates explicit component/resource IDs, and redacts common credential patterns. FileLogSource reads UTF-8 files only beneath an operator-configured root, rejects traversal/out-of-root paths and enforces a byte ceiling. Log content is evidence only; it is never executed or interpreted as instructions.

Stream ingestion, rotation/cursors, retention policy and multi-source correlation remain future work.

## Recovery lifecycle

ACTIVE or SUSPECT -> QUIESCING -> SLEEP -> DIAGNOSING -> REPAIRING -> VALIDATING -> CANARY -> ACTIVE

Any repair, health, canary or adapter exception fails closed to QUARANTINED. The adapter is responsible for stopping new scheduling and draining/cancelling its own work. A component resumes only after the repair executor reports success, health checks pass, canary checks pass and configured evidence has been persisted.

The coordinator can read from a LogSource and optionally persist redacted outcome metadata and event fingerprints through a RecoveryEvidenceSink. The JSONL evidence implementation uses process-local locking; it is not a multi-process transactional or tamper-evident ledger.

## Python process supervision

PythonProcessSupervisor launches explicitly allow-listed executable files without a shell, confines working directories beneath a configured root, starts with an explicit environment mapping, bounds retained stdout/stderr per stream, enforces a wall-clock timeout and supports external cancellation. On POSIX it starts a new session and signals the process group for termination. On Windows this version terminates the direct child only.

**Important security boundary:** this is an OS process supervisor, not a sandbox. Allow-listed executables and their arguments must be trusted. It does not provide filesystem/network syscall isolation, OS-level CPU/memory quotas, durable checkpoints, restart policies, heartbeat monitoring, Windows Job Object containment or protection against a compromised worker. Do not run untrusted code through it.

## Adapter replacement and repair safeguards

- A repair executor must explicitly declare sandboxed = True; the coordinator does not itself create the sandbox.
- Log messages are evidence only, never executable instructions.
- Replacement adapters must match the resource kind and provide every required capability; the registry permits replacement only while the resource is asleep.
- A production repair executor requires an isolated workspace/process/container, explicit permissions, quotas, timeout, cancellation, artifact capture, approval and rollback.
- A failed validation must not resume the component.

## Adapter discovery and staged replacement

AdapterRegistry catalogs adapter instances that are already available to the application; it never downloads or installs code. Fallback selection requires a matching resource kind, all required capabilities, a numeric minimum version, an explicit non-empty license allow-list and a caller-supplied dependency check. Selection is deterministic by priority, version and adapter ID.

AdapterReplacementCoordinator only operates while the resource is in SLEEP. It checks the candidate adapter's health and canary methods before updating the ResourceRegistry adapter ID. A failed check leaves the existing registration unchanged. The caller remains responsible for routing runtime work to the returned adapter and for resuming the resource through the recovery lifecycle. Version comparison currently supports numeric dot-separated versions only; prerelease/build metadata and full semantic-version range expressions are not supported.

## Implemented verification

- Resource registry, metrics/snapshots and lifecycle transitions have focused tests.
- ResourceAllocator tests cover quota enforcement, unit matching, expiry, release and concurrent reservations without overcommit.
- Log parsing/redaction, bounded file ingestion, path traversal and evidence persistence have focused tests.
- Coordinator integration tests cover log source -> analysis -> sleep/repair/validate/canary -> evidence -> resume, including evidence-write failure before resume.
- Process supervisor tests cover allow-list enforcement, working-directory confinement, bounded output, timeout and external cancellation.
- Adapter catalog tests cover capability/kind matching, numeric minimum versions, explicit license allow-lists, dependency checks, priority selection, asleep-only replacement and no mutation after failed health/canary checks.

## Remaining gates

1. Persistent resource registry, durable leases and cross-process concurrency control.
2. Stream log sources, cursoring, rotation, retention and robust cross-source correlation.
3. OS sandbox implementation for untrusted repair and worker code; platform-specific process-tree containment.
4. CPU/memory/disk/network quotas and resource telemetry collectors.
5. Checkpoint/restore, heartbeat, crash restart policy and lifecycle integration with ResourceRegistry/RecoveryCoordinator.
6. Adapter discovery, compatibility/version/license validation, tested staged switchover and canary traffic policy.
7. Durable, multi-process, tamper-evident recovery evidence and retention policy.
8. Human approval and permission integration for source/dependency changes.
9. Exact-head CI, security review and adversarial tests before any merge.

No arbitrary self-modification, privilege escalation, automatic production code patching or physical hardware control is enabled.
