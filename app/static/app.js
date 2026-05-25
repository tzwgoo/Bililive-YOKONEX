const statusPill = document.getElementById("status-pill");
const messageText = document.getElementById("message-text");
const roomId = document.getElementById("room-id");
const anchorName = document.getElementById("anchor-name");
const sessionModeSelect = document.getElementById("session-mode");
const triggerModeSelect = document.getElementById("trigger-mode");
const likeMultipleInput = document.getElementById("like-multiple");
const danmakuEnabledSelect = document.getElementById("danmaku-enabled");
const danmakuKeywordsInput = document.getElementById("danmaku-keywords");
const danmakuCooldownSecondsInput = document.getElementById("danmaku-cooldown-seconds");
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
const bluetoothStatusPill = document.getElementById("bluetooth-status-pill");
const bluetoothMessageText = document.getElementById("bluetooth-message-text");
const bluetoothScanBtn = document.getElementById("bluetooth-scan-btn");
const bluetoothDisconnectBtn = document.getElementById("bluetooth-disconnect-btn");
const bluetoothDevices = document.getElementById("bluetooth-devices");
const bluetoothWaveforms = document.getElementById("bluetooth-waveforms");
const bluetoothRules = document.getElementById("bluetooth-rules");

const giftEvents = document.getElementById("gift-events");
const danmakuEvents = document.getElementById("danmaku-events");
const likeEvents = document.getElementById("like-events");
const giftCount = document.getElementById("gift-count");
const danmakuCount = document.getElementById("danmaku-count");
const likeCount = document.getElementById("like-count");
const lastEventAt = document.getElementById("last-event-at");
const triggerModeLabel = document.getElementById("trigger-mode-label");
const likeMultipleLabel = document.getElementById("like-multiple-label");
const danmakuEnabledLabel = document.getElementById("danmaku-enabled-label");
const danmakuKeywordsLabel = document.getElementById("danmaku-keywords-label");
const danmakuCooldownSecondsLabel = document.getElementById("danmaku-cooldown-seconds-label");
const fixedDanmakuCommandId = "danmaku_trigger";
const commandWsUrlStorageKey = "biliLive.commandWsUrl";
const commandUidStorageKey = "biliLive.commandUid";
const commandTokenStorageKey = "biliLive.commandToken";
const sessionModeStorageKey = "biliLive.sessionMode";
const triggerModeStorageKey = "biliLive.triggerMode";
const likeMultipleStorageKey = "biliLive.likeMultiple";
const danmakuEnabledStorageKey = "biliLive.danmakuEnabled";
const danmakuKeywordsStorageKey = "biliLive.danmakuKeywords";
const danmakuCooldownSecondsStorageKey = "biliLive.danmakuCooldownSeconds";
const triggerModeOptions = {
  by_quantity: "按礼物数量触发",
  single: "单次触发",
};
const sessionModeOptions = {
  open_live: {
    modeLabel: "官方 open-live",
    label: "主播身份码",
    placeholder: "请输入主播身份码 code",
  },
  third_party: {
    modeLabel: "第三方房间消息流",
    label: "房间长 ID",
    placeholder: "请输入直播间房间长 ID room_id",
  },
};

function restoreCommandForm() {
  const savedWsUrl = window.localStorage.getItem(commandWsUrlStorageKey);
  const savedUid = window.localStorage.getItem(commandUidStorageKey);
  const savedToken = window.localStorage.getItem(commandTokenStorageKey);
  if (savedWsUrl) {
    commandWsUrlInput.value = savedWsUrl;
  }
  if (savedUid) {
    commandUidInput.value = savedUid;
  }
  if (savedToken) {
    commandTokenInput.value = savedToken;
  }
}

function persistCommandForm() {
  window.localStorage.setItem(commandWsUrlStorageKey, commandWsUrlInput.value.trim());
  window.localStorage.setItem(commandUidStorageKey, commandUidInput.value.trim());
  window.localStorage.setItem(commandTokenStorageKey, commandTokenInput.value);
}

