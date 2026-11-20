import json
import math

import pytest

from universal_platform.engineering.errors import EngineeringError
from universal_platform.engineering.quantity import LENGTH, Quantity


def test_quantity_v1_snapshot_round_trip_preserves_si_value_dimension_and_source_unit():
    original = Quantity.of(25, "mm")
    snapshot = original.to_dict()
    restored = Quantity.from_dict(json.loads(json.dumps(snapshot)))
    assert restored == original
    assert restored.si_value == pytest.approx(0.025)
    assert restored.dimension == LENGTH
    assert restored.source_unit == "mm"
    assert restored.in_unit("mm") == pytest.approx(25)


def test_derived_quantity_snapshot_preserves_dimension_and_si_base_representation():
    area = Quantity.of(2, "m") * Quantity.of(3, "m")
    restored = Quantity.from_dict(area.to_dict())
    assert restored.dimension == (2, 0, 0, 0, 0)
    assert restored.si_value == pytest.approx(6)


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": "2.0"},
        {"extra": "unknown"},
        {"dimension": [1, 0, 0]},
        {"dimension": [True, 0, 0, 0, 0]},
        {"source_unit": "not-a-unit"},
        {"si_value": math.inf},
        {"si_value": True},
    ],
)
def test_quantity_snapshot_rejects_invalid_contract_values(changes):
    snapshot = Quantity.of(1, "m").to_dict()
    snapshot.update(changes)
    with pytest.raises(EngineeringError):
        Quantity.from_dict(snapshot)


def test_quantity_rejects_mutable_dimensions_and_non_numeric_values():
    with pytest.raises(EngineeringError, match="immutable tuple"):
        Quantity(1.0, [1, 0, 0, 0, 0], "m")
    with pytest.raises(EngineeringError, match="numeric"):
        Quantity.of(True, "m")
    with pytest.raises(EngineeringError, match="numeric"):
        Quantity.of("1", "m")
