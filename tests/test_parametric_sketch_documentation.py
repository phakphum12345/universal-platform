from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_parametric_sketch_contract_is_indexed_and_schema_exists():
    index = (ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    contract = ROOT / "docs" / "design-3d" / "PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md"
    schema = ROOT / "schemas" / "geometry" / "parametric-sketch.schema.json"
    assert contract.is_file()
    assert schema.is_file()
    assert "PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md" in index
    assert "parametric-sketch.schema.json" in index


def test_sketch_status_documents_exact_evidence_and_bounded_scope():
    contract = (ROOT / "docs" / "design-3d" / "PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "implementation" / "IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")
    traceability = (ROOT / "docs" / "traceability" / "REQUIREMENTS_TRACEABILITY_MATRIX.md").read_text(encoding="utf-8")
    for text in (contract, roadmap, status):
        assert "e2d631b49910e3d7f05fea6337742fd87385fb81" in text
        assert "618" in text
    assert "CAD-SKETCH-001" in traceability
    assert "unique" in contract.lower()
    assert "B-rep" in roadmap
