# Hardware Schematic Netlist Contract

**Status:** Normalized connectivity model v1.0 implemented under PR #46. PR #59 adds a deterministic symbol/layout SVG renderer; PR #60 adds a conservative static ERC ruleset v1.0; circuit simulation and richer electrical constraints remain open.

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

This is a metadata/connectivity model only. It does not import/export EDA formats, run SPICE/circuit simulation, select components, verify electrical ratings, bind firmware drivers, or operate hardware. ERC v1.0 is a separate static pin-type lint pass and does not establish electrical correctness. Structural PASS is not electrical correctness or physical validation.

## 5. Rendering implementation boundary

PR #59 introduces a separate versioned SchematicLayout with reusable symbol definitions, explicit component placements, pin anchors and net routes. The pure-Python SVG renderer is deterministic and reports nets that do not have a complete route. It does not infer placement, import EDA libraries, or claim electrical correctness.

## 6. Future work

- EDA symbol/library import and stable external object references.
- Extend ERC with voltage/current domains, datasheet-backed constraints, standards profiles and reviewable waivers.
- Component ratings, power budgets, net classes and electrical constraints.
- Driver/interface mapping with source and firmware-version provenance.
- Reference circuit cases and independent simulation adapters.


## Driver bindings

DriverBindingModel (PR #47) can map declared driver signals to component pins and validate references/directions. It does not execute the driver or communicate with a board.


## Electrical rule checking

See [Electrical Rule Checking Contract](ELECTRICAL_RULE_CHECKING_CONTRACT.md). PR #60 adds deterministic offline checks for unconnected pins, multiple push-pull outputs, multiple declared power sources, power inputs without a declared source, power/signal-driver conflicts, and open-drain/open-collector nets without a declared power source. The result includes ruleset version, canonical input SHA-256, stable findings, evidence references, severity and limitations. Warnings produce FAIL pending review. Voltage/current/thermal/timing analysis, standards, datasheet constraints, passive pull-up inference, waivers and simulation remain outside v1.0.
