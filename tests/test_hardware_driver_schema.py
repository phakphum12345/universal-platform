import json
from pathlib import Path


def test_driver_binding_schema_is_versioned_and_strict():
    path = Path(__file__).parents[1] / "schemas" / "hardware" / "driver-binding.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"schema_version", "interfaces", "bindings"}
    assert schema["$defs"]["interface"]["properties"]["protocol"]["enum"] == [
        "GPIO", "I2C", "SPI", "UART", "CAN", "USB", "PCIE", "PWM", "ADC", "DAC", "GENERIC"
    ]
