# Universal Calculation and Engineering Engine

**Status:** PROPOSED modular capability specification.

## Calculation record
Every calculation records problem statement, domain, inputs, units, assumptions, equations/method, constants and source, precision, uncertainty, boundary conditions, solver/tool version, intermediate values, result, validation method, and limitations.

## Core mathematical capabilities
Unit conversion and dimensional analysis; arithmetic and numerical methods; algebra; calculus; linear algebra; statistics and probability; optimization; numerical integration; differential equations; geometry; signal analysis; error propagation; sensitivity and uncertainty analysis.

## Domain modules
- Computing: capacity, complexity estimates, memory/storage, performance and reliability models.
- Electrical/electronics: Ohm/Kirchhoff laws, power, impedance, filters, analog/digital circuits, timing, signal integrity, thermal estimates.
- Semiconductor: logic, timing, power, interfaces, device limits and datasheet-derived constraints.
- Communications: bandwidth, link budgets, modulation, latency, throughput, antenna and propagation estimates.
- Mechanical: force, torque, motion, stress/strain, heat transfer, fluid and vibration models.
- Physics: mechanics, electromagnetism, optics, thermodynamics and other validated subdomains.
- Chemistry/materials: stoichiometry, concentration, reaction and material-property calculations with safety constraints.
- Biology/medical: validated quantitative models only; not a substitute for professional diagnosis or treatment.
- Manufacturing: tolerances, process capability, yield, cost and quality estimates.
- Environment/earth/space: energy, climate, geospatial and orbital calculations within validated assumptions.
- Economics/social/applied sciences: transparent statistical and decision models with declared limitations.

## Units and uncertainty
Use a canonical unit system internally, preserve source units, show conversions, reject dimensionally invalid expressions, and report significant figures and uncertainty appropriate to input quality.

## Distinguish result types
- CALCULATION: result derived from equations/data.
- ESTIMATE: result dependent on approximations.
- SIMULATION: model execution under stated assumptions.
- MEASUREMENT: physical observation from an instrument/source.
Never label one type as another.

## Verification
Use independent calculation, known reference cases, dimensional checks, property-based tests, numerical stability checks, and source validation. Unsupported constants or assumptions must be disclosed.

## Acceptance criteria
- Inputs and units are explicit.
- Results are reproducible.
- Assumptions and uncertainty are visible.
- Domain module is versioned and tested.
- Safety-critical calculations require independent review and appropriate standards.
