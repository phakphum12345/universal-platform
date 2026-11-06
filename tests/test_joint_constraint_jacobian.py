import math

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.joint_constraints import generate_joint_constraints
from universal_platform.engineering.joint_jacobian import build_joint_constraint_jacobian
from universal_platform.engineering.mechanism_model import (
    CoordinateKind, FrameReference, GeneralizedCoordinate, JointCoordinateParameterization,
    JointFramePlacement, JointKind, JointModel, LinkModel, MechanismModel,
)
from universal_platform.engineering.nonlinear_solver import JacobianMethod
from universal_platform.engineering.transforms import RigidTransform


def model_for(kind, coords=(), parameterization=None):
    parent, child, joint = "frame/parent", "frame/child", "frame/joint"
    axis = (1.0,0.0,0.0) if kind is JointKind.PRISMATIC else (
        (0.0,0.0,1.0) if kind in (JointKind.REVOLUTE,JointKind.PRISMATIC,JointKind.CYLINDRICAL,JointKind.HELICAL) else None
    )
    model = MechanismModel(
        "model/jacobian", "r1",
        (LinkModel("link/parent","p1",parent),LinkModel("link/child","p1",child)),
        (JointModel("joint/main",kind,"link/parent","link/child",joint,axis),),
        (FrameReference(parent,owner_link_id="link/parent"),FrameReference(child,owner_link_id="link/child"),FrameReference(joint)),
        schema_version="1.2",
        joint_placements=(JointFramePlacement("joint/main",RigidTransform(parent,joint),RigidTransform(joint,child)),),
        generalized_coordinates=tuple(coords),
        joint_parameterizations=(() if parameterization is None else (parameterization,)),
    )
    return model


def coord(name, kind, axis, **kwargs):
    return GeneralizedCoordinate(name,kind,"rad" if kind is CoordinateKind.ROTATIONAL else "m",axis,**kwargs)


def param(*ids):
    return JointCoordinateParameterization("joint/main",tuple(ids))


def poses(child_rotation=None, child_translation=(0,0,0)):
    identity=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    return {
        "link/parent":RigidTransform("frame/parent","world"),
        "link/child":RigidTransform("frame/child","world",child_rotation or identity,Vec3(*child_translation)),
    }


def jac_value(jac, row_component, variable_id):
    row = next(i for i, name in enumerate(jac.row_ids) if name.endswith(row_component))
    column = next(i for i, item in enumerate(jac.columns) if item.variable.variable_id == variable_id)
    return jac.values[row][column]


def test_fixed_joint_jacobian_includes_body_pose_tangent_columns():
    generated = generate_joint_constraints(model_for(JointKind.FIXED))
    jac = build_joint_constraint_jacobian(generated, poses(), {})
    assert jac.shape == (6, 12)
    assert jac_value(jac,"translation_x","link/link/child/pose/translation_x") == pytest.approx(1.0)
    assert jac_value(jac,"translation_x","link/link/parent/pose/translation_x") == pytest.approx(-1.0)
    assert jac_value(jac,"rotation_z","link/link/child/pose/rotation_z") == pytest.approx(1.0)


def test_generalized_coordinate_jacobian_matches_revolute_and_prismatic_reference():
    revolute = model_for(JointKind.REVOLUTE,(coord("q/theta",CoordinateKind.ROTATIONAL,(0,0,1)),),param("q/theta"))
    jr = build_joint_constraint_jacobian(generate_joint_constraints(revolute),poses(),{"q/theta":0.2})
    assert jac_value(jr,"rotation_z","coordinate/q/theta") == pytest.approx(-1.0,abs=1e-6)
    prismatic = model_for(JointKind.PRISMATIC,(coord("q/x",CoordinateKind.TRANSLATIONAL,(1,0,0)),),param("q/x"))
    jp = build_joint_constraint_jacobian(generate_joint_constraints(prismatic),poses(),{"q/x":0.1})
    assert jac_value(jp,"translation_x","coordinate/q/x") == pytest.approx(-1.0,abs=1e-6)


