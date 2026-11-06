"""Evidence-oriented nominal and local mechanism mobility diagnostics.

Nominal mobility is a topology/joint-count estimate. Local mobility is
estimated independently from a caller-supplied constraint Jacobian at one
named configuration. Neither result is a physical-feasibility or certification
claim; singularity is only compared with an explicitly supplied regular-rank
reference.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Mapping, Sequence

from .errors import InvalidModelError
from .mechanism_model import (
    JointKind,
    MechanismModel,
    validate_mechanism_model,
)
from .joint_constraints import generate_joint_constraints
from .joint_jacobian import build_joint_constraint_jacobian
from .nonlinear_solver import (
    JacobianMethod,
    JacobianRankDiagnostics,
    _estimate_jacobian_rank,
)
from .transforms import RigidTransform


SCHEMA_VERSION = "1.0"


class MobilityFormulation(str, Enum):
    PLANAR = "PLANAR"
    SPATIAL = "SPATIAL"


class SingularityStatus(str, Enum):
    POSSIBLE_SINGULARITY = "POSSIBLE_SINGULARITY"
    NOT_DETECTED = "NOT_DETECTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ConstraintJacobian:
    """Constraint Jacobian at one configuration.

    Rows are scalar constraint equations. Columns contain free-body pose
    tangent variables and may additionally declare independent joint
    generalized-coordinate variables. Caller-supplied matrices retain their
    explicit ordering; the geometric adapter builds a finite-difference matrix
    from complete placements and generated joint residuals.
    """

    constraint_ids: tuple[str, ...]
    coordinate_ids: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    configuration_id: str
    source: str
    joint_coordinate_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NominalMobilityEstimate:
    formulation: MobilityFormulation
    body_dimension: int
    link_count: int
    ground_link_id: str
    free_body_dof: int
    nominal_joint_constraints: int
    estimated_dof: int
    joint_dof_counts: tuple[tuple[str, int], ...]
    formula: str


@dataclass(frozen=True, slots=True)
class MobilityAnalysisResult:
    schema_version: str
    model_id: str
    model_revision: str
    configuration_id: str
    jacobian_source: str
    nominal: NominalMobilityEstimate
    jacobian_rank: JacobianRankDiagnostics
    local_mobility: int
    redundant_constraint_count: int
    nominal_overconstrained: bool
    singularity_status: SingularityStatus
    reference_constraint_rank: int | None
    limitations: tuple[str, ...]
    joint_coordinate_count: int = 0

    @property
    def redundant_constraints_detected(self) -> bool:
        return self.redundant_constraint_count > 0

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, JSON-compatible versioned snapshot."""
        return {
            "schema_version": self.schema_version,
            "model": {"model_id": self.model_id, "revision": self.model_revision},
            "configuration_id": self.configuration_id,
            "jacobian_source": self.jacobian_source,
            "nominal": {
                "formulation": self.nominal.formulation.value,
                "body_dimension": self.nominal.body_dimension,
                "link_count": self.nominal.link_count,
                "ground_link_id": self.nominal.ground_link_id,
                "free_body_dof": self.nominal.free_body_dof,
                "nominal_joint_constraints": self.nominal.nominal_joint_constraints,
                "estimated_dof": self.nominal.estimated_dof,
                "joint_dof_counts": dict(self.nominal.joint_dof_counts),
                "formula": self.nominal.formula,
            },
            "local": {
                "constraint_count": self.jacobian_rank.row_count,
                "coordinate_count": self.jacobian_rank.column_count,
                "body_pose_coordinate_count": self.nominal.free_body_dof,
                "joint_coordinate_count": self.joint_coordinate_count,
                "total_variable_count": self.jacobian_rank.column_count,
                "estimated_constraint_rank": self.jacobian_rank.estimated_rank,
                "rank_status": self.jacobian_rank.status.value,
                "rank_method": self.jacobian_rank.method,
                "rank_tolerance": self.jacobian_rank.threshold,
                "estimated_mobility": self.local_mobility,
                "redundant_constraint_count": self.redundant_constraint_count,
                "nominal_overconstrained": self.nominal_overconstrained,
                "singularity_status": self.singularity_status.value,
                "reference_constraint_rank": self.reference_constraint_rank,
            },
            "limitations": list(self.limitations),
        }


