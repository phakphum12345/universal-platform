# Engineering Reference Validation Pack

**Status:** Implementation candidate in PR #38.

## Purpose

Provide a versioned, machine-readable set of independently derived reference cases for implemented engineering primitives. This is an executable regression baseline, not a collection of informal examples.

## Registry

- File: tests/reference_cases/engineering_reference_cases.json
- Registry schema version: 1.0
- Every case has a stable unique ID, operation identifier, explicit inputs, expected output, numerical tolerance and reference/formula note.
- Tests fail if IDs are duplicated, formulas are missing, tolerances are invalid, or an operation has no executable dispatcher.

## Coverage

- SI unit conversion and dimensional arithmetic.
- Axial stress, axial strain and factor of safety.
- Ohm's law and DC electrical power.
- Linear thermal expansion.
- Analytic box/cylinder volume and rigid point transformation.
- Pivoted linear-system solve and transparent static linear algebra.
- Planar two-link inverse kinematics with forward reconstruction.
- Four-bar loop closure with mixed input length units and explicit branch.
- Material record dimensional validation.
- Assembly joint metadata and nominal DOF.
- Scalar maximum constraint evaluation.
- Fail-closed physical-execution safety decision.
- UNKNOWN evidence cannot be promoted to PASS.

## Numerical policy

Each case carries its own absolute/relative tolerance. Expected values are independently calculated from the stated closed-form relation or reference geometry; they are not copied from the implementation under test. The pack preserves input units and converts only through the public Quantity API.

## Interpretation and limitations

- Passing a reference case validates the specific mathematical/API behavior represented by that case only.
- The material example uses illustrative inputs; it is not a certified material database or design allowable.
- Static linear-system solving is algebraic verification, not finite-element analysis.
- Analytic mechanism examples do not establish manufacturing, dynamic or physical feasibility.
- This pack does not validate CAD B-rep, mesh generation, schematic netlists, hardware drivers, toolpath generation or production release; those remain explicit capability gaps for later roadmap work.
