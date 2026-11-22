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

  function setServiceState(kind, label, detail) {
    serviceState.className = "status-pill " + kind;
    serviceState.textContent = label;
    serviceDetail.textContent = detail;
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
    tokenInput.focus();
  });

  tokenInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") checkButton.click();
  });
})();
