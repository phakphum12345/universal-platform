#!/usr/bin/env python3
"""Validate the shared-backend documentation tree without modifying files."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path("docs/shared-backend")
EXPECTED = (
    "README.md", "SOURCE_AUDIT.md", "ARCHITECTURE.md", "REQUIREMENTS.md", "API_CONTRACT.md",
    "SECURITY.md", "DATA_ARCHITECTURE.md", "IMPLEMENTATION_PLAN.md",
    "TEST_STRATEGY.md", "ZERO_COST_POLICY.md", "REQUIREMENTS_TRACEABILITY.md",
    "IMPLEMENTATION_STATUS.md", "DECISIONS.md",
    "INTEGRATION/FLUTTER_INTEGRATION.md",
    "INTEGRATION/LARAVEL_INTEGRATION.md",
    "INTEGRATION/PYTHON_INTEGRATION.md",
    "OPERATIONS/LOCAL_DEPLOYMENT.md",
    "OPERATIONS/BACKUP_RESTORE.md",
    "OPERATIONS/MONITORING.md",
    "diagrams/SYSTEM_OVERVIEW.md",
    "diagrams/REQUEST_FLOW.md",
)


def main() -> int:
    errors: list[str] = []
    if not ROOT.is_dir():
        print(f"FAIL: missing documentation directory: {ROOT}")
        return 1

    expected_set = set(EXPECTED)
    for relative in EXPECTED:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing: {path.as_posix()}")
            continue
        raw = path.read_bytes()
        if not raw:
            errors.append(f"empty: {path.as_posix()}")
            continue
        if raw.startswith(b"\xef\xbb\xbf"):
            errors.append(f"UTF-8 BOM found: {path.as_posix()}")
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"not valid UTF-8: {path.as_posix()}")
            continue
        if not content.strip():
            errors.append(f"whitespace-only: {path.as_posix()}")
        if not content.lstrip().startswith("#"):
            errors.append(f"missing Markdown heading: {path.as_posix()}")

    actual = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*.md")
        if path.is_file()
    }
    missing = sorted(expected_set - actual)
    unexpected = sorted(actual - expected_set)
    if missing:
        errors.append("missing expected files: " + ", ".join(missing))
    if unexpected:
        errors.append("unexpected Markdown files (review inventory): " + ", ".join(unexpected))

    for relative in EXPECTED:
        path = ROOT / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            target = target.strip().split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                errors.append(f"broken local link in {relative}: {target}")

    if errors:
        print("FAIL: shared-backend documentation validation")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS: validated {len(EXPECTED)} Markdown files")
    print("PASS: UTF-8 without BOM, non-empty files, headings, and local links")
    print("NOTE: documentation validation does not prove backend implementation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
