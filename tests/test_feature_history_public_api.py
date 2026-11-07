import json


def test_feature_history_schema_and_public_api_are_available():
    from pathlib import Path
    from universal_platform.engineering.feature_history import (
        FeatureHistory, FeatureKind, FeatureNode, regenerate_feature_history,
    )
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


def test_durable_feature_history_store_is_exported_from_engineering_package():
    from universal_platform.engineering import (
        FeatureHistoryRevision,
        FeatureHistoryRevisionConflict,
        FeatureHistoryStoreIntegrityError,
        SQLiteFeatureHistoryStore,
    )
    from universal_platform.engineering.feature_history_store import (
        FeatureHistoryRevision as InternalRevision,
        FeatureHistoryRevisionConflict as InternalConflict,
        FeatureHistoryStoreIntegrityError as InternalIntegrityError,
        SQLiteFeatureHistoryStore as InternalStore,
    )

    assert FeatureHistoryRevision is InternalRevision
    assert FeatureHistoryRevisionConflict is InternalConflict
    assert FeatureHistoryStoreIntegrityError is InternalIntegrityError
    assert SQLiteFeatureHistoryStore is InternalStore
