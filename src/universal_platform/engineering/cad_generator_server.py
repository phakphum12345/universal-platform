"""Explicit local launcher for the CAD Generator and Control Center.

Importing this module does not open a socket. The server binds only to IPv4
loopback and uses an OS-selected port unless the operator explicitly chooses
one. SQLite data is stored in a per-user data directory by default.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from secrets import token_urlsafe
from typing import Sequence

from .cad_generator_http_api import (
    CADGeneratorHTTPServer,
    SQLiteCADAPIAuditLog,
    create_cad_generator_http_server,
)
from .cad_generator_service import CADGeneratorService
from .feature_artifact_store import SQLiteFeatureArtifactCache
from .feature_history_store import SQLiteFeatureHistoryStore


def resolve_data_directory(
    data_directory: str | Path | None = None,
    *,
    local_app_data: str | Path | None = None,
    xdg_data_home: str | Path | None = None,
    home: str | Path | None = None,
    windows: bool | None = None,
) -> Path:
    """Resolve a persistent per-user data directory without changing the CWD."""
    if data_directory is not None:
        return Path(data_directory).expanduser().resolve()
    user_home = Path(home).expanduser() if home is not None else Path.home()
    is_windows = os.name == "nt" if windows is None else windows
    local_root = (
        Path(local_app_data).expanduser()
        if local_app_data is not None and str(local_app_data).strip()
        else None
    )
    xdg_root = (
        Path(xdg_data_home).expanduser()
        if xdg_data_home is not None and str(xdg_data_home).strip()
        else None
    )
    if is_windows or local_root is not None:
        root = local_root if local_root is not None else user_home / "AppData" / "Local"
    else:
        root = xdg_root if xdg_root is not None else user_home / ".local" / "share"
    return (root / "UniversalPlatform" / "CADGenerator").resolve()


def _validate_port(port: int) -> int:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 through 65535")
    return port


def _parse_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("port must be an integer") from error
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return port


def create_local_server(
    data_directory: str | Path,
    *,
    port: int = 0,
    bearer_token: str | None = None,
) -> tuple[CADGeneratorHTTPServer, str, bool, Path]:
    """Build the local service and bind its loopback socket without starting it."""
    selected_port = _validate_port(port)
    data_path = Path(data_directory).expanduser().resolve()
    data_path.mkdir(parents=True, exist_ok=True)

    generated_token = bearer_token is None
    token = token_urlsafe(32) if generated_token else bearer_token
    if not isinstance(token, str) or len(token.encode("utf-8")) < 32:
        raise ValueError("bearer token must contain at least 32 UTF-8 bytes")

    history_store = SQLiteFeatureHistoryStore(data_path / "feature-history.sqlite3")
    artifact_cache = SQLiteFeatureArtifactCache(data_path / "feature-artifacts.sqlite3")
    audit_log = SQLiteCADAPIAuditLog(data_path / "cad-api-audit.sqlite3")
    service = CADGeneratorService(history_store, artifact_cache)
    server = create_cad_generator_http_server(
        service,
        audit_log=audit_log,
        bearer_token=token,
        host="127.0.0.1",
        port=selected_port,
    )
    return server, token, generated_token, data_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="up-cad-generator",
        description="Start the local-only CAD Generator and Control Center.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="persistent data directory (default: per-user LocalAppData/XDG data path)",
    )
    parser.add_argument(
        "--port",
        type=_parse_port,
        default=0,
        help="IPv4 loopback port; 0 selects an available port (default)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Start the foreground local service; Ctrl+C closes the listening socket."""
    args = build_parser().parse_args(argv)
    data_path = resolve_data_directory(
        args.data_dir,
        local_app_data=os.environ.get("LOCALAPPDATA"),
        xdg_data_home=os.environ.get("XDG_DATA_HOME"),
    )
    configured_token = os.environ.get("UP_CAD_BEARER_TOKEN")
    try:
        server, token, generated, data_path = create_local_server(
            data_path,
            port=args.port,
            bearer_token=configured_token,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(
            f"CAD Generator startup failed ({error.__class__.__name__}): {error}",
            file=sys.stderr,
        )
        return 2

    origin = f"http://127.0.0.1:{server.server_port}"
    print(f"CAD Generator: {origin}/", flush=True)
    print(f"Control Center: {origin}/control-center", flush=True)
    print(f"Persistent data: {data_path}", flush=True)
    if generated:
        print(
            f"Bearer token (copy into the local UI; not saved): {token}",
            flush=True,
        )
    else:
        print("Bearer token loaded from UP_CAD_BEARER_TOKEN; value not echoed.", flush=True)
    print("Bound to 127.0.0.1 only. Press Ctrl+C to stop.", flush=True)

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("Stopping local CAD Generator.", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
