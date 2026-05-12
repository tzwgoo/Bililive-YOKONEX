const statusPill = document.getElementById("status-pill");
const messageText = document.getElementById("message-text");
const modeLabel = document.getElementById("mode-label");
const roomId = document.getElementById("room-id");
const anchorName = document.getElementById("anchor-name");
const configLoaded = document.getElementById("config-loaded");
const sessionModeSelect = document.getElementById("session-mode");
const sessionValueLabel = document.getElementById("session-value-label");
const sessionValueInput = document.getElementById("session-value-input");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const commandStatusPill = document.getElementById("command-status-pill");
const commandMessageText = document.getElementById("command-message-text");
const commandWsUrlInput = document.getElementById("command-ws-url");
const commandUidInput = document.getElementById("command-uid");
const commandTokenInput = document.getElementById("command-token");
const commandConnectBtn = document.getElementById("command-connect-btn");
const commandDisconnectBtn = document.getElementById("command-disconnect-btn");
const commandStatusUid = document.getElementById("command-status-uid");
const commandUserId = document.getElementById("command-user-id");
const commandLastLoginAt = document.getElementById("command-last-login-at");

const giftEvents = document.getElementById("gift-events");
const danmakuEvents = document.getElementById("danmaku-events");
const likeEvents = document.getElementById("like-events");
const giftCount = document.getElementById("gift-count");
const danmakuCount = document.getElementById("danmaku-count");
const likeCount = document.getElementById("like-count");
const lastEventAt = document.getElementById("last-event-at");
const lastHeartbeatAt = document.getElementById("last-heartbeat-at");
const lastCommandMessage = document.getElementById("last-command-message");
const commandWsUrlStorageKey = "biliLive.commandWsUrl";
const commandUidStorageKey = "biliLive.commandUid";
const sessionModeOptions = {
  open_live: {
    label: "主播身份码",
    placeholder: "请输入主播身份码 code",
  },
  third_party: {
    label: "房间长 ID",
    placeholder: "请输入直播间房间长 ID room_id",
  },
};

function restoreCommandForm() {
  const savedWsUrl = window.localStorage.getItem(commandWsUrlStorageKey);
  const savedUid = window.localStorage.getItem(commandUidStorageKey);
  if (savedWsUrl) {
    commandWsUrlInput.value = savedWsUrl;
  }
  if (savedUid) {
    commandUidInput.value = savedUid;
  }
}

function persistCommandForm() {
  window.localStorage.setItem(commandWsUrlStorageKey, commandWsUrlInput.value.trim());
  window.localStorage.setItem(commandUidStorageKey, commandUidInput.value.trim());
}

function formatTimestamp(value) {
  if (!value) {
    return "-";
  }
  return new Date(value * 1000).toLocaleString("zh-CN", { hour12: false });
}

function updateStatusTone(element, status) {
  element.dataset.state = status || "idle";
}

function updateSessionModeForm() {
  const mode = sessionModeSelect.value;
  const modeConfig = sessionModeOptions[mode] || sessionModeOptions.open_live;
  sessionValueLabel.textContent = modeConfig.label;
  sessionValueInput.placeholder = modeConfig.placeholder;
}

function updateEventCounts() {
  giftCount.textContent = String(giftEvents.children.length);
  danmakuCount.textContent = String(danmakuEvents.children.length);
  likeCount.textContent = String(likeEvents.children.length);
}

function prependEvent(container, html) {
  const wrapper = document.createElement("article");
  wrapper.className = "event-card";
  wrapper.innerHTML = html;
  container.prepend(wrapper);
  while (container.children.length > 20) {
    container.removeChild(container.lastChild);
  }
  updateEventCounts();
}

function renderEvent(event) {
  if (event.event_type === "gift") {
    const dispatch = event.command_dispatch || {};
    const dispatchClass = dispatch.ok === false ? " dispatch-failed" : dispatch.command_id ? " dispatch-success" : "";
    const commandText = dispatch.command_id
      ? `<small class="dispatch-chip${dispatchClass}">槽位 ${dispatch.command_id} · ${dispatch.message || "已处理"}</small>`
      : "";
    prependEvent(
      giftEvents,
      `<div class="event-card-head"><small>${formatTimestamp(event.timestamp)}</small></div><h3>${event.uname || "匿名用户"}</h3><p>${event.payload.gift_name} x ${event.payload.gift_num}</p><small>价值 ${event.payload.r_price}</small>${commandText}`
    );
    return;
  }
  if (event.event_type === "danmaku") {
    prependEvent(
      danmakuEvents,
      `<div class="event-card-head"><small>${formatTimestamp(event.timestamp)}</small></div><h3>${event.uname || "匿名用户"}</h3><p>${event.payload.msg || ""}</p>`
    );
    return;
  }
  if (event.event_type === "like") {
    prependEvent(
      likeEvents,
      `<div class="event-card-head"><small>${formatTimestamp(event.timestamp)}</small></div><h3>${event.uname || "匿名用户"}</h3><p>${event.payload.like_text || "点赞"} (${event.payload.like_count || 0})</p>`
    );
    return;
  }
  if (event.event_type === "system") {
    messageText.textContent = event.payload.message || "互动状态已变更";
  }
}