def estimate_nominal_mobility(
    model: MechanismModel,
    formulation: MobilityFormulation,
    *,
    ground_link_id: str,
) -> NominalMobilityEstimate:
    """Estimate nominal DOF from free rigid bodies and joint metadata.

    PLANAR uses 3 coordinates per moving link; SPATIAL uses 6. Every joint is
    treated as an ideal lower pair with the nominal relative DOF declared by
    JointKind. Higher-pair constraints are not represented by this schema.
    """
    validation = validate_mechanism_model(model)
    if not validation.valid:
        raise InvalidModelError(
            "Cannot estimate mobility for invalid mechanism model: "
            + "; ".join(validation.errors)
        )
    if not isinstance(formulation, MobilityFormulation):
        raise InvalidModelError("formulation must be a MobilityFormulation")
    if len(model.links) < 2:
        raise InvalidModelError("Mobility analysis requires at least two links")
    if not isinstance(ground_link_id, str) or not ground_link_id.strip():
        raise InvalidModelError("ground_link_id must be a non-empty stable link ID")
    if ground_link_id not in {item.link_id for item in model.links}:
        raise InvalidModelError(f"Unknown ground_link_id: {ground_link_id!r}")

    dimension = 3 if formulation is MobilityFormulation.PLANAR else 6
    planar_joint_dof = {
        JointKind.FIXED: 0,
        JointKind.REVOLUTE: 1,
        JointKind.PRISMATIC: 1,
        JointKind.PLANAR: 3,
    }
    joint_dof: list[tuple[str, int]] = []
    constraints = 0
    for joint in model.joints:
        dof = (
            planar_joint_dof.get(joint.joint_kind)
            if formulation is MobilityFormulation.PLANAR
            else joint.nominal_dof
        )
        if dof is None:
            raise InvalidModelError(
                f"Joint {joint.joint_id!r} ({joint.joint_kind.value}) "
                "is not supported by the PLANAR mobility formulation"
            )
        if dof > dimension:
            raise InvalidModelError(
                f"Joint {joint.joint_id!r} has more relative DOF than the "
                f"{formulation.value} body dimension"
            )
        joint_dof.append((joint.joint_id, dof))
        constraints += dimension - dof

    free_body_dof = dimension * (len(model.links) - 1)
    estimated = free_body_dof - constraints
    formula = (
        "M = 3*(N-1) - sum(3-f_i)"
        if formulation is MobilityFormulation.PLANAR
        else "M = 6*(N-1) - sum(6-f_i)"
    )
    return NominalMobilityEstimate(
        formulation=formulation,
        body_dimension=dimension,
        link_count=len(model.links),
        ground_link_id=ground_link_id,
        free_body_dof=free_body_dof,
        nominal_joint_constraints=constraints,
        estimated_dof=estimated,
        joint_dof_counts=tuple(joint_dof),
        formula=formula,
    )


