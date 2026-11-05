import math

import pytest

from universal_platform.engineering.assembly import Assembly, Joint, JointType, PartOccurrence
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.kinematics import JointPlacement, solve_tree_forward_kinematics
from universal_platform.engineering.transforms import RigidTransform


def occurrence(name):
    return PartOccurrence(name, "part-" + name, "r1")


def placement(joint_id, parent="base", child="arm"):
    return JointPlacement(
        joint_id,
        RigidTransform(parent, "joint-" + joint_id),
        RigidTransform("joint-" + joint_id, child),
    )


def make_assembly(joint_type=JointType.REVOLUTE, lower=-math.pi, upper=math.pi):
    joint = Joint(
        "j1", "base", "arm", joint_type,
        Vec3(0.0, 0.0, 1.0) if joint_type in (JointType.REVOLUTE, JointType.PRISMATIC) else None,
        lower, upper,
    )
    return Assembly("assembly", (occurrence("base"), occurrence("arm")), (joint,))


def test_revolute_forward_kinematics_rotates_child_pose_about_joint_axis():
    assembly = make_assembly()
    poses = solve_tree_forward_kinematics(
        assembly, "base", {"j1": placement("j1")}, {"j1": math.pi / 2}
    )
    rotated = poses["arm"].apply_vector(Vec3(1.0, 0.0, 0.0))
    assert rotated.x == pytest.approx(0.0, abs=1e-9)
    assert rotated.y == pytest.approx(1.0, abs=1e-9)
    assert rotated.z == pytest.approx(0.0, abs=1e-9)


def test_prismatic_forward_kinematics_translates_child_pose():
    assembly = make_assembly(JointType.PRISMATIC, -10.0, 10.0)
    poses = solve_tree_forward_kinematics(
        assembly, "base", {"j1": placement("j1")}, {"j1": 2.5}
    )
    assert poses["arm"].apply_point(Vec3(0.0, 0.0, 0.0)) == Vec3(0.0, 0.0, 2.5)


def test_fixed_joint_keeps_static_child_pose():
    assembly = make_assembly(JointType.FIXED)
    poses = solve_tree_forward_kinematics(
        assembly, "base", {"j1": placement("j1")}
    )
    assert poses["arm"].apply_point(Vec3(1.0, 2.0, 3.0)) == Vec3(1.0, 2.0, 3.0)


def test_fixed_joint_rejects_nonzero_coordinate():
    assembly = make_assembly(JointType.FIXED)
    with pytest.raises(InvalidModelError, match="cannot move"):
        solve_tree_forward_kinematics(
            assembly, "base", {"j1": placement("j1")}, {"j1": 0.1}
        )


def test_rejects_coordinate_outside_joint_limits():
    assembly = make_assembly(JointType.REVOLUTE, -1.0, 1.0)
    with pytest.raises(InvalidModelError, match="above its upper limit"):
        solve_tree_forward_kinematics(
            assembly, "base", {"j1": placement("j1")}, {"j1": 1.1}
        )


def test_rejects_non_finite_joint_coordinate():
    assembly = make_assembly()
    with pytest.raises(InvalidModelError, match="must be finite"):
        solve_tree_forward_kinematics(
            assembly, "base", {"j1": placement("j1")}, {"j1": float("nan")}
        )


def test_rejects_missing_or_extra_joint_placements():
    assembly = make_assembly()
    with pytest.raises(InvalidModelError, match="placement mismatch"):
        solve_tree_forward_kinematics(assembly, "base", {}, {})


def test_rejects_unknown_joint_coordinate_key():
    assembly = make_assembly()
    with pytest.raises(InvalidModelError, match="Unknown joint coordinates"):
        solve_tree_forward_kinematics(
            assembly, "base", {"j1": placement("j1")}, {"not-a-joint": 0.0}
        )


def test_rejects_unsupported_joint_type():
    assembly = make_assembly(JointType.SPHERICAL)
    with pytest.raises(InvalidModelError, match="not supported"):
        solve_tree_forward_kinematics(
            assembly, "base", {"j1": placement("j1")}, {"j1": 0.0}
        )


def test_rejects_placement_frame_mismatch():
    assembly = make_assembly()
    bad = JointPlacement(
        "j1", RigidTransform("wrong-parent", "joint-j1"),
        RigidTransform("joint-j1", "arm"),
    )
    with pytest.raises(InvalidModelError, match="parent placement frame mismatch"):
        solve_tree_forward_kinematics(assembly, "base", {"j1": bad}, {"j1": 0.0})


def test_rejects_unknown_root_and_disconnected_occurrence():
    assembly = Assembly("assembly", (occurrence("base"), occurrence("arm")), ())
    with pytest.raises(InvalidModelError, match="Unknown root occurrence"):
        solve_tree_forward_kinematics(assembly, "missing", {}, {})
    with pytest.raises(InvalidModelError, match="disconnected from root"):
        solve_tree_forward_kinematics(assembly, "base", {}, {})


def test_rejects_cycle_that_includes_root():
    joints = (
        Joint("j1", "base", "arm", JointType.FIXED),
        Joint("j2", "arm", "base", JointType.FIXED),
    )
    assembly = Assembly("assembly", (occurrence("base"), occurrence("arm")), joints)
    placements = {
        "j1": placement("j1", "base", "arm"),
        "j2": placement("j2", "arm", "base"),
    }
    with pytest.raises(InvalidModelError, match="Root occurrence cannot have a parent"):
        solve_tree_forward_kinematics(assembly, "base", placements, {})