async function refreshStatus() {
  const response = await fetch("/api/status");
  const data = await response.json();
  statusPill.textContent = data.status;
  updateStatusTone(statusPill, data.status);
  messageText.textContent = data.message || "运行正常";
  modeLabel.textContent = data.mode_label || "官方 open-live";
  roomId.textContent = data.room_id || "-";
  anchorName.textContent = data.anchor_name || "-";
  configLoaded.textContent = data.config_loaded ? "已加载" : "缺失";
  lastEventAt.textContent = formatTimestamp(data.last_event_at);
  lastHeartbeatAt.textContent = formatTimestamp(data.last_heartbeat_at);
  lastCommandMessage.textContent = data.last_command_message || "-";
  startBtn.disabled = !data.can_start;
  stopBtn.disabled = !data.can_stop;
  if (data.mode && sessionModeOptions[data.mode]) {
    sessionModeSelect.value = data.mode;
    updateSessionModeForm();
  }
}

async function refreshCommandStatus() {
  const response = await fetch("/api/command/status");
  const data = await response.json();
  commandStatusPill.textContent = data.status;
  updateStatusTone(commandStatusPill, data.status);
  commandMessageText.textContent = data.message || "未登录";
  commandStatusUid.textContent = data.uid || "-";
  commandUserId.textContent = data.user_id || "-";
  commandLastLoginAt.textContent = formatTimestamp(data.last_login_at);
  commandConnectBtn.disabled = !data.can_connect;
  commandDisconnectBtn.disabled = !data.can_disconnect;

  if (!commandWsUrlInput.value && data.ws_url) {
    commandWsUrlInput.value = data.ws_url;
  }
  if (!commandUidInput.value && data.uid) {
    commandUidInput.value = data.uid;
  }
}

startBtn.addEventListener("click", async () => {
  startBtn.disabled = true;
  const mode = sessionModeSelect.value;
  const value = sessionValueInput.value.trim();
  if (!value) {
    messageText.textContent = `${sessionValueLabel.textContent}不能为空`;
    await refreshStatus();
    return;
  }
  const response = await fetch("/api/session/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode: sessionModeSelect.value,
      value: sessionValueInput.value,
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    messageText.textContent = payload.detail || "启动失败";
    await refreshStatus();
    return;
  }
  await refreshStatus();
});

stopBtn.addEventListener("click", async () => {
  stopBtn.disabled = true;
  await fetch("/api/session/stop", { method: "POST" });
  await refreshStatus();
});

commandConnectBtn.addEventListener("click", async () => {
  commandConnectBtn.disabled = true;
  persistCommandForm();
  const response = await fetch("/api/command/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ws_url: commandWsUrlInput.value,
      uid: commandUidInput.value,
      token: commandTokenInput.value,
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    commandMessageText.textContent = payload.detail || "指令通道登录失败";
    await refreshCommandStatus();
    return;
  }
  commandTokenInput.value = "";
  await refreshCommandStatus();
});

commandDisconnectBtn.addEventListener("click", async () => {
  commandDisconnectBtn.disabled = true;
  await fetch("/api/command/disconnect", { method: "POST" });
  await refreshCommandStatus();
});

sessionModeSelect.addEventListener("change", () => {
  updateSessionModeForm();
});

const source = new EventSource("/api/events/stream");
source.onmessage = (event) => {
  renderEvent(JSON.parse(event.data));
};

source.onerror = () => {
  messageText.textContent = "实时事件流暂时断开，页面会继续自动刷新状态";
};

async function refreshDashboard() {
  await Promise.all([refreshStatus(), refreshCommandStatus()]);
}

restoreCommandForm();
updateSessionModeForm();
updateEventCounts();
refreshDashboard();
setInterval(refreshDashboard, 5000);
