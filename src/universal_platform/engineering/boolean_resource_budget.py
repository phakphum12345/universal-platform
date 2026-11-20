"""Invocation-wide resource accounting for exact faceted Boolean operations."""
from __future__ import annotations

from collections.abc import Mapping

from .errors import InvalidModelError

_DEFAULT_LIMITS = {
    "source_triangles": 2048,
    "unique_planes": 2048,
    "fragments": 65536,
    "aggregate_rational_bits": 64_000_000,
    "edges": 131072,
    "topology_checks": 10_000_000,
    "coverage_checks": 10_000_000,
    "coplanar_checks": 1_000_000,
    "coplanar_coverage_checks": 1_000_000,
    "classification_checks": 250_000,
    "ray_triangle_checks": 50_000_000,
    "faces": 100_000,
    "vertices": 100_000,
    "inter_shell_pair_checks": 5_000_000,
    "containment_ray_checks": 5_000_000,
}


class BooleanResourceLedger:
    """Cumulative fail-closed budget shared by every stage of one invocation.

    Limits are invocation-wide ceilings. Existing stage-local ceilings remain
    in place as additional safeguards; charging the same geometry in a later
    stage is intentional because it represents additional work/materialization.
    """

    def __init__(self, limits: Mapping[str, int] | None = None) -> None:
        if limits is not None and not isinstance(limits, Mapping):
            raise InvalidModelError("Boolean resource limits must be a mapping")
        self._limits = dict(_DEFAULT_LIMITS)
        for name, value in (limits or {}).items():
            if name not in self._limits:
                raise InvalidModelError(f"unknown Boolean resource dimension: {name}")
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise InvalidModelError(f"Boolean resource limit {name} must be a positive integer")
            if value > _DEFAULT_LIMITS[name]:
                raise InvalidModelError(f"Boolean resource limit {name} exceeds its supported hard ceiling")
            self._limits[name] = value
        self._used = {name: 0 for name in self._limits}

    def charge(self, name: str, amount: int) -> None:
        if name not in self._limits:
            raise InvalidModelError(f"unknown Boolean resource dimension: {name}")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise InvalidModelError("Boolean resource charge must be a non-negative integer")
        total = self._used[name] + amount
        if total > self._limits[name]:
            raise InvalidModelError(
                f"Boolean invocation resource budget exceeded for {name}: "
                f"{total} > {self._limits[name]}"
            )
        self._used[name] = total

    def remaining(self, name: str) -> int:
        if name not in self._limits:
            raise InvalidModelError(f"unknown Boolean resource dimension: {name}")
        return self._limits[name] - self._used[name]

    @property
    def usage(self) -> tuple[tuple[str, int], ...]:
        """Deterministic immutable snapshot of all charged dimensions."""
        return tuple(sorted(self._used.items()))

    @property
    def limits(self) -> tuple[tuple[str, int], ...]:
        return tuple(sorted(self._limits.items()))
