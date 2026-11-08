import json
from pathlib import Path
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
    assert 'id="mesh-preview"' in html
    assert 'id="mesh-validation"' in html
    assert 'id="mesh-selection"' in html
    assert 'id="mesh-clear-selection"' in html
    assert 'id="feature-tree"' in html
    assert 'id="feature-tree-state"' in html
    assert 'id="feature-inspector"' in html
    assert 'id="feature-edit-parameters"' in html
    assert 'id="feature-apply-edit"' in html
    assert 'id="feature-add"' in html
    assert 'id="feature-add-kind"' in html
    assert 'id="feature-add-output"' in html
    assert 'id="feature-remove"' in html
    assert 'id="feature-remove-cascade"' in html
    assert 'id="feature-suppress"' in html
    assert 'id="feature-unsuppress"' in html
    assert 'id="feature-suppress-cascade"' in html

    with urlopen(base + "/static/cad_generator.js", timeout=3) as response:
        script = response.read().decode("utf-8")
        assert response.headers["Content-Type"].startswith("text/javascript")
    assert "localStorage" not in script
    assert "credentials: \"omit\"" in script
    assert "/v1/templates/polygon-extrusion" in script
    assert "renderMeshPreview" in script
    assert "MAX_PREVIEW_TRIANGLES" in script
    assert "MAX_PREVIEW_VERTICES" in script
    assert "innerHTML" not in script
    assert 'id="mesh-zoom-in"' in html
    assert 'id="mesh-zoom-out"' in html
    assert 'id="mesh-reset-view"' in html
    assert 'meshPreview.addEventListener("pointerdown"' in script
    assert 'meshPreview.addEventListener("pointermove"' in script
    assert 'meshPreview.addEventListener("wheel"' in script
    assert "meshCamera.pitch = clamp" in script
    assert "meshCamera.zoom * factor, 0.5, 4" in script
    assert "meshCamera.yaw += dx * 0.01" in script
    assert "meshCamera.panX + dx, -600, 600" in script
    assert "meshCamera.panY + dy, -400, 400" in script
    assert "Malformed triangle indices prevent rendering" in script
    assert "function disableMeshPreview()" in script
    assert 'byId("mesh-validation").textContent += " ·' in script
    assert "pointercancel" in script
    assert "function selectMeshTriangle(index)" in script
    assert "Math.hypot(nx, ny, nz)" in script
    assert "mesh.length_unit" in script
    assert "mesh.frame_id" in script
    assert 'polygon.setAttribute("aria-pressed"' in script
    assert 'polygon.setAttribute("data-triangle-index"' in script
    assert 'event.key === "Enter" || event.key === " "' in script
    assert "suppressMeshClick" in script
    assert "clearMeshSelection" in script
    assert "function renderFeatureTree()" in script
    assert "MAX_FEATURE_TREE_NODES = 500" in script
    assert "deterministic topological order" in script
    assert "Feature dependency cycle detected" in script
    assert "featureInspector.textContent = JSON.stringify" in script
    assert "function commitFeatureEdit(operation, fields)" in script
    assert '"/v1/histories/" + encodeURIComponent(id) + "/edit"' in script
    assert 'commitFeatureEdit("replace"' in script
    assert 'commitFeatureEdit("add"' in script
    assert 'commitFeatureEdit("remove"' in script
    assert 'commitFeatureEdit("suppress"' in script
    assert 'commitFeatureEdit("unsuppress"' in script
    assert "window.confirm(" in script
    assert "selectedFeatureSuppressed" in script
    assert "revisionSelect.value !== String(expected)" in script
    assert "function updateFeatureEditorControls(hasSelection)" in script
    assert "revisionSelect.value === String(expected)" in script
    assert 'byId("feature-add").disabled = !canEditCurrentHead' in script
    assert 'byId("feature-remove").disabled = !(canEditCurrentHead && hasSelection)' in script
    assert 'snapshotInput.addEventListener("input", renderFeatureTree)' in script
    assert "innerHTML" not in script

    with urlopen(base + "/static/cad_generator.css", timeout=3) as response:
        stylesheet = response.read().decode("utf-8")
        assert response.headers["Content-Type"].startswith("text/css")
    assert "touch-action: none" in stylesheet
    assert ".mesh-face-selected" in stylesheet
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
    mesh_payload = generated["regeneration"]["artifacts"][-1]["payload"]
    assert mesh_payload["validation"]["watertight"] is True
    assert len(mesh_payload["mesh"]["vertices"]) >= 4
    assert len(mesh_payload["mesh"]["triangles"]) >= 4
    assert len(generated["regeneration"]["artifacts"][-1]["content_sha256"]) == 64
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


def test_ci_checks_cad_generator_javascript_syntax_without_external_dependencies():
    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "engineering-core.yml")
    content = workflow.read_text(encoding="utf-8")
    assert "node --check src/universal_platform/engineering/static/cad_generator.js" in content
    assert "hashFiles('src/universal_platform/engineering/static/cad_generator.js') != ''" in content


