# Zero-Cost Policy

## Objective
Avoid adding paid platform services or billable infrastructure. Prefer software and hardware already available to the project owner.

## Preferred approach
- Existing Windows/local hardware for local runtime.
- Existing Laravel and Python implementations.
- Flutter/Dart clients.
- SQLite/local filesystem where workload and recovery requirements permit.
- Open-source tooling already compatible with the repositories.
- GitHub Actions only within applicable public-repository and platform policies.

## Approval required
No new cloud host, managed database, paid queue, monitoring SaaS, commercial API gateway, paid runner, subscription, or automatic resource provisioning without explicit approval.

## Hidden costs
Local-first is not literally cost-free: electricity, hardware, connectivity, backups, maintenance, and any external provider usage may still cost money. Google APIs, email delivery, DNS, and network tunneling may have quotas or charges; verify before relying on them.

## CI cost controls
Prefer Linux for documentation and static checks. Use platform-specific runners only for platform-specific builds. Avoid duplicate jobs and unnecessary artifacts. Check repository visibility, included minutes, storage, and account billing separately; do not infer billing status from visibility alone.
