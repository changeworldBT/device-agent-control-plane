const roles = ["planner", "classifier", "summarizer", "verifier"];
let state = { config: null, routes: [] };

const elements = {
  modeSelect: document.querySelector("#modeSelect"),
  agentModeSelect: document.querySelector("#agentModeSelect"),
  providerSelect: document.querySelector("#providerSelect"),
  providersList: document.querySelector("#providersList"),
  agentsList: document.querySelector("#agentsList"),
  routesList: document.querySelector("#routesList"),
  jsonEditor: document.querySelector("#jsonEditor"),
  statusLine: document.querySelector("#statusLine"),
  sourceBadge: document.querySelector("#sourceBadge"),
  openclawConfigPath: document.querySelector("#openclawConfigPath"),
  openclawWorkspacePath: document.querySelector("#openclawWorkspacePath"),
  openclawReport: document.querySelector("#openclawReport"),
  botChannelBadge: document.querySelector("#botChannelBadge"),
  botChannelSelect: document.querySelector("#botChannelSelect"),
  botChannelText: document.querySelector("#botChannelText"),
  botChannelsList: document.querySelector("#botChannelsList"),
  botChannelPreview: document.querySelector("#botChannelPreview"),
};

let openclawReport = null;
let botChannelState = null;

document.querySelectorAll(".surface").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".surface").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".mode-panel").forEach((item) => item.classList.add("hidden"));
    button.classList.add("active");
    document.querySelector(`#${button.dataset.panel}`).classList.remove("hidden");
  });
});

document.querySelector("#reloadButton").addEventListener("click", loadConfig);
document.querySelector("#previewButton").addEventListener("click", previewRoutes);
document.querySelector("#saveButton").addEventListener("click", saveConfig);
document.querySelector("#openclawPreviewButton").addEventListener("click", previewOpenClawMigration);
document.querySelector("#openclawApplyButton").addEventListener("click", applyOpenClawGeneratedConfig);
document.querySelector("#botChannelPreviewButton").addEventListener("click", previewBotChannel);

for (const select of [elements.modeSelect, elements.agentModeSelect, elements.providerSelect]) {
  select.addEventListener("change", () => {
    applyControlsToConfig();
    renderAll();
  });
}

elements.jsonEditor.addEventListener("input", () => {
  elements.statusLine.textContent = "JSON editor has unsaved changes.";
});

async function loadConfig() {
  setStatus("Loading configuration...");
  const response = await fetch("/api/config");
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || "Failed to load configuration.");
    return;
  }
  state = payload;
  renderAll();
  setStatus(`Loaded ${payload.source} config: ${payload.path}`);
}

async function loadOpenClawDefaults() {
  const response = await fetch("/api/openclaw/defaults");
  const payload = await response.json();
  if (!response.ok) return;
  elements.openclawConfigPath.value = payload.config_path || "";
  elements.openclawWorkspacePath.value = payload.workspace_path || "";
}

async function loadBotChannels() {
  const response = await fetch("/api/bot-channels");
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || "Failed to load bot channels.");
    return;
  }
  botChannelState = payload;
  renderBotChannels(payload);
}

async function previewRoutes() {
  const config = configFromEditor();
  if (!config) return;
  applyControlsToConfig(config);
  const response = await fetch("/api/route-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || "Route preview failed.");
    return;
  }
  state.config = config;
  state.routes = payload.routes;
  renderAll({ keepEditor: true });
  setStatus("Route preview updated.");
}

async function saveConfig() {
  const config = configFromEditor();
  if (!config) return;
  applyControlsToConfig(config);
  const response = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || "Save failed.");
    return;
  }
  state = payload;
  renderAll();
  setStatus(`Saved local config: ${payload.local_config_path}`);
}

async function previewOpenClawMigration() {
  const response = await fetch("/api/openclaw/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      config_path: elements.openclawConfigPath.value,
      workspace_path: elements.openclawWorkspacePath.value,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || "OpenClaw preview failed.");
    return;
  }
  openclawReport = payload;
  renderOpenClawReport(payload);
  setStatus("OpenClaw migration preview generated. Review before loading into editor.");
}

function applyOpenClawGeneratedConfig() {
  if (!openclawReport || !openclawReport.generated_config) {
    setStatus("Run OpenClaw migration preview first.");
    return;
  }
  state.config = openclawReport.generated_config;
  state.routes = [];
  elements.jsonEditor.value = JSON.stringify(openclawReport.generated_config, null, 2);
  renderAll({ keepEditor: true });
  setStatus("Generated OpenClaw config loaded into editor. Use Preview routes, then Save local config.");
}

async function previewBotChannel() {
  const response = await fetch("/api/bot-channels/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      channel: elements.botChannelSelect.value,
      text: elements.botChannelText.value,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || "Bot channel preview failed.");
    return;
  }
  renderBotChannelPreview(payload);
  setStatus(`Bot channel dry-run ready: ${payload.channel}`);
}

