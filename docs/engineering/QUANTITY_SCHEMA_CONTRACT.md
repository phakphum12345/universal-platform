# Quantity Schema Contract

**Status:** Implemented v1.0 JSON exchange subset; unit catalogue remains intentionally limited.

## 1. Representation

Quantity stores a finite numeric value in SI base units, a five-integer dimensional signature (length, mass, time, electric current and temperature), and the source unit used to construct or report the value.

The source unit is retained for traceability. Arithmetic may create a composite dimension whose source unit is recorded as `1`; the dimension vector remains authoritative for dimensional checks.

## 2. Schema v1.0

Required fields:
- `schema_version`: exactly `1.0`.
- `si_value`: finite number in SI base units.
- `dimension`: exactly five integer exponents.
- `source_unit`: one of the unit identifiers in `schemas/engineering/quantity.schema.json`.

Unknown fields and unsupported schema versions are rejected. `to_dict()` emits deterministic JSON-compatible data; `from_dict()` validates and restores the immutable dimensional signature.

## 3. Unit policy

The current unit catalogue is dependency-free and finite. It includes common length, mass, time, current, temperature, force, pressure, velocity, area, volume, density, voltage, power, energy, resistance and frequency units. It is not a general UCUM implementation and does not support arbitrary user-defined units.

## 4. Limitations

- No arbitrary unit registry or user-defined conversion plugin.
- No uncertainty distribution/covariance attached to Quantity.
- No frame identity attached to scalar Quantity; framed vector/tensor values need a separate contract.
- The source-unit string is provenance metadata; the SI value and dimension vector govern arithmetic.
