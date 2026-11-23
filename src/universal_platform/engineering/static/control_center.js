(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const shell = byId("app-shell");
  const navigationToggle = byId("navigation-toggle");
  const themeToggle = byId("theme-toggle");
  const tokenInput = byId("service-token");
  const serviceState = byId("service-state");
  const serviceDetail = byId("service-detail");
  const checkButton = byId("check-service");
  const clearButton = byId("clear-token");
  const platformState = byId("platform-overall-state");
  const platformDetail = byId("platform-status-detail");
  const platformComponents = byId("platform-components");
  const workspaceState = byId("workspace-state");
  const workspaceDetail = byId("workspace-detail");
  const workspaceList = byId("workspace-list");
  const workspaceEditor = byId("workspace-editor");
  const workspaceCreateButton = byId("workspace-create");
  const workspaceSaveButton = byId("workspace-save");
  const workspaceReloadButton = byId("workspace-reload");
  const workspaceMoreButton = byId("workspace-load-more");
  let activeToken = null;
  let selectedWorkspace = null;
  let workspaceOffset = 0;
  let workspaceHasMore = false;
  let creatingWorkspace = false;
  let savingWorkspace = false;
  let loadingWorkspaceId = null;
  let workspaceLoadSequence = 0;

  function setServiceState(kind, label, detail) {
    serviceState.className = "status-pill " + kind;
    serviceState.textContent = label;
    serviceDetail.textContent = detail;
  }

  function setPlatformState(kind, label, detail, components = []) {
    platformState.className = "status-pill " + kind;
    platformState.textContent = label;
    platformDetail.textContent = detail;
    platformComponents.replaceChildren();

    for (const component of components) {
      const item = document.createElement("li");
      item.className = "component-row";
      item.dataset.componentId = component.id;
      const heading = document.createElement("strong");
      heading.textContent = component.id;
      const status = document.createElement("span");
      status.className = "component-status " + component.status.toLowerCase();
      status.textContent = component.status;
      const explanation = document.createElement("p");
      explanation.textContent = component.evidence || component.reason || "No additional evidence was supplied.";
      item.append(heading, status, explanation);
      platformComponents.append(item);
    }
  }

  function setWorkspaceState(kind, label, detail) {
    workspaceState.className = "status-pill " + kind;
    workspaceState.textContent = label;
    workspaceDetail.textContent = detail;
  }

  async function requestJson(path, method, token, body) {
    const options = {
      method,
      headers: { Authorization: "Bearer " + token },
      credentials: "omit",
      cache: "no-store",
      redirect: "error"
    };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    const response = await fetch(path, options);
    let payload;
    try {
      payload = await response.json();
    } catch (_error) {
      throw new Error("The service returned an invalid JSON response.");
    }
    return { response, payload };
  }

  async function checkPlatformStatus(token) {
    setPlatformState("unknown", "PENDING · Checking platform", "Requesting the authenticated /v1/platform/status contract.");
    try {
      const { response, payload } = await requestJson("/v1/platform/status", "GET", token);
      if (!response.ok) {
        const message = payload && payload.error && typeof payload.error.message === "string"
          ? payload.error.message : "The platform status request was rejected.";
        setPlatformState("failed", "FAIL · HTTP " + response.status, message);
        return;
      }
      const allowedStatuses = new Set(["READY", "UNKNOWN", "UNSUPPORTED", "FAIL"]);
      const validComponents = Array.isArray(payload.components) && payload.components.every((component) =>
        component && typeof component.id === "string" && component.id.length > 0 &&
        allowedStatuses.has(component.status) &&
        (component.reason === undefined || typeof component.reason === "string") &&
        (component.evidence === undefined || typeof component.evidence === "string")
      );
      if (payload.api_version !== "1.0" || payload.status !== "PARTIAL" || !validComponents ||
          !Array.isArray(payload.limitations) || !payload.limitations.every((item) => typeof item === "string")) {
        setPlatformState("unknown", "UNKNOWN · Unexpected response", "The endpoint responded, but its payload did not match the known platform status contract.");
        return;
      }
      setPlatformState("partial", "PARTIAL · Platform integration", payload.limitations.join(" "), payload.components);
    } catch (_error) {
      setPlatformState("failed", "FAIL · Status request error", "The platform status endpoint could not be reached or returned invalid JSON.");
    }
  }

  function parseMetadata(id) {
    let metadata;
    try {
      metadata = JSON.parse(byId(id).value);
    } catch (_error) {
      throw new Error("Metadata must be valid JSON.");
    }
    if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
      throw new Error("Metadata must be a JSON object.");
    }
    return metadata;
  }

  function renderWorkspaces(records, { append = false } = {}) {
    if (!append) workspaceList.replaceChildren();
    if (records.length === 0 && !append && workspaceOffset === 0) {
      const empty = document.createElement("li");
      empty.className = "workspace-empty";
      empty.textContent = "No workspaces have been created yet.";
      workspaceList.append(empty);
      return;
    }
    for (const record of records) {
      const existing = workspaceList.querySelector('[data-workspace-id="' + CSS.escape(record.workspace_id) + '"]');
      if (existing) existing.closest("li")?.remove();
      const item = document.createElement("li");
      const select = document.createElement("button");
      select.type = "button";
      select.className = "workspace-select";
      select.dataset.workspaceId = record.workspace_id;
      select.setAttribute("aria-pressed", String(selectedWorkspace?.workspace_id === record.workspace_id));
      const name = document.createElement("strong");
      name.textContent = record.name;
      const details = document.createElement("small");
      details.textContent = "Revision " + record.revision + " · " + record.workspace_id;
      select.append(name, details);
      select.addEventListener("click", () => loadWorkspace(record.workspace_id));
      item.append(select);
      workspaceList.append(item);
    }
  }

  async function loadWorkspaces(token = activeToken, { append = false } = {}) {
    if (!token) {
      setWorkspaceState("unknown", "UNKNOWN · Authentication required", "Enter the local bearer token and check the service before loading workspaces.");
      return;
    }
    if (!append) {
      workspaceOffset = 0;
      workspaceHasMore = false;
      workspaceMoreButton.hidden = true;
      workspaceMoreButton.disabled = true;
    }
    setWorkspaceState("unknown", "PENDING · Loading", "Reading workspace metadata from the local SQLite store.");
    try {
      const requestedOffset = append ? workspaceOffset : 0;
      const { response, payload } = await requestJson(
        "/v1/workspaces?limit=100&offset=" + requestedOffset, "GET", token
      );
      if (!response.ok) {
        const message = payload?.error?.message || "Workspace list request failed.";
        setWorkspaceState("failed", "FAIL · HTTP " + response.status, message);
        return;
      }
      if (!Array.isArray(payload.workspaces) || payload.count !== payload.workspaces.length ||
          payload.limit !== 100 || payload.offset !== requestedOffset ||
          typeof payload.has_more !== "boolean" ||
          !payload.workspaces.every((item) => item && typeof item.workspace_id === "string" &&
            typeof item.name === "string" && Number.isInteger(item.revision))) {
        setWorkspaceState("unknown", "UNKNOWN · Invalid response", "The workspace endpoint returned data outside the supported response contract.");
        return;
      }
      renderWorkspaces(payload.workspaces, { append });
      workspaceOffset = requestedOffset + payload.count;
      workspaceHasMore = payload.has_more;
      workspaceMoreButton.hidden = !workspaceHasMore;
      workspaceMoreButton.disabled = false;
      setWorkspaceState("ready", "READY · " + workspaceOffset + " loaded", "Workspace records were read from the configured local SQLite store.");
    } catch (_error) {
      setWorkspaceState("failed", "FAIL · Connection error", "The workspace API could not be reached.");
    }
  }

  async function loadWorkspace(workspaceId, { force = false } = {}) {
    if (!activeToken || loadingWorkspaceId === workspaceId) return;
    if (!force && selectedWorkspace?.workspace_id === workspaceId && !workspaceEditor.hidden) return;
    const loadSequence = ++workspaceLoadSequence;
    loadingWorkspaceId = workspaceId;
    try {
      const { response, payload } = await requestJson("/v1/workspaces/" + encodeURIComponent(workspaceId), "GET", activeToken);
      if (loadSequence !== workspaceLoadSequence) return;
      if (!response.ok) {
        setWorkspaceState("failed", "FAIL · HTTP " + response.status, payload?.error?.message || "Workspace could not be loaded.");
        return;
      }
      const record = payload.workspace;
      if (!record || record.workspace_id !== workspaceId || !Number.isInteger(record.revision) ||
          typeof record.name !== "string" || typeof record.description !== "string" ||
          !record.metadata || typeof record.metadata !== "object" || Array.isArray(record.metadata)) {
        setWorkspaceState("unknown", "UNKNOWN · Invalid response", "The workspace item did not match the supported response contract.");
        return;
      }
      selectedWorkspace = record;
      byId("workspace-edit-name").value = record.name;
      byId("workspace-edit-description").value = record.description;
      byId("workspace-edit-metadata").value = JSON.stringify(record.metadata, null, 2);
      byId("workspace-edit-state").textContent = "Selected revision " + record.revision + ". Updates use optimistic revision checks.";
      workspaceEditor.hidden = false;
      workspaceReloadButton.hidden = true;
      for (const button of workspaceList.querySelectorAll("[data-workspace-id]")) {
        button.setAttribute("aria-pressed", String(button.dataset.workspaceId === record.workspace_id));
      }
    } catch (_error) {
      if (loadSequence === workspaceLoadSequence) {
        setWorkspaceState("failed", "FAIL · Connection error", "The selected workspace could not be loaded.");
      }
    } finally {
      if (loadSequence === workspaceLoadSequence) loadingWorkspaceId = null;
    }
  }

  navigationToggle.addEventListener("click", () => {
    const open = shell.classList.toggle("nav-open");
    navigationToggle.setAttribute("aria-expanded", String(open));
    navigationToggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  });

  document.querySelectorAll("#primary-navigation a").forEach((link) => {
    link.addEventListener("click", () => {
      shell.classList.remove("nav-open");
      navigationToggle.setAttribute("aria-expanded", "false");
      navigationToggle.setAttribute("aria-label", "Open navigation");
    });
  });

  themeToggle.addEventListener("click", () => {
    const light = document.documentElement.dataset.theme !== "light";
    if (light) document.documentElement.dataset.theme = "light";
    else delete document.documentElement.dataset.theme;
    themeToggle.setAttribute("aria-pressed", String(light));
    themeToggle.textContent = light ? "Use dark theme" : "Use light theme";
  });

  checkButton.addEventListener("click", async () => {
    const token = tokenInput.value;
    if (!token) {
      setServiceState("unknown", "UNKNOWN · Token required", "Enter the local bearer token to check the CAD Generator API.");
      tokenInput.focus();
      return;
    }
    activeToken = token;
    checkButton.disabled = true;
    setServiceState("unknown", "PENDING · Checking", "Requesting the existing authenticated /health endpoint.");
    try {
      const { response, payload } = await requestJson("/health", "GET", token);
      if (!response.ok) {
        const message = payload?.error?.message || "The service rejected the health request.";
        setServiceState("failed", "FAIL · HTTP " + response.status, message);
        setWorkspaceState("failed", "FAIL · Authentication", "The service rejected the supplied token.");
        return;
      }
      if (payload.status === "READY" && payload.service === "cad-generator" && payload.api_version === "1.0") {
        setServiceState("ready", "PASS · CAD API READY", "Verified CAD Generator API v" + payload.api_version + ". This does not establish platform-wide health.");
        await Promise.all([checkPlatformStatus(token), loadWorkspaces(token)]);
      } else {
        setServiceState("unknown", "UNKNOWN · Unexpected response", "The endpoint responded, but its payload did not match the known CAD health contract.");
      }
    } catch (_error) {
      setServiceState("failed", "FAIL · Connection error", "The local CAD Generator API could not be reached. Confirm that its loopback service is running.");
      setWorkspaceState("failed", "FAIL · Connection error", "The workspace API could not be reached.");
    } finally {
      checkButton.disabled = false;
    }
  });

  clearButton.addEventListener("click", () => {
    tokenInput.value = "";
    activeToken = null;
    selectedWorkspace = null;
    workspaceLoadSequence += 1;
    loadingWorkspaceId = null;
    workspaceEditor.hidden = true;
    workspaceList.replaceChildren();
    workspaceReloadButton.hidden = true;
    workspaceMoreButton.hidden = true;
    workspaceOffset = 0;
    workspaceHasMore = false;
    setServiceState("unknown", "UNKNOWN · Not checked", "Local token cleared from this page's memory.");
    setPlatformState("unknown", "UNKNOWN · Not checked", "Platform status was cleared; run Check service to verify it again.");
    setWorkspaceState("unknown", "UNKNOWN · Not loaded", "The token was cleared; workspace data is no longer accessible.");
    tokenInput.focus();
  });

  workspaceMoreButton.addEventListener("click", async () => {
    if (!workspaceHasMore || workspaceMoreButton.disabled) return;
    workspaceMoreButton.disabled = true;
    try {
      await loadWorkspaces(activeToken, { append: true });
    } finally {
      workspaceMoreButton.disabled = false;
    }
  });

  workspaceReloadButton.addEventListener("click", async () => {
    if (!selectedWorkspace || !activeToken) return;
    workspaceReloadButton.disabled = true;
    try {
      await loadWorkspace(selectedWorkspace.workspace_id, { force: true });
    } finally {
      workspaceReloadButton.disabled = false;
    }
  });

  workspaceCreateButton.addEventListener("click", async () => {
    if (!activeToken) {
      setWorkspaceState("unknown", "UNKNOWN · Authentication required", "Check the service before creating a workspace.");
      return;
    }
    if (creatingWorkspace) return;
    creatingWorkspace = true;
    workspaceCreateButton.disabled = true;
    try {
      const body = {
        name: byId("workspace-name").value,
        description: byId("workspace-description").value,
        metadata: parseMetadata("workspace-metadata")
      };
      const { response, payload } = await requestJson("/v1/workspaces", "POST", activeToken, body);
      if (!response.ok) {
        setWorkspaceState("failed", "FAIL · HTTP " + response.status, payload?.error?.message || "Workspace creation failed.");
        return;
      }
      byId("workspace-name").value = "";
      byId("workspace-description").value = "";
      byId("workspace-metadata").value = "{}";
      setWorkspaceState("ready", "READY · Created", "Workspace " + payload.workspace.name + " was saved locally.");
      await loadWorkspaces();
      await loadWorkspace(payload.workspace.workspace_id);
    } catch (error) {
      setWorkspaceState("failed", "FAIL · Invalid input", error.message);
    } finally {
      creatingWorkspace = false;
      workspaceCreateButton.disabled = false;
    }
  });

  workspaceSaveButton.addEventListener("click", async () => {
    if (!activeToken || !selectedWorkspace || savingWorkspace) return;
    savingWorkspace = true;
    workspaceSaveButton.disabled = true;
    try {
      const body = {
        expected_revision: selectedWorkspace.revision,
        name: byId("workspace-edit-name").value,
        description: byId("workspace-edit-description").value,
        metadata: parseMetadata("workspace-edit-metadata")
      };
      const { response, payload } = await requestJson(
        "/v1/workspaces/" + encodeURIComponent(selectedWorkspace.workspace_id),
        "PUT", activeToken, body
      );
      if (response.status === 409) {
        setWorkspaceState("failed", "FAIL · Revision conflict", "Your draft is preserved. Another client saved a newer revision; use Reload latest to replace this draft explicitly.");
        workspaceReloadButton.hidden = false;
        return;
      }
      if (!response.ok) {
        setWorkspaceState("failed", "FAIL · HTTP " + response.status, payload?.error?.message || "Workspace update failed.");
        return;
      }
      if (!payload.workspace || payload.workspace.workspace_id !== selectedWorkspace.workspace_id ||
          payload.workspace.name !== body.name.trim() || payload.workspace.revision !== body.expected_revision + 1) {
        setWorkspaceState("unknown", "UNKNOWN · Invalid update response", "The server response did not confirm the requested workspace revision.");
        return;
      }
      const workspaceId = selectedWorkspace.workspace_id;
      const { response: verifyResponse, payload: verifyPayload } = await requestJson(
        "/v1/workspaces/" + encodeURIComponent(workspaceId), "GET", activeToken
      );
      const persistedWorkspace = verifyPayload?.workspace;
      if (!verifyResponse.ok || !persistedWorkspace ||
          persistedWorkspace.workspace_id !== workspaceId ||
          persistedWorkspace.name !== payload.workspace.name ||
          persistedWorkspace.description !== payload.workspace.description ||
          persistedWorkspace.revision !== payload.workspace.revision) {
        setWorkspaceState("unknown", "UNKNOWN · Persistence verification failed", "The update response was received, but a follow-up read did not confirm the saved workspace. The editor draft has been retained.");
        return;
      }
      selectedWorkspace = persistedWorkspace;
      byId("workspace-edit-state").textContent = "Saved revision " + selectedWorkspace.revision + ". Verified by a follow-up read.";
      workspaceReloadButton.hidden = true;
      setWorkspaceState("ready", "READY · Saved", "The updated workspace was read back from local SQLite storage.");
      const selectedButton = workspaceList.querySelector(
        '[data-workspace-id="' + CSS.escape(workspaceId) + '"]'
      );
      if (selectedButton) {
        const name = selectedButton.querySelector("strong");
        const details = selectedButton.querySelector("small");
        if (name) name.textContent = selectedWorkspace.name;
        if (details) details.textContent = "Revision " + selectedWorkspace.revision + " · " + workspaceId;
      }
    } catch (error) {
      setWorkspaceState("failed", "FAIL · Invalid input", error.message);
    } finally {
      savingWorkspace = false;
      workspaceSaveButton.disabled = false;
    }
  });

  tokenInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") checkButton.click();
  });
})();
