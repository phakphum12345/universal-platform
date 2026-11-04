# Contributing

## Current stage
Documentation and requirements consolidation. Proposed architecture and roadmap are not automatically approved for implementation.

## Before proposing changes
- Read README, VISION, MASTER_BLUEPRINT, ROADMAP, and DECISION_REGISTER.
- Label statements as confirmed requirement, proposal, assumption, or open question.
- Inspect existing projects before proposing reuse.
- Review licenses, provenance, security, and maintenance of external components.
- Prefer minimal, testable, reversible changes.

## Evidence expectations
For code or workflow changes, include exact revision/SHA, commands, exit codes, environment, dependencies, tests, logs, artifacts, security/license checks, limitations, and rollback instructions.

Use PASS, FAIL, SKIPPED, and UNKNOWN accurately. An unrun check is not a pass.

## Safety
- Never commit secrets, tokens, or private keys.
- Isolate untrusted code.
- Do not introduce physical hardware control into the initial analysis-only scope.
- Do not implement autonomous privilege escalation or uncontrolled self-modification.
- Production writes, deployment, and destructive actions require explicit human authorization.

Update the decision register when decisions change. Do not claim a capability exists until implementation and evidence support it.