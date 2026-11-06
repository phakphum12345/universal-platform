# Hardware Schematic Netlist Contract

**Status:** Normalized connectivity model v1.0 implemented under PR #46; rendering and electrical verification remain open.

## 1. Purpose

Represent an offline hardware schematic as a stable, versioned connectivity graph that can be validated, serialized and later adapted to EDA tools. The model separates component identity, symbol identity, pin identity and net connectivity.

## 2. Core records

- `Component`: stable component ID, reference designator, symbol ID, pin declarations, optional value and manufacturer part.
- `Pin`: stable pin ID, package/symbol pin number, pin name and electrical type.
- `Net`: stable net ID, optional name and terminal references.
- `PinRef`: component ID plus pin ID.
- `SchematicModel`: versioned component and net collections.

## 3. Validation rules

- Stable IDs and reference designators must be valid and unique.
- Component pin IDs and pin numbers must be unique within each component.
- Net IDs and named net labels must be unique.
- Every net terminal must resolve to a declared component pin.
- A pin may belong to at most one net.
- A NO_CONNECT pin cannot be assigned to a net.
- A net must contain at least two distinct terminals.
- Serialization sorts components, pins, nets and terminals deterministically.

## 4. Safety and scope

This is a metadata/connectivity model only. It does not render a schematic, import/export EDA formats, perform electrical rule checking, run SPICE/circuit simulation, select components, verify electrical ratings, bind firmware drivers, or operate hardware. Structural PASS is not electrical correctness or physical validation.

## 5. Future work

- EDA symbol/library import and stable external object references.
- Schematic diagram rendering and layout.
- Electrical rule checking with versioned standards and reviewable waivers.
- Component ratings, power budgets, net classes and electrical constraints.
- Driver/interface mapping with source and firmware-version provenance.
- Reference circuit cases and independent simulation adapters.


## Driver bindings

DriverBindingModel (PR #47) can map declared driver signals to component pins and validate references/directions. It does not execute the driver or communicate with a board.
