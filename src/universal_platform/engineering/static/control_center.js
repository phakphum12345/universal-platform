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
  const settingsState = byId("settings-state");
  const settingsDetail = byId("settings-detail");
  const settingsTheme = byId("settings-theme");
  const settingsDensity = byId("settings-density");
  const settingsReducedMotion = byId("settings-reduced-motion");
  const settingsSaveButton = byId("settings-save");
  const settingsReloadButton = byId("settings-reload");
  let settingsRevision = null;
  let savingSettings = false;
  let activeToken = null;
  let selectedWorkspace = null;
  let workspaceOffset = 0;
  let workspaceHasMore = false;
  let creatingWorkspace = false;
  let savingWorkspace = false;
  let loadingWorkspaceId = null;
  let workspaceLoadSequence = 0;
  const catalogueState = byId("catalog-state");
  const moduleList = byId("module-list");
  const toolList = byId("tool-list");
  const functionList = byId("function-list");

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

  function setSettingsState(kind, label, detail) {
    settingsState.className = "status-pill " + kind;
    settingsState.textContent = label;
    settingsDetail.textContent = detail;
  }

  function applyTheme(theme) {
    if (theme === "light" || theme === "dark") {
      document.documentElement.dataset.theme = theme;
    } else {
      delete document.documentElement.dataset.theme;
    }
    const light = theme === "light";
    themeToggle.setAttribute("aria-pressed", String(light));
    themeToggle.textContent = light ? "Use dark theme" : "Use light theme";
  }

  function applyDensity(density) {
    if (density === "compact") document.documentElement.dataset.density = "compact";
    else delete document.documentElement.dataset.density;
  }

  function applyReducedMotion(enabled) {
    if (enabled) document.documentElement.dataset.reducedMotion = "true";
    else delete document.documentElement.dataset.reducedMotion;
  }

  function markSettingsDirty() {
    if (settingsRevision === null) return;
    setSettingsState(
      "unknown",
      "PENDING · Unsaved changes",
      "Your changes are only a draft until Save settings completes and a follow-up read confirms persistence."
    );
    settingsSaveButton.disabled = false;
  }

  function setCatalogueState(kind, label, detail) {
    catalogueState.className = "status-pill " + kind;
    catalogueState.textContent = label;
    catalogueState.setAttribute("aria-label", detail);
  }

  function appendCatalogueEmpty(list, message) {
    const item = document.createElement("li");
    item.className = "catalog-empty";
    item.textContent = message;
    list.append(item);
  }

  function renderCatalogue(modules, functions, tools) {
    moduleList.replaceChildren();
    functionList.replaceChildren();
    toolList.replaceChildren();

    if (modules.length === 0) appendCatalogueEmpty(moduleList, "No modules are registered on this host.");
    for (const module of modules) {
      const item = document.createElement("li");
      item.className = "catalog-item";
      item.dataset.moduleId = module.module_id;
      const heading = document.createElement("strong");
      heading.textContent = module.module_id;
      const metadata = document.createElement("p");
      metadata.textContent = module.domain + " · v" + module.version + " · " + module.maturity;
      const registration = document.createElement("p");
      registration.className = "catalog-status";
      registration.textContent = module.registration_status + " · " + module.execution_status.replaceAll("_", " ");
      const operations = document.createElement("p");
      operations.className = "catalog-note";
      operations.textContent = "Operations: " + module.operations.map((operation) => operation.operation_id).join(", ");
      item.append(heading, metadata, registration, operations);
      moduleList.append(item);
    }

    if (functions.length === 0) appendCatalogueEmpty(functionList, "No module operations are registered.");
    for (const entry of functions) {
      const item = document.createElement("li");
      item.className = "catalog-item";
      item.dataset.functionId = entry.function_id;
      const heading = document.createElement("strong");
      heading.textContent = entry.function_id;
      const metadata = document.createElement("p");
      metadata.textContent = entry.domain + " · " + entry.operation.execution_kind + " · module v" + entry.module_version;
      const permissions = document.createElement("p");
      permissions.className = "catalog-note";
      permissions.textContent = "Required permissions: " +
        (entry.operation.required_permissions.length ? entry.operation.required_permissions.join(", ") : "none declared");
      const execution = document.createElement("p");
      execution.className = "catalog-status";
      execution.textContent = entry.registration_status + " · " + entry.execution_status.replaceAll("_", " ");
      const note = document.createElement("p");
      note.className = "catalog-note";
      note.textContent = "No execution action is available from the catalogue.";
      item.append(heading, metadata, permissions, execution, note);
      functionList.append(item);
    }

    if (tools.length === 0) {
      appendCatalogueEmpty(toolList, "UNKNOWN · No separately governed tool registry is configured on this host.");
    } else {
      for (const tool of tools) {
        const item = document.createElement("li");
        item.className = "catalog-item";
        const heading = document.createElement("strong");
        heading.textContent = tool.tool_id;
        const detail = document.createElement("p");
        detail.textContent = tool.description || "No description supplied.";
        item.append(heading, detail);
        toolList.append(item);
      }
    }
  }

  async function loadCatalogue(token = activeToken) {
    if (!token) {
      setCatalogueState("unknown", "UNKNOWN · Authentication required", "Authenticate to read the local module catalogue.");
      return;
    }
    setCatalogueState("unknown", "PENDING · Loading catalogue", "Reading registered module metadata from the authenticated local host.");
    try {
      const [moduleResult, functionResult, toolResult] = await Promise.all([
        requestJson("/v1/modules", "GET", token),
        requestJson("/v1/functions", "GET", token),
        requestJson("/v1/tools", "GET", token)
      ]);
      for (const result of [moduleResult, functionResult, toolResult]) {
        if (!result.response.ok) {
          const message = result.payload?.error?.message || "The capability catalogue request failed.";
          setCatalogueState("failed", "FAIL · HTTP " + result.response.status, message);
          return;
        }
      }
      const modules = moduleResult.payload.modules;
      const functions = functionResult.payload.functions;
      const tools = toolResult.payload.tools;
      const validModules = moduleResult.payload.schema_version === "1.0" &&
        Array.isArray(modules) && modules.every((item) => item &&
          typeof item.module_id === "string" && typeof item.version === "string" &&
          typeof item.domain === "string" && typeof item.maturity === "string" &&
          item.registration_status === "REGISTERED" &&
          item.execution_status === "NOT_ENABLED_BY_CATALOGUE" &&
          Array.isArray(item.operations));
      const validFunctions = functionResult.payload.schema_version === "1.0" &&
        Array.isArray(functions) && functions.every((item) => item &&
          typeof item.function_id === "string" && typeof item.module_id === "string" &&
          item.operation && Array.isArray(item.operation.required_permissions) &&
          item.execution_status === "NOT_ENABLED_BY_CATALOGUE");
      const validTools = toolResult.payload.schema_version === "1.0" &&
        Array.isArray(tools) && toolResult.payload.status === "UNKNOWN";
      if (!validModules || !validFunctions || !validTools) {
        setCatalogueState("unknown", "UNKNOWN · Invalid catalogue response", "The host returned data outside the supported metadata contract.");
        return;
      }
      renderCatalogue(modules, functions, tools);
      setCatalogueState(
        "unknown",
        "REGISTERED · " + modules.length + " module · " + functions.length + " function",
        "Metadata is registered. This does not grant permissions or establish execution readiness. Tool availability remains UNKNOWN."
      );
    } catch (_error) {
      setCatalogueState("failed", "FAIL · Catalogue request error", "The authenticated module and function catalogue could not be reached.");
    }
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

  async function loadSettings(token = activeToken) {
    if (!token) {
      setSettingsState("unknown", "UNKNOWN · Authentication required", "Check the authenticated local service before loading settings.");
      return;
    }
    setSettingsState("unknown", "PENDING · Loading", "Reading user preferences from local SQLite storage.");
    try {
      const { response, payload } = await requestJson("/v1/settings", "GET", token);
      if (!response.ok) {
        setSettingsState("failed", "FAIL · HTTP " + response.status, payload?.error?.message || "Settings could not be loaded.");
        return;
      }
      const record = payload?.settings;
      const values = record?.values;
      if (!record || record.scope !== "user" || !Number.isInteger(record.revision) ||
          !values || !["system", "light", "dark"].includes(values["appearance.theme"]) ||
          !["comfortable", "compact"].includes(values["appearance.density"]) ||
          typeof values["accessibility.reduced_motion"] !== "boolean") {
        setSettingsState("unknown", "UNKNOWN · Invalid response", "The settings endpoint returned data outside the supported user-preference contract.");
        return;
      }
      settingsRevision = record.revision;
      settingsTheme.value = values["appearance.theme"];
      settingsDensity.value = values["appearance.density"];
      settingsReducedMotion.checked = values["accessibility.reduced_motion"];
      settingsTheme.disabled = false;
      settingsDensity.disabled = false;
      settingsReducedMotion.disabled = false;
      settingsSaveButton.disabled = false;
      settingsReloadButton.hidden = true;
      applyTheme(settingsTheme.value);
      applyDensity(settingsDensity.value);
      applyReducedMotion(settingsReducedMotion.checked);
      setSettingsState("ready", "READY · Revision " + settingsRevision, "Saved user preferences were loaded from the authenticated local settings store.");
    } catch (_error) {
      setSettingsState("failed", "FAIL · Connection error", "The local settings API could not be reached or returned invalid JSON.");
    }
  }

  async function saveSettings() {
    if (!activeToken || settingsRevision === null || savingSettings) return;
    savingSettings = true;
    settingsSaveButton.disabled = true;
    const expectedRevision = settingsRevision;
    const values = {
      "appearance.theme": settingsTheme.value,
      "appearance.density": settingsDensity.value,
      "accessibility.reduced_motion": settingsReducedMotion.checked
    };
    try {
      const { response, payload } = await requestJson(
        "/v1/settings",
        "PUT",
        activeToken,
        { expected_revision: expectedRevision, values }
      );
      if (response.status === 409) {
        setSettingsState("failed", "FAIL · Revision conflict", "Your draft is preserved. Another client saved a newer revision; use Reload latest to replace this draft explicitly.");
        settingsReloadButton.hidden = false;
        return;
      }
      if (!response.ok || !payload?.settings || !Number.isInteger(payload.settings.revision)) {
        setSettingsState("failed", "FAIL · HTTP " + response.status, payload?.error?.message || "Settings save was not confirmed.");
        return;
      }
      const savedRevision = payload.settings.revision;
      const { response: verifyResponse, payload: verifyPayload } = await requestJson(
        "/v1/settings", "GET", activeToken
      );
      const persisted = verifyPayload?.settings;
      if (!verifyResponse.ok || !persisted || persisted.scope !== "user" ||
          persisted.revision !== savedRevision ||
          persisted.values?.["appearance.theme"] !== values["appearance.theme"] ||
          persisted.values?.["appearance.density"] !== values["appearance.density"] ||
          persisted.values?.["accessibility.reduced_motion"] !== values["accessibility.reduced_motion"]) {
        setSettingsState("unknown", "UNKNOWN · Persistence verification failed", "The write response was received, but a follow-up read did not confirm the saved settings. Your draft has been retained.");
        settingsReloadButton.hidden = false;
        return;
      }
      settingsRevision = persisted.revision;
      settingsReloadButton.hidden = true;
      applyTheme(values["appearance.theme"]);
      applyDensity(values["appearance.density"]);
      applyReducedMotion(values["accessibility.reduced_motion"]);
      setSettingsState("ready", "PASS · Saved revision " + settingsRevision, "Settings were read back successfully from local SQLite storage.");
    } catch (_error) {
      setSettingsState("failed", "FAIL · Save error", "Settings could not be saved or verified. Your draft remains on this page.");
    } finally {
      savingSettings = false;
      settingsSaveButton.disabled = settingsRevision === null;
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
    const nextTheme = settingsTheme.value === "light" ? "system" : "light";
    settingsTheme.value = nextTheme;
    applyTheme(nextTheme);
    markSettingsDirty();
  });

  settingsTheme.addEventListener("change", () => {
    applyTheme(settingsTheme.value);
    markSettingsDirty();
  });
  settingsDensity.addEventListener("change", () => {
    applyDensity(settingsDensity.value);
    markSettingsDirty();
  });
  settingsReducedMotion.addEventListener("change", () => {
    applyReducedMotion(settingsReducedMotion.checked);
    markSettingsDirty();
  });
  settingsSaveButton.addEventListener("click", saveSettings);
  settingsReloadButton.addEventListener("click", async () => {
    if (!activeToken) return;
    settingsReloadButton.disabled = true;
    try {
      await loadSettings(activeToken);
    } finally {
      settingsReloadButton.disabled = false;
    }
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
        setCatalogueState("failed", "FAIL · Authentication", "The service rejected the supplied token.");
        setSettingsState("failed", "FAIL · Authentication", "The service rejected the supplied token.");
        return;
      }
      if (payload.status === "READY" && payload.service === "cad-generator" && payload.api_version === "1.0") {
        setServiceState("ready", "PASS · CAD API READY", "Verified CAD Generator API v" + payload.api_version + ". This does not establish platform-wide health.");
        await Promise.all([
          checkPlatformStatus(token),
          loadWorkspaces(token),
          loadCatalogue(token),
          loadSettings(token)
        ]);
      } else {
        setServiceState("unknown", "UNKNOWN · Unexpected response", "The endpoint responded, but its payload did not match the known CAD health contract.");
      }
    } catch (_error) {
      setServiceState("failed", "FAIL · Connection error", "The local CAD Generator API could not be reached. Confirm that its loopback service is running.");
      setWorkspaceState("failed", "FAIL · Connection error", "The workspace API could not be reached.");
      setSettingsState("failed", "FAIL · Connection error", "The local settings API could not be reached.");
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
    settingsRevision = null;
    settingsTheme.value = "system";
    settingsDensity.value = "comfortable";
    settingsReducedMotion.checked = false;
    settingsTheme.disabled = true;
    settingsDensity.disabled = true;
    settingsReducedMotion.disabled = true;
    settingsSaveButton.disabled = true;
    settingsReloadButton.hidden = true;
    applyTheme("system");
    applyDensity("comfortable");
    applyReducedMotion(false);
    setSettingsState("unknown", "UNKNOWN · Not loaded", "The token was cleared; saved preferences are no longer accessible.");
    setServiceState("unknown", "UNKNOWN · Not checked", "Local token cleared from this page's memory.");
    setPlatformState("unknown", "UNKNOWN · Not checked", "Platform status was cleared; run Check service to verify it again.");
    setWorkspaceState("unknown", "UNKNOWN · Not loaded", "The token was cleared; workspace data is no longer accessible.");
    setCatalogueState("unknown", "UNKNOWN · Not loaded", "The token was cleared; catalogue data is no longer accessible.");
    moduleList.replaceChildren();
    functionList.replaceChildren();
    toolList.replaceChildren();
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