def analyze_mechanism_mobility(
    model: MechanismModel,
    formulation: MobilityFormulation,
    jacobian: ConstraintJacobian,
    *,
    ground_link_id: str,
    reference_constraint_rank: int | None = None,
    rank_tolerance: float = 1e-10,
) -> MobilityAnalysisResult:
    """Compare nominal DOF with local Jacobian mobility at one configuration.

    The local estimate is coordinate_count - estimated_rank(J). A supplied
    reference rank represents the expected regular-configuration rank for the
    same constraint system. A lower local rank is flagged as a *possible*
    singularity, never as a proof of one.
    """
    nominal = estimate_nominal_mobility(model, formulation, ground_link_id=ground_link_id)
    if not isinstance(jacobian, ConstraintJacobian):
        raise InvalidModelError("jacobian must be a ConstraintJacobian")
    for label, value in (
        ("configuration_id", jacobian.configuration_id),
        ("source", jacobian.source),
    ):
        if not isinstance(value, str) or not value.strip():
            raise InvalidModelError(f"Jacobian {label} must be a non-empty string")
    if not jacobian.constraint_ids or not jacobian.coordinate_ids:
        raise InvalidModelError("Jacobian must declare at least one constraint and coordinate")
    if any(not isinstance(item, str) or not item.strip()
           for item in jacobian.constraint_ids + jacobian.coordinate_ids):
        raise InvalidModelError("Jacobian identifiers must be non-empty strings")
    if len(set(jacobian.constraint_ids)) != len(jacobian.constraint_ids):
        raise InvalidModelError("Jacobian constraint identifiers must be unique")
    if len(set(jacobian.coordinate_ids)) != len(jacobian.coordinate_ids):
        raise InvalidModelError("Jacobian coordinate identifiers must be unique")
    if any(not isinstance(item, str) or not item.strip() for item in jacobian.joint_coordinate_ids):
        raise InvalidModelError("Joint coordinate identifiers must be non-empty strings")
    if len(set(jacobian.joint_coordinate_ids)) != len(jacobian.joint_coordinate_ids):
        raise InvalidModelError("Joint coordinate identifiers must be unique")
    if not set(jacobian.joint_coordinate_ids).issubset(set(jacobian.coordinate_ids)):
        raise InvalidModelError("Joint coordinate identifiers must be a subset of Jacobian variables")
    if len(jacobian.values) != len(jacobian.constraint_ids):
        raise InvalidModelError("Jacobian row count must match constraint identifiers")
    if any(len(row) != len(jacobian.coordinate_ids) for row in jacobian.values):
        raise InvalidModelError("Jacobian column count must match coordinate identifiers")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)
        for row in jacobian.values for value in row
    ):
        raise InvalidModelError("Jacobian values must be finite numbers (not booleans)")
    if isinstance(rank_tolerance, bool) or not isfinite(rank_tolerance) or rank_tolerance <= 0.0:
        raise InvalidModelError("rank_tolerance must be finite and positive")

    expected_variables = nominal.free_body_dof + len(jacobian.joint_coordinate_ids)
    if len(jacobian.coordinate_ids) != expected_variables:
        raise InvalidModelError(
            "Jacobian coordinate count must match free-body generalized DOF plus declared "
            f"joint coordinates ({expected_variables}) for the selected ground link"
        )

    max_rank = min(len(jacobian.constraint_ids), len(jacobian.coordinate_ids))
    if reference_constraint_rank is not None and (
        type(reference_constraint_rank) is not int
        or reference_constraint_rank < 0
        or reference_constraint_rank > max_rank
    ):
        raise InvalidModelError(
            f"reference_constraint_rank must be an integer from 0 to {max_rank}"
        )

    rank = _estimate_jacobian_rank(
        [list(map(float, row)) for row in jacobian.values], rank_tolerance
    )
    if rank.estimated_rank is None:
        local_mobility = -1
        redundant = -1
        singularity = SingularityStatus.UNKNOWN
    else:
        local_mobility = len(jacobian.coordinate_ids) - rank.estimated_rank
        redundant = max(0, len(jacobian.constraint_ids) - rank.estimated_rank)
        if reference_constraint_rank is None:
            singularity = SingularityStatus.UNKNOWN
        elif rank.estimated_rank < reference_constraint_rank:
            singularity = SingularityStatus.POSSIBLE_SINGULARITY
        elif rank.estimated_rank == reference_constraint_rank:
            singularity = SingularityStatus.NOT_DETECTED
        else:
            # A local rank above the supplied regular reference makes that
            # reference inconsistent; do not silently report regularity.
            singularity = SingularityStatus.UNKNOWN

    return MobilityAnalysisResult(
        schema_version=SCHEMA_VERSION,
        model_id=model.model_id,
        model_revision=model.revision,
        configuration_id=jacobian.configuration_id,
        jacobian_source=jacobian.source,
        nominal=nominal,
        jacobian_rank=rank,
        local_mobility=local_mobility,
        redundant_constraint_count=redundant,
        nominal_overconstrained=nominal.estimated_dof < 0,
        singularity_status=singularity,
        reference_constraint_rank=reference_constraint_rank,
        joint_coordinate_count=len(jacobian.joint_coordinate_ids),
        limitations=(
            (
                "Nominal DOF assumes ideal lower pairs and independent joint constraints; higher pairs are not modeled.",
                "Local mobility is an estimate from a Jacobian at one configuration; rank depends on scaling and tolerance.",
                "When declared, local variables combine free-body pose tangent coordinates and independent joint generalized coordinates.",
                "Automatically generated geometric Jacobians use finite differences, not symbolic or exact derivatives.",
                "Redundant Jacobian rows are reported separately and do not alone prove physical overconstraint.",
                "A possible singularity requires an explicit regular-configuration reference rank; absence of a flag is not a proof of regularity.",
                "No collision/contact, dynamics, physical feasibility, safety certification or fabrication validation is performed.",
            )
            + (
                (
                    "PLANAR analysis assumes every body and joint anchor lies in the supplied plane frame.",
                    "PLANAR body variables are projected to two in-plane translations and one plane-normal rotation; out-of-plane body motion is rejected.",
                )
                if formulation is MobilityFormulation.PLANAR else ()
            )
        ),
    )



