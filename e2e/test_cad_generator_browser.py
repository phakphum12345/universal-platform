"""Real-browser acceptance tests for the local CAD Generator workbench.

Install the optional browser extra and Chromium before running:
    python -m pip install -e ".[dev,browser]"
    python -m playwright install --with-deps chromium
    python -m pytest -q e2e/test_cad_generator_browser.py
"""
from __future__ import annotations

import json
from threading import Thread

import pytest
from playwright.sync_api import Page, sync_playwright

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
    SketchConstraintKind,
    SketchPoint,
    SketchSegment,
)


TOKEN = "browser-e2e-token-" + ("x" * 40)


def make_history(*, height: float = 2.0) -> FeatureHistory:
    coordinates = ((0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0))
    point_ids = ("p0", "p1", "p2", "p3")
    points = tuple(
        SketchPoint(point_id, x, y)
        for point_id, (x, y) in zip(point_ids, coordinates)
    )
    segments = tuple(
        SketchSegment(f"edge.{index}", point_ids[index], point_ids[(index + 1) % 4])
        for index in range(4)
    )
    constraints = tuple(
        constraint
        for point_id, (x, y) in zip(point_ids, coordinates)
        for constraint in (
            SketchConstraint(
                f"x.{point_id}", SketchConstraintKind.FIX_X, (point_id,), x
            ),
            SketchConstraint(
                f"y.{point_id}", SketchConstraintKind.FIX_Y, (point_id,), y
            ),
        )
    )
    sketch = ParametricSketch("profile", "part.xy", "mm", points, segments, constraints)
    return FeatureHistory(
        "history.browser-e2e",
        (
            FeatureNode.create(
                "mesh", FeatureKind.MESH, ("extrusion",)
            ),
            FeatureNode.create(
                "extrusion",
                FeatureKind.EXTRUSION,
                ("profile",),
                {"solid_id": "solid.browser", "height": height},
            ),
            FeatureNode.create(
                "profile",
                FeatureKind.SKETCH_PROFILE,
                (),
                {"sketch": sketch.to_dict()},
            ),
        ),
        ("mesh",),
    )


@pytest.fixture
def workbench(tmp_path):
    service = CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path / "source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3"),
    )
    service.save_history(make_history(), expected_revision=0)
    audit = SQLiteCADAPIAuditLog(tmp_path / "api-audit.sqlite3")
    server = create_cad_generator_http_server(
        service,
        audit_log=audit,
        bearer_token=TOKEN,
        max_request_bytes=32_768,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            page.goto(base, wait_until="domcontentloaded")
            page.locator("#token").fill(TOKEN)
            page.get_by_role("button", name="Connect").click()
            page.locator("#connection-state").get_by_text("Connected").wait_for()
            page.get_by_role("button", name="Load revision").click()
            page.locator('#feature-tree button[data-feature-id="extrusion"]').wait_for()
            yield page, service, page_errors
        finally:
            browser.close()
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


def test_workbench_starts_without_runtime_errors_and_gates_edit_controls(workbench):
    page, service, page_errors = workbench

    assert page_errors == []
    assert page.locator("#feature-add").is_enabled()
    assert page.locator("#feature-apply-edit").is_enabled()
    assert page.locator("#feature-remove").is_enabled()
    assert service.history_store.load("history.browser-e2e").revision == 1

    # Selecting an earlier immutable revision must disable every edit action.
    page.locator("#revision").select_option("1")
    page.get_by_role("button", name="Load revision").click()
    assert page.locator("#feature-add").is_disabled()
    assert page.locator("#feature-apply-edit").is_disabled()
    assert page.locator("#feature-remove").is_disabled()
    assert page_errors == []


def test_parameter_edit_add_remove_and_explicit_cascade_work_in_browser(workbench):
    page, service, page_errors = workbench

    page.locator('#feature-tree button[data-feature-id="extrusion"]').click()
    page.locator("#feature-edit-parameters").fill(
        json.dumps({"solid_id": "solid.browser", "height": 3.5})
    )
    page.get_by_role("button", name="Apply parameter edit").click()
    page.get_by_text("Saved replace as immutable revision 2.").wait_for()
    edited = service.history_store.load("history.browser-e2e", revision=2).history
    extrusion = next(node for node in edited.nodes if node.feature_id == "extrusion")
    assert extrusion.parameters["height"] == 3.5

    # Add a dependent output and then a downstream non-output feature.
    page.locator("#feature-add-id").fill("feature.parent")
    page.locator("#feature-add-kind").select_option("MESH")
    page.locator("#feature-add-inputs").fill("extrusion")
    page.locator("#feature-add-parameters").fill("{}")
    page.locator("#feature-add-output").check()
    page.get_by_role("button", name="Add feature").click()
    page.get_by_text("Saved add as immutable revision 3.").wait_for()

    page.locator("#feature-add-id").fill("feature.child")
    page.locator("#feature-add-kind").select_option("MESH")
    page.locator("#feature-add-inputs").fill("feature.parent")
    page.locator("#feature-add-parameters").fill("{}")
    page.locator("#feature-add-output").uncheck()
    page.get_by_role("button", name="Add feature").click()
    page.get_by_text("Saved add as immutable revision 4.").wait_for()

    # Removing a node with dependents is rejected until cascade is explicit.
    page.locator('#feature-tree button[data-feature-id="feature.parent"]').click()
    page.get_by_role("button", name="Remove selected feature").click()
    page.get_by_text("dependent", exact=False).wait_for()
    assert service.history_store.load("history.browser-e2e").revision == 4

    page.locator("#feature-remove-cascade").check()
    page.get_by_role("button", name="Remove selected feature").click()
    page.get_by_text("Saved remove as immutable revision 5.").wait_for()
    final_history = service.history_store.load("history.browser-e2e").history
    remaining = {node.feature_id for node in final_history.nodes}
    assert "feature.parent" not in remaining
    assert "feature.child" not in remaining
    assert "mesh" in final_history.output_feature_ids
    assert page_errors == []


def test_stale_writer_conflict_is_visible_and_does_not_overwrite(workbench):
    page, service, page_errors = workbench

    page.locator('#feature-tree button[data-feature-id="extrusion"]').click()
    page.locator("#feature-edit-parameters").fill(
        json.dumps({"solid_id": "solid.browser", "height": 9.0})
    )

    # Simulate another local client committing after this page loaded revision 1.
    service.save_history(make_history(height=4.0), expected_revision=1)
    page.get_by_role("button", name="Apply parameter edit").click()
    page.get_by_text("Revision conflict. Refresh revisions and load the latest head before retrying.").wait_for()

    latest = service.history_store.load("history.browser-e2e")
    extrusion = next(node for node in latest.history.nodes if node.feature_id == "extrusion")
    assert latest.revision == 2
    assert extrusion.parameters["height"] == 4.0
    assert page_errors == []


def test_feature_parameters_are_rendered_as_text_not_html(workbench):
    page, service, page_errors = workbench

    page.locator('#feature-tree button[data-feature-id="extrusion"]').click()
    payload = {
        "solid_id": "solid.browser",
        "height": 2.0,
        "note": '<img src=x onerror="window.__xss=true">',
    }
    page.locator("#feature-edit-parameters").fill(json.dumps(payload))
    page.get_by_role("button", name="Apply parameter edit").click()
    page.get_by_text("Saved replace as immutable revision 2.").wait_for()

    assert page.locator("#feature-inspector img").count() == 0
    assert page.locator("#feature-inspector").inner_text().find("<img") >= 0
    assert page.evaluate("window.__xss === undefined")
    assert page_errors == []
