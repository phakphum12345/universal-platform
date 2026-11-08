"""Loopback-only, bearer-authenticated HTTP adapter for the CAD generator.

Importing this module never opens a socket. Call create_cad_generator_http_server
and explicitly invoke serve_forever() to start the local service.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
from pathlib import Path
import re
import sqlite3
from threading import RLock
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import uuid4

from .cad_generator_service import CADGeneratorService
from .cad_generator_templates import build_polygon_extrusion_history
from .errors import InvalidModelError
from .feature_history import FeatureKind, FeatureNode
from .feature_artifact_store import FeatureArtifactCacheIntegrityError
from .feature_history_store import (
    FeatureHistoryNavigationUnavailable,
    FeatureHistoryRevisionConflict,
    FeatureHistoryStoreIntegrityError,
)

_HISTORY_ID = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_MAX_BODY_DEFAULT = 1_048_576
_AUDIT_SCHEMA_VERSION = 1


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _parse_feature_node(value: object) -> FeatureNode:
    required = {"feature_id", "kind", "input_feature_ids", "parameters"}
    if not isinstance(value, dict) or set(value) != required:
        raise _HTTPError(
            400, "INVALID_FEATURE",
            "feature must contain exactly feature_id, kind, input_feature_ids and parameters",
        )
    if not isinstance(value["input_feature_ids"], list) or not isinstance(value["parameters"], dict):
        raise _HTTPError(400, "INVALID_FEATURE", "feature inputs must be an array and parameters must be an object")
    try:
        kind = FeatureKind(value["kind"])
    except (TypeError, ValueError) as exc:
        raise _HTTPError(400, "INVALID_FEATURE", "feature kind is unsupported") from exc
    return FeatureNode.create(
        value["feature_id"], kind, tuple(value["input_feature_ids"]), value["parameters"]
    )


class CADAPIAuditIntegrityError(RuntimeError):
    """Raised when the append-only local API audit chain is invalid."""


class SQLiteCADAPIAuditLog:
    """Explicit local SQLite audit log with a SHA-256 append-only hash chain.

    Request bodies, bearer tokens and other credentials are never accepted by
    this API. Audit rows contain only method, normalized path, request ID,
    peer address, event kind, status and outcome.
    """

    def __init__(self, database_path: str | Path):
        raw = str(database_path)
        if not raw.strip() or raw in {":memory:", ""} or raw.startswith("file:"):
            raise ValueError("audit database_path must be an explicit filesystem path")
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > _AUDIT_SCHEMA_VERSION:
                raise CADAPIAuditIntegrityError("audit database schema is newer than this implementation")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS cad_api_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT NOT NULL,
                    previous_sha256 TEXT,
                    event_sha256 TEXT NOT NULL UNIQUE
                )"""
            )
            connection.execute(f"PRAGMA user_version = {_AUDIT_SCHEMA_VERSION}")

    def append(
        self, *, request_id: str, event: str, method: str, path: str,
        peer: str, status: int | None = None, outcome: str | None = None,
    ) -> str:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "event": event,
            "method": method,
            "path": path,
            "peer": peer,
            "status": status,
            "outcome": outcome,
        }
        encoded = _canonical_json(record)
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT event_sha256 FROM cad_api_audit ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous = row[0] if row else None
            digest = sha256(((previous or "") + encoded).encode("utf-8")).hexdigest()
            connection.execute(
                "INSERT INTO cad_api_audit(event_json, previous_sha256, event_sha256) VALUES (?, ?, ?)",
                (encoded, previous, digest),
            )
            connection.execute("COMMIT")
        return digest

    def verify(self) -> bool:
        previous: str | None = None
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT event_json, previous_sha256, event_sha256 "
                "FROM cad_api_audit ORDER BY sequence"
            ).fetchall()
        for encoded, stored_previous, stored_digest in rows:
            if stored_previous != previous:
                return False
            expected = sha256(((previous or "") + encoded).encode("utf-8")).hexdigest()
            if not hmac.compare_digest(expected, stored_digest):
                return False
            try:
                parsed = json.loads(encoded)
                if _canonical_json(parsed) != encoded:
                    return False
            except (TypeError, ValueError):
                return False
            previous = stored_digest
        return True

    def count(self) -> int:
        with closing(self._connect()) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM cad_api_audit").fetchone()[0])


