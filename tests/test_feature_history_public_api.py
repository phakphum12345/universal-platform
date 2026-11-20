import json


def test_feature_history_schema_and_public_api_are_available():
    from pathlib import Path

    from universal_platform.engineering import (
        FeatureHistory as PublicHistory,
    )
    from universal_platform.engineering import (
        FeatureKind as PublicKind,
    )
    from universal_platform.engineering import (
        FeatureNode as PublicNode,
    )
    from universal_platform.engineering import (
        regenerate_feature_history as public_regenerate,
    )
    from universal_platform.engineering import (
        upgrade_feature_history as public_upgrade,
    )
    from universal_platform.engineering.feature_history import (
        FeatureHistory,
        FeatureKind,
        FeatureNode,
        regenerate_feature_history,
        upgrade_feature_history,
    )
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "geometry" /
                         "feature-history.schema.json").read_text(encoding="utf-8"))
    history = PublicHistory("history", (PublicNode.create("mesh", PublicKind.MESH),), ("mesh",))
    upgraded = public_upgrade(history)
    assert set(history.to_dict()) == set(schema["oneOf"][0]["required"])
    assert set(upgraded.to_dict()) == set(schema["oneOf"][1]["required"])
    assert schema["oneOf"][0]["additionalProperties"] is False
    assert schema["oneOf"][1]["additionalProperties"] is False
    assert PublicHistory is FeatureHistory
    assert PublicKind is FeatureKind
    assert PublicNode is FeatureNode
    assert public_regenerate is regenerate_feature_history
    assert public_upgrade is upgrade_feature_history


def test_durable_feature_history_store_is_exported_from_engineering_package():
    from universal_platform.engineering import (
        FeatureHistoryRevision,
        FeatureHistoryRevisionConflict,
        FeatureHistoryStoreIntegrityError,
        SQLiteFeatureHistoryStore,
    )
    from universal_platform.engineering.feature_history_store import (
        FeatureHistoryRevision as InternalRevision,
    )
    from universal_platform.engineering.feature_history_store import (
        FeatureHistoryRevisionConflict as InternalConflict,
    )
    from universal_platform.engineering.feature_history_store import (
        FeatureHistoryStoreIntegrityError as InternalIntegrityError,
    )
    from universal_platform.engineering.feature_history_store import (
        SQLiteFeatureHistoryStore as InternalStore,
    )

    assert FeatureHistoryRevision is InternalRevision
    assert FeatureHistoryRevisionConflict is InternalConflict
    assert FeatureHistoryStoreIntegrityError is InternalIntegrityError
    assert SQLiteFeatureHistoryStore is InternalStore