function restoreSessionDraft() {
  const savedSessionMode = window.localStorage.getItem(sessionModeStorageKey);
  const savedTriggerMode = window.localStorage.getItem(triggerModeStorageKey);
  const savedLikeMultiple = window.localStorage.getItem(likeMultipleStorageKey);
  const savedDanmakuEnabled = window.localStorage.getItem(danmakuEnabledStorageKey);
  const savedDanmakuKeywords = window.localStorage.getItem(danmakuKeywordsStorageKey);
  const savedDanmakuCooldownSeconds = window.localStorage.getItem(danmakuCooldownSecondsStorageKey);
  if (savedSessionMode && sessionModeOptions[savedSessionMode]) {
    sessionModeSelect.value = savedSessionMode;
  }
  if (savedTriggerMode && triggerModeOptions[savedTriggerMode]) {
    triggerModeSelect.value = savedTriggerMode;
  }
  if (savedLikeMultiple && Number(savedLikeMultiple) > 0) {
    likeMultipleInput.value = savedLikeMultiple;
  } else if (!likeMultipleInput.value) {
    likeMultipleInput.value = "100";
  }
  if (savedDanmakuEnabled === "true" || savedDanmakuEnabled === "false") {
    danmakuEnabledSelect.value = savedDanmakuEnabled;
  }
  if (savedDanmakuKeywords) {
    danmakuKeywordsInput.value = savedDanmakuKeywords;
  }
  if (savedDanmakuCooldownSeconds && Number(savedDanmakuCooldownSeconds) >= 0) {
    danmakuCooldownSecondsInput.value = savedDanmakuCooldownSeconds;
  } else if (!danmakuCooldownSecondsInput.value) {
    danmakuCooldownSecondsInput.value = "0";
  }
}

function persistSessionDraft() {
  window.localStorage.setItem(sessionModeStorageKey, sessionModeSelect.value);
  window.localStorage.setItem(triggerModeStorageKey, triggerModeSelect.value);
  const normalizedLikeMultiple = String(Math.max(1, Number(likeMultipleInput.value || 100) || 100));
  likeMultipleInput.value = normalizedLikeMultiple;
  window.localStorage.setItem(likeMultipleStorageKey, normalizedLikeMultiple);
  const normalizedDanmakuCooldownSeconds = String(Math.max(0, Number(danmakuCooldownSecondsInput.value || 0) || 0));
  danmakuCooldownSecondsInput.value = normalizedDanmakuCooldownSeconds;
  window.localStorage.setItem(danmakuEnabledStorageKey, danmakuEnabledSelect.value);
  window.localStorage.setItem(danmakuKeywordsStorageKey, danmakuKeywordsInput.value.trim());
  window.localStorage.setItem(danmakuCooldownSecondsStorageKey, normalizedDanmakuCooldownSeconds);
}

