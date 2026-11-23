# Main Branch Protection — Recommended Repository Policy

**Status:** Recommended configuration; not yet enabled on GitHub.
**Target:** `main`
**Audit baseline:** 2026-11-23

## Current finding

The GitHub Branch API most recently returned `protected: false` for `main` (verified 2026-11-23). Required status checks are therefore not enforced by GitHub, even though the workflows run in pull requests. This document is a recommendation only; no branch protection setting was changed by this audit.

This document records the settings to apply. It does not claim that the settings have been changed.

## Recommended rule

In GitHub, open **Repository → Settings → Branches → Add branch protection rule** (or create a repository ruleset targeting the default branch).

- Branch name pattern: `main`.
- Require a pull request before merging.
- Require at least one independent approval where a second maintainer/reviewer is available.
- Dismiss stale approvals when new commits are pushed.
- Require conversation resolution before merging.
- Require status checks to pass before merging.
- Require branches to be up to date before merging.
- Block force pushes.
- Block branch deletion.
- Include administrators / do not allow bypass, except for an explicitly documented emergency process.
- Do not enable automatic deletion of head branches as a substitute for explicit branch lifecycle review.

If the repository is currently maintained by one person, do not invent an approval or approve your own PR merely to satisfy the rule. Use an explicitly documented owner-only exception until an independent reviewer is available.

## Required status checks

After the relevant workflows have completed at least once on a pull request, select the exact check contexts presented by GitHub. Expected core contexts include:

- `Repository Quality and Dependency Security / repository-quality`
- `Engineering Core Tests / python-tests`
- `Engineering Core Tests / windows-process-supervisor`
- `Engineering Core Tests / workflow-sanity`
- `Cross-Shell Runtime Validation / Ubuntu · bash`
- `Cross-Shell Runtime Validation / Ubuntu · sh`
- `Cross-Shell Runtime Validation / Windows · PowerShell`
- `Cross-Shell Runtime Validation / Windows · cmd`

Additional path-scoped checks should be required for changes that affect their domains, such as Geometry Batch Validation and CAD Generator Browser E2E. Confirm the exact check names in the GitHub UI; do not select similarly named stale or unrelated contexts.

## Verification after applying the rule

1. Query `GET /repos/{owner}/{repo}/branches/main/protection` and verify protection is enabled.
2. Verify required status checks and strict/up-to-date behavior.
3. Open a test pull request with a deliberately failing check and confirm GitHub blocks merging.
4. Confirm direct pushes, force pushes and branch deletion are blocked for ordinary maintainers.
5. Record the exact settings and verification evidence in a new audit entry.

## Current limitation

The connected GitHub actions available to this workflow can inspect branch protection but do not expose a branch-protection write operation. No settings mutation has been attempted. A repository administrator must apply the rule in GitHub Settings or through an authorized GitHub administration workflow.