class _CADGeneratorRequestHandler(BaseHTTPRequestHandler):
    server_version = "UniversalPlatformCADAPI/1.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        super().setup()
        self.request.settimeout(self.server.request_timeout_seconds)

    def log_message(self, format: str, *args: object) -> None:
        # Do not emit request headers, paths with query strings, or credentials.
        return

    def do_GET(self) -> None:
        self._handle_request()

    def do_POST(self) -> None:
        self._handle_request()

    def do_PUT(self) -> None:
        self._handle_request()

    def do_PATCH(self) -> None:
        self._handle_request()

    def do_DELETE(self) -> None:
        self._handle_request()

    def _send_static(self, status: int, asset: tuple[str, bytes], request_id: str) -> None:
        content_type, content = asset
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'",
        )
        self.send_header("X-Request-ID", request_id)
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(content)
        self.close_connection = True

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = _canonical_json(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(encoded)
        self.close_connection = True

    def _authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not supplied.startswith(prefix):
            return False
        return hmac.compare_digest(
            supplied[len(prefix):], self.server.bearer_token
        )

    def _check_local_request(self) -> bool:
        if self.client_address[0] != "127.0.0.1":
            return False
        expected_host = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host", "").lower() != expected_host:
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin != f"http://{expected_host}":
            return False
        if self.headers.get("Transfer-Encoding") is not None:
            return False
        return True

    def _read_json(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise _HTTPError(415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise _HTTPError(411, "LENGTH_REQUIRED", "Content-Length is required")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise _HTTPError(400, "INVALID_CONTENT_LENGTH", "Content-Length must be an integer") from exc
        if length < 0:
            raise _HTTPError(400, "INVALID_CONTENT_LENGTH", "Content-Length must be non-negative")
        if length > self.server.max_request_bytes:
            raise _HTTPError(413, "REQUEST_TOO_LARGE", "Request body exceeds the configured limit")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise _HTTPError(400, "INCOMPLETE_BODY", "Request body is incomplete")
        try:
            value = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise _HTTPError(400, "INVALID_JSON", "Request body must be strict UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise _HTTPError(400, "INVALID_JSON_SHAPE", "Request body must be a JSON object")
        return value

    def _dispatch(self) -> tuple[int, dict[str, Any]]:
        if self.command not in {"GET", "POST"}:
            raise _HTTPError(405, "METHOD_NOT_ALLOWED", "Only GET and POST are supported")
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        if parsed.query and self.command != "GET":
            raise _HTTPError(400, "UNEXPECTED_QUERY", "Query parameters are only accepted on GET")
        if self.command == "GET" and path == "/health":
            return 200, {"status": "READY", "service": "cad-generator", "api_version": "1.0"}

        if self.command == "POST" and path == "/v1/templates/polygon-extrusion":
            body = self._read_json()
            required = {"history_id", "points", "height"}
            if set(body) not in (required, required | {"length_unit"}):
                raise _HTTPError(
                    400, "INVALID_FIELDS",
                    "Expected history_id, points, height and optional length_unit",
                )
            history = build_polygon_extrusion_history(
                body["history_id"], body["points"],
                height=body["height"], length_unit=body.get("length_unit", "mm"),
            )
            return 200, {
                "template": "polygon-extrusion-v1",
                "history": history.to_dict(),
                "limitations": [
                    "Straight-edge closed polygon only; no arcs, splines or construction geometry",
                    "Vertices are fixed by explicit X/Y constraints; no automatic constraint inference",
                    "Self-intersection and solid validity are decided by the regeneration pipeline",
                    "Maximum 64 vertices; this is not a general CAD kernel",
                ],
            }

        prefix = "/v1/histories/"
        if self.command == "POST" and path == "/v1/histories":
            body = self._read_json()
            if set(body) != {"history", "expected_revision"}:
                raise _HTTPError(400, "INVALID_FIELDS", "Expected exactly history and expected_revision")
            expected = body["expected_revision"]
            if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
                raise _HTTPError(400, "INVALID_REVISION", "expected_revision must be a non-negative integer")
            if not isinstance(body["history"], dict):
                raise _HTTPError(400, "INVALID_HISTORY", "history must be a JSON object")
            history_id = body["history"].get("history_id")
            if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
                raise _HTTPError(400, "INVALID_HISTORY_ID", "history ID must use lowercase letters, digits, dot, underscore or hyphen")
            revision = self.server.generator_service.save_snapshot(
                body["history"], expected_revision=expected
            )
            return 201, {
                "history_id": revision.history_id,
                "revision": revision.revision,
                "parent_sha256": revision.parent_sha256,
                "content_sha256": revision.content_sha256,
                "created_at": revision.created_at,
            }

        if not path.startswith(prefix):
            raise _HTTPError(404, "NOT_FOUND", "Route was not found")
        remainder = path[len(prefix):]
        parts = remainder.split("/")
        history_id = parts[0]
        if not _HISTORY_ID.fullmatch(history_id):
            raise _HTTPError(400, "INVALID_HISTORY_ID", "history ID is invalid")

        if self.command == "GET" and len(parts) == 2 and parts[1] == "navigation":
            if parsed.query:
                raise _HTTPError(400, "UNEXPECTED_QUERY", "This route does not accept query parameters")
            return 200, self.server.generator_service.get_navigation_state(history_id).to_dict()

        if self.command == "GET" and len(parts) == 2 and parts[1] == "revisions":
            if parsed.query:
                raise _HTTPError(400, "UNEXPECTED_QUERY", "This route does not accept query parameters")
            return 200, {
                "history_id": history_id,
                "revisions": list(self.server.generator_service.list_revisions(history_id)),
            }

        if self.command == "GET" and len(parts) == 1:
            query = parse_qs(parsed.query, strict_parsing=True)
            if set(query) - {"revision"} or any(len(values) != 1 for values in query.values()):
                raise _HTTPError(400, "INVALID_QUERY", "Only one revision parameter is supported")
            revision_number: int | None = None
            if "revision" in query:
                try:
                    revision_number = int(query["revision"][0])
                except ValueError as exc:
                    raise _HTTPError(400, "INVALID_REVISION", "revision must be a positive integer") from exc
                if revision_number < 1:
                    raise _HTTPError(400, "INVALID_REVISION", "revision must be a positive integer")
            revision = self.server.generator_service.get_revision(
                history_id, revision=revision_number
            )
            return 200, {
                "history_id": revision.history_id,
                "revision": revision.revision,
                "parent_sha256": revision.parent_sha256,
                "content_sha256": revision.content_sha256,
                "created_at": revision.created_at,
                "history": revision.history.to_dict(),
            }

        if self.command == "POST" and len(parts) == 2 and parts[1] in {"undo", "redo"}:
            body = self._read_json()
            if set(body) != {"expected_revision"}:
                raise _HTTPError(400, "INVALID_FIELDS", "Undo/Redo requires exactly expected_revision")
            expected = body["expected_revision"]
            if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
                raise _HTTPError(400, "INVALID_REVISION", "expected_revision must be a positive integer")
            operation = parts[1]
            revision = (
                self.server.generator_service.undo_history(history_id, expected_revision=expected)
                if operation == "undo"
                else self.server.generator_service.redo_history(history_id, expected_revision=expected)
            )
            return 201, {
                "history_id": revision.history_id,
                "revision": revision.revision,
                "parent_sha256": revision.parent_sha256,
                "content_sha256": revision.content_sha256,
                "created_at": revision.created_at,
                "operation": revision.operation,
                "source_revision": revision.source_revision,
                "target_revision": revision.target_revision,
            }

        if self.command == "POST" and len(parts) == 2 and parts[1] == "edit":
            body = self._read_json()
            operation = body.get("operation")
            expected = body.get("expected_revision")
            if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
                raise _HTTPError(400, "INVALID_REVISION", "expected_revision must be a positive integer")

            feature = None
            feature_id = None
            cascade = False
            make_output = False
            if operation == "add":
                if set(body) not in (
                    {"expected_revision", "operation", "feature"},
                    {"expected_revision", "operation", "feature", "make_output"},
                ):
                    raise _HTTPError(400, "INVALID_FIELDS", "add requires expected_revision, operation, feature and optional make_output")
                feature = _parse_feature_node(body["feature"])
                make_output = body.get("make_output", False)
                if not isinstance(make_output, bool):
                    raise _HTTPError(400, "INVALID_FIELDS", "make_output must be a boolean")
            elif operation == "replace":
                if set(body) != {"expected_revision", "operation", "feature_id", "feature"}:
                    raise _HTTPError(400, "INVALID_FIELDS", "replace requires expected_revision, operation, feature_id and feature")
                feature_id = body["feature_id"]
                feature = _parse_feature_node(body["feature"])
            elif operation in {"remove", "suppress"}:
                if set(body) not in (
                    {"expected_revision", "operation", "feature_id"},
                    {"expected_revision", "operation", "feature_id", "cascade"},
                ):
                    raise _HTTPError(400, "INVALID_FIELDS", f"{operation} requires expected_revision, operation, feature_id and optional cascade")
                feature_id = body["feature_id"]
                cascade = body.get("cascade", False)
                if not isinstance(cascade, bool):
                    raise _HTTPError(400, "INVALID_FIELDS", "cascade must be a boolean")
            elif operation == "unsuppress":
                if set(body) != {"expected_revision", "operation", "feature_id"}:
                    raise _HTTPError(400, "INVALID_FIELDS", "unsuppress requires expected_revision, operation and feature_id")
                feature_id = body["feature_id"]
            else:
                raise _HTTPError(400, "INVALID_OPERATION", "operation must be add, replace, remove, suppress or unsuppress")

            revision = self.server.generator_service.edit_history(
                history_id,
                expected_revision=expected,
                operation=operation,
                feature=feature,
                feature_id=feature_id,
                cascade=cascade,
                make_output=make_output,
            )
            return 201, {
                "history_id": revision.history_id,
                "revision": revision.revision,
                "parent_sha256": revision.parent_sha256,
                "content_sha256": revision.content_sha256,
                "created_at": revision.created_at,
            }

        if self.command == "POST" and len(parts) == 2 and parts[1] == "regenerate":
            body = self._read_json()
            if set(body) - {"revision"}:
                raise _HTTPError(400, "INVALID_FIELDS", "Only revision is accepted")
            revision_number = body.get("revision")
            if revision_number is not None and (
                isinstance(revision_number, bool)
                or not isinstance(revision_number, int)
                or revision_number < 1
            ):
                raise _HTTPError(400, "INVALID_REVISION", "revision must be a positive integer")
            run = self.server.generator_service.regenerate(
                history_id, revision=revision_number
            )
            return (200 if run.successful else 422), run.to_dict()

        if self.command not in {"GET", "POST"}:
            raise _HTTPError(405, "METHOD_NOT_ALLOWED", "Only GET and POST are supported")
        raise _HTTPError(404, "NOT_FOUND", "Route was not found")

    def _handle_request(self) -> None:
        request_id = str(uuid4())
        path = urlsplit(self.path).path
        peer = self.client_address[0]
        audit = self.server.audit_log
        try:
            audit.append(
                request_id=request_id, event="REQUEST_RECEIVED",
                method=self.command, path=path, peer=peer,
            )
        except Exception:
            self._send_json(503, {
                "error": {"code": "AUDIT_UNAVAILABLE", "message": "Audit storage is unavailable"},
                "request_id": request_id,
            })
            return

        status = 500
        outcome = "INTERNAL_ERROR"
        payload: dict[str, Any]
        static_asset: tuple[str, bytes] | None = None
        try:
            if not self._check_local_request():
                raise _HTTPError(403, "LOCAL_ONLY", "Request must originate from the configured loopback origin")
            if self.command == "GET" and path in self.server.static_assets:
                static_asset = self.server.static_assets[path]
                status, payload = 200, {"_static_asset": path}
                outcome = "STATIC_ASSET"
            else:
                if not self._authorized():
                    raise _HTTPError(401, "UNAUTHORIZED", "A valid bearer token is required")
                status, payload = self._dispatch()
                outcome = "SUCCESS" if status < 400 else "REJECTED"
        except _HTTPError as exc:
            status = exc.status
            outcome = exc.code
            payload = {"error": {"code": exc.code, "message": exc.message}}
        except FeatureHistoryNavigationUnavailable as exc:
            status, outcome = 409, exc.code
            payload = {"error": {"code": outcome, "message": str(exc)}}
        except FeatureHistoryRevisionConflict as exc:
            status, outcome = 409, "REVISION_CONFLICT"
            payload = {"error": {"code": outcome, "message": str(exc)}}
        except KeyError:
            status, outcome = 404, "NOT_FOUND"
            payload = {"error": {"code": outcome, "message": "History or revision was not found"}}
        except (InvalidModelError, ValueError, TypeError) as exc:
            status, outcome = 400, "INVALID_REQUEST"
            payload = {"error": {"code": outcome, "message": str(exc)}}
        except (FeatureHistoryStoreIntegrityError, FeatureArtifactCacheIntegrityError):
            status, outcome = 500, "STORAGE_INTEGRITY_ERROR"
            payload = {"error": {"code": outcome, "message": "Stored engineering data failed integrity validation"}}
        except Exception:
            status, outcome = 500, "INTERNAL_ERROR"
            payload = {"error": {"code": outcome, "message": "Request could not be completed"}}

        payload["request_id"] = request_id
        try:
            audit.append(
                request_id=request_id, event="REQUEST_COMPLETED",
                method=self.command, path=path, peer=peer,
                status=status, outcome=outcome,
            )
        except Exception:
            status = 503
            static_asset = None
            payload = {
                "error": {"code": "AUDIT_UNAVAILABLE", "message": "Audit completion could not be recorded"},
                "request_id": request_id,
            }
        if static_asset is not None:
            self._send_static(status, static_asset, request_id)
            return
        self._send_json(status, payload)


class _HTTPError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


class CADGeneratorHTTPServer(HTTPServer):
    """Explicitly started single-threaded HTTP server bound to IPv4 loopback."""

    allow_reuse_address = False
    request_queue_size = 8

    def __init__(
        self, server_address: tuple[str, int], generator_service: CADGeneratorService,
        audit_log: SQLiteCADAPIAuditLog, bearer_token: str, max_request_bytes: int,
        request_timeout_seconds: float,
    ):
        self.generator_service = generator_service
        self.audit_log = audit_log
        self.bearer_token = bearer_token
        self.max_request_bytes = max_request_bytes
        self.request_timeout_seconds = request_timeout_seconds
        static_root = Path(__file__).with_name("static")
        self.static_assets = {
            "/": ("text/html; charset=utf-8", (static_root / "cad_generator.html").read_bytes()),
            "/static/cad_generator.css": ("text/css; charset=utf-8", (static_root / "cad_generator.css").read_bytes()),
            "/static/cad_generator.js": ("text/javascript; charset=utf-8", (static_root / "cad_generator.js").read_bytes()),
        }
        super().__init__(server_address, _CADGeneratorRequestHandler)


def create_cad_generator_http_server(
    generator_service: CADGeneratorService,
    *,
    audit_log: SQLiteCADAPIAuditLog,
    bearer_token: str,
    host: str = "127.0.0.1",
    port: int = 0,
    max_request_bytes: int = _MAX_BODY_DEFAULT,
    request_timeout_seconds: float = 5.0,
) -> CADGeneratorHTTPServer:
    """Create (but do not start) a loopback-only server; port 0 selects dynamically."""
    if not isinstance(generator_service, CADGeneratorService):
        raise TypeError("generator_service must be a CADGeneratorService")
    if not isinstance(audit_log, SQLiteCADAPIAuditLog):
        raise TypeError("audit_log must be a SQLiteCADAPIAuditLog")
    if not isinstance(bearer_token, str) or len(bearer_token.encode("utf-8")) < 32:
        raise ValueError("bearer_token must contain at least 32 UTF-8 bytes")
    if host != "127.0.0.1":
        raise ValueError("host must be exactly 127.0.0.1; non-loopback binds are prohibited")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 to 65535")
    if isinstance(max_request_bytes, bool) or not isinstance(max_request_bytes, int) or not 1 <= max_request_bytes <= 16_777_216:
        raise ValueError("max_request_bytes must be between 1 and 16777216")
    if isinstance(request_timeout_seconds, bool) or not isinstance(request_timeout_seconds, (int, float)) or request_timeout_seconds <= 0 or request_timeout_seconds > 30:
        raise ValueError("request_timeout_seconds must be greater than 0 and at most 30")
    return CADGeneratorHTTPServer(
        (host, port), generator_service, audit_log, bearer_token,
        max_request_bytes, float(request_timeout_seconds),
    )


__all__ = [
    "CADAPIAuditIntegrityError",
    "CADGeneratorHTTPServer",
    "SQLiteCADAPIAuditLog",
    "create_cad_generator_http_server",
]