def _validate_planar_plane_frame(
    model: MechanismModel,
    body_poses: Mapping[str, RigidTransform],
    plane_frame: RigidTransform,
    *,
    plane_tolerance_m: float,
    angular_tolerance_rad: float,
) -> None:
    if not isinstance(plane_frame, RigidTransform):
        raise InvalidModelError("PLANAR mobility requires an explicit plane_frame RigidTransform")
    if plane_frame.length_unit != "m":
        raise InvalidModelError("PLANAR mobility plane_frame must use metres (m)")
    for name, value in (
        ("plane_tolerance_m", plane_tolerance_m),
        ("angular_tolerance_rad", angular_tolerance_rad),
    ):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value <= 0.0):
            raise InvalidModelError(f"{name} must be finite and positive")

    world_frames = {pose.to_frame for pose in body_poses.values()}
    if len(world_frames) != 1 or plane_frame.to_frame not in world_frames:
        raise InvalidModelError(
            "plane_frame must map into the same shared world frame as every body pose"
        )
    plane_to_world_inverse = plane_frame.inverse()
    for link_id, pose in body_poses.items():
        body_to_plane = pose.then(plane_to_world_inverse)
        if abs(body_to_plane.translation.z) > plane_tolerance_m:
            raise InvalidModelError(
                f"Body origin for link {link_id!r} is outside the declared plane"
            )
        local_z_in_plane = tuple(body_to_plane.rotation[row][2] for row in range(3))
        if (
            abs(local_z_in_plane[0]) > angular_tolerance_rad
            or abs(local_z_in_plane[1]) > angular_tolerance_rad
            or abs(local_z_in_plane[2] - 1.0) > angular_tolerance_rad
        ):
            raise InvalidModelError(
                f"Body frame for link {link_id!r} must keep local +Z aligned with the plane normal"
            )

    placements = {item.joint_id: item for item in model.joint_placements}
    coordinates = {item.coordinate_id: item for item in model.generalized_coordinates}
    parameterizations = {
        item.joint_id: item for item in model.joint_parameterizations
    }
    for joint in model.joints:
        placement = placements[joint.joint_id]
        parent_pose = body_poses[joint.parent_link_id]
        joint_to_world = placement.parent_to_joint.inverse().then(parent_pose)
        joint_to_plane = joint_to_world.then(plane_to_world_inverse)
        if abs(joint_to_plane.translation.z) > plane_tolerance_m:
            raise InvalidModelError(
                f"Joint frame origin for {joint.joint_id!r} is outside the declared plane"
            )
        parameterization = parameterizations.get(joint.joint_id)
        if parameterization is None:
            continue
        for coordinate_id in parameterization.coordinate_ids:
            coordinate = coordinates[coordinate_id]
            axis = tuple(
                sum(joint_to_plane.rotation[row][column] * coordinate.axis[column]
                    for column in range(3))
                for row in range(3)
            )
            if coordinate.coordinate_kind.value == "ROTATIONAL":
                if (
                    abs(axis[0]) > angular_tolerance_rad
                    or abs(axis[1]) > angular_tolerance_rad
                    or abs(abs(axis[2]) - 1.0) > angular_tolerance_rad
                ):
                    raise InvalidModelError(
                        f"Rotational coordinate axis {coordinate_id!r} must be parallel to the plane normal"
                    )
            elif abs(axis[2]) > angular_tolerance_rad:
                raise InvalidModelError(
                    f"Translational coordinate axis {coordinate_id!r} must lie in the plane"
                )