def test_helical_coordinate_derivative_contains_pitch_coupling():
    model = model_for(
        JointKind.HELICAL,(coord("q/s",CoordinateKind.ROTATIONAL,(0,0,1)),),
        JointCoordinateParameterization("joint/main",("q/s",),pitch_m_per_rad=0.01),
    )
    jac = build_joint_constraint_jacobian(generate_joint_constraints(model),poses(),{"q/s":0.2})
    assert jac_value(jac,"rotation_z","coordinate/q/s") == pytest.approx(-1.0,abs=1e-6)
    assert jac_value(jac,"translation_z","coordinate/q/s") == pytest.approx(-0.01,abs=1e-6)


def test_central_and_forward_differences_agree_within_step_error():
    model = model_for(JointKind.REVOLUTE,(coord("q/t",CoordinateKind.ROTATIONAL,(0,0,1)),),param("q/t"))
    generated=generate_joint_constraints(model)
    central=build_joint_constraint_jacobian(generated,poses(),{"q/t":0.3},method=JacobianMethod.CENTRAL_FINITE_DIFFERENCE)
    forward=build_joint_constraint_jacobian(generated,poses(),{"q/t":0.3},method=JacobianMethod.FORWARD_FINITE_DIFFERENCE)
    assert jac_value(central,"rotation_z","coordinate/q/t") == pytest.approx(-1.0,abs=1e-6)
    assert jac_value(forward,"rotation_z","coordinate/q/t") == pytest.approx(-1.0,abs=2e-6)


def test_coordinate_bounds_select_feasible_one_sided_difference_or_lock_column():
    bounded = model_for(JointKind.REVOLUTE,(coord("q/t",CoordinateKind.ROTATIONAL,(0,0,1),lower_limit=-1,upper_limit=0),),param("q/t"))
    jac=build_joint_constraint_jacobian(generate_joint_constraints(bounded),poses(),{"q/t":0.0})
    col=next(item for item in jac.columns if item.variable.variable_id=="coordinate/q/t")
    assert col.method=="BACKWARD_FINITE_DIFFERENCE"
    assert jac_value(jac,"rotation_z","coordinate/q/t")==pytest.approx(-1.0,abs=1e-6)
    locked=model_for(JointKind.REVOLUTE,(coord("q/fixed",CoordinateKind.ROTATIONAL,(0,0,1),lower_limit=0,upper_limit=0),),param("q/fixed"))
    locked_jac=build_joint_constraint_jacobian(generate_joint_constraints(locked),poses(),{"q/fixed":0.0})
    col=next(item for item in locked_jac.columns if item.variable.variable_id=="coordinate/q/fixed")
    assert col.method=="BOUND_LOCKED"
    assert all(row[0]==0.0 for row in locked_jac.values)


def test_jacobian_snapshot_is_deterministic_and_preserves_units():
    model=model_for(JointKind.REVOLUTE,(coord("q/t",CoordinateKind.ROTATIONAL,(0,0,1)),),param("q/t"))
    generated=generate_joint_constraints(model)
    first=build_joint_constraint_jacobian(generated,poses(),{"q/t":0.0})
    second=build_joint_constraint_jacobian(generated,poses(),{"q/t":0.0})
    assert first.to_dict()==second.to_dict()
    assert first.row_units[:3]==("m","m","m")
    assert first.row_units[3:]==("rad","rad","rad")
    assert first.to_dict()["entry_unit_convention"]=="row residual unit divided by column variable unit"


def test_rejects_analytic_mode_and_invalid_steps():
    generated=generate_joint_constraints(model_for(JointKind.FIXED))
    with pytest.raises(InvalidModelError,match="finite differences only"):
        build_joint_constraint_jacobian(generated,poses(),{},method=JacobianMethod.ANALYTIC)
    with pytest.raises(InvalidModelError,match="finite and positive"):
        build_joint_constraint_jacobian(generated,poses(),{},finite_difference_step=0)
