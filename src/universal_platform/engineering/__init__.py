"""Safe, evidence-oriented engineering primitives.

This package performs offline calculations and model validation only. It does
not communicate with or control physical devices.
"""
from .boolean_boundary_selection import (
    BooleanBoundarySelection,
    SelectedBoundaryFragment,
    select_boolean_boundary_fragments,
)
from .boolean_resource_budget import BooleanResourceLedger
from .boolean_shell_assembly import (
    AssembledBooleanComponent,
    BooleanShellAssemblyResult,
    assemble_boolean_shells,
    assemble_rational_boolean_solid,
)
from .brep import (
    BRepEdge,
    BRepEdgeUse,
    BRepFace,
    BRepLoop,
    BRepShell,
    BRepSolid,
    BRepValidationResult,
    BRepVertex,
    brep_from_triangle_mesh,
    triangle_mesh_from_brep,
    validate_brep_solid,
)
from .brep_boolean import (
    BRepBooleanOperation,
    BRepBooleanResult,
    BRepMultiShellBooleanResult,
    boolean_axis_aligned_brep_solids,
    boolean_axis_aligned_multishell_solids,
)
from .brep_multishell import (
    BRepMultiShellSolid,
    BRepMultiShellValidationResult,
    validate_brep_multishell_solid,
)
from .cad_generator_http_api import (
    CADAPIAuditIntegrityError,
    CADGeneratorHTTPServer,
    SQLiteCADAPIAuditLog,
    create_cad_generator_http_server,
)
from .cad_generator_service import (
    CADGeneratorBooleanRun,
    CADGeneratorRun,
    CADGeneratorService,
)
from .cad_generator_templates import build_polygon_extrusion_history
from .contracts import ModuleRequest, ModuleResponse
from .faceted_boolean_arrangement import (
    FacetedBooleanArrangement,
    arrange_faceted_boolean_meshes,
)
from .feature_artifact_store import (
    FeatureArtifactCacheIntegrityError,
    SQLiteFeatureArtifactCache,
)
from .feature_history import (
    FeatureArtifact,
    FeatureHistory,
    FeatureKind,
    FeatureNode,
    FeatureRegenerationResult,
    RegenerationStatus,
    regenerate_feature_history,
    upgrade_feature_history,
)
from .feature_history_editor import (
    add_feature,
    remove_feature,
    replace_feature,
    suppress_feature,
    unsuppress_feature,
)
from .feature_history_merge import (
    FeatureHistoryMergeConflict,
    FeatureHistoryMergeResult,
    merge_feature_histories,
)
from .feature_history_store import (
    FeatureHistoryBranch,
    FeatureHistoryMergeConflictError,
    FeatureHistoryMergeProvenance,
    FeatureHistoryNavigationState,
    FeatureHistoryNavigationUnavailable,
    FeatureHistoryRevision,
    FeatureHistoryRevisionConflict,
    FeatureHistoryStoreIntegrityError,
    SQLiteFeatureHistoryStore,
)
from .frame_graph import FrameGraph
from .framed_coordinates import FramedPoint3, FramedVector3
from .geometric_loop_closure import (
    GeometricLoopClosureResult,
    GeometricLoopClosureStatus,
    GeometricLoopResidualGroup,
    evaluate_geometric_loop_closure,
)
from .geometric_loop_coordinate_solver import (
    GeometricLoopCoordinateSolveResult,
    GeometricLoopCoordinateSolveStatus,
    solve_geometric_loop_coordinates,
)
from .global_triangle_arrangement import (
    GlobalArrangementEdge,
    GlobalArrangementFace,
    GlobalArrangementVertex,
    GlobalTriangleArrangement,
    SourceCoverageReport,
    arrange_triangle_mesh_globally,
)
from .inverse_kinematics import (
    PlanarIKResult,
    solve_planar_two_link_inverse_kinematics,
)
from .joint_constraints import (
    GeneratedJointConstraintSet,
    JointConstraintDefinition,
    JointConstraintEvaluation,
    JointConstraintResidual,
    generate_joint_constraints,
)
from .joint_jacobian import (
    JointConstraintJacobian,
    JointConstraintJacobianColumn,
    JointConstraintVariable,
    build_joint_constraint_jacobian,
)
from .kinematics import JointPlacement, solve_tree_forward_kinematics
from .material_classification import (
    ExactMeshMaterialClassifier,
    MaterialClassification,
    MaterialClassificationResult,
    classify_point_against_mesh,
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
from .mechanism_mobility import (
    ConstraintJacobian,
    MobilityAnalysisResult,
    MobilityFormulation,
    NominalMobilityEstimate,
    SingularityStatus,
    analyze_geometric_mechanism_mobility,
    analyze_mechanism_mobility,
    estimate_nominal_mobility,
)
from .mechanism_model import (
    SCHEMA_VERSION as MECHANISM_SCHEMA_VERSION,
)
from .mechanism_model import (
    SUPPORTED_SCHEMA_VERSIONS as SUPPORTED_MECHANISM_SCHEMA_VERSIONS,
)
from .mechanism_model import (
    CoordinateKind,
    FrameReference,
    GeneralizedCoordinate,
    GeometryKind,
    GeometryPlacement,
    GeometryReference,
    JointCoordinateParameterization,
    JointFramePlacement,
    JointKind,
    JointModel,
    LinkModel,
    MechanismModel,
    ModelValidationResult,
    SolverCapability,
    validate_mechanism_model,
)
from .mesh import (
    MeshValidationResult,
    TriangleMesh,
    tessellate_box,
    tessellate_cylinder,
    tessellate_extruded_profile,
    validate_triangle_mesh,
)
from .mesh_intersection import (
    MeshIntersection,
    MeshIntersectionAnalysis,
    analyze_mesh_intersections,
)
from .mesh_topology import MeshTopologyAnalysis, analyze_mesh_topology
from .module_registry import ModuleManifest, ModuleOperation, ModuleRegistry
from .nonlinear_solver import (
    JacobianMethod,
    JacobianRankDiagnostics,
    JacobianRankStatus,
    JacobianScaleDiagnostics,
    JacobianScaleStatus,
    NonlinearConstraint,
    NonlinearConstraintResidual,
    NonlinearSolveResult,
    NonlinearSolverOptions,
    NonlinearSolveStatus,
    VariableBound,
    solve_nonlinear_constraints,
)
from .parametric_sketch import (
    ParametricSketch,
    ParametricSketchSolveResult,
    SketchArc,
    SketchConstraint,
    SketchConstraintKind,
    SketchPoint,
    SketchSegment,
    solve_parametric_sketch,
)
from .physics import (
    AxialStressSolver,
    LinearThermalExpansionSolver,
    OhmsLawSolver,
    PhysicsDomain,
    PhysicsInput,
    PhysicsMethod,
    PhysicsOutput,
    PhysicsProblem,
    PhysicsResult,
    PhysicsSolverDescriptor,
    PhysicsSolverRegistry,
    PhysicsSolverResponse,
    register_builtin_physics_solvers,
)
from .planar_boolean import (
    PlanarRegionBooleanOperation,
    PlanarRegionBooleanResult,
    boolean_planar_regions,
)
from .planar_four_bar_adapter import (
    PlanarFourBarAdapterResult,
    PlanarFourBarModelSnapshot,
    solve_planar_four_bar_model,
)
from .planar_mechanisms import (
    PlanarFourBarResult,
    PlanarMobilityEstimate,
    estimate_planar_mobility,
    solve_planar_four_bar_loop,
)
from .planar_region import PRECISION_POLICY as PLANAR_REGION_PRECISION_POLICY
from .planar_region import PlanarRegion
from .planar_region_extrusion import PlanarRegionExtrusionResult, extrude_planar_region
from .planar_region_set_boolean import (
    PlanarRegionSetBooleanResult,
    boolean_planar_region_set,
)
from .primitive_geometry import (
    BoxSolid,
    CylinderSolid,
    ExtrudedProfileSolid,
    FramedBounds3,
    PrimitiveGeometryModel,
    Vec2,
)
from .profile_boolean import (
    ProfileBooleanOperation,
    ProfileBooleanResult,
    ProfileLoop,
    boolean_profiles,
)
from .provenance import (
    EvidenceGateResult,
    EvidenceKind,
    EvidenceRecord,
    EvidenceStatus,
    SourceRef,
    evaluate_evidence_gate,
)
from .quantity import CURRENT, DIMENSIONLESS, LENGTH, MASS, TEMPERATURE, TIME, Quantity
from .rational_faceted_solid import RationalFacetedSolid, RationalPoint3
from .safety import RiskTier, SafetyDecision, SafetyGate
from .sketch_region import SketchRegionConversionResult, sketch_to_planar_regions
from .step import STEPArtifact, STEPImportResult, export_step, import_step
from .stl_interchange import (
    BinarySTLArtifact,
    STLInterchangeManifest,
    export_binary_stl,
    validate_binary_stl_artifact,
)
from .three_mf import ThreeMFArtifact, ThreeMFImportResult, export_3mf, import_3mf
from .transforms import RigidTransform
from .triangle_coverage_oracle import (
    ExactCoverageResult,
    certify_triangle_partition,
    coplanar_triangle_intersection_kind,
)
from .triangle_fragment_arrangement import (
    RationalPlane,
    RationalTriangleFragment,
    arrange_triangles_by_planes,
)
from .triangle_intersection_events import (
    TriangleFragment,
    TriangleIntersectionSegment,
    extract_transverse_triangle_intersection,
    split_triangle_by_intersecting_plane,
)

__all__ = [
    "CURRENT",
    "DIMENSIONLESS",
    "LENGTH",
    "MASS",
    "MECHANISM_SCHEMA_VERSION",
    "PLANAR_REGION_PRECISION_POLICY",
    "SUPPORTED_MECHANISM_SCHEMA_VERSIONS",
    "TEMPERATURE",
    "TIME",
    "AssembledBooleanComponent",
    "AxialStressSolver",
    "BRepBooleanOperation",
    "BRepBooleanResult",
    "BRepEdge",
    "BRepEdgeUse",
    "BRepFace",
    "BRepLoop",
    "BRepMultiShellBooleanResult",
    "BRepMultiShellSolid",
    "BRepMultiShellValidationResult",
    "BRepShell",
    "BRepSolid",
    "BRepValidationResult",
    "BRepVertex",
    "BinarySTLArtifact",
    "BooleanBoundarySelection",
    "BooleanResourceLedger",
    "BooleanShellAssemblyResult",
    "BoxSolid",
    "BranchContinuityStatus",
    "CADAPIAuditIntegrityError",
    "CADGeneratorBooleanRun",
    "CADGeneratorHTTPServer",
    "CADGeneratorRun",
    "CADGeneratorService",
    "ConstraintJacobian",
    "CoordinateKind",
    "CylinderSolid",
    "DerivativeKinematicsResult",
    "EvidenceGateResult",
    "EvidenceKind",
    "EvidenceRecord",
    "EvidenceStatus",
    "ExactCoverageResult",
    "ExactMeshMaterialClassifier",
    "ExtrudedProfileSolid",
    "FacetedBooleanArrangement",
    "FeatureArtifact",
    "FeatureArtifactCacheIntegrityError",
    "FeatureHistory",
    "FeatureHistoryBranch",
    "FeatureHistoryMergeConflict",
    "FeatureHistoryMergeConflictError",
    "FeatureHistoryMergeProvenance",
    "FeatureHistoryMergeResult",
    "FeatureHistoryNavigationState",
    "FeatureHistoryNavigationUnavailable",
    "FeatureHistoryRevision",
    "FeatureHistoryRevisionConflict",
    "FeatureHistoryStoreIntegrityError",
    "FeatureKind",
    "FeatureNode",
    "FeatureRegenerationResult",
    "FrameGraph",
    "FrameReference",
    "FramedBounds3",
    "FramedPoint3",
    "FramedVector3",
    "GeneralizedCoordinate",
    "GeneratedJointConstraintSet",
    "GeometricLoopClosureResult",
    "GeometricLoopClosureStatus",
    "GeometricLoopCoordinateSolveResult",
    "GeometricLoopCoordinateSolveStatus",
    "GeometricLoopResidualGroup",
    "GeometryKind",
    "GeometryPlacement",
    "GeometryReference",
    "GlobalArrangementEdge",
    "GlobalArrangementFace",
    "GlobalArrangementVertex",
    "GlobalTriangleArrangement",
    "JacobianMethod",
    "JacobianRankDiagnostics",
    "JacobianRankStatus",
    "JacobianScaleDiagnostics",
    "JacobianScaleStatus",
    "JointConstraintDefinition",
    "JointConstraintEvaluation",
    "JointConstraintJacobian",
    "JointConstraintJacobianColumn",
    "JointConstraintResidual",
    "JointConstraintVariable",
    "JointCoordinateParameterization",
    "JointFramePlacement",
    "JointKind",
    "JointModel",
    "JointPlacement",
    "LinearThermalExpansionSolver",
    "LinkModel",
    "LoopClosureConstraint",
    "LoopClosureResult",
    "LoopClosureStatus",
    "LoopTopology",
    "MaterialClassification",
    "MaterialClassificationResult",
    "MechanismKinematicsInput",
    "MechanismKinematicsResult",
    "MechanismLoop",
    "MechanismModel",
    "MeshIntersection",
    "MeshIntersectionAnalysis",
    "MeshTopologyAnalysis",
    "MeshValidationResult",
    "MobilityAnalysisResult",
    "MobilityFormulation",
    "ModelValidationResult",
    "ModuleGrant",
    "ModuleHandler",
    "ModuleManifest",
    "ModuleOperation",
    "ModuleRegistry",
    "ModuleRequest",
    "ModuleResponse",
    "ModuleRuntime",
    "NominalMobilityEstimate",
    "NonlinearConstraint",
    "NonlinearConstraintResidual",
    "NonlinearSolveResult",
    "NonlinearSolveStatus",
    "NonlinearSolverOptions",
    "OhmsLawSolver",
    "ParametricSketch",
    "ParametricSketchSolveResult",
    "PhysicsDomain",
    "PhysicsInput",
    "PhysicsMethod",
    "PhysicsModuleBridge",
    "PhysicsOutput",
    "PhysicsProblem",
    "PhysicsResult",
    "PhysicsSolverDescriptor",
    "PhysicsSolverRegistry",
    "PhysicsSolverResponse",
    "PlanarFourBarAdapterResult",
    "PlanarFourBarModelSnapshot",
    "PlanarFourBarResult",
    "PlanarIKResult",
    "PlanarMobilityEstimate",
    "PlanarRegion",
    "PlanarRegionBooleanOperation",
    "PlanarRegionBooleanResult",
    "PlanarRegionExtrusionResult",
    "PlanarRegionSetBooleanResult",
    "PrimitiveGeometryModel",
    "ProfileBooleanOperation",
    "ProfileBooleanResult",
    "ProfileLoop",
    "Quantity",
    "RationalBooleanComponent",
    "RationalBooleanShell",
    "RationalBooleanSolid",
    "RationalFacetedSolid",
    "RationalPlane",
    "RationalPoint3",
    "RationalTriangleFragment",
    "RegenerationStatus",
    "RigidTransform",
    "RiskTier",
    "SQLiteCADAPIAuditLog",
    "SQLiteFeatureArtifactCache",
    "SQLiteFeatureHistoryStore",
    "STEPArtifact",
    "STEPImportResult",
    "STLInterchangeManifest",
    "SafetyDecision",
    "SafetyGate",
    "SelectedBoundaryFragment",
    "SingularityStatus",
    "SketchArc",
    "SketchConstraint",
    "SketchConstraintKind",
    "SketchPoint",
    "SketchRegionConversionResult",
    "SketchSegment",
    "SolverCapability",
    "SourceCoverageReport",
    "SourceRef",
    "ThreeMFArtifact",
    "ThreeMFImportResult",
    "TriangleFragment",
    "TriangleIntersectionSegment",
    "TriangleMesh",
    "VariableBound",
    "Vec2",
    "add_feature",
    "analyze_geometric_mechanism_mobility",
    "analyze_loop_topology",
    "analyze_mechanism_mobility",
    "analyze_mesh_intersections",
    "analyze_mesh_topology",
    "arrange_faceted_boolean_meshes",
    "arrange_triangle_mesh_globally",
    "arrange_triangles_by_planes",
    "assemble_boolean_shells",
    "assemble_rational_boolean_solid",
    "boolean_axis_aligned_brep_solids",
    "boolean_axis_aligned_multishell_solids",
    "boolean_planar_region_set",
    "boolean_planar_regions",
    "boolean_profiles",
    "brep_from_triangle_mesh",
    "build_joint_constraint_jacobian",
    "build_polygon_extrusion_history",
    "certify_triangle_partition",
    "classify_point_against_mesh",
    "coplanar_triangle_intersection_kind",
    "create_builtin_physics_module_bridge",
    "create_cad_generator_http_server",
    "estimate_nominal_mobility",
    "estimate_planar_mobility",
    "evaluate_evidence_gate",
    "evaluate_geometric_loop_closure",
    "export_3mf",
    "export_binary_stl",
    "export_step",
    "extract_transverse_triangle_intersection",
    "extrude_planar_region",
    "generate_joint_constraints",
    "import_3mf",
    "import_step",
    "merge_feature_histories",
    "regenerate_feature_history",
    "register_builtin_physics_solvers",
    "remove_feature",
    "replace_feature",
    "select_boolean_boundary_fragments",
    "sketch_to_planar_regions",
    "solve_geometric_loop_coordinates",
    "solve_mechanism_kinematics",
    "solve_mechanism_loops",
    "solve_nonlinear_constraints",
    "solve_parametric_sketch",
    "solve_planar_four_bar_loop",
    "solve_planar_four_bar_model",
    "solve_planar_two_link_inverse_kinematics",
    "solve_tree_forward_kinematics",
    "split_triangle_by_intersecting_plane",
    "suppress_feature",
    "tessellate_box",
    "tessellate_cylinder",
    "tessellate_extruded_profile",
    "triangle_mesh_from_brep",
    "unsuppress_feature",
    "upgrade_feature_history",
    "validate_binary_stl_artifact",
    "validate_brep_multishell_solid",
    "validate_brep_solid",
    "validate_mechanism_model",
    "validate_triangle_mesh",
]

from .rational_boolean_solid import (
    RationalBooleanComponent,
    RationalBooleanShell,
    RationalBooleanSolid,
)

__all__.extend(["RationalBooleanComponent", "RationalBooleanShell", "RationalBooleanSolid"])

from .module_runtime import ModuleGrant, ModuleHandler, ModuleRuntime

__all__.extend(["ModuleGrant", "ModuleHandler", "ModuleRuntime"])

from .physics_module_adapter import (
    PhysicsModuleBridge,
    create_builtin_physics_module_bridge,
)

__all__.extend(["PhysicsModuleBridge", "create_builtin_physics_module_bridge"])

