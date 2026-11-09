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
            FeatureNode.create("mesh", FeatureKind.MESH, ("extrusion",)),
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
            FeatureNode.create("mesh.alt", FeatureKind.MESH, ("extrusion.alt",)),
            FeatureNode.create(
                "extrusion.alt", FeatureKind.EXTRUSION, ("profile.alt",),
                {"solid_id": "solid.browser.alt", "height": 1.5},
            ),
            FeatureNode.create(
                "profile.alt", FeatureKind.SKETCH_PROFILE, (),
                {"sketch": sketch.to_dict()},
            ),
        ),
        ("mesh", "mesh.alt"),
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
            page.locator("#history-id").fill("history.browser-e2e")
            page.locator("#token").fill(TOKEN)
            page.get_by_role("button", name="Connect").click()
            page.locator("#connection-state").filter(has_text="Connected").wait_for()
            page.locator('#revision option[value="1"]').wait_for(state="attached")
            page.locator("#revision").select_option("1")
            page.get_by_role("button", name="Load revision").click()
            try:
                page.locator('#feature-tree button[data-feature-id="extrusion"]').wait_for(timeout=5_000)
            except Exception as exc:
                raise AssertionError(
                    "Feature tree did not render; state="
                    + page.locator("#feature-tree-state").inner_text()
                    + "; status=" + page.locator("#status-message").inner_text()
                    + "; page_errors=" + repr(page_errors)
                ) from exc
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
    assert page.locator("#feature-suppress").is_enabled()
    assert page.locator("#feature-unsuppress").is_disabled()
    assert service.history_store.load("history.browser-e2e").revision == 1

    # Create a newer head, refresh the revision list, then load the older snapshot.
    service.save_history(make_history(height=2.5), expected_revision=1)
    page.get_by_role("button", name="Refresh revisions").click()
    page.locator("#revision option[value=\"2\"]").wait_for(state="attached")
    page.locator("#revision").select_option("1")
    page.get_by_role("button", name="Load revision").click()
    page.locator("#revision-state").filter(has_text="Loaded revision 1").wait_for()
    assert page.locator("#feature-add").is_disabled()
    assert page.locator("#feature-apply-edit").is_disabled()
    assert page.locator("#feature-remove").is_disabled()

    # Returning to the latest head restores the allowed edit controls.
    page.locator("#revision").select_option("2")
    page.get_by_role("button", name="Load revision").click()
    page.locator("#revision-state").filter(has_text="Loaded revision 2").wait_for()
    assert page.locator("#feature-add").is_enabled()
    assert page.locator("#feature-apply-edit").is_enabled()
    assert page.locator("#feature-remove").is_enabled()
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
    page.locator("#status-message").filter(has_text="dependent").wait_for()
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



def test_suppression_cascade_confirmation_and_dependency_order_restore_in_browser(workbench):
    page, service, page_errors = workbench
    page.locator('#feature-tree button[data-feature-id="extrusion"]').click()

    # Active dependents must not be suppressed implicitly.
    page.get_by_role("button", name="Suppress selected feature", exact=True).click()
    page.locator("#status-message").filter(has_text="active dependents").wait_for()
    assert service.history_store.load("history.browser-e2e").revision == 1

    # Explicit cascade requires a browser confirmation and preserves source nodes.
    page.locator("#feature-suppress-cascade").check()
    page.on("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Suppress selected feature", exact=True).click()
    page.get_by_text("Saved suppress as immutable revision 2.").wait_for()
    suppressed = service.history_store.load("history.browser-e2e", revision=2).history
    assert suppressed.suppressed_feature_ids == ("extrusion", "mesh")
    assert {node.feature_id for node in suppressed.nodes} == {
        "profile", "extrusion", "mesh", "profile.alt", "extrusion.alt", "mesh.alt"
    }

    page.locator('#feature-tree button[data-feature-id="mesh"]').click()
    assert page.locator("#feature-unsuppress").is_disabled()

    # Restore the dependency first; the suppressed output becomes restorable.
    page.locator('#feature-tree button[data-feature-id="extrusion"]').click()
    assert page.locator("#feature-unsuppress").is_enabled()
    page.get_by_role("button", name="Unsuppress selected feature", exact=True).click()
    page.get_by_text("Saved unsuppress as immutable revision 3.").wait_for()

    page.locator('#feature-tree button[data-feature-id="mesh"]').click()
    assert page.locator("#feature-unsuppress").is_enabled()
    page.get_by_role("button", name="Unsuppress selected feature", exact=True).click()
    page.get_by_text("Saved unsuppress as immutable revision 4.").wait_for()

    restored = service.history_store.load("history.browser-e2e", revision=4).history
    assert restored.suppressed_feature_ids == ()
    assert page.locator('#feature-tree button[data-feature-id="mesh"]').inner_text().find("SUPPRESSED") == -1
    assert page_errors == []


