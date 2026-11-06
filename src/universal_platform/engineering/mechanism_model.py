"""Normalized, stable-ID mechanism model contracts.

These records describe mechanism topology and references; they do not imply
that every joint type is supported by a kinematics or constraint solver.
Validation is structural and deliberately separate from solver capability.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite, sqrt

from .transforms import RigidTransform


SCHEMA_VERSION = "1.1"
SUPPORTED_SCHEMA_VERSIONS = ("1.0", "1.1")


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
class GeometryPlacement:
    """Rigid placement from a geometry-local frame into its reference frame.

    Translation components use metres. The transform's source frame is the
    geometry-local frame and its destination is GeometryReference.frame_id.
    """

    geometry_id: str
    geometry_to_frame: RigidTransform
    length_unit: str = "m"

    def to_dict(self) -> dict[str, object]:
        return {
            "geometry_id": self.geometry_id,
            "geometry_to_frame": _transform_to_dict(self.geometry_to_frame),
            "length_unit": self.length_unit,
        }


@dataclass(frozen=True, slots=True)
class JointFramePlacement:
    """Static parent-link→joint and joint→child-link frame placements.

    Both transforms map source-frame coordinates into destination-frame
    coordinates. Translation components use metres. The joint frame is the
    exact JointModel.frame_id; motion is not applied by this record.
    """

    joint_id: str
    parent_to_joint: RigidTransform
    joint_to_child: RigidTransform
    length_unit: str = "m"

    def to_dict(self) -> dict[str, object]:
        return {
            "joint_id": self.joint_id,
            "parent_to_joint": _transform_to_dict(self.parent_to_joint),
            "joint_to_child": _transform_to_dict(self.joint_to_child),
            "length_unit": self.length_unit,
        }


def _transform_to_dict(transform: RigidTransform) -> dict[str, object]:
    return {
        "from_frame": transform.from_frame,
        "to_frame": transform.to_frame,
        "rotation": [list(row) for row in transform.rotation],
        "translation_m": [
            transform.translation.x,
            transform.translation.y,
            transform.translation.z,
        ],
    }


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
    joint_placements: tuple[JointFramePlacement, ...] = ()
    geometry_placements: tuple[GeometryPlacement, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelValidationResult:
    valid: bool
    errors: tuple[str, ...]
    link_count: int
    joint_count: int
    frame_count: int
    geometry_count: int
    joint_placement_count: int = 0
    geometry_placement_count: int = 0
    joints_without_placement: tuple[str, ...] = ()
    geometry_without_placement: tuple[str, ...] = ()


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
    if model.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"Unsupported mechanism schema_version: {model.schema_version!r}")
    if model.schema_version == "1.0" and (
        model.joint_placements or model.geometry_placements
    ):
        errors.append("Placement records require mechanism schema_version '1.1'")

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
    joint_placement_ids = unique_ids(
        model.joint_placements, "joint_id", "joint placement"
    )
    geometry_placement_ids = unique_ids(
        model.geometry_placements, "geometry_id", "geometry placement"
    )
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

    joint_by_id = {item.joint_id: item for item in model.joints}
    link_by_id = {item.link_id: item for item in model.links}

    for placement in model.geometry_placements:
        geometry = geometry_by_id.get(placement.geometry_id)
        if geometry is None:
            errors.append(
                f"Geometry placement {placement.geometry_id!r} references unknown geometry"
            )
            continue
        transform = placement.geometry_to_frame
        if not isinstance(transform, RigidTransform):
            errors.append(
                f"Geometry placement {placement.geometry_id!r} requires a RigidTransform"
            )
            continue
        if transform.from_frame not in frame_ids:
            errors.append(
                f"Geometry placement {placement.geometry_id!r} references unknown local frame"
            )
        if transform.to_frame != geometry.frame_id:
            errors.append(
                f"Geometry placement {placement.geometry_id!r} destination frame must match "
                f"geometry reference frame {geometry.frame_id!r}"
            )
        local_frame = frame_by_id.get(transform.from_frame)
        if local_frame is not None and local_frame.owner_link_id not in (
            None, geometry.owner_link_id
        ):
            errors.append(
                f"Geometry placement {placement.geometry_id!r} local frame is owned by another link"
            )
        if placement.length_unit != "m":
            errors.append(
                f"Geometry placement {placement.geometry_id!r} length_unit must be 'm'"
            )

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

    for placement in model.joint_placements:
        joint = joint_by_id.get(placement.joint_id)
        if joint is None:
            errors.append(
                f"Joint placement {placement.joint_id!r} references unknown joint"
            )
            continue
        parent = link_by_id.get(joint.parent_link_id)
        child = link_by_id.get(joint.child_link_id)
        if parent is None or child is None:
            continue
        parent_transform = placement.parent_to_joint
        child_transform = placement.joint_to_child
        if not isinstance(parent_transform, RigidTransform):
            errors.append(
                f"Joint placement {placement.joint_id!r} parent_to_joint must be a RigidTransform"
            )
        else:
            if parent_transform.from_frame != parent.frame_id:
                errors.append(
                    f"Joint placement {placement.joint_id!r} parent source frame must match "
                    f"link frame {parent.frame_id!r}"
                )
            if parent_transform.to_frame != joint.frame_id:
                errors.append(
                    f"Joint placement {placement.joint_id!r} parent destination frame must match "
                    f"joint frame {joint.frame_id!r}"
                )
        if not isinstance(child_transform, RigidTransform):
            errors.append(
                f"Joint placement {placement.joint_id!r} joint_to_child must be a RigidTransform"
            )
        else:
            if child_transform.from_frame != joint.frame_id:
                errors.append(
                    f"Joint placement {placement.joint_id!r} child source frame must match "
                    f"joint frame {joint.frame_id!r}"
                )
            if child_transform.to_frame != child.frame_id:
                errors.append(
                    f"Joint placement {placement.joint_id!r} child destination frame must match "
                    f"link frame {child.frame_id!r}"
                )
        if placement.length_unit != "m":
            errors.append(
                f"Joint placement {placement.joint_id!r} length_unit must be 'm'"
            )

    placed_joint_ids = {item.joint_id for item in model.joint_placements}
    placed_geometry_ids = {item.geometry_id for item in model.geometry_placements}
    return ModelValidationResult(
        valid=not errors,
        errors=tuple(errors),
        link_count=len(model.links),
        joint_count=len(model.joints),
        frame_count=len(model.frames),
        geometry_count=len(model.geometry),
        joint_placement_count=len(model.joint_placements),
        geometry_placement_count=len(model.geometry_placements),
        joints_without_placement=tuple(
            item.joint_id for item in model.joints if item.joint_id not in placed_joint_ids
        ),
        geometry_without_placement=tuple(
            item.geometry_id for item in model.geometry
            if item.geometry_id not in placed_geometry_ids
        ),
    )
