(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const tokenInput = byId("token");
  const connectButton = byId("connect");
  const connectionState = byId("connection-state");
  const historyIdInput = byId("history-id");
  const expectedRevisionInput = byId("expected-revision");
  const snapshotInput = byId("snapshot");
  const revisionSelect = byId("revision");
  const statusMessage = byId("status-message");
  const resultOutput = byId("result");
  const featureTree = byId("feature-tree");
  const featureTreeState = byId("feature-tree-state");
  const featureInspector = byId("feature-inspector");
  const featureEditParametersInput = byId("feature-edit-parameters");
  const buttons = ["save", "list", "load", "regenerate", "generate-profile", "feature-apply-edit", "feature-add", "feature-remove", "feature-suppress", "feature-unsuppress", "undo", "redo"].map(byId);
  const profilePoints = [];
  const profileCanvas = byId("profile-canvas");
  const profileGeometry = byId("profile-geometry");
  const svgNamespace = "http://www.w3.org/2000/svg";
  const meshFaces = byId("mesh-faces");
  const meshPreview = byId("mesh-preview");
  const meshControlButtons = ["mesh-zoom-in", "mesh-zoom-out", "mesh-reset-view"].map(byId);
  const meshSelection = byId("mesh-selection");
  const meshClearSelectionButton = byId("mesh-clear-selection");
  const MAX_PREVIEW_TRIANGLES = 5000;
  const MAX_PREVIEW_VERTICES = 10000;
  const MAX_FEATURE_TREE_NODES = 500;
  let bearerToken = "";
  let connected = false;
  let activeMesh = null;
  const defaultMeshCamera = { yaw: 0.7853981633974483, pitch: 0.6154797086703874, zoom: 1, panX: 0, panY: 0 };
  let meshCamera = { ...defaultMeshCamera };
  let meshDrag = null;
  let selectedMeshTriangleIndex = null;
  let selectedFeatureId = null;
  let selectedFeatureSuppressed = false;
  let selectedFeatureDependenciesActive = false;
  let navigationState = null;
  let navigationBusy = false;
  let suppressMeshClick = false;

  function setStatus(message, kind = "") {
    statusMessage.textContent = message;
    statusMessage.className = "status-message" + (kind ? " " + kind : "");
  }

  function showResult(value) {
    resultOutput.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  }

  function updateFeatureEditorControls(hasSelection) {
    const expected = Number(expectedRevisionInput.value);
    const canEditCurrentHead = connected &&
      Number.isSafeInteger(expected) && expected >= 1 &&
      !revisionSelect.disabled && revisionSelect.value === String(expected);
    const canEditSelection = canEditCurrentHead && hasSelection;
    featureEditParametersInput.disabled = !canEditSelection;
    byId("feature-apply-edit").disabled = !canEditSelection;
    byId("feature-remove").disabled = !canEditSelection;
    byId("feature-add").disabled = !canEditCurrentHead;
    byId("feature-suppress").disabled = !(canEditSelection && !selectedFeatureSuppressed);
    byId("feature-unsuppress").disabled = !(
      canEditSelection && selectedFeatureSuppressed && selectedFeatureDependenciesActive
    );
    byId("feature-suppress-cascade").disabled = !(canEditSelection && !selectedFeatureSuppressed);
  }

  function updateNavigationControls() {
    const expected = Number(expectedRevisionInput.value);
    const currentHead = connected &&
      Number.isSafeInteger(expected) && expected >= 1 &&
      !revisionSelect.disabled && revisionSelect.value === String(expected);
    const canUndo = currentHead && !navigationBusy && Boolean(navigationState && navigationState.can_undo);
    const canRedo = currentHead && !navigationBusy && Boolean(navigationState && navigationState.can_redo);
    byId("undo").disabled = !canUndo;
    byId("redo").disabled = !canRedo;
    if (!connected || !navigationState) {
      byId("navigation-state").textContent = "Undo/Redo unavailable until a saved current revision is loaded.";
    } else if (!currentHead) {
      byId("navigation-state").textContent = "Undo/Redo is disabled while viewing a historical revision.";
    } else {
      byId("navigation-state").textContent =
        (navigationState.can_undo ? "Undo available" : "No Undo target") + " · " +
        (navigationState.can_redo ? "Redo available" : "No Redo target") +
        " · current revision " + navigationState.current_revision;
    }
  }

  async function refreshNavigation() {
    if (!connected) {
      navigationState = null;
      updateNavigationControls();
      return null;
    }
    try {
      navigationState = await api(
        "/v1/histories/" + encodeURIComponent(currentHistoryId()) + "/navigation"
      );
    } catch (error) {
      if (error.status === 404) {
        navigationState = null;
      } else {
        throw error;
      }
    }
    updateNavigationControls();
    return navigationState;
  }

  async function performNavigation(operation) {
    if (operation !== "undo" && operation !== "redo") {
      throw new Error("Unsupported navigation operation.");
    }
    const expected = Number(expectedRevisionInput.value);
    if (!Number.isSafeInteger(expected) || expected < 1 ||
        revisionSelect.disabled || revisionSelect.value !== String(expected)) {
      throw new Error("Load the current head revision before using Undo/Redo.");
    }
    navigationBusy = true;
    updateNavigationControls();
    try {
      const id = currentHistoryId();
      const result = await api(
        "/v1/histories/" + encodeURIComponent(id) + "/" + operation,
        { method: "POST", body: { expected_revision: expected } }
      );
      await refreshRevisions(result.revision);
      const loaded = await api(
        "/v1/histories/" + encodeURIComponent(id) + "?revision=" + encodeURIComponent(result.revision)
      );
      snapshotInput.value = JSON.stringify(loaded.history, null, 2);
      renderFeatureTree();
      byId("revision-state").textContent =
        operation.toUpperCase() + " created revision " + result.revision +
        " from revision " + result.target_revision;
      setStatus(
        operation.toUpperCase() + " restored revision " + result.target_revision +
        " as new immutable revision " + result.revision + ".",
        "good"
      );
      showResult(result);
      return result;
    } catch (error) {
      setStatus(error.message, "bad");
      showResult(error.payload || error.message);
      if (error.status === 409) await refreshRevisions();
      throw error;
    } finally {
      navigationBusy = false;
      updateNavigationControls();
    }
  }

  function renderFeatureTree() {
    updateFeatureEditorControls(false);
    featureTree.replaceChildren();
    featureInspector.textContent = "Select a feature to inspect its inputs and parameters.";
    const raw = snapshotInput.value.trim();
    if (!raw) {
      selectedFeatureId = null;
      featureTreeState.textContent = "No FeatureHistory snapshot.";
      return;
    }

    let snapshot;
    try {
      snapshot = JSON.parse(raw);
    } catch (_) {
      selectedFeatureId = null;
      featureTreeState.textContent = "Invalid JSON; feature tree preview unavailable.";
      return;
    }
    if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot) ||
        !(snapshot.schema_version === "1.0" || snapshot.schema_version === "1.1") ||
        typeof snapshot.history_id !== "string" ||
        (snapshot.schema_version === "1.1" && !Array.isArray(snapshot.suppressed_feature_ids)) ||
        !Array.isArray(snapshot.nodes) || !Array.isArray(snapshot.output_feature_ids)) {
      selectedFeatureId = null;
      featureTreeState.textContent = "Snapshot structure is not recognized; backend validation remains authoritative.";
      return;
    }
    if (snapshot.nodes.length > MAX_FEATURE_TREE_NODES) {
      selectedFeatureId = null;
      featureTreeState.textContent = "Feature tree preview is limited to " + MAX_FEATURE_TREE_NODES + " nodes.";
      return;
    }
    if (snapshot.nodes.length === 0 || snapshot.output_feature_ids.length === 0) {
      selectedFeatureId = null;
      featureTreeState.textContent = "FeatureHistory requires nodes and output feature IDs.";
      return;
    }

    const nodeById = new Map();
    for (const node of snapshot.nodes) {
      if (!node || typeof node !== "object" || Array.isArray(node) ||
          typeof node.feature_id !== "string" || !node.feature_id ||
          typeof node.kind !== "string" || !node.kind ||
          !Array.isArray(node.input_feature_ids) ||
          !node.parameters || typeof node.parameters !== "object" || Array.isArray(node.parameters) ||
          node.input_feature_ids.some((id) => typeof id !== "string" || !id) ||
          new Set(node.input_feature_ids).size !== node.input_feature_ids.length ||
          nodeById.has(node.feature_id)) {
        selectedFeatureId = null;
        featureTreeState.textContent = "Malformed or duplicate feature node; preview unavailable.";
        return;
      }
      nodeById.set(node.feature_id, node);
    }
    const outputs = new Set(snapshot.output_feature_ids);
    if (outputs.size !== snapshot.output_feature_ids.length ||
        snapshot.output_feature_ids.some((id) => typeof id !== "string" || !nodeById.has(id))) {
      selectedFeatureId = null;
      selectedFeatureSuppressed = false;
      selectedFeatureDependenciesActive = false;
      featureTreeState.textContent = "Output feature references are invalid.";
      return;
    }
    const rawSuppressed = snapshot.schema_version === "1.1" ? snapshot.suppressed_feature_ids : [];
    const suppressed = new Set(rawSuppressed);
    const activeOutputs = [...outputs].filter((id) => !suppressed.has(id));
    if (rawSuppressed.some((id, index) =>
          typeof id !== "string" || !nodeById.has(id) ||
          (index > 0 && rawSuppressed[index - 1] >= id)
        ) ||
        activeOutputs.length === 0 ||
        snapshot.nodes.some((node) =>
          !suppressed.has(node.feature_id) &&
          node.input_feature_ids.some((id) => suppressed.has(id))
        )) {
      selectedFeatureId = null;
      selectedFeatureSuppressed = false;
      selectedFeatureDependenciesActive = false;
      featureTreeState.textContent = "Suppression metadata or active dependency/output invariants are invalid.";
      return;
    }

    const indegree = new Map();
    const dependents = new Map();
    for (const node of snapshot.nodes) {
      indegree.set(node.feature_id, node.input_feature_ids.length);
      dependents.set(node.feature_id, []);
      if (node.input_feature_ids.some((id) => !nodeById.has(id) || id === node.feature_id)) {
        selectedFeatureId = null;
        featureTreeState.textContent = "Missing or self-referential feature dependency.";
        return;
      }
    }
    for (const node of snapshot.nodes) {
      for (const dependency of node.input_feature_ids) dependents.get(dependency).push(node.feature_id);
    }
    const ready = snapshot.nodes.filter((node) => indegree.get(node.feature_id) === 0)
      .map((node) => node.feature_id).sort();
    const ordered = [];
    while (ready.length) {
      const id = ready.shift();
      ordered.push(nodeById.get(id));
      for (const dependent of dependents.get(id)) {
        indegree.set(dependent, indegree.get(dependent) - 1);
        if (indegree.get(dependent) === 0) {
          ready.push(dependent);
          ready.sort();
        }
      }
    }
    if (ordered.length !== snapshot.nodes.length) {
      selectedFeatureId = null;
      featureTreeState.textContent = "Feature dependency cycle detected; preview unavailable.";
      return;
    }

    featureTreeState.textContent =
      "Structure preview only · " + ordered.length + " features · " +
      suppressed.size + " suppressed · outputs: " +
      snapshot.output_feature_ids.join(", ") + " · deterministic topological order";
    const showFeature = (node) => {
      selectedFeatureId = node.feature_id;
      selectedFeatureSuppressed = suppressed.has(node.feature_id);
      selectedFeatureDependenciesActive = node.input_feature_ids.every((id) => !suppressed.has(id));
      featureTree.querySelectorAll("button[data-feature-id]").forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.featureId === selectedFeatureId));
      });
      featureEditParametersInput.value = JSON.stringify(node.parameters, null, 2);
      updateFeatureEditorControls(true);
      featureInspector.textContent = JSON.stringify({
        feature_id: node.feature_id,
        kind: node.kind,
        input_feature_ids: node.input_feature_ids,
        suppressed: selectedFeatureSuppressed,
        parameters: node.parameters,
      }, null, 2);
    };
    for (const node of ordered) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      const dependencies = document.createElement("span");
      button.type = "button";
      button.className = "feature-tree-node" + (suppressed.has(node.feature_id) ? " is-suppressed" : "");
      button.dataset.featureId = node.feature_id;
      button.setAttribute("aria-pressed", "false");
      button.textContent = node.feature_id + " · " + node.kind +
        (outputs.has(node.feature_id) ? " · output" : "") +
        (suppressed.has(node.feature_id) ? " · SUPPRESSED" : "");
      button.addEventListener("click", () => showFeature(node));
      dependencies.className = "feature-tree-dependencies";
      dependencies.textContent = node.input_feature_ids.length
        ? "Depends on: " + node.input_feature_ids.join(", ")
        : "No dependencies";
      item.append(button, dependencies);
      featureTree.append(item);
    }
    const initial = ordered.find((node) => node.feature_id === selectedFeatureId) || ordered[0];
    showFeature(initial);
  }

  function setConnected(value) {
    connected = value;
    if (!value) navigationState = null;
    connectionState.textContent = value ? "Connected" : "Not connected";
    connectionState.className = "state" + (value ? " good" : "");
    buttons.forEach((button) => { button.disabled = !value; });
    renderProfile();
    renderFeatureTree();
    updateNavigationControls();
  }

  function profileToCanvas(point) {
    return { x: 40 + point.x * 20, y: 320 - point.y * 20 };
  }

  function renderProfile() {
    profileGeometry.replaceChildren();
    const screenPoints = profilePoints.map(profileToCanvas);
    if (screenPoints.length >= 3) {
      const polygon = document.createElementNS(svgNamespace, "polygon");
      polygon.setAttribute("points", screenPoints.map((point) => point.x + "," + point.y).join(" "));
      polygon.setAttribute("class", "profile-edge");
      profileGeometry.append(polygon);
    } else if (screenPoints.length === 2) {
      const line = document.createElementNS(svgNamespace, "polyline");
      line.setAttribute("points", screenPoints.map((point) => point.x + "," + point.y).join(" "));
      line.setAttribute("class", "profile-open-edge");
      profileGeometry.append(line);
    }
    screenPoints.forEach((point, index) => {
      const marker = document.createElementNS(svgNamespace, "circle");
      marker.setAttribute("cx", String(point.x));
      marker.setAttribute("cy", String(point.y));
      marker.setAttribute("r", "5");
      marker.setAttribute("class", "profile-vertex");
      profileGeometry.append(marker);
      const label = document.createElementNS(svgNamespace, "text");
      label.setAttribute("x", String(point.x + 8));
      label.setAttribute("y", String(point.y - 8));
      label.setAttribute("class", "profile-vertex-label");
      label.textContent = "P" + index;
      profileGeometry.append(label);
    });
    byId("profile-state").textContent = profilePoints.length + " vertices";
    byId("undo-point").disabled = profilePoints.length === 0;
    byId("clear-profile").disabled = profilePoints.length === 0;
    byId("generate-profile").disabled = !connected || profilePoints.length < 3;
  }

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function disableMeshPreview() {
    activeMesh = null;
    meshDrag = null;
    selectedMeshTriangleIndex = null;
    suppressMeshClick = false;
    meshFaces.replaceChildren();
    meshCamera = { ...defaultMeshCamera };
    meshControlButtons.forEach((button) => { button.disabled = true; });
    meshClearSelectionButton.disabled = true;
    meshSelection.textContent = "Select a triangle to inspect its area and centroid.";
  }

  function clearMeshPreview(message = "No mesh artifact loaded.") {
    disableMeshPreview();
    byId("mesh-state").textContent = "No mesh preview";
    byId("mesh-state").className = "state";
    byId("mesh-validation").textContent = message;
    byId("mesh-details").textContent = "No mesh artifact loaded.";
  }

  function formatMeshMeasurement(value) {
    return value === 0 ? "0" : Number(value.toPrecision(8)).toString();
  }

  function selectMeshTriangle(index) {
    if (!activeMesh || !Number.isInteger(index) || index < 0 || index >= activeMesh.triangles.length) return;
    const triangle = activeMesh.triangles[index];
    const [a, b, c] = triangle.map((vertexIndex) => activeMesh.vertices[vertexIndex]);
    const ab = { x: b.x - a.x, y: b.y - a.y, z: b.z - a.z };
    const ac = { x: c.x - a.x, y: c.y - a.y, z: c.z - a.z };
    const nx = ab.y * ac.z - ab.z * ac.y;
    const ny = ab.z * ac.x - ab.x * ac.z;
    const nz = ab.x * ac.y - ab.y * ac.x;
    const area = 0.5 * Math.hypot(nx, ny, nz);
    const centroid = {
      x: (a.x + b.x + c.x) / 3,
      y: (a.y + b.y + c.y) / 3,
      z: (a.z + b.z + c.z) / 3,
    };
    if (![area, centroid.x, centroid.y, centroid.z].every(Number.isFinite)) {
      meshSelection.textContent = "Triangle measurement unavailable: result is outside the finite numeric range.";
      meshClearSelectionButton.disabled = true;
      return;
    }
    selectedMeshTriangleIndex = index;
    const unit = activeMesh.lengthUnit;
    meshSelection.textContent =
      "Triangle " + (index + 1) + " · area " + formatMeshMeasurement(area) + " " + unit + "²" +
      " · centroid (" + [centroid.x, centroid.y, centroid.z].map(formatMeshMeasurement).join(", ") + ") " + unit +
      " · frame " + activeMesh.frameId;
    meshClearSelectionButton.disabled = false;
    drawMeshPreview();
  }

  function clearMeshSelection() {
    selectedMeshTriangleIndex = null;
    meshClearSelectionButton.disabled = true;
    meshSelection.textContent = "Select a triangle to inspect its area and centroid.";
    if (activeMesh) drawMeshPreview();
  }

  function drawMeshPreview() {
    if (!activeMesh) return;
    const { vertices, triangles } = activeMesh;
    const cosYaw = Math.cos(meshCamera.yaw), sinYaw = Math.sin(meshCamera.yaw);
    const cosPitch = Math.cos(meshCamera.pitch), sinPitch = Math.sin(meshCamera.pitch);
    const projected = vertices.map((vertex) => {
      const x = cosYaw * vertex.x - sinYaw * vertex.y;
      const y = sinYaw * vertex.x + cosYaw * vertex.y;
      const z = vertex.z;
      return {
        u: x,
        v: cosPitch * y - sinPitch * z,
        depth: sinPitch * y + cosPitch * z,
      };
    });
    const minU = Math.min(...projected.map((point) => point.u));
    const maxU = Math.max(...projected.map((point) => point.u));
    const minV = Math.min(...projected.map((point) => point.v));
    const maxV = Math.max(...projected.map((point) => point.v));
    const rangeU = Math.max(maxU - minU, 1e-9);
    const rangeV = Math.max(maxV - minV, 1e-9);
    const scale = Math.min(540 / rangeU, 320 / rangeV) * meshCamera.zoom;
    const centerU = (minU + maxU) * 0.5;
    const centerV = (minV + maxV) * 0.5;
    const screen = projected.map((point) => ({
      x: 320 + (point.u - centerU) * scale + meshCamera.panX,
      y: 210 - (point.v - centerV) * scale + meshCamera.panY,
    }));
    const faces = triangles.map((indices, triangleIndex) => {
      if (!Array.isArray(indices) || indices.length !== 3 ||
          indices.some((index) => !Number.isInteger(index) || index < 0 || index >= vertices.length)) return null;
      const a = vertices[indices[0]], b = vertices[indices[1]], c = vertices[indices[2]];
      const ab = [b.x - a.x, b.y - a.y, b.z - a.z];
      const ac = [c.x - a.x, c.y - a.y, c.z - a.z];
      const normal = [
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
      ];
      const faceClass = normal[2] > 0 ? "mesh-face-top" :
        (normal[0] - normal[1] > 0 ? "mesh-face-side-a" : "mesh-face-side-b");
      return {
        points: indices.map((index) => screen[index].x + "," + screen[index].y).join(" "),
        depth: indices.reduce((sum, index) => sum + projected[index].depth, 0) / 3,
        faceClass,
        triangleIndex,
      };
    }).filter((face) => face !== null).sort((left, right) => right.depth - left.depth);
    meshFaces.replaceChildren();
    faces.forEach((face) => {
      const polygon = document.createElementNS(svgNamespace, "polygon");
      polygon.setAttribute("points", face.points);
      polygon.setAttribute("class", "mesh-face " + face.faceClass +
        (selectedMeshTriangleIndex === face.triangleIndex ? " mesh-face-selected" : ""));
      polygon.setAttribute("data-triangle-index", String(face.triangleIndex));
      polygon.setAttribute("role", "button");
      polygon.setAttribute("tabindex", "0");
      polygon.setAttribute("aria-label", "Select mesh triangle " + (face.triangleIndex + 1));
      polygon.setAttribute("aria-pressed", String(selectedMeshTriangleIndex === face.triangleIndex));
      polygon.addEventListener("click", () => {
        if (suppressMeshClick) {
          suppressMeshClick = false;
          return;
        }
        selectMeshTriangle(face.triangleIndex);
      });
      polygon.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectMeshTriangle(face.triangleIndex);
        }
      });
      meshFaces.append(polygon);
    });
  }

  function renderMeshPreview(run) {
    const artifacts = run?.regeneration?.artifacts || [];
    const artifact = artifacts.find((item) => item.kind === "MESH");
    if (!artifact || !artifact.payload?.mesh || !artifact.payload?.validation) {
      clearMeshPreview("The selected regeneration result does not contain a mesh artifact.");
      return;
    }
    const mesh = artifact.payload.mesh;
    const validation = artifact.payload.validation;
    const vertices = Array.isArray(mesh.vertices) ? mesh.vertices : [];
    const triangles = Array.isArray(mesh.triangles) ? mesh.triangles : [];
    const valid = validation.valid === true;
    const watertight = validation.watertight === true;
    const oriented = validation.consistently_oriented === true;
    const allChecks = valid && watertight && oriented;
    byId("mesh-state").textContent = allChecks ? "Mesh checks passed" : "Mesh validation warning";
    byId("mesh-state").className = "state " + (allChecks ? "good" : "bad");
    byId("mesh-validation").textContent =
      "valid: " + valid + " · watertight: " + watertight +
      " · consistently oriented: " + oriented +
      (validation.issues?.length ? " · issues: " + validation.issues.join("; ") : "");
    byId("mesh-details").textContent =
      "Revision " + run.source_revision.revision +
      " · " + vertices.length + " vertices · " + triangles.length + " triangles" +
      " · content SHA-256 " + artifact.content_sha256 +
      " · computation SHA-256 " + artifact.computation_sha256;
    if (!Array.isArray(vertices) || !Array.isArray(triangles) ||
        vertices.length < 4 || vertices.length > MAX_PREVIEW_VERTICES) {
      disableMeshPreview();
      byId("mesh-validation").textContent += " · Mesh vertex data is outside the preview bounds.";
      byId("mesh-state").textContent = "Preview unavailable";
      return;
    }
    if (triangles.length === 0 || triangles.length > MAX_PREVIEW_TRIANGLES) {
      disableMeshPreview();
      byId("mesh-validation").textContent += " · Preview is limited to 1–5,000 triangles; full mesh remains in the result JSON.";
      byId("mesh-state").textContent = "Preview unavailable";
      return;
    }
    if (triangles.some((indices) => !Array.isArray(indices) || indices.length !== 3 ||
        indices.some((index) => !Number.isInteger(index) || index < 0 || index >= vertices.length))) {
      disableMeshPreview();
      byId("mesh-validation").textContent += " · Malformed triangle indices prevent rendering this mesh.";
      byId("mesh-state").textContent = "Preview unavailable";
      return;
    }
    if (vertices.some((vertex) => !vertex || ![vertex.x, vertex.y, vertex.z].every(Number.isFinite))) {
      disableMeshPreview();
      byId("mesh-validation").textContent += " · Non-finite or malformed vertex coordinates prevent rendering.";
      byId("mesh-state").textContent = "Preview unavailable";
      return;
    }
    activeMesh = { vertices, triangles, lengthUnit: mesh.length_unit, frameId: mesh.frame_id };
    selectedMeshTriangleIndex = null;
    meshClearSelectionButton.disabled = true;
    meshSelection.textContent = "Select a triangle to inspect its area and centroid.";
    meshCamera = { ...defaultMeshCamera };
    meshControlButtons.forEach((button) => { button.disabled = false; });
    drawMeshPreview();
  }

  function updateMeshZoom(factor) {
    if (!activeMesh) return;
    meshCamera.zoom = clamp(meshCamera.zoom * factor, 0.5, 4);
    drawMeshPreview();
  }

  byId("mesh-zoom-in").addEventListener("click", () => updateMeshZoom(1.2));
  byId("mesh-zoom-out").addEventListener("click", () => updateMeshZoom(1 / 1.2));
  byId("mesh-reset-view").addEventListener("click", () => {
    meshCamera = { ...defaultMeshCamera };
    drawMeshPreview();
  });
  meshClearSelectionButton.addEventListener("click", clearMeshSelection);

  meshPreview.addEventListener("pointerdown", (event) => {
    if (!activeMesh || (event.button !== 0 && event.button !== 1)) return;
    suppressMeshClick = false;
    meshDrag = {
      pointerId: event.pointerId, x: event.clientX, y: event.clientY,
      mode: event.shiftKey || event.button === 1 ? "pan" : "orbit",
      moved: false,
    };
    meshPreview.setPointerCapture(event.pointerId);
  });
  meshPreview.addEventListener("pointermove", (event) => {
    if (!meshDrag || meshDrag.pointerId !== event.pointerId) return;
    const dx = event.clientX - meshDrag.x, dy = event.clientY - meshDrag.y;
    meshDrag.x = event.clientX;
    meshDrag.y = event.clientY;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) meshDrag.moved = true;
    if (meshDrag.mode === "pan") {
      meshCamera.panX = clamp(meshCamera.panX + dx, -600, 600);
      meshCamera.panY = clamp(meshCamera.panY + dy, -400, 400);
    } else {
      meshCamera.yaw += dx * 0.01;
      meshCamera.pitch = clamp(meshCamera.pitch + dy * 0.01, -1.35, 1.35);
    }
    drawMeshPreview();
  });
  ["pointerup", "pointercancel", "lostpointercapture"].forEach((eventName) => {
    meshPreview.addEventListener(eventName, (event) => {
      if (meshDrag && meshDrag.pointerId === event.pointerId) {
        suppressMeshClick = eventName === "pointerup" && meshDrag.moved;
        meshDrag = null;
      }
    });
  });
  meshPreview.addEventListener("wheel", (event) => {
    if (!activeMesh) return;
    event.preventDefault();
    updateMeshZoom(event.deltaY < 0 ? 1.1 : 1 / 1.1);
  }, { passive: false });
  function addProfilePoint(x, y) {
    if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || x > 26 || y < 0 || y > 15) {
      throw new Error("Profile coordinates must be within X 0–26 mm and Y 0–15 mm.");
    }
    if (profilePoints.length >= 64) {
      throw new Error("The bounded polygon editor supports at most 64 vertices.");
    }
    const duplicate = profilePoints.some((point) =>
      Math.abs(point.x - x) <= 1e-9 && Math.abs(point.y - y) <= 1e-9
    );
    if (duplicate) throw new Error("A profile vertex already exists at this coordinate.");
    profilePoints.push({ x, y });
    renderProfile();
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Authorization", "Bearer " + bearerToken);
    if (options.body !== undefined) headers.set("Content-Type", "application/json");
    const response = await fetch(path, {
      method: options.method || "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
    });
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : { message: await response.text() };
    if (!response.ok) {
      const error = new Error(payload?.error?.message || "HTTP " + response.status);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  function currentHistoryId() {
    const id = historyIdInput.value.trim();
    if (!/^[a-z0-9]+(?:[._-][a-z0-9]+)*$/.test(id)) {
      throw new Error("History ID must use lowercase letters, digits, dot, underscore or hyphen.");
    }
    return id;
  }

  function parseObjectField(id, label) {
    let value;
    try {
      value = JSON.parse(byId(id).value);
    } catch (_) {
      throw new Error(label + " must be valid JSON.");
    }
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error(label + " must be a JSON object.");
    }
    return value;
  }

  async function commitFeatureEdit(operation, fields) {
    const id = currentHistoryId();
    const expected = Number(expectedRevisionInput.value);
    if (!Number.isSafeInteger(expected) || expected < 1) {
      throw new Error("A saved current head revision is required before editing.");
    }
    if (revisionSelect.disabled || revisionSelect.value !== String(expected)) {
      throw new Error("Load the current head revision before editing; historical revisions are read-only.");
    }
    const result = await api("/v1/histories/" + encodeURIComponent(id) + "/edit", {
      method: "POST",
      body: { expected_revision: expected, operation, ...fields },
    });
    await refreshRevisions(result.revision);
    const loaded = await api(
      "/v1/histories/" + encodeURIComponent(id) + "?revision=" + encodeURIComponent(result.revision)
    );
    snapshotInput.value = JSON.stringify(loaded.history, null, 2);
    renderFeatureTree();
    byId("revision-state").textContent = "Loaded edited head revision " + result.revision;
    setStatus("Saved " + operation + " as immutable revision " + result.revision + ".", "good");
    showResult(result);
    return result;
  }

  function reportFeatureEditError(error) {
    if (error.status === 409) {
      setStatus("Revision conflict. Refresh revisions and load the latest head before retrying.", "bad");
    } else {
      setStatus(error.message, "bad");
    }
    showResult(error.payload || error.message);
  }

  async function refreshRevisions(selectRevision = null) {
    const id = currentHistoryId();
    const result = await api("/v1/histories/" + encodeURIComponent(id) + "/revisions");
    const revisions = result.revisions || [];
    revisionSelect.replaceChildren();
    if (!revisions.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No revisions";
      revisionSelect.append(option);
      revisionSelect.disabled = true;
      byId("load").disabled = true;
      byId("regenerate").disabled = true;
      expectedRevisionInput.value = "0";
      navigationState = null;
      byId("revision-state").textContent = "No revision loaded";
      updateFeatureEditorControls(false);
      updateNavigationControls();
      return result;
    }
    revisions.forEach((number) => {
      const option = document.createElement("option");
      option.value = String(number);
      option.textContent = "Revision " + number;
      revisionSelect.append(option);
    });
    const head = revisions[revisions.length - 1];
    expectedRevisionInput.value = String(head);
    const target = selectRevision === null ? head : selectRevision;
    revisionSelect.value = String(target);
    revisionSelect.disabled = false;
    byId("load").disabled = false;
    byId("regenerate").disabled = false;
    byId("revision-state").textContent = "Head revision " + head;
    updateFeatureEditorControls(false);
    await refreshNavigation();
    return result;
  }

  connectButton.addEventListener("click", async () => {
    bearerToken = tokenInput.value;
    if (new TextEncoder().encode(bearerToken).length < 32) {
      setConnected(false);
      setStatus("The local bearer token must contain at least 32 UTF-8 bytes.", "bad");
      return;
    }
    connectButton.disabled = true;
    try {
      const health = await api("/health");
      setConnected(true);
      try {
        await refreshRevisions();
        setStatus("Connected to the local CAD Generator API. The selected history is ready.", "good");
      } catch (historyError) {
        if (historyError.status !== 404) throw historyError;
        expectedRevisionInput.value = "0";
        revisionSelect.replaceChildren();
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "No revisions";
        revisionSelect.append(option);
        revisionSelect.disabled = true;
        byId("load").disabled = true;
        byId("regenerate").disabled = true;
        navigationState = null;
        updateNavigationControls();
        setStatus("Connected. No saved history exists for this ID yet; create the first revision.", "good");
      }
      showResult(health);
    } catch (error) {
      bearerToken = "";
      setConnected(false);
      setStatus(error.message, "bad");
      showResult(error.payload || error.message);
    } finally {
      connectButton.disabled = false;
    }
  });

  byId("save").addEventListener("click", async () => {
    try {
      const id = currentHistoryId();
      const history = JSON.parse(snapshotInput.value);
      if (!history || typeof history !== "object" || Array.isArray(history)) {
        throw new Error("FeatureHistory snapshot must be a JSON object.");
      }
      if (history.history_id !== id) {
        throw new Error("History ID field must match the History ID input.");
      }
      const expected = Number(expectedRevisionInput.value);
      if (!Number.isSafeInteger(expected) || expected < 0) {
        throw new Error("Expected current revision must be a non-negative integer.");
      }
      const result = await api("/v1/histories", {
        method: "POST",
        body: { history, expected_revision: expected },
      });
      await refreshRevisions(result.revision);
      setStatus("Saved immutable revision " + result.revision + ".", "good");
      showResult(result);
    } catch (error) {
      setStatus(error.message, "bad");
      showResult(error.payload || error.message);
    }
  });

  byId("list").addEventListener("click", async () => {
    try {
      const result = await refreshRevisions();
      setStatus("Revision list refreshed.", "good");
      showResult(result);
    } catch (error) {
      setStatus(error.message, "bad");
      showResult(error.payload || error.message);
    }
  });

  revisionSelect.addEventListener("change", () => {
    updateFeatureEditorControls(selectedFeatureId !== null);
    updateNavigationControls();
  });

  byId("load").addEventListener("click", async () => {
    try {
      const id = currentHistoryId();
      const revisionValue = revisionSelect.value;
      const revision = Number(revisionValue);
      if (!revisionValue || !Number.isSafeInteger(revision) || revision < 1) {
        throw new Error("Select a saved revision before loading.");
      }
      const result = await api(
        "/v1/histories/" + encodeURIComponent(id) + "?revision=" + encodeURIComponent(revision)
      );
      snapshotInput.value = JSON.stringify(result.history, null, 2);
      renderFeatureTree();
      byId("revision-state").textContent = "Loaded revision " + revision;
      setStatus("Loaded immutable source revision " + revision + ".", "good");
      showResult({
        history_id: result.history_id,
        revision: result.revision,
        parent_sha256: result.parent_sha256,
        content_sha256: result.content_sha256,
        created_at: result.created_at,
      });
    } catch (error) {
      setStatus(error.message, "bad");
      showResult(error.payload || error.message);
    }
  });

  byId("undo").addEventListener("click", async () => {
    try {
      await performNavigation("undo");
    } catch (_) {
      // performNavigation reports the actionable error in the status region.
    }
  });

  byId("redo").addEventListener("click", async () => {
    try {
      await performNavigation("redo");
    } catch (_) {
      // performNavigation reports the actionable error in the status region.
    }
  });

  byId("regenerate").addEventListener("click", async () => {
    try {
      const id = currentHistoryId();
      const revisionValue = revisionSelect.value;
      const revision = Number(revisionValue);
      if (!revisionValue || !Number.isSafeInteger(revision) || revision < 1) {
        throw new Error("Select a saved revision before regeneration.");
      }
      const result = await api(
        "/v1/histories/" + encodeURIComponent(id) + "/regenerate",
        { method: "POST", body: { revision } }
      );
      const success = result.regeneration?.status === "SUCCESS";
      if (success) renderMeshPreview(result);
      else clearMeshPreview("Regeneration failed; no successful mesh preview is available.");
      setStatus(
        success ? "Regeneration completed for revision " + revision + "." :
          "Regeneration failed for revision " + revision + ". Inspect the result and limitations.",
        success ? "good" : "bad"
      );
      showResult(result);
    } catch (error) {
      setStatus(error.message, "bad");
      showResult(error.payload || error.message);
    }
  });

  byId("add-point").addEventListener("click", () => {
    try {
      const x = Number(byId("sketch-x").value);
      const y = Number(byId("sketch-y").value);
      addProfilePoint(x, y);
      setStatus("Added profile vertex " + profilePoints.length + ".", "good");
    } catch (error) {
      setStatus(error.message, "bad");
    }
  });

  byId("undo-point").addEventListener("click", () => {
    profilePoints.pop();
    renderProfile();
    setStatus("Removed the last profile vertex.");
  });

  byId("clear-profile").addEventListener("click", () => {
    profilePoints.length = 0;
    renderProfile();
    setStatus("Cleared the sketch profile.");
  });

  profileCanvas.addEventListener("click", (event) => {
    const matrix = profileCanvas.getScreenCTM();
    if (!matrix) return;
    const cursor = profileCanvas.createSVGPoint();
    cursor.x = event.clientX;
    cursor.y = event.clientY;
    const local = cursor.matrixTransform(matrix.inverse());
    const x = Math.round(((local.x - 40) / 20) * 10) / 10;
    const y = Math.round(((320 - local.y) / 20) * 10) / 10;
    if (x < 0 || x > 26 || y < 0 || y > 15) return;
    try {
      addProfilePoint(x, y);
      byId("sketch-x").value = String(x);
      byId("sketch-y").value = String(y);
      setStatus("Added profile vertex " + profilePoints.length + ".", "good");
    } catch (error) {
      setStatus(error.message, "bad");
    }
  });

  byId("generate-profile").addEventListener("click", async () => {
    try {
      const id = currentHistoryId();
      const height = Number(byId("extrusion-height").value);
      if (!Number.isFinite(height) || height <= 0) {
        throw new Error("Extrusion height must be a finite positive number.");
      }
      if (profilePoints.length < 3) {
        throw new Error("Add at least three profile vertices before generating.");
      }
      const result = await api("/v1/templates/polygon-extrusion", {
        method: "POST",
        body: {
          history_id: id,
          points: profilePoints.map((point) => [point.x, point.y]),
          height,
          length_unit: "mm",
        },
      });
      snapshotInput.value = JSON.stringify(result.history, null, 2);
      renderFeatureTree();
      setStatus("FeatureHistory JSON generated. Save the revision, then regenerate to validate the solid.", "good");
      showResult({
        template: result.template,
        history_id: result.history.history_id,
        point_count: profilePoints.length,
        extrusion_height_mm: height,
        limitations: result.limitations,
      });
    } catch (error) {
      setStatus(error.message, "bad");
      showResult(error.payload || error.message);
    }
  });

  byId("feature-apply-edit").addEventListener("click", async () => {
    try {
      const snapshot = JSON.parse(snapshotInput.value);
      const node = snapshot.nodes.find((item) => item.feature_id === selectedFeatureId);
      if (!node) throw new Error("Select a feature from the current FeatureHistory snapshot.");
      const parameters = parseObjectField("feature-edit-parameters", "Feature parameters");
      const feature = { ...node, parameters };
      await commitFeatureEdit("replace", { feature_id: selectedFeatureId, feature });
    } catch (error) {
      reportFeatureEditError(error);
    }
  });

  byId("feature-add").addEventListener("click", async () => {
    try {
      const featureId = byId("feature-add-id").value.trim();
      const inputs = byId("feature-add-inputs").value.trim();
      const feature = {
        feature_id: featureId,
        kind: byId("feature-add-kind").value,
        input_feature_ids: inputs ? inputs.split(",").map((value) => value.trim()) : [],
        parameters: parseObjectField("feature-add-parameters", "New feature parameters"),
      };
      const makeOutput = byId("feature-add-output").checked;
      await commitFeatureEdit("add", { feature, make_output: makeOutput });
      byId("feature-add-id").value = "";
      byId("feature-add-inputs").value = "";
      byId("feature-add-parameters").value = "{}";
      byId("feature-add-output").checked = false;
    } catch (error) {
      reportFeatureEditError(error);
    }
  });

  byId("feature-remove").addEventListener("click", async () => {
    try {
      if (!selectedFeatureId) throw new Error("Select a feature to remove.");
      const cascade = byId("feature-remove-cascade").checked;
      await commitFeatureEdit("remove", { feature_id: selectedFeatureId, cascade });
      byId("feature-remove-cascade").checked = false;
    } catch (error) {
      reportFeatureEditError(error);
    }
  });

  byId("feature-suppress").addEventListener("click", async () => {
    try {
      if (!selectedFeatureId) throw new Error("Select a feature to suppress.");
      const cascade = byId("feature-suppress-cascade").checked;
      if (cascade && !window.confirm(
        "Suppress this feature and every dependent feature? Source nodes and previous revisions will be retained."
      )) return;
      await commitFeatureEdit("suppress", { feature_id: selectedFeatureId, cascade });
      byId("feature-suppress-cascade").checked = false;
    } catch (error) {
      reportFeatureEditError(error);
    }
  });

  byId("feature-unsuppress").addEventListener("click", async () => {
    try {
      if (!selectedFeatureId) throw new Error("Select a feature to unsuppress.");
      await commitFeatureEdit("unsuppress", { feature_id: selectedFeatureId });
    } catch (error) {
      reportFeatureEditError(error);
    }
  });


  revisionSelect.addEventListener("change", () => {
    byId("revision-state").textContent = "Selected revision " + revisionSelect.value;
    renderFeatureTree();
  });

  byId("clear-result").addEventListener("click", () => {
    showResult("No operation result displayed.");
    clearMeshPreview();
    setStatus(connected ? "Connected; ready for the next operation." : "Enter your local bearer token and connect to begin.");
  });

  snapshotInput.addEventListener("input", renderFeatureTree);

  tokenInput.addEventListener("input", () => {
    bearerToken = "";
    setConnected(false);
    setStatus("Token changed. Connect again to authorize API requests.");
  });

  setConnected(false);
  renderProfile();
  renderFeatureTree();
})();
