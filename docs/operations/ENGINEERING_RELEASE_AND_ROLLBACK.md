# Engineering Release and Rollback

**Status:** PROPOSED operational contract; no production release process is implemented by this document.

## Release package
A release candidate includes source SHA/tag, build instructions, dependency lock/provenance, supported platform matrix, configuration schema/version, tests and evidence, security/license findings, known limitations, migration notes, artifacts and hashes, approval record and rollback plan.

## Versioning
Use an explicit versioning policy for public APIs, schemas, modules and artifacts. Breaking contract changes require a major version or a documented migration path and compatibility tests. Pin external tools/adapters to tested versions; do not rely on floating latest versions for reproducible engineering results.

## Release gates
1. Requirements and scope accepted.
2. Reproducible build and required tests pass.
3. Security, license and data-handling reviews complete.
4. Evidence and known limitations published.
5. Human review and approval recorded.
6. Release artifact hashes and provenance verified.
7. Rollback procedure tested where feasible.

## Rollback
Define trigger, decision owner, affected versions, data/schema migration reversal, artifact retention, dependency downgrade, cache invalidation, user communication and post-rollback verification. Never delete audit evidence to hide a failed release.

## Authority boundary
This process prepares software/artifacts only. Deployment, procurement, fabrication release, machine operation, physical device control or production data changes require separate scoped authorization. No self-approval or autonomous privilege escalation.

## Acceptance
A release is traceable and reproducible; rollback is actionable; approvals are scoped; failed verification blocks release; post-release monitoring and incident records are retained.
