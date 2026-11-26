from __future__ import annotations

import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from universal_platform.engineering.cad_generator_http_api import (
    SQLiteCADAPIAuditLog,
    create_cad_generator_http_server,
)
from universal_platform.engineering.cad_generator_service import CADGeneratorService
from universal_platform.engineering.feature_artifact_store import SQLiteFeatureArtifactCache
from universal_platform.engineering.feature_history_store import SQLiteFeatureHistoryStore
from universal_platform.engineering.settings_store import SQLiteSettingsStore

TOKEN = "settings-api-test-token-with-at-least-32-bytes"


@pytest.fixture
def settings_api(tmp_path):
    service = CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path / "history.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3"),
    )
    audit = SQLiteCADAPIAuditLog(tmp_path / "api-audit.sqlite3")
    settings = SQLiteSettingsStore(tmp_path / "settings.sqlite3")
    server = create_cad_generator_http_server(
        service, audit_log=audit, bearer_token=TOKEN, settings_store=settings,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", audit, settings
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def send(base, path, *, method="GET", body=None, token=TOKEN, request_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if request_id:
        headers["X-Request-ID"] = request_id
    request = Request(
        base + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read().decode("utf-8")), response.headers


def test_settings_api_reads_defaults_with_effective_sources(settings_api):
    base, audit, store = settings_api
    status, payload, headers = send(base, "/v1/settings", request_id="settings-read-001")
    assert status == 200
    assert payload["settings"]["revision"] == 0
    assert payload["settings"]["values"]["appearance.theme"] == "system"
    assert payload["settings"]["sources"]["appearance.theme"] == "default"
    assert headers["X-Request-ID"] == payload["request_id"] == "settings-read-001"
    assert audit.verify()
    assert store.verify_audit()


def test_settings_api_updates_with_cas_and_value_free_audit(settings_api):
    base, audit, store = settings_api
    status, payload, _ = send(
        base, "/v1/settings", method="PUT",
        body={"expected_revision": 0, "values": {"appearance.theme": "dark"}},
        request_id="settings-write-001",
    )
    assert status == 200
    assert payload["settings"]["revision"] == 1
    assert payload["settings"]["values"]["appearance.theme"] == "dark"
    events = store.audit_events()
    assert events[0]["changed_keys"] == ["appearance.theme"]
    assert "dark" not in str(events[0])
    assert audit.verify()


def test_settings_api_rejects_stale_and_secret_like_settings(settings_api):
    base, audit, _store = settings_api
    send(
        base, "/v1/settings", method="PUT",
        body={"expected_revision": 0, "values": {"appearance.theme": "light"}},
    )
    status, conflict, _ = send(
        base, "/v1/settings", method="PUT",
        body={"expected_revision": 0, "values": {"appearance.theme": "dark"}},
    )
    assert status == 409
    assert conflict["error"]["code"] == "REVISION_CONFLICT"
    status, invalid, _ = send(
        base, "/v1/settings", method="PUT",
        body={"expected_revision": 1, "values": {"provider.password": "never-echo"}},
    )
    assert status == 400
    assert invalid["error"]["code"] == "INVALID_REQUEST"
    assert "never-echo" not in str(invalid)
    assert audit.verify()


def test_settings_api_rejects_unknown_query_fields_and_methods(settings_api):
    base, audit, _store = settings_api
    status, payload, _ = send(base, "/v1/settings?scope=workspace")
    assert status == 400
    assert payload["error"]["code"] == "UNEXPECTED_QUERY"
    status, payload, _ = send(base, "/v1/settings", method="POST")
    assert status == 405
    assert payload["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert audit.verify()

def test_settings_api_is_reported_ready_only_when_store_is_configured(settings_api):
    base, audit, _store = settings_api
    status, payload, _ = send(base, "/v1/platform/status")
    assert status == 200
    components = {item["id"]: item for item in payload["components"]}
    assert components["settings"]["status"] == "READY"
    assert "authenticated read" in components["settings"]["evidence"]
    assert payload["status"] == "PARTIAL"
    assert audit.verify()
