"""Safe, evidence-oriented engineering primitives.

This package performs offline calculations and model validation only. It does
not communicate with or control physical devices.
"""
from .quantity import Quantity, DIMENSIONLESS, LENGTH, MASS, TIME, CURRENT, TEMPERATURE
from .module_registry import ModuleManifest, ModuleOperation, ModuleRegistry
from .physics import (
    AxialStressSolver, LinearThermalExpansionSolver, OhmsLawSolver,
    PhysicsDomain, PhysicsInput, PhysicsMethod, PhysicsOutput, PhysicsProblem,
    PhysicsResult, PhysicsSolverDescriptor, PhysicsSolverRegistry,
    PhysicsSolverResponse, register_builtin_physics_solvers,
)
from .contracts import ModuleRequest, ModuleResponse
from .provenance import EvidenceKind, EvidenceRecord, EvidenceStatus, SourceRef, EvidenceGateResult, evaluate_evidence_gate
from .safety import RiskTier, SafetyGate, SafetyDecision
from .transforms import RigidTransform
from .framed_coordinates import FramedPoint3, FramedVector3
from .frame_graph import FrameGraph
from .primitive_geometry import BoxSolid, CylinderSolid, ExtrudedProfileSolid, FramedBounds3, PrimitiveGeometryModel, Vec2
from .profile_boolean import ProfileBooleanOperation, ProfileBooleanResult, ProfileLoop, boolean_profiles
from .step import STEPArtifact, STEPImportResult, export_step, import_step
from .three_mf import ThreeMFArtifact, ThreeMFImportResult, export_3mf, import_3mf
from .mesh import TriangleMesh, MeshValidationResult, tessellate_box, tessellate_cylinder, tessellate_extruded_profile, validate_triangle_mesh
from .brep import (
    BRepVertex, BRepEdge, BRepEdgeUse, BRepLoop, BRepFace, BRepShell,
    BRepValidationResult, BRepSolid, validate_brep_solid,
    brep_from_triangle_mesh, triangle_mesh_from_brep,
)
from .brep_boolean import (
    BRepBooleanOperation, BRepBooleanResult, boolean_axis_aligned_brep_solids,
)
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
from .feature_history import (
    FeatureArtifact, FeatureHistory, FeatureKind, FeatureNode,
    FeatureRegenerationResult, RegenerationStatus, regenerate_feature_history, upgrade_feature_history,
)
from .feature_history_merge import (
    FeatureHistoryMergeConflict, FeatureHistoryMergeResult, merge_feature_histories,
)
from .feature_history_editor import (
    add_feature, replace_feature, remove_feature, suppress_feature, unsuppress_feature,
)
from .feature_history_store import (
    FeatureHistoryBranch, FeatureHistoryMergeConflictError, FeatureHistoryMergeProvenance,
    FeatureHistoryNavigationState, FeatureHistoryNavigationUnavailable,
    FeatureHistoryRevision, FeatureHistoryRevisionConflict,
    FeatureHistoryStoreIntegrityError, SQLiteFeatureHistoryStore,
)
from .feature_artifact_store import (
    FeatureArtifactCacheIntegrityError, SQLiteFeatureArtifactCache,
)
from .cad_generator_service import CADGeneratorRun, CADGeneratorService
from .cad_generator_templates import build_polygon_extrusion_history
from .cad_generator_http_api import (
    CADAPIAuditIntegrityError,
    CADGeneratorHTTPServer,
    SQLiteCADAPIAuditLog,
    create_cad_generator_http_server,
)
from .sketch_region import SketchRegionConversionResult, sketch_to_planar_regions
from .parametric_sketch import (
    ParametricSketch, ParametricSketchSolveResult, SketchConstraint,
    SketchConstraintKind, SketchPoint, SketchSegment, SketchArc, solve_parametric_sketch,
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
    "PhysicsDomain", "PhysicsMethod", "PhysicsInput", "PhysicsProblem",
    "PhysicsOutput", "PhysicsResult", "PhysicsSolverDescriptor",
    "PhysicsSolverResponse", "PhysicsSolverRegistry", "AxialStressSolver",
    "OhmsLawSolver", "LinearThermalExpansionSolver", "register_builtin_physics_solvers",
    "ModuleManifest", "ModuleOperation", "ModuleRegistry", "ModuleRequest", "ModuleResponse",
    "TEMPERATURE", "EvidenceKind", "EvidenceRecord", "EvidenceStatus",
    "SourceRef", "EvidenceGateResult", "evaluate_evidence_gate", "RiskTier", "SafetyGate", "SafetyDecision",
    "RigidTransform", "FrameGraph", "FramedPoint3", "FramedVector3", "BoxSolid", "CylinderSolid", "ExtrudedProfileSolid", "FramedBounds3", "PrimitiveGeometryModel", "Vec2", "TriangleMesh", "MeshValidationResult", "tessellate_box", "tessellate_cylinder", "tessellate_extruded_profile", "validate_triangle_mesh", "ProfileBooleanOperation", "ProfileBooleanResult", "ProfileLoop", "boolean_profiles", "JointPlacement",
    "BRepVertex", "BRepEdge", "BRepEdgeUse", "BRepLoop", "BRepFace", "BRepShell",
    "BRepBooleanOperation", "BRepBooleanResult", "boolean_axis_aligned_brep_solids",
    "BRepValidationResult", "BRepSolid", "validate_brep_solid",
    "brep_from_triangle_mesh", "triangle_mesh_from_brep",
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
    "solve_nonlinear_constraints", "FeatureArtifact", "FeatureHistory", "FeatureKind", "FeatureNode", "FeatureRegenerationResult", "RegenerationStatus", "regenerate_feature_history", "upgrade_feature_history", "add_feature", "replace_feature", "remove_feature", "suppress_feature", "unsuppress_feature", "FeatureHistoryRevision", "FeatureHistoryNavigationState", "FeatureHistoryNavigationUnavailable", "FeatureHistoryRevisionConflict", "FeatureHistoryStoreIntegrityError", "SQLiteFeatureHistoryStore", "FeatureArtifactCacheIntegrityError", "SQLiteFeatureArtifactCache", "CADGeneratorRun", "CADGeneratorService", "build_polygon_extrusion_history", "CADAPIAuditIntegrityError", "CADGeneratorHTTPServer", "SQLiteCADAPIAuditLog", "create_cad_generator_http_server", "SketchRegionConversionResult", "sketch_to_planar_regions", "ParametricSketch", "ParametricSketchSolveResult", "SketchConstraint", "SketchConstraintKind", "SketchPoint", "SketchSegment", "SketchArc", "solve_parametric_sketch", "STEPArtifact", "STEPImportResult", "export_step", "import_step", "ThreeMFArtifact", "ThreeMFImportResult", "export_3mf", "import_3mf", "BinarySTLArtifact", "STLInterchangeManifest", "export_binary_stl", "validate_binary_stl_artifact", "MeshTopologyAnalysis", "analyze_mesh_topology", "MeshIntersection", "MeshIntersectionAnalysis", "analyze_mesh_intersections", "PlanarRegion", "PLANAR_REGION_PRECISION_POLICY", "PlanarRegionBooleanOperation", "PlanarRegionBooleanResult", "boolean_planar_regions", "PlanarRegionSetBooleanResult", "boolean_planar_region_set", "PlanarRegionExtrusionResult", "extrude_planar_region",
]
