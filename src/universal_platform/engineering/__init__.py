"""Safe, evidence-oriented engineering primitives.

This package performs offline calculations and model validation only. It does
not communicate with or control physical devices.
"""
from .quantity import Quantity, DIMENSIONLESS, LENGTH, MASS, TIME, CURRENT, TEMPERATURE
from .module_registry import ModuleManifest, ModuleOperation, ModuleRegistry
from .contracts import ModuleRequest, ModuleResponse
from .provenance import EvidenceKind, EvidenceRecord, EvidenceStatus, SourceRef, EvidenceGateResult, evaluate_evidence_gate
from .safety import RiskTier, SafetyGate, SafetyDecision
from .transforms import RigidTransform
from .framed_coordinates import FramedPoint3, FramedVector3
from .frame_graph import FrameGraph
from .primitive_geometry import BoxSolid, CylinderSolid, ExtrudedProfileSolid, FramedBounds3, PrimitiveGeometryModel, Vec2
from .profile_boolean import ProfileBooleanOperation, ProfileBooleanResult, ProfileLoop, boolean_profiles
from .mesh import TriangleMesh, MeshValidationResult, tessellate_box, tessellate_cylinder, tessellate_extruded_profile, validate_triangle_mesh
from .stl_interchange import BinarySTLArtifact, STLInterchangeManifest, export_binary_stl, validate_binary_stl_artifact
from .mesh_topology import MeshTopologyAnalysis, analyze_mesh_topology
from .mesh_intersection import MeshIntersection, MeshIntersectionAnalysis, analyze_mesh_intersections
from .planar_region import PlanarRegion, PRECISION_POLICY as PLANAR_REGION_PRECISION_POLICY
from .planar_boolean import PlanarRegionBooleanOperation, PlanarRegionBooleanResult, boolean_planar_regions
from .planar_region_set_boolean import PlanarRegionSetBooleanResult, boolean_planar_region_set
from .planar_region_extrusion import PlanarRegionExtrusionResult, extrude_planar_region
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
    analyze_geometric_mechanism_mobility,
    ConstraintJacobian,
    MobilityAnalysisResult,
    MobilityFormulation,
    NominalMobilityEstimate,
    SingularityStatus,
    analyze_mechanism_mobility,
    estimate_nominal_mobility,
)
from .joint_jacobian import (
    JointConstraintJacobian,
    JointConstraintJacobianColumn,
    JointConstraintVariable,
    build_joint_constraint_jacobian,
)
from .joint_constraints import (
    GeneratedJointConstraintSet,
    JointConstraintDefinition,
    JointConstraintEvaluation,
    JointConstraintResidual,
    generate_joint_constraints,
)
from .geometric_loop_coordinate_solver import (
    GeometricLoopCoordinateSolveResult, GeometricLoopCoordinateSolveStatus,
    solve_geometric_loop_coordinates,
)
from .geometric_loop_closure import (
    GeometricLoopClosureResult, GeometricLoopClosureStatus,
    GeometricLoopResidualGroup, evaluate_geometric_loop_closure,
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
from .sketch_region import SketchRegionConversionResult, sketch_to_planar_regions
from .parametric_sketch import (
    ParametricSketch, ParametricSketchSolveResult, SketchConstraint,
    SketchConstraintKind, SketchPoint, SketchSegment, solve_parametric_sketch,
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
    "ModuleManifest", "ModuleOperation", "ModuleRegistry", "ModuleRequest", "ModuleResponse",
    "TEMPERATURE", "EvidenceKind", "EvidenceRecord", "EvidenceStatus",
    "SourceRef", "EvidenceGateResult", "evaluate_evidence_gate", "RiskTier", "SafetyGate", "SafetyDecision",
    "RigidTransform", "FrameGraph", "FramedPoint3", "FramedVector3", "BoxSolid", "CylinderSolid", "ExtrudedProfileSolid", "FramedBounds3", "PrimitiveGeometryModel", "Vec2", "TriangleMesh", "MeshValidationResult", "tessellate_box", "tessellate_cylinder", "tessellate_extruded_profile", "validate_triangle_mesh", "ProfileBooleanOperation", "ProfileBooleanResult", "ProfileLoop", "boolean_profiles", "JointPlacement",
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
    "validate_mechanism_model", "GeneratedJointConstraintSet",
    "JointConstraintDefinition", "JointConstraintEvaluation",
    "JointConstraintResidual", "generate_joint_constraints",
    "JointConstraintJacobian", "JointConstraintJacobianColumn",
    "JointConstraintVariable", "build_joint_constraint_jacobian",
    "LoopClosureConstraint", "LoopClosureResult",
    "LoopClosureStatus", "LoopTopology", "MechanismLoop", "analyze_loop_topology",
    "solve_mechanism_loops", "BranchContinuityStatus", "DerivativeKinematicsResult",
    "MechanismKinematicsInput", "MechanismKinematicsResult",
    "solve_mechanism_kinematics", "GeometricLoopCoordinateSolveResult",
    "GeometricLoopCoordinateSolveStatus", "solve_geometric_loop_coordinates",
    "GeometricLoopClosureResult",
    "GeometricLoopClosureStatus", "GeometricLoopResidualGroup",
    "evaluate_geometric_loop_closure", "ConstraintJacobian", "MobilityAnalysisResult",
    "MobilityFormulation", "NominalMobilityEstimate", "SingularityStatus",
    "analyze_mechanism_mobility", "analyze_geometric_mechanism_mobility",
    "estimate_nominal_mobility", "JacobianMethod", "JacobianScaleDiagnostics",
    "JacobianScaleStatus", "JacobianRankDiagnostics", "JacobianRankStatus",
    "NonlinearConstraint", "NonlinearConstraintResidual", "NonlinearSolveResult",
    "NonlinearSolveStatus", "NonlinearSolverOptions", "VariableBound",
    "solve_nonlinear_constraints", "SketchRegionConversionResult", "sketch_to_planar_regions", "ParametricSketch", "ParametricSketchSolveResult", "SketchConstraint", "SketchConstraintKind", "SketchPoint", "SketchSegment", "solve_parametric_sketch", "BinarySTLArtifact", "STLInterchangeManifest", "export_binary_stl", "validate_binary_stl_artifact", "MeshTopologyAnalysis", "analyze_mesh_topology", "MeshIntersection", "MeshIntersectionAnalysis", "analyze_mesh_intersections", "PlanarRegion", "PLANAR_REGION_PRECISION_POLICY", "PlanarRegionBooleanOperation", "PlanarRegionBooleanResult", "boolean_planar_regions", "PlanarRegionSetBooleanResult", "boolean_planar_region_set", "PlanarRegionExtrusionResult", "extrude_planar_region",
]
