from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_point_contact_contract_is_indexed():
    index = (ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    contract = ROOT / "docs" / "design-3d" / "CAD_BOOLEAN_POINT_CONTACT_CONTRACT.md"
    assert contract.is_file()
    assert "CAD_BOOLEAN_POINT_CONTACT_CONTRACT.md" in index


def test_point_contact_status_records_exact_merge_and_retained_failure_gates():
    contract = (ROOT / "docs" / "design-3d" / "CAD_BOOLEAN_POINT_CONTACT_CONTRACT.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "implementation" / "IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")
    traceability = (ROOT / "docs" / "traceability" / "REQUIREMENTS_TRACEABILITY_MATRIX.md").read_text(encoding="utf-8")
    for text in (contract, roadmap, status):
        assert "2eea0bdc9226c8ec3b3d5458e3902ee01b8314f0" in text
        assert "639" in text
    assert "CAD-PLANAR-TOPOLOGY-TOUCH-001" in traceability
    assert "fail closed" in contract.lower()
    assert "clockwise" in contract.lower()