function renderAll(options = {}) {
  const config = state.config;
  if (!config) return;

  elements.sourceBadge.textContent = state.source || "draft";
  fillProviderSelect(config);
  elements.modeSelect.value = config.mode;
  elements.agentModeSelect.value = config.agents.mode;
  elements.providerSelect.value = config.active_provider || config.default_provider;
  renderProviders(config);
  renderAgents(config);
  renderRoutes(state.routes || []);

  if (!options.keepEditor) {
    elements.jsonEditor.value = JSON.stringify(config, null, 2);
  }
}

function fillProviderSelect(config) {
  const selected = elements.providerSelect.value || config.active_provider || config.default_provider;
  elements.providerSelect.innerHTML = Object.keys(config.providers)
    .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
    .join("");
  elements.providerSelect.value = config.providers[selected] ? selected : config.default_provider;
}

function renderProviders(config) {
  elements.providersList.innerHTML = Object.entries(config.providers)
    .map(([name, provider]) => {
      const caps = (provider.capabilities || []).join(", ") || "none";
      const model = provider.default_model || provider.default_model_env || "model via agent";
      return `<div class="item"><strong>${escapeHtml(name)}</strong><span>${escapeHtml(provider.kind)} | ${escapeHtml(model)}</span><span>${escapeHtml(caps)}</span></div>`;
    })
    .join("");
}

function renderAgents(config) {
  elements.agentsList.innerHTML = Object.entries(config.agents.members)
    .map(([name, agent]) => {
      const provider = agent.provider || config.active_provider || config.default_provider;
      const roleList = (agent.roles || []).join(", ") || "unassigned";
      const model = agent.model || agent.model_env || "provider default";
      return `<div class="item"><strong>${escapeHtml(name)}</strong><span>${escapeHtml(provider)} | ${escapeHtml(model)}</span><span>${escapeHtml(roleList)}</span></div>`;
    })
    .join("");
}

function renderRoutes(routes) {
  elements.routesList.innerHTML = routes
    .map((route) => {
      const key = `${route.role} -> ${route.agent_id}`;
      const value = `${route.provider_name} | ${route.model || route.model_env || "unset"}`;
      const secret = route.api_key_configured ? "api key configured" : "api key not configured";
      return `<div class="item"><strong>${escapeHtml(key)}</strong><span>${escapeHtml(value)}</span><span>${escapeHtml(secret)}</span></div>`;
    })
    .join("");
}

function renderOpenClawReport(report) {
  const agents = report.imported_agents || [];
  const warnings = report.warnings || [];
  elements.openclawReport.innerHTML = [
    `<div class="item"><strong>${agents.length} agent(s) mapped</strong><span>${escapeHtml((report.model_refs || []).join(", ") || "no model refs")}</span></div>`,
    `<div class="item"><strong>Workspace evidence</strong><span>${escapeHtml((report.workspace_files_found || []).length)} file(s) found</span><span>${escapeHtml((report.skipped_secret_paths || []).join(" | "))}</span></div>`,
    ...warnings.map((warning) => `<div class="item"><strong>Warning</strong><span>${escapeHtml(warning)}</span></div>`),
  ].join("");
}

function renderBotChannels(payload) {
  const channels = payload.channels || [];
  const defaultChannel = payload.config.default_channel;
  elements.botChannelBadge.textContent = payload.source || "example";
  elements.botChannelSelect.innerHTML = channels
    .map((channel) => `<option value="${escapeHtml(channel.name)}">${escapeHtml(channel.name)} · ${escapeHtml(channel.kind)}</option>`)
    .join("");
  elements.botChannelSelect.value = channels.find((channel) => channel.name === defaultChannel)?.name || channels[0]?.name || "";
  elements.botChannelsList.innerHTML = channels
    .map((channel) => {
      const status = channel.enabled ? "enabled" : "disabled";
      const caps = (channel.capabilities || []).join(", ") || "no capabilities";
      return `<div class="item"><strong>${escapeHtml(channel.name)} · ${escapeHtml(channel.kind)}</strong><span>${escapeHtml(status)}</span><span>${escapeHtml(caps)}</span></div>`;
    })
    .join("");
}

function renderBotChannelPreview(payload) {
  elements.botChannelPreview.innerHTML = [
    `<div class="item"><strong>${escapeHtml(payload.channel)} · ${escapeHtml(payload.kind)}</strong><span>${escapeHtml(payload.method)} ${escapeHtml(payload.endpoint || "gateway/sdk")}</span></div>`,
    `<div class="item"><strong>Payload</strong><span>${escapeHtml(JSON.stringify(payload.body))}</span></div>`,
    `<div class="item"><strong>Notes</strong><span>${escapeHtml((payload.notes || []).join(" | "))}</span></div>`,
  ].join("");
}

function applyControlsToConfig(config = state.config) {
  if (!config) return;
  config.mode = elements.modeSelect.value;
  config.agents.mode = elements.agentModeSelect.value;
  config.active_provider = elements.providerSelect.value;
}

function configFromEditor() {
  try {
    return JSON.parse(elements.jsonEditor.value);
  } catch (error) {
    setStatus(`Invalid JSON: ${error.message}`);
    return null;
  }
}

function setStatus(message) {
  elements.statusLine.textContent = message;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

loadOpenClawDefaults();
loadBotChannels();
loadConfig();
