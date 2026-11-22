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

  async function checkPlatformStatus(token) {
    setPlatformState("unknown", "PENDING · Checking platform", "Requesting the authenticated /v1/platform/status contract.");
    try {
      const response = await fetch("/v1/platform/status", {
        method: "GET",
        headers: { Authorization: "Bearer " + token },
        credentials: "omit",
        cache: "no-store",
        redirect: "error"
      });
      const payload = await response.json();
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
      setPlatformState(
        "partial",
        "PARTIAL · Platform integration",
        payload.limitations.join(" "),
        payload.components
      );
    } catch (_error) {
      setPlatformState("failed", "FAIL · Status request error", "The platform status endpoint could not be reached or returned invalid JSON.");
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
    if (light) {
      document.documentElement.dataset.theme = "light";
    } else {
      delete document.documentElement.dataset.theme;
    }
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
    checkButton.disabled = true;
    setServiceState("unknown", "PENDING · Checking", "Requesting the existing authenticated /health endpoint.");
    try {
      const response = await fetch("/health", {
        method: "GET",
        headers: { Authorization: "Bearer " + token },
        credentials: "omit",
        cache: "no-store",
        redirect: "error"
      });
      const payload = await response.json();
      if (!response.ok) {
        const message = payload && payload.error && typeof payload.error.message === "string"
          ? payload.error.message : "The service rejected the health request.";
        setServiceState("failed", "FAIL · HTTP " + response.status, message);
        return;
      }
      if (payload.status === "READY" && payload.service === "cad-generator" && payload.api_version === "1.0") {
        setServiceState("ready", "PASS · CAD API READY", "Verified CAD Generator API v" + payload.api_version + ". This does not establish platform-wide health.");
        await checkPlatformStatus(token);
      } else {
        setServiceState("unknown", "UNKNOWN · Unexpected response", "The endpoint responded, but its payload did not match the known CAD health contract.");
      }
    } catch (_error) {
      setServiceState("failed", "FAIL · Connection error", "The local CAD Generator API could not be reached. Confirm that its loopback service is running.");
    } finally {
      checkButton.disabled = false;
    }
  });

  clearButton.addEventListener("click", () => {
    tokenInput.value = "";
    setServiceState("unknown", "UNKNOWN · Not checked", "Local token cleared from this page's memory.");
    setPlatformState("unknown", "UNKNOWN · Not checked", "Platform status was cleared; run Check service to verify it again.");
    tokenInput.focus();
  });

  tokenInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") checkButton.click();
  });
})();
