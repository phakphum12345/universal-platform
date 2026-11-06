import json
from pathlib import Path

def test_hardware_schematic_schema_is_versioned_and_strict():
    path=Path(__file__).parents[1]/"schemas"/"hardware"/"schematic.schema.json"
    schema=json.loads(path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"]=="1.0"
    assert schema["additionalProperties"] is False
    assert set(schema["required"])=={"schema_version","components","nets"}
    assert schema["$defs"]["net"]["properties"]["terminals"]["minItems"]==2
    assert "NO_CONNECT" in schema["$defs"]["pin"]["properties"]["electrical_type"]["enum"]
