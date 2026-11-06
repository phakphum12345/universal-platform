"""Stable-ID model adapter for one planar four-revolute (4R) mechanism.

This adapter validates a versioned, unit-aware model snapshot and maps the
existing analytic circle-intersection result back to stable model identifiers.
It is intentionally limited to one planar four-bar loop.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from .errors import InvalidModelError
from .planar_mechanisms import PlanarFourBarResult, solve_planar_four_bar_loop
from .provenance import EvidenceKind, EvidenceRecord, EvidenceStatus
from .quantity import LENGTH, Quantity

AssemblyBranch = Literal["left", "right"]


@dataclass(frozen=True, slots=True)
class PlanarFourBarModelSnapshot:
    """Immutable input snapshot; lengths and tolerance must be length quantities."""

    model_id: str
    model_revision: str
    ground_link_id: str
    input_link_id: str
    coupler_link_id: str
    output_link_id: str
    input_ground_joint_id: str
    input_coupler_joint_id: str
    coupler_output_joint_id: str
    output_ground_joint_id: str
    ground_length: Quantity
    input_crank_length: Quantity
    coupler_length: Quantity
    output_rocker_length: Quantity
    input_angle_rad: float
    branch: AssemblyBranch = "left"
    tolerance: Quantity = Quantity(1e-9, LENGTH, "m")


@dataclass(frozen=True, slots=True)
class PlanarFourBarAdapterResult:
    """Solved planar 4R snapshot mapped to stable link and joint identifiers."""

    schema_version: str
    model_id: str
    model_revision: str
    branch: AssemblyBranch
    geometry: PlanarFourBarResult
    joint_positions_m: tuple[tuple[str, tuple[float, float]], ...]
    link_angles_rad: tuple[tuple[str, float], ...]
    residuals_m: tuple[tuple[str, float], ...]
    evidence: EvidenceRecord

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible adapter result snapshot."""
        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "branch": self.branch,
            "joint_positions_m": {
                key: {"x": value[0], "y": value[1]}
                for key, value in self.joint_positions_m
            },
            "link_angles_rad": dict(self.link_angles_rad),
            "residuals_m": dict(self.residuals_m),
            "closure_error_m": self.geometry.closure_error,
            "evidence": {
                "kind": self.evidence.kind.value,
                "status": self.evidence.status.value,
                "statement": self.evidence.statement,
                "method": self.evidence.method,
                "limitations": list(self.evidence.limitations),
            },
            "limitations": [
                "One planar four-link/four-revolute loop only",
                "Analytic circle-intersection geometry; no general assembly solver",
                "No dynamics, collision/contact, physical feasibility or certification",
            ],
        }


