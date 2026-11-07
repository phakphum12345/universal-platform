import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from universal_platform.engineering import (
    CADGeneratorService,
    SQLiteCADAPIAuditLog,
    SQLiteFeatureArtifactCache,
    SQLiteFeatureHistoryStore,
    create_cad_generator_http_server,
)
from universal_platform.engineering.feature_history import FeatureHistory, FeatureKind, FeatureNode
from universal_platform.engineering.parametric_sketch import (
    ParametricSketch,
    SketchConstraint,
    SketchConstraintKind as Kind,
    SketchPoint,
    SketchSegment,
)


TOKEN = "local-test-token-" + ("x" * 40)


def make_history():
    coordinates = ((0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0))
    ids = ("p0", "p1", "p2", "p3")
    points = tuple(SketchPoint(key, x, y) for key, (x, y) in zip(ids, coordinates))
    segments = tuple(SketchSegment(f"edge.{i}", ids[i], ids[(i + 1) % 4]) for i in range(4))
    constraints = tuple(
        item
        for key, (x, y) in zip(ids, coordinates)
        for item in (
            SketchConstraint(f"x.{key}", Kind.FIX_X, (key,), x),
            SketchConstraint(f"y.{key}", Kind.FIX_Y, (key,), y),
        )
    )
    sketch = ParametricSketch("profile", "part.xy", "mm", points, segments, constraints)
    return FeatureHistory(
        "history.http-api",
        (
            FeatureNode.create("mesh", FeatureKind.MESH, ("extrusion",)),
            FeatureNode.create(
                "extrusion", FeatureKind.EXTRUSION, ("profile",),
                {"solid_id": "solid.http", "height": 2.0},
            ),
            FeatureNode.create("profile", FeatureKind.SKETCH_PROFILE, (), {"sketch": sketch.to_dict()}),
        ),
        ("mesh",),
    )


@pytest.fixture
def api(tmp_path):
    service = CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path / "source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3"),
    )
    audit = SQLiteCADAPIAuditLog(tmp_path / "api-audit.sqlite3")
    server = create_cad_generator_http_server(
        service, audit_log=audit, bearer_token=TOKEN,
        max_request_bytes=32_768,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", audit, server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def send(base, path, *, method="GET", body=None, token=TOKEN, extra_headers=None):
    headers = dict(extra_headers or {})
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_local_authoring_ui_is_served_same_origin_without_exposing_cors(api):
    base, audit, _ = api
    with urlopen(base + "/", timeout=3) as response:
        html = response.read().decode("utf-8")
        assert response.status == 200
        assert response.headers["Content-Type"].startswith("text/html")
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]
        assert "Access-Control-Allow-Origin" not in response.headers
    assert "CAD Generator" in html
    assert "/static/cad_generator.js" in html
    assert "/static/cad_generator.css" in html
    assert 'id="profile-canvas"' in html
    assert "Generate FeatureHistory JSON" in html

    with urlopen(base + "/static/cad_generator.js", timeout=3) as response:
        script = response.read().decode("utf-8")
        assert response.headers["Content-Type"].startswith("text/javascript")
    assert "localStorage" not in script
    assert "credentials: \"omit\"" in script
    assert "/v1/templates/polygon-extrusion" in script
    assert "innerHTML" not in script

    with urlopen(base + "/static/cad_generator.css", timeout=3) as response:
        stylesheet = response.read().decode("utf-8")
        assert response.headers["Content-Type"].startswith("text/css")
    assert ".panel" in stylesheet

    status, health = send(base, "/health", extra_headers={"Origin": base})
    assert status == 200
    assert health["status"] == "READY"
    assert audit.verify()


def test_http_polygon_template_endpoint_generates_and_regenerates_a_profile(api):
    base, audit, _ = api
    status, template = send(
        base, "/v1/templates/polygon-extrusion", method="POST",
        body={
            "history_id": "history.from-canvas",
            "points": [[0, 0], [12, 0], [12, 8], [0, 8]],
            "height": 4,
            "length_unit": "mm",
        },
    )
    assert status == 200
    assert template["template"] == "polygon-extrusion-v1"
    history = template["history"]
    assert history["history_id"] == "history.from-canvas"
    assert len(history["nodes"][0]["parameters"]["sketch"]["points"]) == 4

    status, saved = send(
        base, "/v1/histories", method="POST",
        body={"history": history, "expected_revision": 0},
    )
    assert status == 201
    status, generated = send(
        base, "/v1/histories/history.from-canvas/regenerate",
        method="POST", body={"revision": saved["revision"]},
    )
    assert status == 200
    assert generated["regeneration"]["status"] == "SUCCESS"
    assert generated["regeneration"]["artifacts"][-1]["payload"]["validation"]["watertight"] is True
    assert audit.verify()


