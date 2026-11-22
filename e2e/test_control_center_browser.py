"""Real-browser acceptance tests for the local-first Control Center shell.

Run with:
    python -m pip install -e ".[dev,browser]"
    python -m playwright install --with-deps chromium
    python -m pytest -q e2e/test_control_center_browser.py
"""
from __future__ import annotations

from threading import Thread

import pytest
from playwright.sync_api import sync_playwright

from universal_platform.engineering import (
    CADGeneratorService,
    SQLiteCADAPIAuditLog,
    SQLiteFeatureArtifactCache,
    SQLiteFeatureHistoryStore,
    create_cad_generator_http_server,
)

TOKEN = "control-center-browser-token-" + ("x" * 40)


@pytest.fixture
def control_center(tmp_path):
    service = CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path / "source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3"),
    )
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
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            page.goto(base + "/control-center", wait_until="domcontentloaded")
            yield page, context, base, audit, page_errors
        finally:
            context.close()
            browser.close()
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


def test_control_center_renders_accessible_shell_and_preserves_cad_workbench(control_center):
    page, _context, base, _audit, page_errors = control_center

    assert page.title() == "Universal Platform · Control Center"
    assert page.get_by_role("heading", name="Control Center").is_visible()
    assert page.locator("#service-state").inner_text().startswith("UNKNOWN")
    assert page.locator("#primary-navigation").get_by_role(
        "link", name="CAD Generator"
    ).get_attribute("href") == "/"
    assert page.locator("#primary-navigation button:disabled").count() >= 1
    assert page.locator("iframe").count() == 0
    assert page_errors == []

    with page.expect_popup() as popup_info:
        page.locator("#primary-navigation").get_by_role(
            "link", name="CAD Generator"
        ).click()
    popup = popup_info.value
    assert popup.url == base + "/"
    assert "CAD Generator" in popup.title()
    popup.close()


def test_mobile_navigation_and_keyboard_skip_link(control_center):
    page, _context, _base, _audit, page_errors = control_center
    page.set_viewport_size({"width": 390, "height": 844})

    toggle = page.locator("#navigation-toggle")
    assert toggle.is_visible()
    assert toggle.get_attribute("aria-expanded") == "false"
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    assert page.locator("#app-shell").evaluate(
        "element => element.classList.contains('nav-open')"
    )
    page.locator("#primary-navigation").get_by_role(
        "link", name="CAD Generator"
    ).focus()
    page.locator("#primary-navigation").get_by_role(
        "link", name="CAD Generator"
    ).click()
    assert toggle.get_attribute("aria-expanded") == "false"

    page.goto(_base_url(page) + "/control-center", wait_until="domcontentloaded")
    page.keyboard.press("Tab")
    skip_link = page.locator(".skip-link")
    assert skip_link.evaluate(
        "element => getComputedStyle(element).transform === 'matrix(1, 0, 0, 1, 0, 0)'"
    )
    assert skip_link.get_attribute("href") == "#main-content"
    assert page.locator("#main-content").get_attribute("tabindex") == "-1"
    assert page_errors == []


def _base_url(page):
    return page.url.split("/control-center", 1)[0]


def test_theme_switch_and_authenticated_health_states_do_not_persist_token(control_center):
    page, context, _base, audit, page_errors = control_center

    theme = page.locator("#theme-toggle")
    theme.click()
    assert page.locator("html").get_attribute("data-theme") == "light"
    assert theme.get_attribute("aria-pressed") == "true"
    theme.click()
    assert page.locator("html").get_attribute("data-theme") is None
    assert theme.get_attribute("aria-pressed") == "false"

    page.locator("#check-service").click()
    assert "Token required" in page.locator("#service-state").inner_text()
    assert page.locator("#service-token").evaluate("element => document.activeElement === element")

    page.locator("#service-token").fill("incorrect-token")
    page.locator("#check-service").click()
    page.get_by_text("FAIL · HTTP 401").wait_for()

    page.locator("#service-token").fill(TOKEN)
    page.locator("#check-service").click()
    page.get_by_text("PASS · CAD API READY").wait_for()
    assert "not establish platform-wide health" in page.locator("#service-detail").inner_text()

    persistence = page.evaluate("""() => ({
      local: Object.keys(localStorage),
      session: Object.keys(sessionStorage),
      cookie: document.cookie,
      url: location.href
    })""")
    assert persistence["local"] == []
    assert persistence["session"] == []
    assert persistence["cookie"] == ""
    assert TOKEN not in persistence["url"]
    assert context.cookies() == []
    assert audit.verify()
    assert page_errors == []


def test_health_connection_failure_is_reported_as_fail_not_ready(control_center):
    page, _context, _base, _audit, page_errors = control_center
    page.locator("#service-token").fill(TOKEN)
    page.route("**/health", lambda route: route.abort("failed"))
    page.locator("#check-service").click()
    page.get_by_text("FAIL · Connection error").wait_for()
    assert page.locator("#service-state").inner_text().startswith("FAIL")
    assert page_errors == []
