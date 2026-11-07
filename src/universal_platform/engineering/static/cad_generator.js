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
  const buttons = ["save", "list", "load", "regenerate", "generate-profile"].map(byId);
  const profilePoints = [];
  const profileCanvas = byId("profile-canvas");
  const profileGeometry = byId("profile-geometry");
  const svgNamespace = "http://www.w3.org/2000/svg";
  let bearerToken = "";
  let connected = false;

  function setStatus(message, kind = "") {
    statusMessage.textContent = message;
    statusMessage.className = "status-message" + (kind ? " " + kind : "");
  }

  function showResult(value) {
    resultOutput.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  }

  function setConnected(value) {
    connected = value;
    connectionState.textContent = value ? "Connected" : "Not connected";
    connectionState.className = "state" + (value ? " good" : "");
    buttons.forEach((button) => { button.disabled = !value; });
    renderProfile();
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
      byId("revision-state").textContent = "No revision loaded";
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

  byId("load").addEventListener("click", async () => {
    try {
      const id = currentHistoryId();
      const revision = Number(revisionSelect.value);
      const result = await api(
        "/v1/histories/" + encodeURIComponent(id) + "?revision=" + encodeURIComponent(revision)
      );
      snapshotInput.value = JSON.stringify(result.history, null, 2);
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

  byId("regenerate").addEventListener("click", async () => {
    try {
      const id = currentHistoryId();
      const revision = Number(revisionSelect.value);
      const result = await api(
        "/v1/histories/" + encodeURIComponent(id) + "/regenerate",
        { method: "POST", body: { revision } }
      );
      const success = result.regeneration?.status === "SUCCESS";
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

  revisionSelect.addEventListener("change", () => {
    byId("revision-state").textContent = "Selected revision " + revisionSelect.value;
  });

  byId("clear-result").addEventListener("click", () => {
    showResult("No operation result displayed.");
    setStatus(connected ? "Connected; ready for the next operation." : "Enter your local bearer token and connect to begin.");
  });

  tokenInput.addEventListener("input", () => {
    bearerToken = "";
    setConnected(false);
    setStatus("Token changed. Connect again to authorize API requests.");
  });

  setConnected(false);
  renderProfile();
})();
