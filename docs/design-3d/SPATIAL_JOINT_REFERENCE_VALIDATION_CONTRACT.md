# Spatial Joint Reference Validation Contract

**Status:** IMPLEMENTED reference suite in PR #54; exact PR head `3da8c733895baab939548e0ba2e81670ca0c6359` and post-merge SHA `22bbf1714224095cfd652d6887130d26facef087` both passed CI with 452 tests.

## 1. Scope

Validate the existing spatial joint foundation for the declared lower-pair families:

| Joint kind | Independent coordinates | Expected spatial local mobility |
|---|---:|---:|
| FIXED | 0 | 0 |
| REVOLUTE | 1 rotational | 1 |
| PRISMATIC | 1 translational | 1 |
| CYLINDRICAL | 1 rotational + 1 translational | 2 |
| HELICAL | 1 rotational with pitch coupling | 1 |
| SPHERICAL | 3 rotational | 3 |
| PLANAR | 2 translational + 1 rotational | 3 |
| UNIVERSAL | 2 rotational | 2 |

The values are nominal references for a single isolated joint between two rigid links with one link grounded. They are not a proof of assembled mechanism mobility.

## 2. Preconditions and model contract

- Use stable model, link, joint, frame and coordinate IDs.
- Use mechanism schema v1.2 with explicit joint placements and complete generalized-coordinate parameterization for every non-fixed joint.
- Coordinate units are explicit (rad or m); axes are finite, normalized and expressed in the joint frame.
- HELICAL includes a finite non-zero pitch in m/rad.
- SPHERICAL uses an explicitly declared supported Euler convention.
- PLANAR declares a right-handed orthonormal in-plane basis.
- UNIVERSAL declares two non-parallel rotational axes.
- Body poses map each link frame into one shared world frame.

## 3. Acceptance criteria

1. **Family completeness:** all eight JointKind values appear exactly once in the versioned reference fixture.
2. **Generated constraints:** each family generates six deterministic residual rows in stable translation-x/y/z then rotation-x/y/z order, with units m and rad.
3. **Pose consistency:** reference body poses at the supplied coordinate values satisfy all six residual tolerances; a deliberately perturbed pose is reported FAIL without suppressing residual values.
4. **Jacobian references:** every independent coordinate has a deterministic finite-difference column. At the zero configuration, coordinate derivatives match the fixture's independently specified component/sign/pitch reference values within stated tolerances.
5. **Spatial mobility:** a two-link, one-joint reference returns the table's expected local mobility, a six-row constraint Jacobian of estimated rank 6 at the regular reference configuration, and a variable count of 6 plus the joint-coordinate count.
6. **Ground invariance:** reversing the selected ground link does not change local mobility and removes that link's six pose columns.
7. **Placement composition:** a nontrivial parent-to-joint and joint-to-child placement with translation and rotation still evaluates a satisfying reference pose.
8. **Determinism:** repeated model/fixture evaluation yields stable row IDs, column IDs, ordering and JSON-compatible snapshots.
9. **Fail-closed behavior:** missing placements, missing coordinates, invalid axes, invalid parameterization and non-finite values remain rejected.
10. **Planar distinction:** a PLANAR joint family is covered by the SPATIAL rigid-body formulation; the separate 2D MobilityFormulation.PLANAR remains rejected until an explicit plane-frame/coplanarity contract exists.

## 4. Reference fixture

tests/fixtures/spatial_joint_reference_cases.json is the versioned source for the eight family definitions, coordinate axes/units, nominal DOF and expected Jacobian entries. Tests construct models from this fixture rather than duplicating reference data in each test.

## 5. Non-goals and limitations

This contract covers one-joint local reference behavior only. It does not establish arbitrary multi-loop closure, global mobility, branch discovery, singularity-free parameterization, dynamics, inertia, friction, contact, collision, physical feasibility, physical testing, certification, machine control or manufacturing readiness. Finite-difference Jacobian rank remains tolerance- and scale-dependent. Higher-pair joints are outside the current schema.
