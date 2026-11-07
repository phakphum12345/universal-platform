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
  const buttons = ["save", "list", "load", "regenerate"].map(byId);
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
})();
