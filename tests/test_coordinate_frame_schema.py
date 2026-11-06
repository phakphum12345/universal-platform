import json
from pathlib import Path


def test_coordinate_frame_graph_schema_is_valid_json_and_versioned():
    schema_path = (
        Path(__file__).parents[1]
        / "schemas"
        / "geometry"
        / "coordinate-frame-graph.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"schema_version", "frames", "transforms"}
    transform = schema["$defs"]["rigidTransform"]
    assert transform["additionalProperties"] is False
    assert set(transform["required"]) == {
        "schema_version", "from_frame", "to_frame", "rotation", "translation"
    }
    assert schema["$defs"]["rigidTransform"]["properties"]["translation"]["properties"]["unit"]["enum"] == [
        "m", "mm", "cm", "km", "in"
    ]
