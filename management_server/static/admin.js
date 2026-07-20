const state = { csrfToken: "", clients: [], selectedClientId: "", detail: null };
const commandIds = Array.from({ length: 10 }, (_, index) => `command_${["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"][index]}`);

function el(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  if (options.method && options.method !== "GET") headers["X-CSRF-Token"] = state.csrfToken;
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    window.location.href = "/admin/login";
    throw new Error("登录已失效");
  }
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
  return payload;
}

function showToast(message, type = "success") {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.dataset.type = type;
  toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("visible"), 3200);
}

function formatTime(timestamp) {
  if (!timestamp) return "从未";
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(timestamp * 1000));
}

async function loadSession() {
  const me = await api("/api/admin/me");
  state.csrfToken = me.csrf_token;
  document.querySelector("#admin-name").textContent = me.username.toUpperCase();
}

async function loadClients({ keepSelection = true } = {}) {
  const payload = await api("/api/admin/clients");
  state.clients = payload.clients;
  document.querySelector("#online-count").textContent = payload.online_count;
  document.querySelector("#total-count").textContent = payload.total_count;
  document.querySelector("#device-count").textContent = payload.clients.reduce((sum, item) => sum + Number(item.connected_devices || 0), 0);
  document.querySelector("#waveform-count").textContent = payload.clients.reduce((sum, item) => sum + Number(item.waveform_count || 0), 0);
  renderClientList();
  if (keepSelection && state.selectedClientId) await selectClient(state.selectedClientId, false);
}

function renderClientList() {
  const container = document.querySelector("#client-list");
  container.replaceChildren();
  if (!state.clients.length) {
    container.append(el("p", "empty-state", "还没有客户端完成注册"));
    return;
  }
  state.clients.forEach((client) => {
    const button = el("button", `client-item${client.client_id === state.selectedClientId ? " selected" : ""}`);
    const top = el("span", "client-item-top");
    top.append(el("i", client.online ? "online" : ""), el("strong", "", client.client_name || client.client_id.slice(0, 8)));
    const meta = el("span", "client-item-meta");
    meta.append(el("span", "", client.user_id || "未登录用户"), el("span", "", `${client.connected_devices || 0} 台设备`));
    const foot = el("span", "client-item-foot", client.online ? "实时在线" : `最后心跳 ${formatTime(client.last_seen)}`);
    button.append(top, meta, foot);
    button.addEventListener("click", () => selectClient(client.client_id));
    container.append(button);
  });
}

async function selectClient(clientId, rerenderList = true) {
  state.selectedClientId = clientId;
  state.detail = await api(`/api/admin/clients/${clientId}`);
  if (rerenderList) renderClientList();
  document.querySelector("#detail-empty").hidden = true;
  document.querySelector("#client-detail").hidden = false;
  renderDetail();
}

function renderDetail() {
  const detail = state.detail;
  document.querySelector("#detail-name").textContent = detail.client_name;
  document.querySelector("#detail-id").textContent = detail.client_id;
  document.querySelector("#detail-status").textContent = detail.online ? "在线" : "离线";
  document.querySelector("#detail-status-dot").className = detail.online ? "online" : "";
  document.querySelector("#detail-user").textContent = detail.user_id || "未登录";
  document.querySelector("#detail-last-seen").textContent = formatTime(detail.last_seen);
  const commandChip = document.querySelector("#command-channel");
  commandChip.textContent = detail.command_connected ? "指令通道已连接" : "指令通道未连接";
  commandChip.classList.toggle("positive", detail.command_connected);
  document.querySelector("#waveform-summary").textContent = `${detail.waveforms.length} 个波形`;
  renderCommands();
  renderDevices();
  renderHistory();
}

function renderCommands() {
  const container = document.querySelector("#command-grid");
  container.replaceChildren();
  const available = new Set(state.detail.command_ids || []);
  commandIds.forEach((commandId, index) => {
    const button = el("button", "command-button");
    button.append(el("span", "", String(index + 1).padStart(2, "0")), el("strong", "", commandId));
    button.disabled = !state.detail.online || !state.detail.command_connected || !available.has(commandId);
    button.addEventListener("click", () => runCommand("command.send", { command_id: commandId }, `发送 ${commandId}`));
    container.append(button);
  });
}

function compatibleWaveforms(device) {
  return state.detail.waveforms.filter((waveform) => {
    if (device.device_type === "toy" && waveform.waveform_type !== "toy") return false;
    if (device.device_type !== "toy" && waveform.waveform_type !== "ems") return false;
    if (waveform.device_family === "gcq") return device.protocol.includes("gcq");
    if (waveform.device_family === "toy") return !device.protocol.includes("gcq");
    return true;
  });
}

