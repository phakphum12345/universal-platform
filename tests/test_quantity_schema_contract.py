import json
from pathlib import Path


def test_quantity_schema_is_valid_json_and_matches_runtime_version():
    path = Path(__file__).parents[1] / "schemas" / "engineering" / "quantity.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"schema_version", "si_value", "dimension", "source_unit"}
    assert schema["properties"]["dimension"]["minItems"] == 5
    assert schema["properties"]["dimension"]["maxItems"] == 5
