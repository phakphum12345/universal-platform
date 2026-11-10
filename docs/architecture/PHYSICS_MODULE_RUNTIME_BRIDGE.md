# Physics Module Runtime Bridge

**Status:** Bounded integration of the existing built-in analytical solvers through the host-controlled ModuleRuntime. This is not a general plugin loader or a sandbox.

## Scope

The bridge exposes exactly these existing solver IDs:

- `builtin.axial-stress`
- `builtin.ohms-law`
- `builtin.linear-thermal-expansion`

It does not duplicate their equations. It adapts validated module requests into the existing `PhysicsProblem` and `PhysicsInput` records, invokes `PhysicsSolverRegistry.solve`, and serializes quantities plus the original evidence record.

## Policy

- Module identity: `org.universal.physics`
- Operation: `physics.solve`
- Required host grant: `engineering.physics.solve`
- Manifest and operation schema versions: `1.0`
- License allow-list is configured by host code and defaults to `Apache-2.0`.
- The bridge's dependency policy accepts only solvers with no external dependencies.
- Request-supplied permissions never grant authority; the host must call `bridge.grant()`.
- `bridge.revoke()` removes the host grant for subsequent invocations.

## Input contract

The operation requires `solver_id`, `problem_id`, `validity_range`, and a `values` object. Quantity-valued inputs require exactly `value` and `unit`, and the bridge accepts only canonical units for each solver. Scalar thermal inputs must be finite numbers. Unknown/missing fields, non-canonical units, non-finite values and unsupported solver IDs fail closed.

Optional `assumptions` and `boundary_conditions` are retained in the generated physics evidence metadata.

## Output and evidence

The response includes solver identity/version, domain/method, each output quantity's v1.0 SI snapshot, and the complete evidence record including status, method, assumptions, boundary conditions and limitations. An evidence PASS means the selected bounded solver completed its declared calculation; it is not a safety certification or proof of physical model validity.

## Limitations

- Only the three current built-in analytical solvers are exposed.
- No arbitrary module loading, external solver installation, network access, FEA, CFD or physical-device control is provided.
- Handler execution remains trusted in-process code; ModuleRuntime is an application-level permission boundary, not OS isolation.
- Resource limits in ModuleRequest are not enforced by this bridge; in-process handlers must not treat caller-supplied limits as a sandbox.