def test_undo_redo_controls_persist_across_reload_and_new_edit_clears_redo(workbench):
    page, service, page_errors = workbench
    assert page.locator("#undo").is_disabled()
    assert page.locator("#redo").is_disabled()

    page.locator('#feature-tree button[data-feature-id="extrusion"]').click()
    page.locator("#feature-edit-parameters").fill(
        json.dumps({"solid_id": "solid.browser", "height": 3.25})
    )
    page.get_by_role("button", name="Apply parameter edit").click()
    page.get_by_text("Saved replace as immutable revision 2.").wait_for()
    assert page.locator("#undo").is_enabled()
    assert page.locator("#redo").is_disabled()

    # Selecting a historical revision disables mutation; selecting the head
    # again is not enough after the historical snapshot has actually loaded.
    page.locator("#revision").select_option("1")
    assert page.locator("#undo").is_disabled()
    page.get_by_role("button", name="Load revision").click()
    page.get_by_text("Loaded immutable source revision 1.").wait_for()
    page.locator("#revision").select_option("2")
    assert page.locator("#undo").is_disabled()
    page.get_by_role("button", name="Load revision").click()
    page.get_by_text("Loaded immutable source revision 2.").wait_for()
    assert page.locator("#undo").is_enabled()

    page.get_by_role("button", name="Undo", exact=True).click()
    page.get_by_text("UNDO restored revision 1 as new immutable revision 3.").wait_for()
    assert page.locator("#undo").is_disabled()
    assert page.locator("#redo").is_enabled()
    assert service.history_store.load("history.browser-e2e", revision=3).history.nodes == (
        service.history_store.load("history.browser-e2e", revision=1).history.nodes
    )

    # Navigation state is persisted by the server, not held in page memory.
    page.reload()
    page.locator("#history-id").fill("history.browser-e2e")
    page.locator("#token").fill(TOKEN)
    page.get_by_role("button", name="Connect").click()
    page.locator("#connection-state").filter(has_text="Connected").wait_for()
    page.locator('#revision option[value="3"]').wait_for(state="attached")
    page.locator("#revision").select_option("3")
    page.get_by_role("button", name="Load revision").click()
    page.locator('#feature-tree button[data-feature-id="extrusion"]').wait_for()
    assert page.locator("#redo").is_enabled()

    page.get_by_role("button", name="Redo", exact=True).click()
    page.get_by_text("REDO restored revision 2 as new immutable revision 4.").wait_for()
    assert page.locator("#undo").is_enabled()
    assert page.locator("#redo").is_disabled()

    # Undo, then a new normal edit must clear the persistent Redo stack.
    page.get_by_role("button", name="Undo", exact=True).click()
    page.get_by_text("UNDO restored revision 3 as new immutable revision 5.").wait_for()
    page.locator('#feature-tree button[data-feature-id="extrusion"]').click()
    page.locator("#feature-edit-parameters").fill(
        json.dumps({"solid_id": "solid.browser", "height": 4.5})
    )
    page.get_by_role("button", name="Apply parameter edit").click()
    page.get_by_text("Saved replace as immutable revision 6.").wait_for()
    assert page.locator("#redo").is_disabled()
    state = service.history_store.get_navigation_state("history.browser-e2e")
    assert state.current_revision == 6
    assert state.can_redo is False
    assert page_errors == []


def test_feature_tree_reorder_is_dependency_safe_and_presentation_only(workbench):
    page, service, page_errors = workbench
    reordered_source = FeatureHistory(
        "history.browser-e2e",
        (
            FeatureNode.create("base", FeatureKind.MESH),
            FeatureNode.create("dependent", FeatureKind.MESH, ("base",)),
            FeatureNode.create("independent", FeatureKind.MESH),
        ),
        ("dependent", "independent"),
    )
    service.save_history(reordered_source, expected_revision=1)
    page.get_by_role("button", name="Refresh revisions").click()
    page.locator('#revision option[value="2"]').wait_for(state="attached")
    page.locator("#revision").select_option("2")
    page.get_by_role("button", name="Load revision").click()
    page.get_by_text("Loaded immutable source revision 2.").wait_for()

    def order():
        return [button.get_attribute("data-feature-id") for button in page.locator(
            "#feature-tree li > button[data-feature-id]"
        ).all()]

    original_execution = service.history_store.load("history.browser-e2e", revision=2).history.topological_order()
    assert order() == ["base", "dependent", "independent"]
    assert "stored topological presentation order" in page.locator("#feature-tree-state").inner_text()
    assert page.get_by_role("button", name="Move independent up").is_enabled()
    page.get_by_role("button", name="Move independent up").click()
    page.get_by_text("Saved reorder as immutable revision 3.").wait_for()
    assert order() == ["base", "independent", "dependent"]
    revision_three = service.history_store.load("history.browser-e2e", revision=3).history
    assert tuple(node.feature_id for node in revision_three.nodes) == ("base", "independent", "dependent")
    assert revision_three.topological_order() == original_execution

    # A dependency cannot be moved below its consumer.
    assert page.get_by_role("button", name="Move base down").is_enabled()
    page.get_by_role("button", name="Move base down").click()
    page.get_by_text("Saved reorder as immutable revision 4.").wait_for()
    assert order() == ["independent", "base", "dependent"]
    assert page.get_by_role("button", name="Move base down").is_disabled()
    revision_four = service.history_store.load("history.browser-e2e", revision=4).history
    assert revision_four.topological_order() == original_execution

    # Historical revisions remain read-only for reorder actions.
    page.locator("#revision").select_option("3")
    page.get_by_role("button", name="Load revision").click()
    page.get_by_text("Loaded immutable source revision 3.").wait_for()
    assert page.get_by_role("button", name="Move independent up").is_disabled()
    assert page_errors == []