def test_http_api_edits_feature_history_with_revision_checks_and_immutable_snapshots(api):
    base, audit, _ = api
    status, saved = send(
        base, "/v1/histories", method="POST",
        body={"history": make_history().to_dict(), "expected_revision": 0},
    )
    assert status == 201
    assert saved["revision"] == 1

    replacement = FeatureNode.create(
        "extrusion", FeatureKind.EXTRUSION, ("profile",),
        {"solid_id": "solid.http", "height": 3.0},
    )
    status, replaced = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={
            "expected_revision": 1,
            "operation": "replace",
            "feature_id": "extrusion",
            "feature": replacement.to_dict(),
        },
    )
    assert status == 201
    assert replaced["revision"] == 2

    added_node = FeatureNode.create("extra.mesh", FeatureKind.MESH, ("extrusion",))
    status, added = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={
            "expected_revision": 2,
            "operation": "add",
            "feature": added_node.to_dict(),
            "make_output": True,
        },
    )
    assert status == 201
    assert added["revision"] == 3

    status, removed = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={
            "expected_revision": 3,
            "operation": "remove",
            "feature_id": "extra.mesh",
        },
    )
    assert status == 201
    assert removed["revision"] == 4

    status, original = send(base, "/v1/histories/history.http-api?revision=1")
    assert status == 200
    original_extrusion = next(
        node for node in original["history"]["nodes"] if node["feature_id"] == "extrusion"
    )
    assert original_extrusion["parameters"]["height"] == 2.0

    status, latest = send(base, "/v1/histories/history.http-api?revision=4")
    assert status == 200
    latest_extrusion = next(
        node for node in latest["history"]["nodes"] if node["feature_id"] == "extrusion"
    )
    assert latest_extrusion["parameters"]["height"] == 3.0
    assert latest["history"]["output_feature_ids"] == ["mesh"]

    status, conflict = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={
            "expected_revision": 3,
            "operation": "remove",
            "feature_id": "extra.mesh",
        },
    )
    assert status == 409
    assert conflict["error"]["code"] == "REVISION_CONFLICT"

    status, malformed = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={
            "expected_revision": 4,
            "operation": "add",
            "feature": {"feature_id": "unsafe", "kind": "RUN_SHELL"},
        },
    )
    assert status == 400
    assert malformed["error"]["code"] == "INVALID_FIELDS" or malformed["error"]["code"] == "INVALID_FEATURE"

    status, revisions = send(base, "/v1/histories/history.http-api/revisions")
    assert status == 200
    assert revisions["revisions"] == [1, 2, 3, 4]
    assert audit.verify()



def make_history_with_alternate_output():
    original = make_history()
    profile = next(node for node in original.nodes if node.feature_id == "profile")
    alternate = (
        FeatureNode.create(
            "profile.alt", FeatureKind.SKETCH_PROFILE, (),
            {"sketch": profile.parameters["sketch"]},
        ),
        FeatureNode.create(
            "extrusion.alt", FeatureKind.EXTRUSION, ("profile.alt",),
            {"solid_id": "solid.alt", "height": 1.5},
        ),
        FeatureNode.create("mesh.alt", FeatureKind.MESH, ("extrusion.alt",)),
    )
    return FeatureHistory(
        original.history_id, original.nodes + alternate, ("mesh", "mesh.alt")
    )


def test_http_api_suppresses_and_restores_features_with_revision_checks(api):
    base, audit, _ = api
    status, saved = send(
        base, "/v1/histories", method="POST",
        body={"history": make_history_with_alternate_output().to_dict(), "expected_revision": 0},
    )
    assert status == 201
    assert saved["revision"] == 1

    status, suppressed = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={
            "expected_revision": 1,
            "operation": "suppress",
            "feature_id": "extrusion",
            "cascade": True,
        },
    )
    assert status == 201
    assert suppressed["revision"] == 2

    status, snapshot = send(base, "/v1/histories/history.http-api?revision=2")
    assert status == 200
    assert snapshot["history"]["schema_version"] == "1.1"
    assert snapshot["history"]["suppressed_feature_ids"] == ["extrusion", "mesh"]

    status, regenerated = send(
        base, "/v1/histories/history.http-api/regenerate", method="POST",
        body={"revision": 2},
    )
    assert status == 200
    assert regenerated["regeneration"]["status"] == "SUCCESS"
    assert regenerated["regeneration"]["suppressed_feature_ids"] == ["extrusion", "mesh"]

    status, restored_parent = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={"expected_revision": 2, "operation": "unsuppress", "feature_id": "extrusion"},
    )
    assert status == 201
    assert restored_parent["revision"] == 3

    status, restored_output = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={"expected_revision": 3, "operation": "unsuppress", "feature_id": "mesh"},
    )
    assert status == 201
    assert restored_output["revision"] == 4

    status, conflict = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={"expected_revision": 3, "operation": "unsuppress", "feature_id": "mesh"},
    )
    assert status == 409
    assert conflict["error"]["code"] == "REVISION_CONFLICT"

    status, invalid = send(
        base, "/v1/histories/history.http-api/edit", method="POST",
        body={
            "expected_revision": 4,
            "operation": "unsuppress",
            "feature_id": "mesh",
            "cascade": True,
        },
    )
    assert status == 400
    assert invalid["error"]["code"] == "INVALID_FIELDS"
    assert audit.verify()
