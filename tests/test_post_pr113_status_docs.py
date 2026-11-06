from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_post_pr113_audit_is_indexed_and_pins_exact_integration_baseline():
    audit = ROOT / "docs" / "audit" / "REPOSITORY_AUDIT_2026-11-07_POST_PR113.md"
    index = (ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert audit.is_file()
    assert "REPOSITORY_AUDIT_2026-11-07_POST_PR113.md" in index
    assert "50b5ff50e52e9f9f83d1b33030875b53ee7702e2" in readme
    assert "732 passed" in readme


def test_current_traceability_keeps_bounded_capabilities_partial_or_open():
    matrix = (ROOT / "docs" / "traceability" / "REQUIREMENTS_TRACEABILITY_MATRIX.md").read_text(encoding="utf-8")
    for requirement in (
        "CAD-BREP-001", "CAD-GEN-001", "HW-EDA-001", "HW-BOM-001",
        "PHY-REG-001", "PHY-VALID-001", "RT-008",
    ):
        assert requirement in matrix
    assert "not B-rep modeling" in matrix
    assert "no sandbox" in matrix


def test_roadmap_and_implementation_status_record_current_runtime_limits():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "implementation" / "IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")
    for text in (roadmap, status):
        assert "50b5ff50e52e9f9f83d1b33030875b53ee7702e2" in text
        assert "732" in text
        assert "sandbox" in text.lower()
        assert "distributed" in text.lower()
