import json
import re
from pathlib import Path

from universal_platform.engineering.cad_generator_http_api import _REQUEST_ID


def test_shared_request_id_schema_matches_python_runtime_validator():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "schemas"
        / "shared"
        / "request-id.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["type"] == "string"
    assert schema["minLength"] == 8
    assert schema["maxLength"] == 128
    assert schema["pattern"] == _REQUEST_ID.pattern

    schema_pattern = re.compile(schema["pattern"])
    accepted = (
        "calendar-request-123",
        "request_id.v1",
        "A" * 128,
    )
    rejected = (
        "short",
        "contains space",
        "slash/value",
        "é" * 8,
        "A" * 129,
    )

    for value in accepted:
        assert schema["minLength"] <= len(value) <= schema["maxLength"]
        assert schema_pattern.fullmatch(value)
        assert _REQUEST_ID.fullmatch(value)

    for value in rejected:
        assert not (
            schema["minLength"] <= len(value) <= schema["maxLength"]
            and schema_pattern.fullmatch(value)
        )
        assert _REQUEST_ID.fullmatch(value) is None
