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
from .inverse_kinematics import (
    PlanarIKResult,
    solve_planar_two_link_inverse_kinematics,
)
from .planar_four_bar_adapter import (
    PlanarFourBarModelSnapshot,
    PlanarFourBarAdapterResult,
    solve_planar_four_bar_model,
)
from .planar_mechanisms import (
    PlanarFourBarResult,
    PlanarMobilityEstimate,
    estimate_planar_mobility,
    solve_planar_four_bar_loop,
)
from .mechanism_model import (
    SCHEMA_VERSION as MECHANISM_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS as SUPPORTED_MECHANISM_SCHEMA_VERSIONS,
    FrameReference,
    CoordinateKind,
    GeneralizedCoordinate,
    JointCoordinateParameterization,
    GeometryPlacement,
    JointFramePlacement,
    GeometryKind,
    GeometryReference,
    JointKind,
    JointModel,
    LinkModel,
    MechanismModel,
    ModelValidationResult,
    SolverCapability,
    validate_mechanism_model,
)
from .mechanism_mobility import (
    ConstraintJacobian,
    MobilityAnalysisResult,
    MobilityFormulation,
    NominalMobilityEstimate,
    SingularityStatus,
    analyze_mechanism_mobility,
    estimate_nominal_mobility,
)
from .mechanism_kinematics import (
    BranchContinuityStatus,
    DerivativeKinematicsResult,
    MechanismKinematicsInput,
    MechanismKinematicsResult,
    solve_mechanism_kinematics,
)
from .mechanism_loops import (
    LoopClosureConstraint,
    LoopClosureResult,
    LoopClosureStatus,
    LoopTopology,
    MechanismLoop,
    analyze_loop_topology,
    solve_mechanism_loops,
)
from .nonlinear_solver import (
    JacobianMethod,
    JacobianScaleDiagnostics,
    JacobianScaleStatus,
    JacobianRankDiagnostics,
    JacobianRankStatus,
    NonlinearConstraint,
    NonlinearConstraintResidual,
    NonlinearSolveResult,
    NonlinearSolveStatus,
    NonlinearSolverOptions,
    VariableBound,
    solve_nonlinear_constraints,
)

__all__ = [
    "Quantity", "DIMENSIONLESS", "LENGTH", "MASS", "TIME", "CURRENT",
    "TEMPERATURE", "EvidenceKind", "EvidenceRecord", "EvidenceStatus",
    "SourceRef", "RiskTier", "SafetyGate", "SafetyDecision",
    "RigidTransform", "FrameGraph", "JointPlacement",
    "solve_tree_forward_kinematics", "PlanarIKResult",
    "solve_planar_two_link_inverse_kinematics", "PlanarFourBarResult",
    "PlanarMobilityEstimate", "solve_planar_four_bar_loop",
    "PlanarFourBarModelSnapshot", "PlanarFourBarAdapterResult",
    "solve_planar_four_bar_model", "estimate_planar_mobility",
    "MECHANISM_SCHEMA_VERSION", "SUPPORTED_MECHANISM_SCHEMA_VERSIONS",
    "FrameReference", "CoordinateKind", "GeneralizedCoordinate",
    "JointCoordinateParameterization", "GeometryPlacement", "JointFramePlacement", "GeometryKind",
    "GeometryReference", "JointKind", "JointModel", "LinkModel",
    "MechanismModel", "ModelValidationResult", "SolverCapability",
    "validate_mechanism_model", "LoopClosureConstraint", "LoopClosureResult",
    "LoopClosureStatus", "LoopTopology", "MechanismLoop", "analyze_loop_topology",
    "solve_mechanism_loops", "BranchContinuityStatus", "DerivativeKinematicsResult",
    "MechanismKinematicsInput", "MechanismKinematicsResult",
    "solve_mechanism_kinematics", "ConstraintJacobian", "MobilityAnalysisResult",
    "MobilityFormulation", "NominalMobilityEstimate", "SingularityStatus",
    "analyze_mechanism_mobility", "estimate_nominal_mobility", "JacobianMethod", "JacobianScaleDiagnostics",
    "JacobianScaleStatus", "JacobianRankDiagnostics", "JacobianRankStatus",
    "NonlinearConstraint", "NonlinearConstraintResidual", "NonlinearSolveResult",
    "NonlinearSolveStatus", "NonlinearSolverOptions", "VariableBound",
    "solve_nonlinear_constraints",
]
