import json

from universal_platform.engineering.frame_graph import FrameGraph
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.primitive_geometry import BoxSolid, PrimitiveGeometryModel
from universal_platform.engineering.geometry_batch import main


def _snapshot():
    graph = FrameGraph()
    graph.add_frame("part")
    model = PrimitiveGeometryModel(
        graph,
        (BoxSolid("solid.box", "part", Vec3(2, 3, 4), "mm"),),
    )
    return model.to_dict()


def _write(path, payload, *, indent=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=indent) + "\n", encoding="utf-8")
    return path


def test_batch_validation_reports_every_file_and_fails_if_any_file_is_invalid(tmp_path, capsys):
    valid = _write(tmp_path / "valid.geometry.json", _snapshot())
    invalid = tmp_path / "invalid.geometry.json"
    invalid.write_text("{not-json", encoding="utf-8")
    report_path = tmp_path / "reports" / "geometry.json"

    exit_code = main([
        "validate", str(valid), str(invalid),
        "--format", "json", "--report", str(report_path),
    ])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["summary"] == {"total": 2, "passed": 1, "failed": 1}
    assert [item["status"] for item in report["files"]] == ["PASS", "FAIL"]
    assert report_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_recursive_directory_scan_discovers_multiple_geometry_files(tmp_path, capsys):
    _write(tmp_path / "one.geometry.json", _snapshot())
    _write(tmp_path / "nested" / "two.geometry.json", _snapshot())
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas" / "ignored.schema.json").write_text("{}", encoding="utf-8")

    exit_code = main(["validate", str(tmp_path), "--recursive"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "TOTAL=2 PASS=2 FAIL=0" in output
    assert "one.geometry.json" in output
    assert "two.geometry.json" in output
    assert "ignored.schema.json" not in output


def test_safe_fix_canonicalizes_only_valid_geometry_and_keeps_backup(tmp_path, capsys):
    path = _write(tmp_path / "part.geometry.json", _snapshot(), indent=None)
    original = path.read_text(encoding="utf-8")

    exit_code = main(["validate", str(path), "--fix"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "canonical JSON written" in output
    assert path.with_name(path.name + ".bak").read_text(encoding="utf-8") == original
    assert json.loads(path.read_text(encoding="utf-8")) == _snapshot()


def test_fix_mode_does_not_rewrite_semantically_invalid_geometry(tmp_path, capsys):
    payload = _snapshot()
    payload["solids"][0]["dimensions"]["x"] = -1
    path = _write(tmp_path / "invalid.geometry.json", payload)
    original = path.read_text(encoding="utf-8")

    exit_code = main(["validate", str(path), "--fix"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert path.read_text(encoding="utf-8") == original
    assert not path.with_name(path.name + ".bak").exists()
    assert "FAIL:" in output


def test_fix_mode_fails_when_backup_creation_fails(tmp_path, capsys, monkeypatch):
    from pathlib import Path

    path = _write(tmp_path / "part.geometry.json", _snapshot(), indent=None)
    original = path.read_text(encoding="utf-8")
    write_bytes = Path.write_bytes

    def fail_backup_write(target, data):
        if target.name.endswith(".bak"):
            raise OSError("simulated backup write failure")
        return write_bytes(target, data)

    monkeypatch.setattr(Path, "write_bytes", fail_backup_write)

    exit_code = main(["validate", str(path), "--fix"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL:" in output
    assert "simulated backup write failure" in output
    assert path.read_text(encoding="utf-8") == original