function updateStatusDraftLabels(
  isRunning,
  serverMode,
  serverTriggerMode,
  serverLikeMultiple,
  serverDanmakuEnabled,
  serverDanmakuKeywords,
  serverDanmakuCommandId,
  serverDanmakuCooldownSeconds
) {
  if (isRunning) {
    triggerModeLabel.textContent = triggerModeOptions[serverTriggerMode] || triggerModeOptions.by_quantity;
    likeMultipleLabel.textContent = String(serverLikeMultiple || 100);
    danmakuEnabledLabel.textContent = serverDanmakuEnabled ? "开启" : "关闭";
    danmakuKeywordsLabel.textContent = serverDanmakuKeywords || "-";
    danmakuCooldownSecondsLabel.textContent = `${serverDanmakuCooldownSeconds || 0} 秒`;
    return;
  }

  triggerModeLabel.textContent = triggerModeOptions[triggerModeSelect.value] || triggerModeOptions.by_quantity;
  likeMultipleLabel.textContent = String(Math.max(1, Number(likeMultipleInput.value || 100) || 100));
  danmakuEnabledLabel.textContent = danmakuEnabledSelect.value === "true" ? "开启" : "关闭";
  danmakuKeywordsLabel.textContent = danmakuKeywordsInput.value.trim() || "-";
  danmakuCooldownSecondsLabel.textContent = `${Math.max(0, Number(danmakuCooldownSecondsInput.value || 0) || 0)} 秒`;
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatGiftValue(payload) {
  const giftNum = Number(payload.gift_num || 0) || 0;
  const unitPrice = Number(payload.price || 0) || 0;
  const totalPrice = Number(payload.r_price || 0) || 0;

  if (giftNum > 1 && unitPrice > 0 && totalPrice > 0) {
    return `单价 ${unitPrice} · 总价值 ${totalPrice}`;
  }
  if (unitPrice > 0) {
    return `价值 ${unitPrice}`;
  }
  if (totalPrice > 0) {
    return `价值 ${totalPrice}`;
  }
  return "价值 0";
}

function renderEvent(event) {
  if (event.event_type === "gift") {
    const dispatch = event.command_dispatch || {};
    const dispatchClass = dispatch.ok === false ? " dispatch-failed" : dispatch.command_id ? " dispatch-success" : "";
    const dispatchTimes = dispatch.trigger_count > 1 ? ` · 触发 ${dispatch.trigger_count} 次` : "";
    const commandText = dispatch.command_id
      ? `<small class="dispatch-chip${dispatchClass}">指令 ${dispatch.command_id}${dispatchTimes} · ${dispatch.message || "已处理"}</small>`
      : "";
    prependEvent(
      giftEvents,
      `<div class="event-card-head"><small>${formatTimestamp(event.timestamp)}</small></div><h3>${event.uname || "匿名用户"}</h3><p>${event.payload.gift_name} x ${event.payload.gift_num}</p><small>${formatGiftValue(event.payload)}</small>${commandText}`
    );
    return;
  }
  if (event.event_type === "danmaku") {
    const dispatch = event.command_dispatch || {};
    const dispatchClass = dispatch.ok === false ? " dispatch-failed" : dispatch.command_id ? " dispatch-success" : "";
    const commandText = dispatch.command_id
      ? `<small class="dispatch-chip${dispatchClass}">指令 ${dispatch.command_id} · ${dispatch.message || "已处理"}</small>`
      : "";
    prependEvent(
      danmakuEvents,
      `<div class="event-card-head"><small>${formatTimestamp(event.timestamp)}</small></div><h3>${event.uname || "匿名用户"}</h3><p>${event.payload.msg || ""}</p>${commandText}`
    );
    return;
  }
  if (event.event_type === "like") {
    const dispatch = event.command_dispatch || {};
    const dispatchClass = dispatch.ok === false ? " dispatch-failed" : dispatch.command_id ? " dispatch-success" : "";
    const dispatchTimes = dispatch.trigger_count > 1 ? ` · 触发 ${dispatch.trigger_count} 次` : "";
    const commandText = dispatch.command_id
      ? `<small class="dispatch-chip${dispatchClass}">指令 ${dispatch.command_id}${dispatchTimes} · ${dispatch.message || "已处理"}</small>`
      : "";
    prependEvent(
      likeEvents,
      `<div class="event-card-head"><small>${formatTimestamp(event.timestamp)}</small></div><h3>${event.uname || "匿名用户"}</h3><p>${event.payload.like_text || "点赞"} (${event.payload.like_count || 0})</p>${commandText}`
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
  roomId.textContent = data.room_id || "-";
  anchorName.textContent = data.anchor_name || "-";
  lastEventAt.textContent = formatTimestamp(data.last_event_at);
  startBtn.disabled = !data.can_start;
  stopBtn.disabled = !data.can_stop;
  if (data.can_stop) {
    if (data.mode && sessionModeOptions[data.mode]) {
      sessionModeSelect.value = data.mode;
    }
    if (data.trigger_mode && triggerModeOptions[data.trigger_mode]) {
      triggerModeSelect.value = data.trigger_mode;
    }
    if (data.like_multiple) {
      likeMultipleInput.value = String(data.like_multiple);
    }
    if (typeof data.danmaku_enabled === "boolean") {
      danmakuEnabledSelect.value = data.danmaku_enabled ? "true" : "false";
    }
    if (typeof data.danmaku_keywords === "string") {
      danmakuKeywordsInput.value = data.danmaku_keywords;
    }
    if (typeof data.danmaku_cooldown_seconds === "number") {
      danmakuCooldownSecondsInput.value = String(data.danmaku_cooldown_seconds);
    }
    persistSessionDraft();
  } else {
    restoreSessionDraft();
  }
  updateSessionModeForm();
  updateStatusDraftLabels(
    data.can_stop,
    data.mode,
    data.trigger_mode,
    data.like_multiple,
    data.danmaku_enabled,
    data.danmaku_keywords,
    data.danmaku_command_id,
    data.danmaku_cooldown_seconds
  );
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

function renderBluetoothDevices(devices) {
  if (!Array.isArray(devices) || devices.length === 0) {
    bluetoothDevices.innerHTML = '<p class="mini-empty">暂无设备，点击“扫描设备”开始搜索。</p>';
    return;
  }
  bluetoothDevices.innerHTML = devices
    .map((device) => {
      const action = device.connected
        ? '<span class="mini-chip">当前设备</span>'
        : `<button class="mini-action" data-device-id="${escapeHtml(device.device_id)}">连接</button>`;
      return `<article class="mini-item"><div><strong>${escapeHtml(device.name)}</strong><small>${escapeHtml(device.protocol)} · RSSI ${escapeHtml(device.rssi)}</small></div>${action}</article>`;
    })
    .join("");
}

function renderBluetoothWaveforms(waveforms) {
  if (!Array.isArray(waveforms) || waveforms.length === 0) {
    bluetoothWaveforms.innerHTML = '<p class="mini-empty">暂无波形配置。</p>';
    return;
  }
  bluetoothWaveforms.innerHTML = waveforms
    .map((waveform) => {
      const stepCount = Array.isArray(waveform.steps) ? waveform.steps.length : 0;
      const tag = waveform.builtin ? "内置" : "自定义";
      return `<article class="mini-item"><div><strong>${escapeHtml(waveform.name)}</strong><small>${escapeHtml(tag)} · ${stepCount} 步</small></div></article>`;
    })
    .join("");
}

function renderBluetoothRules(rules) {
  if (!Array.isArray(rules) || rules.length === 0) {
    bluetoothRules.innerHTML = '<p class="mini-empty">暂无事件规则。</p>';
    return;
  }
  bluetoothRules.innerHTML = rules
    .map((rule) => `<article class="mini-item"><div><strong>${escapeHtml(rule.event_type || "unknown")}</strong><small>${rule.enabled ? "已启用" : "未启用"} · 波形 ${escapeHtml(rule.waveform_id || "-")}</small></div></article>`)
    .join("");
}

async function connectBluetoothDevice(deviceId) {
  const response = await fetch("/api/bluetooth/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device_id: deviceId }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    bluetoothMessageText.textContent = payload.detail || "蓝牙连接失败";
    await refreshBluetoothStatus();
    return;
  }
  await refreshBluetoothStatus();
}

async function refreshBluetoothStatus() {
  const response = await fetch("/api/bluetooth/status");
  const data = await response.json();
  bluetoothStatusPill.textContent = data.connected ? "connected" : "idle";
  updateStatusTone(bluetoothStatusPill, data.connected ? "connected" : "idle");
  bluetoothMessageText.textContent = data.message || "未连接";
  bluetoothDisconnectBtn.disabled = !data.connected;
  renderBluetoothDevices(data.devices || []);
  renderBluetoothWaveforms(data.waveforms || []);
  renderBluetoothRules(data.rules || []);
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
      trigger_mode: triggerModeSelect.value,
      like_multiple: Math.max(1, Number(likeMultipleInput.value || 100) || 100),
      danmaku_enabled: danmakuEnabledSelect.value === "true",
      danmaku_keywords: danmakuKeywordsInput.value.trim(),
      danmaku_cooldown_seconds: Math.max(0, Number(danmakuCooldownSecondsInput.value || 0) || 0),
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
  await refreshCommandStatus();
});

commandDisconnectBtn.addEventListener("click", async () => {
  commandDisconnectBtn.disabled = true;
  await fetch("/api/command/disconnect", { method: "POST" });
  await refreshCommandStatus();
});

bluetoothScanBtn.addEventListener("click", async () => {
  bluetoothScanBtn.disabled = true;
  const response = await fetch("/api/bluetooth/scan", { method: "POST" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    bluetoothMessageText.textContent = payload.detail || "蓝牙扫描失败";
  }
  bluetoothScanBtn.disabled = false;
  await refreshBluetoothStatus();
});

bluetoothDisconnectBtn.addEventListener("click", async () => {
  bluetoothDisconnectBtn.disabled = true;
  await fetch("/api/bluetooth/disconnect", { method: "POST" });
  await refreshBluetoothStatus();
});

bluetoothDevices.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const deviceId = target.dataset.deviceId;
  if (!deviceId) {
    return;
  }
  target.setAttribute("disabled", "disabled");
  await connectBluetoothDevice(deviceId);
});

sessionModeSelect.addEventListener("change", () => {
  persistSessionDraft();
  updateSessionModeForm();
});

triggerModeSelect.addEventListener("change", () => {
  persistSessionDraft();
});

likeMultipleInput.addEventListener("change", () => {
  persistSessionDraft();
  updateStatusDraftLabels(false);
});

danmakuEnabledSelect.addEventListener("change", () => {
  persistSessionDraft();
  updateStatusDraftLabels(false);
});

danmakuKeywordsInput.addEventListener("change", () => {
  persistSessionDraft();
  updateStatusDraftLabels(false);
});

danmakuCooldownSecondsInput.addEventListener("change", () => {
  persistSessionDraft();
  updateStatusDraftLabels(false);
});

commandWsUrlInput.addEventListener("change", persistCommandForm);
commandUidInput.addEventListener("change", persistCommandForm);
commandTokenInput.addEventListener("change", persistCommandForm);

const source = new EventSource("/api/events/stream");
source.onmessage = (event) => {
  renderEvent(JSON.parse(event.data));
};

source.onerror = () => {
  messageText.textContent = "实时事件流暂时断开，页面会继续自动刷新状态";
};

async function refreshDashboard() {
  await Promise.all([refreshStatus(), refreshCommandStatus(), refreshBluetoothStatus()]);
}

restoreCommandForm();
restoreSessionDraft();
updateSessionModeForm();
updateEventCounts();
refreshDashboard();
setInterval(refreshDashboard, 5000);