def solve_planar_four_bar_model(
    snapshot: PlanarFourBarModelSnapshot,
) -> PlanarFourBarAdapterResult:
    """Validate and solve one stable-ID, unit-aware planar 4R model snapshot.

    Length quantities are converted to SI metres before the geometric solve.
    Input angle is radians. IDs and output ordering are deterministic.
    """
    if not isinstance(snapshot, PlanarFourBarModelSnapshot):
        raise InvalidModelError("snapshot must be PlanarFourBarModelSnapshot")

    identity_values = (
        snapshot.model_id,
        snapshot.model_revision,
        snapshot.ground_link_id,
        snapshot.input_link_id,
        snapshot.coupler_link_id,
        snapshot.output_link_id,
        snapshot.input_ground_joint_id,
        snapshot.input_coupler_joint_id,
        snapshot.coupler_output_joint_id,
        snapshot.output_ground_joint_id,
    )
    if any(not isinstance(value, str) or not value.strip() for value in identity_values):
        raise InvalidModelError("Model, revision, link and joint identifiers must be non-empty")

    link_ids = (
        snapshot.ground_link_id,
        snapshot.input_link_id,
        snapshot.coupler_link_id,
        snapshot.output_link_id,
    )
    joint_ids = (
        snapshot.input_ground_joint_id,
        snapshot.input_coupler_joint_id,
        snapshot.coupler_output_joint_id,
        snapshot.output_ground_joint_id,
    )
    if len(set(link_ids)) != 4:
        raise InvalidModelError("Four-bar link identifiers must be unique")
    if len(set(joint_ids)) != 4:
        raise InvalidModelError("Four-bar joint identifiers must be unique")

    quantities = (
        snapshot.ground_length,
        snapshot.input_crank_length,
        snapshot.coupler_length,
        snapshot.output_rocker_length,
        snapshot.tolerance,
    )
    if any(not isinstance(value, Quantity) for value in quantities):
        raise InvalidModelError("All four link lengths and tolerance must be Quantity values")
    if any(value.dimension != LENGTH for value in quantities):
        raise InvalidModelError("Four-bar lengths and tolerance must have LENGTH dimension")

    lengths_m = tuple(value.in_unit("m") for value in quantities)
    if any(not isfinite(value) or value <= 0.0 for value in lengths_m):
        raise InvalidModelError("Four-bar lengths and tolerance must be finite and positive")
    if not isinstance(snapshot.input_angle_rad, (int, float)) or not isfinite(snapshot.input_angle_rad):
        raise InvalidModelError("Input angle must be finite radians")
    if snapshot.branch not in ("left", "right"):
        raise InvalidModelError("Branch must be 'left' or 'right'")

    geometry = solve_planar_four_bar_loop(
        *lengths_m[:4],
        float(snapshot.input_angle_rad),
        branch=snapshot.branch,
        tolerance=lengths_m[4],
    )

    positions = (
        (snapshot.input_ground_joint_id, (0.0, 0.0)),
        (snapshot.input_coupler_joint_id, (geometry.input_joint_x, geometry.input_joint_y)),
        (snapshot.coupler_output_joint_id, (geometry.coupler_joint_x, geometry.coupler_joint_y)),
        (snapshot.output_ground_joint_id, (lengths_m[0], 0.0)),
    )
    angles = (
        (snapshot.input_link_id, float(snapshot.input_angle_rad)),
        (snapshot.coupler_link_id, geometry.coupler_angle_rad),
        (snapshot.output_link_id, geometry.output_angle_rad),
    )
    residuals = (
        (f"link/{snapshot.input_link_id}/length", 0.0),
        (f"link/{snapshot.coupler_link_id}/length", abs(
            ((geometry.coupler_joint_x - geometry.input_joint_x) ** 2
             + (geometry.coupler_joint_y - geometry.input_joint_y) ** 2) ** 0.5
            - lengths_m[2]
        )),
        (f"link/{snapshot.output_link_id}/length", abs(
            ((geometry.coupler_joint_x - lengths_m[0]) ** 2
             + geometry.coupler_joint_y ** 2) ** 0.5
            - lengths_m[3]
        )),
    )
    evidence = EvidenceRecord(
        kind=EvidenceKind.SIMULATION,
        status=EvidenceStatus.PASS,
        statement="Planar four-bar geometric closure residuals satisfy the declared SI tolerance",
        method="analytic-circle-intersection; SI-normalized-lengths",
        limitations=(
            "Numerical geometric closure only; not proof of physical feasibility",
            "Single planar 4R loop; no arbitrary topology or 3D constraints",
        ),
        metadata={
            "model_id": snapshot.model_id,
            "model_revision": snapshot.model_revision,
            "branch": snapshot.branch,
            "tolerance_m": lengths_m[4],
        },
    )
    return PlanarFourBarAdapterResult(
        schema_version="1.0",
        model_id=snapshot.model_id,
        model_revision=snapshot.model_revision,
        branch=snapshot.branch,
        geometry=geometry,
        joint_positions_m=positions,
        link_angles_rad=angles,
        residuals_m=residuals,
        evidence=evidence,
    )
