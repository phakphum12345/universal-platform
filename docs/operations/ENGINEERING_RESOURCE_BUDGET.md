# Engineering Resource Budget

**Status:** PROPOSED measurement framework; no numeric budget or minimum hardware is approved.

## Purpose
Make local compute, memory, storage, runtime and hosted-service cost visible before selecting tools or expanding scope.

## Budget dimensions
- CPU: core count, architecture, utilization, parallelism and runtime.
- Memory: peak resident memory, working set and out-of-memory behavior.
- Storage: source, cache, temporary data, model artifacts, logs and retention.
- GPU/accelerator: model/tool requirement, memory, driver and fallback.
- Network: default-disabled policy, endpoints, data classes and transfer volume.
- Time: startup, execution, timeout, cancellation and queue delay.
- Cost: license, hosted compute, storage, bandwidth, support and maintenance.

## Measurement protocol
Pin workload, input size, tool version, OS, hardware, environment and repetitions. Record warm/cold runs, peak resource use, elapsed time, failures and measurement method. Report distributions where variability matters. Do not extrapolate beyond tested workload sizes without labeling estimates.

## Budget policy
Prefer local/offline and existing hardware where adequate. Set numeric thresholds only after measuring the first approved vertical slice on the target systems. Hosted or paid services require a documented benefit/cost comparison and explicit approval.

## Acceptance
Every adapter declares expected and maximum resource needs; runtime enforces time/resource limits; over-budget behavior is safe and observable; cost and network use are documented.


## Current runtime reservation checkpoint

ModuleRuntime now supports optional integration with the in-memory ResourceAllocator. A request with non-empty resource_limits reserves host-defined quota before dispatch and releases its lease after the handler returns or raises. Unknown metrics, unavailable allocator and capacity exhaustion reject the invocation before dispatch. The host defines capacity and units; request values cannot create capacity.

**Important boundary:** this is admission-time quota reservation only. It does not measure or enforce actual CPU, memory, storage, network, I/O or wall-clock consumption, and does not sandbox in-process handlers. Durable/distributed leases and OS-level enforcement remain separate work. Numeric production budgets remain unapproved until measured on target hardware.
