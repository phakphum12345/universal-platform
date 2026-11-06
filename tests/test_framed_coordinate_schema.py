import json
from pathlib import Path


def test_framed_coordinate_schema_is_versioned_and_strict():
    path = Path(__file__).parents[1] / "schemas" / "geometry" / "framed-coordinate.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["kind"]["enum"] == ["POINT", "VECTOR"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"schema_version", "kind", "frame_id", "coordinates"}
