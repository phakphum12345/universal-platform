import pytest
from universal_platform.engineering.quantity import Quantity
from universal_platform.engineering.errors import DimensionMismatchError, EngineeringError, InvalidModelError
from universal_platform.engineering.mechanics import axial_stress, axial_strain, factor_of_safety
from universal_platform.engineering.electrical import ohms_law, electrical_power
from universal_platform.engineering.thermal import linear_thermal_expansion
from universal_platform.engineering.materials import Material


def test_axial_stress_strain_and_factor_of_safety():
    stress = axial_stress(Quantity.of(1000, "N"), Quantity.of(100, "mm") * Quantity.of(100, "mm"))
    assert stress.in_unit("MPa") == pytest.approx(0.1)
    strain = axial_strain(Quantity.of(1, "mm"), Quantity.of(1, "m"))
    assert strain.si_value == pytest.approx(0.001)
    assert factor_of_safety(Quantity.of(250, "MPa"), Quantity.of(100, "MPa")) == pytest.approx(2.5)


def test_mechanics_rejects_dimension_mismatch_and_zero_area():
    with pytest.raises(DimensionMismatchError):
        axial_stress(Quantity.of(2, "V"), Quantity.of(1, "m2"))
    with pytest.raises(EngineeringError):
        axial_stress(Quantity.of(1, "N"), Quantity.of(0, "m2"))


def test_ohms_law_and_power():
    current = ohms_law(Quantity.of(12, "V"), Quantity.of(6, "ohm"))
    assert current.in_unit("A") == pytest.approx(2)
    power = electrical_power(Quantity.of(12, "V"), current)
    assert power.in_unit("W") == pytest.approx(24)


def test_thermal_expansion():
    delta = linear_thermal_expansion(Quantity.of(2, "m"), 12e-6, 50)
    assert delta.in_unit("mm") == pytest.approx(1.2)


def test_material_requires_dimensionally_valid_properties():
    steel = Material("steel-demo", "Demo steel", Quantity.of(7850, "kg/m3"),
                     Quantity.of(200, "GPa"), 0.3, Quantity.of(250, "MPa"))
    assert steel.name == "Demo steel"
    with pytest.raises(InvalidModelError):
        Material("bad", "Bad", Quantity.of(1, "kg"), Quantity.of(1, "Pa"), 0.3)
