# Engineering Safety and Approval Policy

**Status:** PROPOSED governance specification

## 1. Purpose

Protect people, property, infrastructure, data and the environment across engineering analysis, 3D design, simulation and manufacturing preparation.

## 2. Risk tiers

- **Tier 0 — Informational:** learning, research and non-actionable explanations.
- **Tier 1 — Low consequence:** draft geometry, non-critical calculations and sandboxed simulation.
- **Tier 2 — Engineering decision support:** load-bearing designs, electrical/power design, thermal systems, fluid pressure systems and manufacturing instructions.
- **Tier 3 — High consequence:** life-safety structures, vehicles, aircraft, medical devices, high energy systems, pressure vessels, hazardous processes and safety-critical machinery.
- **Tier 4 — Physical execution:** operating machinery, energizing circuits, actuating devices, fabrication release, procurement or deployment.

Tier assignment depends on intended use and consequence, not merely the file type or user interface.

## 3. Required controls

- State intended use and foreseeable misuse.
- Identify hazards, failure modes and affected parties.
- Use authoritative standards and jurisdiction-specific requirements.
- Preserve assumptions, margins, uncertainty and limitations.
- Require independent qualified review for Tier 2/3 as appropriate.
- Require explicit scoped human authorization for Tier 4.
- Maintain change history, approval identity and evidence.
- Stop or return UNKNOWN when required inputs or expertise are unavailable.

## 4. Prohibited implicit authority

AI agents and modules cannot self-approve designs, certify compliance, release manufacturing, purchase materials, deploy changes, energize hardware or operate machinery. A completed calculation or simulation is not permission to act.

## 5. Initial hardware boundary

Initial project capability is offline analysis and simulation only. No physical GPIO writes, bus/register transactions, sensor acquisition, power switching, firmware flashing, actuator or motor operation, remote device control or machine operation.

## 6. Acceptance criteria

- [ ] Risk tier and intended use are recorded.
- [ ] Required standards and reviewers are identified.
- [ ] High-impact outputs cannot self-approve.
- [ ] Physical execution requires a separate permission and human confirmation.
- [ ] Audit evidence captures approvals and scope.
