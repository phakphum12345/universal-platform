"""Batch validation for CAD-neutral primitive geometry JSON snapshots.

Run from the repository root:
    up-geometry validate path/to/part-a.geometry.json path/to/part-b.geometry.json
    python -m universal_platform.engineering.geometry_batch validate models/ --recursive
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import stat
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .errors import InvalidModelError
from .primitive_geometry import PrimitiveGeometryModel


def _is_geometry_candidate(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".json" and ".schema." not in path.name


def _expand_inputs(inputs: Sequence[str], recursive: bool) -> list[Path]:
    """Expand inputs without changing their caller-supplied order.

    Files found inside a directory or glob are sorted for deterministic output.
    Repeated paths are emitted only once, at their first occurrence.
    """
    discovered: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved_path = path.absolute()
        if resolved_path not in seen:
            seen.add(resolved_path)
            discovered.append(resolved_path)

    for raw in inputs:
        matches = (
            sorted((Path(item) for item in glob.glob(raw, recursive=recursive)), key=lambda item: str(item).casefold())
            if glob.has_magic(raw)
            else [Path(raw)]
        )
        for candidate in matches:
            if candidate.is_dir():
                iterator = candidate.rglob("*.json") if recursive else candidate.glob("*.json")
                for path in sorted(iterator, key=lambda item: str(item).casefold()):
                    if "schemas" not in path.parts and _is_geometry_candidate(path):
                        add(path)
            elif _is_geometry_candidate(candidate):
                add(candidate)
    return discovered


def _validate_file(path: Path, fix: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "status": "FAIL",
        "errors": [],
        "changed": False,
        "solid_count": None,
    }
    if path.is_symlink():
        result["errors"].append("symbolic links are not accepted for geometry inputs")
        return result

    try:
        original_bytes = path.read_bytes()
        original = original_bytes.decode("utf-8")
        original_mode = stat.S_IMODE(path.stat().st_mode)
        payload = json.loads(original)
        model = PrimitiveGeometryModel.from_dict(payload)
        result["solid_count"] = len(model.solids)
        result["status"] = "PASS"
        if fix:
            canonical = json.dumps(model.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            if canonical != original:
                backup = path.with_name(path.name + ".bak")
                if backup.exists():
                    result["status"] = "FAIL"
                    result["errors"].append(f"safe-fix backup already exists: {backup}")
                    return result
                backup.write_bytes(original_bytes)
                temporary_name: str | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w", encoding="utf-8", newline="\n",
                        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False,
                    ) as temporary:
                        temporary.write(canonical)
                        temporary_name = temporary.name
                    os.chmod(temporary_name, original_mode)
                    os.replace(temporary_name, path)
                    result["changed"] = True
                finally:
                    if temporary_name and os.path.exists(temporary_name):
                        os.unlink(temporary_name)
    except (OSError, UnicodeError, json.JSONDecodeError, InvalidModelError, KeyError, TypeError, ValueError) as exc:
        result["status"] = "FAIL"
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # Keep processing the remaining files after an unexpected per-file failure.
        result["status"] = "FAIL"
        result["errors"].append(f"Unexpected {type(exc).__name__}: {exc}")
    return result


def _render_text(report: dict[str, Any]) -> str:
    lines = []
    for item in report["files"]:
        suffix = f" ({item['solid_count']} solids)" if item["solid_count"] is not None else ""
        lines.append(f"{item['status']}: {item['path']}{suffix}")
        lines.extend(f"  - {error}" for error in item["errors"])
        if item["changed"]:
            lines.append("  - canonical JSON written; original preserved as .bak")
    summary = report["summary"]
    lines.append(
        f"TOTAL={summary['total']} PASS={summary['passed']} FAIL={summary['failed']}"
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="up-geometry",
        description="Validate multiple CAD-neutral primitive geometry JSON snapshots in one run.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate one or more geometry files or directories")
    validate.add_argument("paths", nargs="+", help="geometry JSON files, directories, or glob patterns")
    validate.add_argument(
        "--recursive", action="store_true",
        help="search directories recursively (directory inputs otherwise search one level)",
    )
    validate.add_argument(
        "--fix", action="store_true",
        help="safely canonicalize valid snapshots; semantic geometry errors are never auto-corrected",
    )
    validate.add_argument(
        "--report", type=Path,
        help="write the complete machine-readable JSON report to this path",
    )
    validate.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="stdout report format (default: text)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    files = _expand_inputs(args.paths, args.recursive)
    if not files:
        parser.error("no geometry JSON files found; pass explicit files or a directory containing JSON models")
    if args.report:
        if args.report.is_symlink():
            parser.error("report path must not be a symbolic link")
        report_target = args.report.resolve()
        if report_target in {path.resolve() for path in files}:
            parser.error("report path must not overwrite a geometry input file")

    results = [_validate_file(path, args.fix) for path in files]
    passed = sum(item["status"] == "PASS" for item in results)
    report: dict[str, Any] = {
        "report_version": "1.0",
        "mode": "fix" if args.fix else "validate",
        "files": results,
        "summary": {"total": len(results), "passed": passed, "failed": len(results) - passed},
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else _render_text(report)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
