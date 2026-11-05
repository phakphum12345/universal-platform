"""Fail-closed governance gate. This module never authorizes physical execution."""
from dataclasses import dataclass
from enum import IntEnum

class RiskTier(IntEnum):
    INFORMATIONAL = 0
    LOW_CONSEQUENCE = 1
    ENGINEERING_DECISION_SUPPORT = 2
    HIGH_CONSEQUENCE = 3
    PHYSICAL_EXECUTION = 4

@dataclass(frozen=True, slots=True)
class SafetyDecision:
    allowed: bool
    tier: RiskTier
    status: str
    reasons: tuple[str, ...]

class SafetyGate:
    """Allow offline analysis by default; deny all physical execution."""
    PHYSICAL_ACTIONS = frozenset({
        "gpio_write", "bus_transaction", "register_write", "sensor_acquisition",
        "power_switch", "firmware_flash", "actuator_move", "motor_control",
        "machine_operation", "fabrication_release", "procurement", "deployment",
    })

    def evaluate(self, action: str, tier: RiskTier, *, approved: bool = False,
                 qualified_review: bool = False) -> SafetyDecision:
        normalized = action.strip().lower()
        if normalized in self.PHYSICAL_ACTIONS or tier is RiskTier.PHYSICAL_EXECUTION:
            return SafetyDecision(False, tier, "REJECTED",
                                  ("Physical execution is outside the initial platform boundary",))
        if tier >= RiskTier.ENGINEERING_DECISION_SUPPORT and not qualified_review:
            return SafetyDecision(False, tier, "REJECTED",
                                  ("Qualified engineering review is required",))
        if tier is RiskTier.HIGH_CONSEQUENCE and not approved:
            return SafetyDecision(False, tier, "REJECTED",
                                  ("Explicit human approval is required",))
        return SafetyDecision(True, tier, "ACCEPTED", ())
