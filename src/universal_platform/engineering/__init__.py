"""Safe, evidence-oriented engineering primitives.

This package performs offline calculations and model validation only. It does
not communicate with or control physical devices.
"""
from .quantity import Quantity, DIMENSIONLESS, LENGTH, MASS, TIME, CURRENT, TEMPERATURE
from .provenance import EvidenceKind, EvidenceRecord, EvidenceStatus, SourceRef
from .safety import RiskTier, SafetyGate, SafetyDecision
from .transforms import RigidTransform
from .frame_graph import FrameGraph
from .kinematics import JointPlacement, solve_tree_forward_kinematics

__all__ = [
    "Quantity", "DIMENSIONLESS", "LENGTH", "MASS", "TIME", "CURRENT",
    "TEMPERATURE", "EvidenceKind", "EvidenceRecord", "EvidenceStatus",
    "SourceRef", "RiskTier", "SafetyGate", "SafetyDecision",
    "RigidTransform", "FrameGraph", "JointPlacement",
    "solve_tree_forward_kinematics",
]