def test_feature_history_branch_fork_and_merge_work_in_browser(workbench):
    page, service, page_errors = workbench
    page.locator("#branch-history-id").fill("history.browser-e2e.experiment")
    page.locator("#branch-name").fill("experiment")
    page.get_by_role("button", name="Fork selected revision").click()
    page.get_by_text("Forked experiment from history.browser-e2e revision 1.").wait_for()
    assert service.history_store.load("history.browser-e2e.experiment").revision == 1

    service.edit_history(
        "history.browser-e2e.experiment",
        expected_revision=1,
        operation="add",
        feature=FeatureNode.create("branch-feature", FeatureKind.MESH),
        make_output=True,
    )
    page.get_by_role("button", name="Refresh branches").click()
    page.get_by_label("Source branch to merge into this history").select_option(
        "history.browser-e2e.experiment"
    )
    page.get_by_role("button", name="Merge selected branch").click()
    expected_merge_message = (
        "Merged history.browser-e2e.experiment into history.browser-e2e "
        "as immutable revision 2."
    )
    page.wait_for_function(
        """expected => {
          const state = document.querySelector("#branch-state")?.textContent || "";
          const status = document.querySelector("#status-message")?.textContent || "";
          return state.includes(expected) || status.length > 0;
        }""",
        expected_merge_message,
        timeout=10_000,
    )
    actual_merge_message = page.locator("#branch-state").inner_text()
    assert expected_merge_message in actual_merge_message, (
        "Browser merge did not complete. "
        f"branch_state={actual_merge_message!r}; "
        f"status={page.locator('#status-message').inner_text()!r}; "
        f"conflicts={page.locator('#branch-conflicts').inner_text()!r}; "
        f"result={page.locator('#result').inner_text()!r}; "
        f"page_errors={page_errors!r}"
    )

    root = service.history_store.load("history.browser-e2e")
    branch = service.history_store.load("history.browser-e2e.experiment")
    assert root.revision == 2
    assert "branch-feature" in {node.feature_id for node in root.history.nodes}
    assert branch.revision == 2
    assert root.merge_provenance is not None
    assert root.merge_provenance.source_history_id == branch.history_id
    assert page_errors == []


def test_feature_history_branch_merge_conflicts_are_shown_in_workbench(workbench):
    page, service, page_errors = workbench
    page.locator("#branch-history-id").fill("history.browser-e2e.conflict")
    page.locator("#branch-name").fill("conflict")
    page.get_by_role("button", name="Fork selected revision").click()
    page.get_by_text("Forked conflict from history.browser-e2e revision 1.").wait_for()

    base = service.history_store.load("history.browser-e2e", revision=1).history
    source_nodes = tuple(
        FeatureNode.create(
            node.feature_id, node.kind, node.input_feature_ids,
            {"solid_id": "source.solid", "height": 4.0}
            if node.feature_id == "extrusion" else node.parameters,
        )
        for node in base.nodes
    )
    service.save_history(
        FeatureHistory(
            "history.browser-e2e.conflict",
            source_nodes,
            base.output_feature_ids,
            base.suppressed_feature_ids,
            base.document_version,
        ),
        expected_revision=1,
    )
    target_nodes = tuple(
        FeatureNode.create(
            node.feature_id, node.kind, node.input_feature_ids,
            {"solid_id": "target.solid", "height": 5.0}
            if node.feature_id == "extrusion" else node.parameters,
        )
        for node in base.nodes
    )
    service.save_history(
        FeatureHistory(
            "history.browser-e2e",
            target_nodes,
            base.output_feature_ids,
            base.suppressed_feature_ids,
            base.document_version,
        ),
        expected_revision=1,
    )
    page.get_by_role("button", name="Refresh revisions").click()
    page.locator('#revision option[value="2"]').wait_for(state="attached")
    page.locator("#revision").select_option("2")
    page.get_by_role("button", name="Load revision").click()
    page.locator("#revision-state").filter(has_text="Loaded revision 2").wait_for()
    page.get_by_role("button", name="Refresh branches").click()
    page.get_by_label("Source branch to merge into this history").select_option(
        "history.browser-e2e.conflict"
    )
    page.get_by_role("button", name="Merge selected branch").click()
    page.get_by_text("Merge blocked by 1 conflict(s).").wait_for()
    assert "node_content" in page.locator("#branch-conflicts").inner_text()
    assert service.history_store.load("history.browser-e2e").revision == 2
    assert service.history_store.load("history.browser-e2e.conflict").revision == 2
    assert page_errors == []
