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
from typing import Sequence

from .errors import InvalidModelError
from .mechanism_model import (
    JointKind,
    MechanismModel,
    validate_mechanism_model,
)
from .nonlinear_solver import (
    JacobianRankDiagnostics,
    _estimate_jacobian_rank,
)


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

    Rows are scalar constraint equations; columns are free-body generalized
    coordinates. The caller owns coordinate ordering, units, scaling and the
    derivation of the matrix. The matrix is not synthesized from JointModel
    metadata because the normalized schema lacks complete joint placements.
    """

    constraint_ids: tuple[str, ...]
    coordinate_ids: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    configuration_id: str
    source: str


@dataclass(frozen=True, slots=True)
class NominalMobilityEstimate:
    formulation: MobilityFormulation
    body_dimension: int
    link_count: int
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
                "free_body_dof": self.nominal.free_body_dof,
                "nominal_joint_constraints": self.nominal.nominal_joint_constraints,
                "estimated_dof": self.nominal.estimated_dof,
                "joint_dof_counts": dict(self.nominal.joint_dof_counts),
                "formula": self.nominal.formula,
            },
            "local": {
                "constraint_count": self.jacobian_rank.row_count,
                "coordinate_count": self.jacobian_rank.column_count,
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
    reference_constraint_rank: int | None = None,
    rank_tolerance: float = 1e-10,
) -> MobilityAnalysisResult:
    """Compare nominal DOF with local Jacobian mobility at one configuration.

    The local estimate is coordinate_count - estimated_rank(J). A supplied
    reference rank represents the expected regular-configuration rank for the
    same constraint system. A lower local rank is flagged as a *possible*
    singularity, never as a proof of one.
    """
    nominal = estimate_nominal_mobility(model, formulation)
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
    if len(jacobian.values) != len(jacobian.constraint_ids):
        raise InvalidModelError("Jacobian row count must match constraint identifiers")
    if any(len(row) != len(jacobian.coordinate_ids) for row in jacobian.values):
        raise InvalidModelError("Jacobian column count must match coordinate identifiers")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)
        for row in jacobian.values for value in row
    ):
        raise InvalidModelError("Jacobian values must be finite numbers (not booleans)")
    if not isfinite(rank_tolerance) or rank_tolerance <= 0.0:
        raise InvalidModelError("rank_tolerance must be finite and positive")

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
        else:
            singularity = SingularityStatus.NOT_DETECTED

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
        limitations=(
            "Nominal DOF assumes ideal lower pairs and independent joint constraints; higher pairs are not modeled.",
            "Local mobility is an estimate from a caller-supplied Jacobian at one configuration; rank depends on scaling and tolerance.",
            "The normalized mechanism schema does not yet generate geometric joint equations or Jacobians automatically.",
            "Redundant Jacobian rows are reported separately and do not alone prove physical overconstraint.",
            "A possible singularity requires an explicit regular-configuration reference rank; absence of a flag is not a proof of regularity.",
            "No collision/contact, dynamics, physical feasibility, safety certification or fabrication validation is performed.",
        ),
    )
