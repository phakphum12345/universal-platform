import json
from pathlib import Path


def test_primitive_geometry_schema_is_versioned_and_strict():
    path = Path(__file__).parents[1] / "schemas" / "geometry" / "primitive-geometry.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"schema_version", "frame_graph", "solids"}
    assert len(schema["properties"]["solids"]["items"]["oneOf"]) == 3
    assert schema["$defs"]["extrudedProfile"]["properties"]["profile"]["minItems"] == 3
