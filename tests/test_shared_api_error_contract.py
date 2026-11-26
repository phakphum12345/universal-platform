"""Regression tests for the additive shared API error envelope."""
from __future__ import annotations

import json
import re
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from universal_platform.engineering import (
    CADGeneratorService,
    SQLiteCADAPIAuditLog,
    SQLiteFeatureArtifactCache,
    SQLiteFeatureHistoryStore,
    create_cad_generator_http_server,
)

TOKEN = "shared-error-contract-test-" + ("x" * 32)
REQUEST_ID = "shared-error-test-0001"


def _request(base: str, path: str, *, token: str | None) -> tuple[int, dict, str]:
    headers = {"X-Request-ID": REQUEST_ID}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(base + path, headers=headers)
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read()), response.headers["X-Request-ID"]
    except HTTPError as exc:
        return exc.code, json.loads(exc.read()), exc.headers["X-Request-ID"]


def _assert_error_contract(payload: dict, schema: dict, response_request_id: str) -> None:
    assert set(schema["required"]) == {"error"}
    error_schema = schema["properties"]["error"]
    assert set(error_schema["required"]) == {"code", "message"}
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["error"]["code"], str)
    assert re.fullmatch(r"^[A-Z][A-Z0-9_]{1,63}$", payload["error"]["code"])
    assert isinstance(payload["error"]["message"], str)
    assert 1 <= len(payload["error"]["message"]) <= 4096
    assert payload["request_id"] == response_request_id == REQUEST_ID
    assert re.fullmatch(r"^[A-Za-z0-9._-]{8,128}$", response_request_id)


def test_python_api_errors_follow_shared_error_envelope(tmp_path: Path) -> None:
    schema_path = Path(__file__).parents[1] / "schemas" / "shared" / "error-envelope.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["request_id"]["$ref"] == "request-id.schema.json"

    service = CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path / "history.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3"),
    )
    audit = SQLiteCADAPIAuditLog(tmp_path / "audit.sqlite3")
    server: HTTPServer = create_cad_generator_http_server(
        service, audit_log=audit, bearer_token=TOKEN
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, unauthorized, request_id = _request(base, "/health", token=None)
        assert status == 401
        _assert_error_contract(unauthorized, schema, request_id)

        status, missing_route, request_id = _request(
            base, "/v1/contract-test-missing-route", token=TOKEN
        )
        assert status == 404
        _assert_error_contract(missing_route, schema, request_id)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
