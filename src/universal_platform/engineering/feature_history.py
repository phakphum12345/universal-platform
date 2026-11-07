"""Deterministic feature DAG and bounded CAD regeneration pipeline.

Only built-in, allow-listed operations are evaluated. No user Python, plugins,
shell commands, network access or physical device actions are executed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from json import dumps, loads
from typing import ClassVar, Mapping
import re

from .errors import InvalidModelError, SolverError
from .mesh import TriangleMesh, tessellate_extruded_profile, validate_triangle_mesh
from .nonlinear_solver import NonlinearSolverOptions
from .parametric_sketch import ParametricSketch, solve_parametric_sketch
from .planar_boolean import PlanarRegionBooleanOperation
from .planar_region_extrusion import PlanarRegionExtrusionResult, extrude_planar_region
from .planar_region_set_boolean import PlanarRegionSetBooleanResult, boolean_planar_region_set
from .sketch_region import SketchRegionConversionResult, sketch_to_planar_regions

_FEATURE_ID = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")


class FeatureKind(str, Enum):
    SKETCH_PROFILE = "SKETCH_PROFILE"
    PLANAR_BOOLEAN = "PLANAR_BOOLEAN"
    EXTRUSION = "EXTRUSION"
    MESH = "MESH"


class RegenerationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class FeatureNode:
    feature_id: str
    kind: FeatureKind
    input_feature_ids: tuple[str, ...] = ()
    parameters_json: str = "{}"

    def __post_init__(self) -> None:
        if not isinstance(self.feature_id, str) or not _FEATURE_ID.fullmatch(self.feature_id):
            raise InvalidModelError("feature_id must be a stable lowercase identifier")
        if not isinstance(self.kind, FeatureKind):
            raise InvalidModelError("feature kind is unsupported")
        if not isinstance(self.input_feature_ids, tuple) or any(
            not isinstance(item, str) or not _FEATURE_ID.fullmatch(item)
            for item in self.input_feature_ids
        ):
            raise InvalidModelError("input_feature_ids must be an immutable tuple of feature identifiers")
        if len(set(self.input_feature_ids)) != len(self.input_feature_ids):
            raise InvalidModelError("feature input references must be unique")
        if self.feature_id in self.input_feature_ids:
            raise InvalidModelError("feature cannot depend on itself")
        if not isinstance(self.parameters_json, str):
            raise InvalidModelError("feature parameters must be canonical JSON text")
        try:
            raw = loads(self.parameters_json)
        except Exception as exc:
            raise InvalidModelError("feature parameters_json must contain valid JSON") from exc
        if not isinstance(raw, dict):
            raise InvalidModelError("feature parameters must be a JSON object")
        canonical = dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False)
        object.__setattr__(self, "parameters_json", canonical)

    @classmethod
    def create(
        cls,
        feature_id: str,
        kind: FeatureKind,
        input_feature_ids: tuple[str, ...] = (),
        parameters: Mapping[str, object] | None = None,
    ) -> "FeatureNode":
        try:
            encoded = dumps(dict(parameters or {}), sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InvalidModelError("feature parameters must be finite JSON-compatible values") from exc
        return cls(feature_id, kind, input_feature_ids, encoded)

    @property
    def parameters(self) -> dict[str, object]:
        return loads(self.parameters_json)

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_id": self.feature_id,
            "kind": self.kind.value,
            "input_feature_ids": list(self.input_feature_ids),
            "parameters": self.parameters,
        }


@dataclass(frozen=True, slots=True)
class FeatureHistory:
    history_id: str
    nodes: tuple[FeatureNode, ...]
    output_feature_ids: tuple[str, ...]

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.history_id, str) or not _FEATURE_ID.fullmatch(self.history_id):
            raise InvalidModelError("history_id must be a stable lowercase identifier")
        if not isinstance(self.nodes, tuple) or not self.nodes or any(
            not isinstance(node, FeatureNode) for node in self.nodes
        ):
            raise InvalidModelError("feature history requires an immutable non-empty node tuple")
        if not isinstance(self.output_feature_ids, tuple) or not self.output_feature_ids:
            raise InvalidModelError("feature history requires at least one output feature")
        ids = [node.feature_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise InvalidModelError("feature identifiers must be unique")
        known = set(ids)
        for node in self.nodes:
            if any(item not in known for item in node.input_feature_ids):
                raise InvalidModelError(f"feature {node.feature_id!r} references a missing dependency")
        if any(item not in known for item in self.output_feature_ids):
            raise InvalidModelError("feature history output references a missing feature")
        if len(set(self.output_feature_ids)) != len(self.output_feature_ids):
            raise InvalidModelError("feature history output identifiers must be unique")
        self.topological_order()

    def topological_order(self) -> tuple[str, ...]:
        dependencies = {node.feature_id: set(node.input_feature_ids) for node in self.nodes}
        order: list[str] = []
        while dependencies:
            ready = sorted(key for key, value in dependencies.items() if not value)
            if not ready:
                raise InvalidModelError("feature dependency graph contains a cycle")
            for feature_id in ready:
                order.append(feature_id)
                dependencies.pop(feature_id)
            for value in dependencies.values():
                value.difference_update(ready)
        return tuple(order)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "history_id": self.history_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "output_feature_ids": list(self.output_feature_ids),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "FeatureHistory":
        required = {"schema_version", "history_id", "nodes", "output_feature_ids"}
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("FeatureHistory snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("unsupported FeatureHistory schema_version")
        if not isinstance(value["nodes"], (list, tuple)) or not isinstance(value["output_feature_ids"], (list, tuple)):
            raise InvalidModelError("FeatureHistory nodes and output_feature_ids must be arrays")
        nodes = []
        for raw in value["nodes"]:
            if not isinstance(raw, Mapping) or set(raw) != {"feature_id", "kind", "input_feature_ids", "parameters"}:
                raise InvalidModelError("FeatureNode snapshot has missing or unknown fields")
            if not isinstance(raw["input_feature_ids"], (list, tuple)) or not isinstance(raw["parameters"], Mapping):
                raise InvalidModelError("FeatureNode inputs and parameters have invalid types")
            try:
                kind = FeatureKind(raw["kind"])
            except (TypeError, ValueError) as exc:
                raise InvalidModelError("unsupported feature kind") from exc
            nodes.append(FeatureNode.create(
                raw["feature_id"], kind, tuple(raw["input_feature_ids"]), raw["parameters"]
            ))
        return cls(value["history_id"], tuple(nodes), tuple(value["output_feature_ids"]))


@dataclass(frozen=True, slots=True)
class FeatureArtifact:
    feature_id: str
    kind: FeatureKind
    content_sha256: str
    computation_sha256: str
    payload_json: str
    value: object

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_id": self.feature_id,
            "kind": self.kind.value,
            "content_sha256": self.content_sha256,
            "computation_sha256": self.computation_sha256,
            "payload": loads(self.payload_json),
        }

    @classmethod
    def from_dict(cls, value: object) -> "FeatureArtifact":
        required = {
            "feature_id", "kind", "content_sha256", "computation_sha256", "payload"
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("FeatureArtifact snapshot has missing or unknown fields")
        feature_id = value["feature_id"]
        if not isinstance(feature_id, str) or not _FEATURE_ID.fullmatch(feature_id):
            raise InvalidModelError("FeatureArtifact feature_id must be a stable lowercase identifier")
        try:
            kind = FeatureKind(value["kind"])
        except (TypeError, ValueError) as exc:
            raise InvalidModelError("FeatureArtifact kind is unsupported") from exc

        def digest_field(name: str) -> str:
            digest = value[name]
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(ch not in "0123456789abcdef" for ch in digest)):
                raise InvalidModelError(f"FeatureArtifact {name} must be a lowercase SHA-256 digest")
            return digest

        content_digest = digest_field("content_sha256")
        computation_digest = digest_field("computation_sha256")
        payload = value["payload"]
        if not isinstance(payload, Mapping):
            raise InvalidModelError("FeatureArtifact payload must be an object")
        try:
            payload_json = dumps(dict(payload), sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InvalidModelError("FeatureArtifact payload must be finite JSON data") from exc
        actual_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        if actual_digest != content_digest:
            raise InvalidModelError("FeatureArtifact content digest mismatch")

        if kind is FeatureKind.SKETCH_PROFILE:
            restored = SketchRegionConversionResult.from_dict(payload)
        elif kind is FeatureKind.PLANAR_BOOLEAN:
            restored = PlanarRegionSetBooleanResult.from_dict(payload)
        elif kind is FeatureKind.EXTRUSION:
            restored = PlanarRegionExtrusionResult.from_dict(payload)
        elif kind is FeatureKind.MESH:
            if set(payload) != {"mesh", "validation"} or not isinstance(payload["validation"], Mapping):
                raise InvalidModelError("mesh FeatureArtifact payload has missing or unknown fields")
            mesh = TriangleMesh.from_dict(payload["mesh"])
            validation = validate_triangle_mesh(mesh)
            if validation.to_dict() != dict(payload["validation"]):
                raise InvalidModelError("mesh FeatureArtifact validation report mismatch")
            restored = (mesh, validation)
        else:
            raise InvalidModelError("FeatureArtifact kind cannot be rehydrated")

        artifact = cls(
            feature_id, kind, content_digest, computation_digest, payload_json, restored
        )
        if artifact.to_dict() != dict(value):
            raise InvalidModelError("FeatureArtifact snapshot is not canonical")
        return artifact


@dataclass(frozen=True, slots=True)
class FeatureRegenerationResult:
    history_id: str
    status: RegenerationStatus
    execution_order: tuple[str, ...]
    artifacts: tuple[FeatureArtifact, ...]
    failed_feature_id: str | None = None
    error: str | None = None
    reused_feature_ids: tuple[str, ...] = ()
    recomputed_feature_ids: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        return self.status is RegenerationStatus.SUCCESS

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "history_id": self.history_id,
            "status": self.status.value,
            "execution_order": list(self.execution_order),
            "artifacts": [item.to_dict() for item in self.artifacts],
            "failed_feature_id": self.failed_feature_id,
            "error": self.error,
            "reused_feature_ids": list(self.reused_feature_ids),
            "recomputed_feature_ids": list(self.recomputed_feature_ids),
            "limitations": [
                "Only built-in allow-listed SKETCH_PROFILE, PLANAR_BOOLEAN, EXTRUSION and MESH operations execute",
                "No user code, plugin, shell, network or physical device execution",
                "Incremental reuse is in-memory and requires a prior successful result; no durable cache, persistent document store, suppression or branch/merge history",
                "Geometry remains bounded by the source PlanarRegion and mesh kernel limitations",
            ],
        }


def _make_artifact(
    feature_id: str,
    kind: FeatureKind,
    value: object,
    payload: dict[str, object],
    computation_sha256: str,
) -> FeatureArtifact:
    payload_json = dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    digest = sha256(payload_json.encode("utf-8")).hexdigest()
    return FeatureArtifact(feature_id, kind, digest, computation_sha256, payload_json, value)


def _solver_options_payload(options: NonlinearSolverOptions | None) -> dict[str, object] | None:
    if options is None:
        return None
    return {
        "max_iterations": options.max_iterations,
        "finite_difference_step": options.finite_difference_step,
        "step_tolerance": options.step_tolerance,
        "initial_damping": options.initial_damping,
        "maximum_damping": options.maximum_damping,
        "jacobian_method": options.jacobian_method.value,
        "rank_tolerance": options.rank_tolerance,
        "column_scale_disparity_threshold": options.column_scale_disparity_threshold,
    }


def _computation_signature(
    node: FeatureNode,
    inputs: list[FeatureArtifact],
    solver_options: NonlinearSolverOptions | None,
) -> str:
    snapshot = {
        "kind": node.kind.value,
        "parameters": node.parameters,
        "inputs": [
            {"feature_id": item.feature_id, "content_sha256": item.content_sha256}
            for item in inputs
        ],
        "solver_options": _solver_options_payload(solver_options) if node.kind is FeatureKind.SKETCH_PROFILE else None,
    }
    encoded = dumps(snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _regions_from_artifact(artifact: FeatureArtifact) -> tuple:
    if isinstance(artifact.value, (SketchRegionConversionResult, PlanarRegionSetBooleanResult)):
        return artifact.value.regions
    raise InvalidModelError("feature dependency does not produce planar regions")


def regenerate_feature_history(
    history: FeatureHistory,
    *,
    solver_options: NonlinearSolverOptions | None = None,
    previous_result: FeatureRegenerationResult | None = None,
) -> FeatureRegenerationResult:
    """Regenerate a feature DAG, reusing only artifacts with matching input fingerprints.

    Any expected feature/model/solver failure aborts the run and discards all
    partial artifacts from the returned result. Reuse is process-local: callers
    must retain a prior successful result and pass it explicitly.
    """
    if not isinstance(history, FeatureHistory):
        raise InvalidModelError("regenerate_feature_history requires a FeatureHistory")
    if previous_result is not None:
        if not isinstance(previous_result, FeatureRegenerationResult):
            raise InvalidModelError("previous_result must be a FeatureRegenerationResult")
        if previous_result.history_id != history.history_id:
            raise InvalidModelError("previous_result belongs to a different feature history")
        if not previous_result.successful:
            raise InvalidModelError("previous_result must be successful before it can be reused")
    previous = {
        item.feature_id: item for item in (previous_result.artifacts if previous_result else ())
    }
    by_id = {node.feature_id: node for node in history.nodes}
    computed: dict[str, FeatureArtifact] = {}
    completed: list[str] = []
    reused: list[str] = []
    recomputed: list[str] = []
    for feature_id in history.topological_order():
        node = by_id[feature_id]
        parameters = node.parameters
        inputs = [computed[item] for item in node.input_feature_ids]
        signature = _computation_signature(node, inputs, solver_options)
        cached = previous.get(feature_id)
        if cached is not None and cached.kind is node.kind and cached.computation_sha256 == signature:
            computed[feature_id] = cached
            completed.append(feature_id)
            reused.append(feature_id)
            continue
        try:
            if node.kind is FeatureKind.SKETCH_PROFILE:
                if inputs or set(parameters) != {"sketch"} or not isinstance(parameters["sketch"], Mapping):
                    raise InvalidModelError("SKETCH_PROFILE requires no inputs and exactly one sketch snapshot")
                sketch = ParametricSketch.from_dict(parameters["sketch"])
                solved = solve_parametric_sketch(sketch, options=solver_options)
                if not solved.converged:
                    raise SolverError("sketch constraints did not converge")
                value = sketch_to_planar_regions(sketch, solved)
                payload = value.to_dict()
            elif node.kind is FeatureKind.PLANAR_BOOLEAN:
                if len(inputs) < 2 or set(parameters) != {"operation"}:
                    raise InvalidModelError("PLANAR_BOOLEAN requires at least two region inputs and operation")
                try:
                    operation = PlanarRegionBooleanOperation(parameters["operation"])
                except (TypeError, ValueError) as exc:
                    raise InvalidModelError("unsupported planar Boolean operation") from exc
                regions = tuple(region for artifact in inputs for region in _regions_from_artifact(artifact))
                value = boolean_planar_region_set(regions, operation)
                payload = value.to_dict()
            elif node.kind is FeatureKind.EXTRUSION:
                if len(inputs) != 1 or set(parameters) - {"solid_id", "height", "region_index"} or not {
                    "solid_id", "height"
                }.issubset(parameters):
                    raise InvalidModelError("EXTRUSION requires one region input, solid_id and height")
                if not isinstance(parameters["solid_id"], str) or not parameters["solid_id"]:
                    raise InvalidModelError("EXTRUSION solid_id must be non-empty")
                region_index = parameters.get("region_index", 0)
                if isinstance(region_index, bool) or not isinstance(region_index, int) or region_index < 0:
                    raise InvalidModelError("EXTRUSION region_index must be a non-negative integer")
                regions = _regions_from_artifact(inputs[0])
                if region_index >= len(regions):
                    raise InvalidModelError("EXTRUSION region_index is outside the input region set")
                value = extrude_planar_region(regions[region_index], parameters["solid_id"], parameters["height"])
                payload = value.to_dict()
            elif node.kind is FeatureKind.MESH:
                if len(inputs) != 1 or parameters:
                    raise InvalidModelError("MESH requires one extrusion input and no parameters")
                if not isinstance(inputs[0].value, PlanarRegionExtrusionResult):
                    raise InvalidModelError("MESH input must be an EXTRUSION feature")
                mesh = tessellate_extruded_profile(inputs[0].value.solid)
                validation = validate_triangle_mesh(mesh)
                if not (validation.valid and validation.watertight and validation.consistently_oriented):
                    raise InvalidModelError("generated mesh failed closed/watertight/orientation validation")
                value = (mesh, validation)
                payload = {"mesh": mesh.to_dict(), "validation": validation.to_dict()}
            else:
                raise InvalidModelError("feature kind is not executable")
            computed[feature_id] = _make_artifact(feature_id, node.kind, value, payload, signature)
            completed.append(feature_id)
            recomputed.append(feature_id)
        except (InvalidModelError, SolverError, TypeError, ValueError, KeyError) as exc:
            return FeatureRegenerationResult(
                history.history_id, RegenerationStatus.FAILED, tuple(completed), (),
                feature_id, str(exc), tuple(reused), tuple(recomputed),
            )
    return FeatureRegenerationResult(
        history.history_id, RegenerationStatus.SUCCESS, tuple(completed),
        tuple(computed[item] for item in history.topological_order()),
        reused_feature_ids=tuple(reused),
        recomputed_feature_ids=tuple(recomputed),
    )