function renderDevices() {
  const container = document.querySelector("#device-list");
  container.replaceChildren();
  if (!state.detail.devices.length) {
    container.append(el("p", "empty-state", "客户端还没有上报蓝牙设备"));
    return;
  }
  state.detail.devices.forEach((device) => {
    const card = el("article", "device-card");
    const heading = el("div", "device-card-heading");
    const title = el("div");
    title.append(el("span", "device-type", `${device.device_type || "unknown"} / ${device.protocol || "-"}`), el("h4", "", device.name || device.device_id));
    heading.append(title, el("span", `device-state${device.connected ? " connected" : ""}`, device.connected ? "已连接" : "未连接"));
    const select = el("select", "waveform-select");
    const placeholder = el("option", "", "选择可用波形");
    placeholder.value = "";
    select.append(placeholder);
    compatibleWaveforms(device).forEach((waveform) => {
      const option = el("option", "", `${waveform.name} · ${waveform.builtin ? "内置" : "自定义"}`);
      option.value = waveform.waveform_id;
      select.append(option);
    });
    const actions = el("div", "device-actions");
    const play = el("button", "primary-button small", "播放波形");
    play.disabled = !state.detail.online || !device.connected;
    play.addEventListener("click", () => {
      if (!select.value) return showToast("请先选择波形", "error");
      runCommand("waveform.play", { device_id: device.device_id, waveform_id: select.value }, "播放波形");
    });
    const stop = el("button", "danger-button", "停止输出");
    stop.disabled = !state.detail.online || !device.connected;
    stop.addEventListener("click", () => runCommand("waveform.stop", { device_id: device.device_id }, "停止输出"));
    const disconnect = el("button", "ghost-button", "断开设备");
    disconnect.disabled = !state.detail.online || !device.connected;
    disconnect.addEventListener("click", () => {
      if (window.confirm(`确定断开 ${device.name || device.device_id}？`)) runCommand("device.disconnect", { device_id: device.device_id }, "断开设备");
    });
    actions.append(play, stop, disconnect);
    card.append(heading, select, actions);
    if (!device.protocol.includes("gcq")) {
      card.append(buildFixedOutputControl(device));
    } else {
      card.append(el("p", "fixed-output-note", "GCQ 设备包含多个独立通道，不提供单一固定强度控制。"));
    }
    container.append(card);
  });
}

function buildFixedOutputControl(device) {
  const maxStrength = device.device_type === "toy" ? 20 : 180;
  const wrapper = el("div", "fixed-output-control");
  const heading = el("div", "fixed-output-heading");
  heading.append(el("strong", "", "固定强度输出"), el("span", "", `范围 1–${maxStrength} / 最长 60 秒`));

  const strengthLabel = el("label", "fixed-field");
  strengthLabel.append(el("span", "", "强度"));
  const strengthInput = el("input");
  strengthInput.type = "number";
  strengthInput.min = "1";
  strengthInput.max = String(maxStrength);
  strengthInput.value = String(device.device_type === "toy" ? 5 : 40);
  strengthLabel.append(strengthInput);

  const durationLabel = el("label", "fixed-field");
  durationLabel.append(el("span", "", "时长（秒）"));
  const durationInput = el("input");
  durationInput.type = "number";
  durationInput.min = "1";
  durationInput.max = "60";
  durationInput.value = "5";
  durationLabel.append(durationInput);

  const trigger = el("button", "fixed-trigger-button", "开始固定输出");
  trigger.disabled = !state.detail.online || !device.connected;
  trigger.addEventListener("click", () => {
    const strength = Number(strengthInput.value);
    const durationSeconds = Number(durationInput.value);
    if (!Number.isInteger(strength) || strength < 1 || strength > maxStrength) return showToast(`强度必须是 1 到 ${maxStrength} 的整数`, "error");
    if (!Number.isInteger(durationSeconds) || durationSeconds < 1 || durationSeconds > 60) return showToast("时长必须是 1 到 60 秒的整数", "error");
    if (!window.confirm(`确定以强度 ${strength} 持续输出 ${durationSeconds} 秒？`)) return;
    runCommand("output.fixed", {
      device_id: device.device_id,
      strength,
      duration_seconds: durationSeconds,
    }, "固定强度输出");
  });
  wrapper.append(heading, strengthLabel, durationLabel, trigger);
  return wrapper;
}

function renderHistory() {
  const container = document.querySelector("#command-history");
  container.replaceChildren();
  if (!state.detail.commands.length) {
    container.append(el("p", "empty-state", "暂无远程操作记录"));
    return;
  }
  state.detail.commands.forEach((command) => {
    const row = el("div", "history-row");
    const status = command.status === "pending" ? "等待" : command.success ? "成功" : "失败";
    row.append(
      el("span", `history-status ${command.success ? "success" : command.status === "pending" ? "pending" : "failed"}`, status),
      el("strong", "", command.action),
      el("span", "history-message", command.message || "等待客户端返回"),
      el("time", "", formatTime(command.created_at)),
    );
    container.append(row);
  });
}

async function runCommand(action, args, label) {
  try {
    showToast(`${label}：正在等待客户端返回`);
    const result = await api(`/api/admin/clients/${state.selectedClientId}/commands`, { method: "POST", body: JSON.stringify({ action, args }) });
    showToast(result.message || `${label}成功`, result.success ? "success" : "error");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    await loadClients();
  }
}

document.querySelector("#refresh-button").addEventListener("click", () => loadClients());
document.querySelector("#logout-button").addEventListener("click", async () => {
  await api("/api/admin/logout", { method: "POST" });
  window.location.href = "/admin/login";
});

window.setInterval(() => { document.querySelector("#clock").textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false }); }, 1000);
window.setInterval(() => loadClients().catch(() => {}), 5000);

(async () => {
  try {
    await loadSession();
    await loadClients({ keepSelection: false });
  } catch (error) {
    showToast(error.message, "error");
  }
})();