def test_http_polygon_template_rejects_invalid_profile_points(api):
    base, _, _ = api
    status, result = send(
        base, "/v1/templates/polygon-extrusion", method="POST",
        body={
            "history_id": "history.invalid-profile",
            "points": [[0, 0], [1, 1]],
            "height": 2,
        },
    )
    assert status == 400
    assert result["error"]["code"] == "INVALID_REQUEST"


def test_http_api_saves_reads_and_regenerates_exact_history_revision(api):
    base, audit, server = api
    status, health = send(base, "/health")
    assert status == 200
    assert health["status"] == "READY"

    status, saved = send(
        base, "/v1/histories", method="POST",
        body={"history": make_history().to_dict(), "expected_revision": 0},
        extra_headers={"Origin": base},
    )
    assert status == 201
    assert saved["history_id"] == "history.http-api"
    assert saved["revision"] == 1
    assert len(saved["content_sha256"]) == 64

    status, revisions = send(base, "/v1/histories/history.http-api/revisions")
    assert status == 200
    assert revisions["revisions"] == [1]

    status, loaded = send(base, "/v1/histories/history.http-api?revision=1")
    assert status == 200
    assert loaded["revision"] == 1
    assert loaded["history"]["history_id"] == "history.http-api"

    status, generated = send(
        base, "/v1/histories/history.http-api/regenerate",
        method="POST", body={"revision": 1},
    )
    assert status == 200
    assert generated["source_revision"]["revision"] == 1
    assert generated["regeneration"]["status"] == "SUCCESS"
    assert generated["regeneration"]["artifacts"][-1]["payload"]["validation"]["watertight"] is True
    assert audit.count() == 10
    assert audit.verify()
    assert server.server_address[0] == "127.0.0.1"
    assert server.server_port != 0


def test_http_api_fails_closed_for_missing_auth_bad_origin_and_bad_method(api):
    base, audit, _ = api
    status, unauthorized = send(base, "/health", token=None)
    assert status == 401
    assert unauthorized["error"]["code"] == "UNAUTHORIZED"

    request = Request(
        base + "/health",
        headers={"Authorization": f"Bearer {TOKEN}", "Origin": "https://attacker.example"},
    )
    with pytest.raises(HTTPError) as error:
        urlopen(request, timeout=3)
    assert error.value.code == 403

    status, rejected = send(base, "/health", method="DELETE")
    assert status == 405
    assert rejected["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert audit.verify()


def test_http_api_enforces_body_size_strict_json_and_revision_conflict(api):
    base, audit, _ = api
    too_large = {"history": {"padding": "x" * 40_000}, "expected_revision": 0}
    status, oversized = send(base, "/v1/histories", method="POST", body=too_large)
    assert status == 413
    assert oversized["error"]["code"] == "REQUEST_TOO_LARGE"

    status, malformed = send(
        base, "/v1/histories", method="POST",
        body={"history": make_history().to_dict(), "expected_revision": 0},
    )
    assert status == 201

    status, conflict = send(
        base, "/v1/histories", method="POST",
        body={"history": make_history().to_dict(), "expected_revision": 0},
    )
    assert status == 409
    assert conflict["error"]["code"] == "REVISION_CONFLICT"
    assert audit.verify()


def test_http_api_rejects_unsafe_bind_and_weak_credentials(tmp_path):
    service = CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path / "source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3"),
    )
    audit = SQLiteCADAPIAuditLog(tmp_path / "audit.sqlite3")
    with pytest.raises(ValueError, match="127.0.0.1"):
        create_cad_generator_http_server(
            service, audit_log=audit, bearer_token=TOKEN, host="0.0.0.0"
        )
    with pytest.raises(ValueError, match="32 UTF-8 bytes"):
        create_cad_generator_http_server(
            service, audit_log=audit, bearer_token="too-short"
        )
    with pytest.raises(ValueError, match="port"):
        create_cad_generator_http_server(
            service, audit_log=audit, bearer_token=TOKEN, port=65536
        )


def test_api_audit_chain_detects_modified_records(tmp_path):
    audit_path = tmp_path / "audit.sqlite3"
    audit = SQLiteCADAPIAuditLog(audit_path)
    audit.append(
        request_id="request-1", event="REQUEST_RECEIVED", method="GET",
        path="/health", peer="127.0.0.1",
    )
    assert audit.verify()
    import sqlite3
    with sqlite3.connect(audit_path) as connection:
        connection.execute(
            "UPDATE cad_api_audit SET event_json = ? WHERE sequence = 1",
            ('{"event":"tampered"}',),
        )
    assert not audit.verify()
