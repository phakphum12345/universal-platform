import pytest

from universal_platform.engineering.mechanism_model import (
    FrameReference, GeometryKind, GeometryReference, JointKind, JointModel,
    LinkModel, MechanismModel, SolverCapability, validate_mechanism_model,
)


def model(**changes):
    values = dict(
        model_id="mechanism/demo",
        revision="r1",
        links=(
            LinkModel("ground", "p1", "frame/ground", ("geom/ground",)),
            LinkModel("crank", "p1", "frame/crank"),
        ),
        joints=(
            JointModel("joint/rev", JointKind.REVOLUTE, "ground", "crank",
                       "frame/joint", (0.0, 0.0, 1.0), "rad", -1.0, 1.0),
        ),
        frames=(
            FrameReference("frame/world"),
            FrameReference("frame/ground", "frame/world", "ground"),
            FrameReference("frame/crank", "frame/world", "crank"),
            FrameReference("frame/joint", "frame/world"),
        ),
        geometry=(
            GeometryReference("geom/ground", "ground", "frame/ground", GeometryKind.ANALYTIC),
        ),
    )
    values.update(changes)
    return MechanismModel(**values)


def test_normalized_model_validates_and_reports_counts():
    result = validate_mechanism_model(model())
    assert result.valid
    assert result.errors == ()
    assert (result.link_count, result.joint_count, result.frame_count, result.geometry_count) == (2, 1, 4, 1)


@pytest.mark.parametrize("kind,dof", [
    (JointKind.FIXED, 0), (JointKind.REVOLUTE, 1), (JointKind.PRISMATIC, 1),
    (JointKind.CYLINDRICAL, 2), (JointKind.HELICAL, 1), (JointKind.SPHERICAL, 3),
    (JointKind.PLANAR, 3), (JointKind.UNIVERSAL, 2),
])
def test_joint_nominal_dof_is_schema_bookkeeping_only(kind, dof):
    joint = JointModel("j", kind, "a", "b", "f",
                       (0.0, 0.0, 1.0) if kind in {
                           JointKind.REVOLUTE, JointKind.PRISMATIC,
                           JointKind.CYLINDRICAL, JointKind.HELICAL
                       } else None)
    assert joint.nominal_dof == dof
    assert joint.solver_capability is SolverCapability.SCHEMA_ONLY


def test_rejects_duplicate_and_dangling_ids():
    bad = model(links=(
        LinkModel("ground", "p1", "missing-frame"),
        LinkModel("ground", "p2", "missing-frame"),
    ))
    result = validate_mechanism_model(bad)
    assert not result.valid
    assert any("Duplicate link" in error for error in result.errors)
    assert any("unknown frame" in error for error in result.errors)


def test_rejects_frame_cycles():
    frames = (
        FrameReference("a", "b"),
        FrameReference("b", "a"),
        FrameReference("frame/ground", owner_link_id="ground"),
        FrameReference("frame/crank", owner_link_id="crank"),
        FrameReference("frame/joint"),
    )
    result = validate_mechanism_model(model(frames=frames))
    assert not result.valid
    assert any("cycle" in error for error in result.errors)


def test_rejects_non_unit_joint_axis_and_bad_limits():
    joint = JointModel("j", JointKind.REVOLUTE, "ground", "crank",
                       "frame/joint", (0.0, 0.0, 2.0), "rad", 2.0, 1.0)
    result = validate_mechanism_model(model(joints=(joint,)))
    assert not result.valid
    assert any("normalized" in error for error in result.errors)
    assert any("inverted" in error for error in result.errors)


def test_rejects_wrong_coordinate_units():
    joint = JointModel("j", JointKind.PRISMATIC, "ground", "crank",
                       "frame/joint", (1.0, 0.0, 0.0), "rad")
    result = validate_mechanism_model(model(joints=(joint,)))
    assert not result.valid
    assert any("translational coordinate" in error for error in result.errors)


def test_external_geometry_requires_explicit_reference():
    geometry = GeometryReference("external", "ground", "frame/ground", GeometryKind.EXTERNAL)
    result = validate_mechanism_model(model(geometry=(geometry,)))
    assert not result.valid
    assert any("external_ref" in error for error in result.errors)


def test_rejects_unknown_schema_version():
    result = validate_mechanism_model(model(schema_version="2.0"))
    assert not result.valid
    assert any("schema_version" in error for error in result.errors)