def _build_planar_constraint_jacobian(
    generated_jacobian,
    model: MechanismModel,
    plane_frame: RigidTransform,
    *,
    ground_link_id: str,
    configuration_id: str,
    jacobian_method: JacobianMethod,
    finite_difference_step: float,
) -> ConstraintJacobian:
    columns = generated_jacobian.columns
    coordinate_indices = [
        index for index, column in enumerate(columns)
        if column.variable.variable_kind == "GENERALIZED_COORDINATE"
    ]
    coordinate_ids = [columns[index].variable.variable_id for index in coordinate_indices]
    reduced_ids = list(coordinate_ids)
    reduced_values = [
        [row[index] for index in coordinate_indices]
        for row in generated_jacobian.values
    ]

    plane_x = tuple(plane_frame.rotation[row][0] for row in range(3))
    plane_y = tuple(plane_frame.rotation[row][1] for row in range(3))
    plane_normal = tuple(plane_frame.rotation[row][2] for row in range(3))
    index_by_variable = {
        column.variable.variable_id: index
        for index, column in enumerate(columns)
    }
    for link in sorted(model.links, key=lambda item: item.link_id):
        if link.link_id == ground_link_id:
            continue
        pose_columns = {
            component: index_by_variable[f"link/{link.link_id}/pose/{component}"]
            for component in (
                "translation_x", "translation_y", "translation_z",
                "rotation_x", "rotation_y", "rotation_z",
            )
        }
        projected = (
            ("translation_x", plane_x, ("translation_x", "translation_y", "translation_z")),
            ("translation_y", plane_y, ("translation_x", "translation_y", "translation_z")),
            ("rotation_normal", plane_normal, ("rotation_x", "rotation_y", "rotation_z")),
        )
        for name, basis, components in projected:
            reduced_ids.append(
                f"link/{link.link_id}/plane/{plane_frame.from_frame}/{name}"
            )
            source_indices = [pose_columns[component] for component in components]
            for row_index, row in enumerate(generated_jacobian.values):
                reduced_values[row_index].append(
                    sum(row[source_indices[axis]] * basis[axis] for axis in range(3))
                )

    expected_columns = 3 * (len(model.links) - 1) + len(model.generalized_coordinates)
    if len(reduced_ids) != expected_columns:
        raise InvalidModelError(
            "Projected planar Jacobian does not cover the expected plane and joint variables"
        )
    return ConstraintJacobian(
        generated_jacobian.row_ids,
        tuple(reduced_ids),
        tuple(tuple(row) for row in reduced_values),
        configuration_id,
        (
            "generated-planar-joint-pose-residuals:"
            + plane_frame.from_frame
            + ":"
            + jacobian_method.value
            + f":step={finite_difference_step:g}"
        ),
        tuple(coordinate_ids),
    )


