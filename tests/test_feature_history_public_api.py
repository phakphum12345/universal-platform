import json


def test_feature_history_schema_and_public_api_are_available():
    from pathlib import Path
    from universal_platform.engineering import (
        FeatureHistory as PublicHistory,
        FeatureKind as PublicKind,
        FeatureNode as PublicNode,
        regenerate_feature_history as public_regenerate,
    )
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "geometry" /
                         "feature-history.schema.json").read_text(encoding="utf-8"))
    history = PublicHistory("history", (PublicNode.create("mesh", PublicKind.MESH),), ("mesh",))
    assert set(history.to_dict()) == set(schema["required"])
    assert schema["additionalProperties"] is False
    assert PublicHistory is FeatureHistory
    assert PublicKind is FeatureKind
    assert PublicNode is FeatureNode
    assert public_regenerate is regenerate_feature_history
