"""Normalized, stable-ID mechanism model contracts.

These records describe mechanism topology and references; they do not imply
that every joint type is supported by a kinematics or constraint solver.
Validation is structural and deliberately separate from solver capability.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite, sqrt


SCHEMA_VERSION = "1.0"


class JointKind(str, Enum):
    FIXED = "FIXED"
    REVOLUTE = "REVOLUTE"
    PRISMATIC = "PRISMATIC"
    CYLINDRICAL = "CYLINDRICAL"
    HELICAL = "HELICAL"
    SPHERICAL = "SPHERICAL"
    PLANAR = "PLANAR"
    UNIVERSAL = "UNIVERSAL"


class GeometryKind(str, Enum):
    ANALYTIC = "ANALYTIC"
    MESH = "MESH"
    CAD_REFERENCE = "CAD_REFERENCE"
    EXTERNAL = "EXTERNAL"


class SolverCapability(str, Enum):
    SCHEMA_ONLY = "SCHEMA_ONLY"
    PLANAR_4R_ADAPTER = "PLANAR_4R_ADAPTER"


@dataclass(frozen=True, slots=True)
class FrameReference:
    """Named coordinate frame and its optional parent in the model frame forest."""

    frame_id: str
    parent_frame_id: str | None = None
    owner_link_id: str | None = None


@dataclass(frozen=True, slots=True)
class GeometryReference:
    """Stable reference to geometry owned by a link and expressed in a frame."""

    geometry_id: str
    owner_link_id: str
    frame_id: str
    geometry_kind: GeometryKind
    external_ref: str | None = None


@dataclass(frozen=True, slots=True)
class LinkModel:
    """Rigid-link identity plus references to its body frame and geometry."""

    link_id: str
    revision: str
    frame_id: str
    geometry_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class JointModel:
    """Joint topology and coordinate metadata between two distinct links.

    Axis components are expressed in the declared joint frame and must be
    finite and unit length when supplied. Limits use radians for rotational
    coordinates and metres for translational coordinates; this schema does
    not infer mixed-coordinate conventions for coupled joints.
    """

    joint_id: str
    joint_kind: JointKind
    parent_link_id: str
    child_link_id: str
    frame_id: str
    axis: tuple[float, float, float] | None = None
    coordinate_unit: str | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None

    @property
    def nominal_dof(self) -> int:
        """Nominal relative DOF for bookkeeping, not assembled mobility."""
        return {
            JointKind.FIXED: 0,
            JointKind.REVOLUTE: 1,
            JointKind.PRISMATIC: 1,
            JointKind.CYLINDRICAL: 2,
            JointKind.HELICAL: 1,
            JointKind.SPHERICAL: 3,
            JointKind.PLANAR: 3,
            JointKind.UNIVERSAL: 2,
        }[self.joint_kind]

    @property
    def solver_capability(self) -> SolverCapability:
        """Schema presence never implies general solver support."""
        return SolverCapability.SCHEMA_ONLY


@dataclass(frozen=True, slots=True)
class MechanismModel:
    """Versioned mechanism topology with stable link, joint and frame IDs."""

    model_id: str
    revision: str
    links: tuple[LinkModel, ...]
    joints: tuple[JointModel, ...]
    frames: tuple[FrameReference, ...]
    geometry: tuple[GeometryReference, ...] = ()
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class ModelValidationResult:
    valid: bool
    errors: tuple[str, ...]
    link_count: int
    joint_count: int
    frame_count: int
    geometry_count: int


def validate_mechanism_model(model: MechanismModel) -> ModelValidationResult:
    """Validate stable IDs, topology and frame/geometry references."""
    if not isinstance(model, MechanismModel):
        raise TypeError("model must be a MechanismModel")

    errors: list[str] = []
    def required(value: str, label: str) -> None:
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label} must be a non-empty string")

    required(model.model_id, "model_id")
    required(model.revision, "revision")
    required(model.schema_version, "schema_version")
    if model.schema_version != SCHEMA_VERSION:
        errors.append(f"Unsupported mechanism schema_version: {model.schema_version!r}")

    def unique_ids(items: tuple, attribute: str, label: str) -> set[str]:
        values = [getattr(item, attribute) for item in items]
        for value in values:
            required(value, f"{label} identifier")
        if len(values) != len(set(values)):
            errors.append(f"Duplicate {label} identifier")
        return {value for value in values if isinstance(value, str) and value.strip()}

    link_ids = unique_ids(model.links, "link_id", "link")
    joint_ids = unique_ids(model.joints, "joint_id", "joint")
    frame_ids = unique_ids(model.frames, "frame_id", "frame")
    geometry_ids = unique_ids(model.geometry, "geometry_id", "geometry")
    geometry_by_id = {item.geometry_id: item for item in model.geometry}
    frame_by_id = {item.frame_id: item for item in model.frames}

    for link in model.links:
        required(link.revision, f"Link {link.link_id!r} revision")
        if link.frame_id not in frame_ids:
            errors.append(f"Link {link.link_id!r} references unknown frame {link.frame_id!r}")
        elif frame_by_id[link.frame_id].owner_link_id not in (None, link.link_id):
            errors.append(f"Link {link.link_id!r} body frame is owned by another link")
        if len(link.geometry_ids) != len(set(link.geometry_ids)):
            errors.append(f"Link {link.link_id!r} has duplicate geometry references")
        for geometry_id in link.geometry_ids:
            if geometry_id not in geometry_ids:
                errors.append(f"Link {link.link_id!r} references unknown geometry {geometry_id!r}")
            elif geometry_by_id[geometry_id].owner_link_id != link.link_id:
                errors.append(f"Link {link.link_id!r} references geometry owned by another link")

    for frame in model.frames:
        if frame.parent_frame_id is not None and frame.parent_frame_id not in frame_ids:
            errors.append(f"Frame {frame.frame_id!r} references unknown parent frame")
        if frame.owner_link_id is not None and frame.owner_link_id not in link_ids:
            errors.append(f"Frame {frame.frame_id!r} references unknown owner link")

    # A frame-parent cycle makes frame ancestry ambiguous.
    parents = {item.frame_id: item.parent_frame_id for item in model.frames}
    for start in parents:
        seen: set[str] = set()
        current: str | None = start
        while current is not None and current in parents:
            if current in seen:
                errors.append(f"Frame parent cycle includes {start!r}")
                break
            seen.add(current)
            current = parents[current]

    for geometry in model.geometry:
        if geometry.owner_link_id not in link_ids:
            errors.append(f"Geometry {geometry.geometry_id!r} references unknown owner link")
        if geometry.frame_id not in frame_ids:
            errors.append(f"Geometry {geometry.geometry_id!r} references unknown frame")
        if not isinstance(geometry.geometry_kind, GeometryKind):
            errors.append(f"Geometry {geometry.geometry_id!r} has unsupported geometry kind")
        if geometry.geometry_kind in (GeometryKind.CAD_REFERENCE, GeometryKind.EXTERNAL):
            required(geometry.external_ref or "", f"Geometry {geometry.geometry_id!r} external_ref")

    for joint in model.joints:
        if not isinstance(joint.joint_kind, JointKind):
            errors.append(f"Joint {joint.joint_id!r} has unsupported joint kind")
            continue
        if joint.parent_link_id not in link_ids or joint.child_link_id not in link_ids:
            errors.append(f"Joint {joint.joint_id!r} references unknown link")
        if joint.parent_link_id == joint.child_link_id:
            errors.append(f"Joint {joint.joint_id!r} cannot connect a link to itself")
        if joint.frame_id not in frame_ids:
            errors.append(f"Joint {joint.joint_id!r} references unknown frame")
        if joint.joint_kind in (JointKind.REVOLUTE, JointKind.PRISMATIC,
                                JointKind.CYLINDRICAL, JointKind.HELICAL) and joint.axis is None:
            errors.append(f"Joint {joint.joint_id!r} requires an axis")
        if joint.axis is not None:
            if (len(joint.axis) != 3 or
                    any(not isinstance(v, (int, float)) or isinstance(v, bool) or not isfinite(v)
                        for v in joint.axis)):
                errors.append(f"Joint {joint.joint_id!r} axis must contain three finite numbers")
            else:
                magnitude = sqrt(sum(float(v) ** 2 for v in joint.axis))
                if magnitude <= 1e-12 or abs(magnitude - 1.0) > 1e-9:
                    errors.append(f"Joint {joint.joint_id!r} axis must be normalized to unit length")
        for label, value in (("lower", joint.lower_limit), ("upper", joint.upper_limit)):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                      or not isfinite(value)):
                errors.append(f"Joint {joint.joint_id!r} {label} limit must be finite")
        if (joint.lower_limit is not None and joint.upper_limit is not None
                and isinstance(joint.lower_limit, (int, float))
                and isinstance(joint.upper_limit, (int, float))
                and isfinite(joint.lower_limit) and isfinite(joint.upper_limit)
                and joint.lower_limit > joint.upper_limit):
            errors.append(f"Joint {joint.joint_id!r} has inverted limits")
        if joint.coordinate_unit not in (None, "rad", "m"):
            errors.append(f"Joint {joint.joint_id!r} coordinate_unit must be 'rad', 'm', or None")
        if joint.joint_kind in (JointKind.REVOLUTE, JointKind.HELICAL) and joint.coordinate_unit not in (None, "rad"):
            errors.append(f"Joint {joint.joint_id!r} rotational coordinate must use radians")
        if joint.joint_kind is JointKind.PRISMATIC and joint.coordinate_unit not in (None, "m"):
            errors.append(f"Joint {joint.joint_id!r} translational coordinate must use metres")

    return ModelValidationResult(
        valid=not errors,
        errors=tuple(errors),
        link_count=len(model.links),
        joint_count=len(model.joints),
        frame_count=len(model.frames),
        geometry_count=len(model.geometry),
    )