def analyze_geometric_mechanism_mobility(
    model: MechanismModel,
    formulation: MobilityFormulation,
    body_poses: Mapping[str, RigidTransform],
    coordinate_values: Mapping[str, float],
    *,
    ground_link_id: str,
    configuration_id: str,
    reference_constraint_rank: int | None = None,
    rank_tolerance: float = 1e-10,
    jacobian_method: JacobianMethod = JacobianMethod.CENTRAL_FINITE_DIFFERENCE,
    finite_difference_step: float = 1e-6,
    plane_frame: RigidTransform | None = None,
    plane_tolerance_m: float = 1e-8,
    angular_tolerance_rad: float = 1e-8,
) -> MobilityAnalysisResult:
    """Estimate local geometric mobility from generated joint residual derivatives.

    SPATIAL uses six pose-tangent coordinates for each non-ground link.
    PLANAR requires an explicit plane-to-world RigidTransform and projects each
    non-ground link to two in-plane translations plus one plane-normal rotation.
    """
    if not isinstance(formulation, MobilityFormulation):
        raise InvalidModelError("formulation must be a MobilityFormulation")
    if not isinstance(configuration_id, str) or not configuration_id.strip():
        raise InvalidModelError("configuration_id must be a non-empty stable identifier")

    if formulation is MobilityFormulation.PLANAR:
        if plane_frame is None:
            raise InvalidModelError(
                "PLANAR mobility requires an explicit plane-frame contract (plane_frame RigidTransform)"
            )
        nominal = estimate_nominal_mobility(
            model, formulation, ground_link_id=ground_link_id
        )
        generated = generate_joint_constraints(model)
        generated.evaluate(body_poses, coordinate_values)
        _validate_planar_plane_frame(
            model,
            body_poses,
            plane_frame,
            plane_tolerance_m=plane_tolerance_m,
            angular_tolerance_rad=angular_tolerance_rad,
        )
        generated_jacobian = build_joint_constraint_jacobian(
            generated,
            body_poses,
            coordinate_values,
            method=jacobian_method,
            finite_difference_step=finite_difference_step,
        )
        reduced = _build_planar_constraint_jacobian(
            generated_jacobian,
            model,
            plane_frame,
            ground_link_id=ground_link_id,
            configuration_id=configuration_id,
            jacobian_method=jacobian_method,
            finite_difference_step=finite_difference_step,
        )
        return analyze_mechanism_mobility(
            model,
            formulation,
            reduced,
            ground_link_id=ground_link_id,
            reference_constraint_rank=reference_constraint_rank,
            rank_tolerance=rank_tolerance,
        )

    if plane_frame is not None:
        raise InvalidModelError("plane_frame is only valid for PLANAR mobility analysis")
    nominal = estimate_nominal_mobility(
        model, formulation, ground_link_id=ground_link_id
    )
    generated = generate_joint_constraints(model)
    generated_jacobian = build_joint_constraint_jacobian(
        generated,
        body_poses,
        coordinate_values,
        method=jacobian_method,
        finite_difference_step=finite_difference_step,
    )

    selected_indices: list[int] = []
    selected_ids: list[str] = []
    joint_coordinate_ids: list[str] = []
    for index, column in enumerate(generated_jacobian.columns):
        variable = column.variable
        if variable.variable_kind == "GENERALIZED_COORDINATE":
            selected_indices.append(index)
            selected_ids.append(variable.variable_id)
            joint_coordinate_ids.append(variable.variable_id)
        elif (
            variable.variable_kind in ("BODY_POSE_TRANSLATION", "BODY_POSE_ROTATION")
            and variable.owner_id != ground_link_id
        ):
            selected_indices.append(index)
            selected_ids.append(variable.variable_id)

    expected_body_variables = nominal.free_body_dof
    expected_joint_variables = len(model.generalized_coordinates)
    if len(selected_ids) != expected_body_variables + expected_joint_variables:
        raise InvalidModelError(
            "Generated Jacobian does not cover the expected free-body and joint-coordinate variables"
        )

    reduced = ConstraintJacobian(
        generated_jacobian.row_ids,
        tuple(selected_ids),
        tuple(
            tuple(row[index] for index in selected_indices)
            for row in generated_jacobian.values
        ),
        configuration_id,
        (
            "generated-joint-pose-residuals:"
            + jacobian_method.value
            + f":step={finite_difference_step:g}"
        ),
        tuple(joint_coordinate_ids),
    )
    return analyze_mechanism_mobility(
        model,
        formulation,
        reduced,
        ground_link_id=ground_link_id,
        reference_constraint_rank=reference_constraint_rank,
        rank_tolerance=rank_tolerance,
    )
