from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.material_classification import (
    ExactMeshMaterialClassifier,
    MaterialClassification,
    classify_point_against_mesh,
)
from universal_platform.engineering.mesh import tessellate_box
from universal_platform.engineering.primitive_geometry import BoxSolid


def box_mesh():
    return tessellate_box(BoxSolid("box.one", "world", Vec3(2.0, 2.0, 2.0)))


def test_exact_classifier_distinguishes_inside_outside_and_boundary():
    mesh = box_mesh()
    inside = classify_point_against_mesh(Vec3(1.0, 1.0, 1.0), mesh)
    outside = classify_point_against_mesh(Vec3(3.0, 1.0, 1.0), mesh)
    boundary = classify_point_against_mesh(Vec3(0.0, 1.0, 1.0), mesh)
    assert inside.classification is MaterialClassification.INSIDE
    assert outside.classification is MaterialClassification.OUTSIDE
    assert boundary.classification is MaterialClassification.BOUNDARY


def test_classifier_returns_unknown_when_ray_budget_is_exceeded():
    result = classify_point_against_mesh(Vec3(1.0, 1.0, 1.0), box_mesh(),
                                         max_ray_checks=1)
    assert result.classification is MaterialClassification.UNKNOWN
    assert "budget" in result.reason


def test_classifier_returns_unknown_for_open_mesh():
    mesh = box_mesh()
    open_mesh = type(mesh)(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices, mesh.triangles[:-1],
    )
    result = classify_point_against_mesh(Vec3(1.0, 1.0, 1.0), open_mesh)
    assert result.classification is MaterialClassification.UNKNOWN



def test_classifier_preflights_ray_work_before_exact_triangle_materialization(monkeypatch):
    import universal_platform.engineering.material_classification as module

    def unexpected_conversion(value):
        raise AssertionError("ray-work preflight must happen before rational conversion")

    monkeypatch.setattr(module, "_q", unexpected_conversion)
    classifier = ExactMeshMaterialClassifier(box_mesh(), max_ray_checks=1)
    assert classifier.reason == "ray-triangle resource budget exceeded"
    result = classifier.classify_rational((__import__("fractions").Fraction(1),) * 3)
    assert result.classification is MaterialClassification.UNKNOWN


def test_classifier_fails_closed_when_aggregate_rational_budget_is_exceeded():
    classifier = ExactMeshMaterialClassifier(
        box_mesh(), max_aggregate_rational_bits=1
    )
    assert classifier.reason == "aggregate rational bit budget exceeded"
