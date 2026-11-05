# Engineering Reference Cases

**Status:** PROPOSED validation catalogue; expected values require independent review before use as acceptance baselines.

## Purpose
Define small, deterministic reference cases for validating quantities, mechanics, electrical, thermal, solver, provenance and constraint behavior. These cases validate only the stated mathematical contract; they do not certify a design or physical system.

## Case record
Each case must pin: case ID/version, source revision, model and equation, inputs with units, assumptions, expected result and tolerance, independent derivation/source, applicable validity range, test implementation, tool version and evidence status.

## Initial reference cases
| ID | Domain | Inputs / method | Expected result | Required checks |
|---|---|---|---|---|
| REF-LIN-001 | Linear algebra | Solve [[2,0],[0,4]] x = [4,8] | x = [2,2], residual near zero | Pivoting, dimensions, residual |
| REF-MECH-001 | Axial stress | F=1000 N, A=0.01 m²; sigma=F/A | 100,000 Pa (0.1 MPa) | Force/area dimensions |
| REF-MECH-002 | Axial strain | deltaL=1 mm, L=1 m; epsilon=deltaL/L | 0.001 (dimensionless) | Length units |
| REF-ELEC-001 | Ohm's law | V=12 V, R=6 ohm; I=V/R | 2 A | Positive resistance, dimensions |
| REF-ELEC-002 | DC power | V=12 V, I=2 A; P=VI | 24 W | Power dimension |
| REF-THERM-001 | Linear expansion | L=2 m, alpha=12e-6 K^-1, deltaT=50 K | deltaL=0.0012 m | Coefficient provenance and sign |
| REF-GEO-001 | Analytic geometry | Box 2 x 3 x 4 length units | Volume=24 cubic units | Positive finite dimensions |
| REF-GEO-002 | Analytic geometry | Cylinder r=1, h=2 | Volume=2 pi cubic units | Positive finite dimensions |
| REF-UNIT-001 | Conversion | 25 mm to m | 0.025 m | Exact conversion factor |
| REF-UNIT-002 | Invalid operation | Add 1 m and 1 s | Reject with dimension error | Fail closed |

These are mathematical smoke/reference cases, not standards-based engineering design cases. Add authoritative domain references before using any case for safety or compliance decisions.

## Acceptance
- Expected values have an independently reviewed derivation.
- Tolerances are justified and versioned.
- Invalid, singular, non-finite and dimensionally inconsistent inputs are covered.
- Results are tied to exact code, model and fixture revisions.
- No case implies CAD-kernel, FEA/CFD or physical validation.
