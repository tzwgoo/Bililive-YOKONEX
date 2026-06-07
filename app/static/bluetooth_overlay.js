const overlayRoot = document.getElementById("overlay-root");
const overlayConnectionText = document.getElementById("overlay-connection-text");
const overlayWaveformName = document.getElementById("overlay-waveform-name");
const overlayDeviceName = document.getElementById("overlay-device-name");
const overlayBatteryValue = document.getElementById("overlay-battery-value");
const overlayChannelAValue = document.getElementById("overlay-channel-a-value");
const overlayChannelBValue = document.getElementById("overlay-channel-b-value");
const overlayChannelCValue = document.getElementById("overlay-channel-c-value");
const overlayChannelABar = document.getElementById("overlay-channel-a-bar");
const overlayChannelBBar = document.getElementById("overlay-channel-b-bar");
const overlayChannelCBar = document.getElementById("overlay-channel-c-bar");
const overlayChannelAArticle = document.getElementById("overlay-channel-a-article");
const overlayChannelBArticle = document.getElementById("overlay-channel-b-article");
const overlayChannelCArticle = document.getElementById("overlay-channel-c-article");
const overlayChannelALabel = document.getElementById("overlay-channel-a-label");
const overlayChannelBLabel = document.getElementById("overlay-channel-b-label");
const overlayChannelCLabel = document.getElementById("overlay-channel-c-label");
const overlayWaveformCanvas = document.getElementById("overlay-waveform-canvas");
const overlayDanmakuList = document.getElementById("overlay-danmaku-list");
const overlayHighlightLabel = document.getElementById("overlay-highlight-label");
const overlayHighlightUser = document.getElementById("overlay-highlight-user");
const overlayHighlightMessage = document.getElementById("overlay-highlight-message");
const overlayHighlightGuard = document.getElementById("overlay-highlight-guard");
const overlayHighlightWaveform = document.getElementById("overlay-highlight-waveform");
const overlayHighlightConnectionText = document.getElementById("overlay-highlight-connection-text");
const overlayHighlightDeviceName = document.getElementById("overlay-highlight-device-name");
const overlayHighlightBatteryValue = document.getElementById("overlay-highlight-battery-value");
const overlayEventWaveformName = document.getElementById("overlay-event-waveform-name");

let overlayState = {
  connected: false,
  device_name: "",
  device_type: "",
  waveform_name: "",
  battery_level: null,
  channel_a: 0,
  channel_b: 0,
  motor_a: 0,
  motor_b: 0,
  motor_c: 0,
  history: [],
  recent_events: [],
  revision: 0,
};

function isToyDevice() {
  return String(overlayState.device_type || "").toLowerCase() === "toy";
}

function resolveOverlayLayout() {
  const width = Math.max(window.innerWidth || 0, 1);
  const height = Math.max(window.innerHeight || 0, 1);
  const ratio = width / height;

  if (width <= 860) {
    return "stack";
  }
  if (height <= 430 && width >= 1080) {
    return "cinema";
  }
  if (height <= 620 || ratio >= 3) {
    return "compact";
  }
  return "wide";
}

function resolveRecentEventLimit() {
  const width = Math.max(window.innerWidth || 0, 1);
  const height = Math.max(window.innerHeight || 0, 1);

  if (width <= 860) {
    return height <= 620 ? 2 : 3;
  }
  if (height <= 360) {
    return 1;
  }
  if (height <= 500) {
    return 2;
  }
  if (height <= 660) {
    return 3;
  }
  return 4;
}

function applyOverlayViewportMode() {
  if (!overlayRoot) {
    return;
  }
  overlayRoot.dataset.layout = overlayRoot.dataset.style === "event" ? resolveOverlayLayout() : "panel";
}

function clampStrength(value, max) {
  max = max || 180;
  return Math.max(0, Math.min(max, Number(value || 0)));
}

function resolveStrengthWidth(value, max) {
  max = max || 180;
  return `${(clampStrength(value, max) / max) * 100}%`;
}

function formatBatteryLevel(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  const normalized = Math.max(0, Math.min(100, Number(value)));
  return `${Math.round(normalized)}%`;
}

function resizeOverlayCanvas() {
  const rect = overlayWaveformCanvas.getBoundingClientRect();
  overlayWaveformCanvas.width = Math.max(120, Math.round(rect.width * window.devicePixelRatio));
  overlayWaveformCanvas.height = Math.max(48, Math.round(rect.height * window.devicePixelRatio));
}

function drawOverlayHistory(history) {
  const context = overlayWaveformCanvas.getContext("2d");
  if (!context) {
    return;
  }
  const width = overlayWaveformCanvas.width;
  const height = overlayWaveformCanvas.height;
  context.clearRect(0, 0, width, height);
  context.lineWidth = Math.max(2, Math.round(window.devicePixelRatio * 2));
  context.lineCap = "round";
  context.lineJoin = "round";

  const items = Array.isArray(history) ? history.slice(-60) : [];
  if (!items.length) {
    return;
  }

  const toy = isToyDevice();
  const maxVal = toy ? 20 : 180;
  const padding = 8 * window.devicePixelRatio;
  const drawLine = (key, color) => {
    context.beginPath();
    items.forEach((item, index) => {
      const x = padding + (index / Math.max(1, items.length - 1)) * (width - padding * 2);
      const strength = clampStrength(item[key], maxVal);
      const y = height - padding - (strength / maxVal) * (height - padding * 2);
      if (index === 0) {
        context.moveTo(x, y);
      } else {
        context.lineTo(x, y);
      }
    });
    context.strokeStyle = color;
    context.shadowBlur = 10 * window.devicePixelRatio;
    context.shadowColor = color;
    context.stroke();
    context.shadowBlur = 0;
  };

  if (toy) {
    drawLine("motor_a", "#ff8a4c");
    drawLine("motor_b", "#51a8ff");
    drawLine("motor_c", "#a78bfa");
  } else {
    drawLine("channel_a", "#ff8a4c");
    drawLine("channel_b", "#51a8ff");
  }
}

function escapeOverlayHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderOverlayDanmaku(recentEvents) {
  const items = Array.isArray(recentEvents) ? recentEvents.slice(0, resolveRecentEventLimit()) : [];
  if (!items.length) {
    overlayDanmakuList.innerHTML = '<article class="overlay-danmaku-item"><strong>等待事件</strong><span>直播触发后显示</span></article>';
    return;
  }
  overlayDanmakuList.innerHTML = items
    .map((item) => {
      const guardLabel = item.guard_label ? ` · ${item.guard_label}` : "";
      const waveformLabel = item.waveform_name || item.waveform_id || "";
      const waveformText = waveformLabel ? ` · ${waveformLabel}` : "";
      return `
        <article class="overlay-danmaku-item">
          <strong>${escapeOverlayHtml(item.event_label || "事件")}${escapeOverlayHtml(guardLabel)} · ${escapeOverlayHtml(item.uname || "匿名用户")}</strong>
          <span>${escapeOverlayHtml(item.msg || "-")}${escapeOverlayHtml(waveformText)}</span>
        </article>
      `;
    })
    .join("");
}

function renderOverlayHighlight(recentEvents) {
  const latestEvent = Array.isArray(recentEvents) && recentEvents.length ? recentEvents[0] : null;
  if (!latestEvent) {
    overlayHighlightLabel.textContent = "等待触发";
    overlayHighlightUser.textContent = "直播事件发生后显示";
    overlayHighlightMessage.textContent = "当前还没有新的弹幕、SC、上舰或点赞触发。";
    overlayHighlightGuard.textContent = "等待身份";
    overlayHighlightWaveform.textContent = overlayState.waveform_name ? `波形 ${overlayState.waveform_name}` : "待机波形";
    return;
  }

  const guardText = latestEvent.guard_label || "普通观众";
  const waveformText = latestEvent.waveform_name || latestEvent.waveform_id || overlayState.waveform_name || "待机中";
  overlayHighlightLabel.textContent = latestEvent.event_label || "事件触发";
  overlayHighlightUser.textContent = latestEvent.uname || "匿名用户";
  overlayHighlightMessage.textContent = latestEvent.msg || "已触发蓝牙演出";
  overlayHighlightGuard.textContent = guardText;
  overlayHighlightWaveform.textContent = `波形 ${waveformText}`;
}

function renderDeviceTypeUI() {
  const toy = isToyDevice();
  if (toy) {
    overlayChannelALabel.textContent = "旋转";
    overlayChannelBLabel.textContent = "吮吸";
    overlayChannelCArticle.classList.remove("is-hidden");
  } else {
    overlayChannelALabel.textContent = "A 通道";
    overlayChannelBLabel.textContent = "B 通道";
    overlayChannelCArticle.classList.add("is-hidden");
  }
}

function renderOverlay(payload) {
  overlayState = {
    ...overlayState,
    ...payload,
  };
  const toy = isToyDevice();
  const maxVal = toy ? 20 : 180;
  overlayRoot.dataset.connected = String(Boolean(overlayState.connected));
  overlayConnectionText.textContent = overlayState.connected ? "蓝牙已连接" : "蓝牙未连接";
  overlayHighlightConnectionText.textContent = overlayConnectionText.textContent;
  overlayWaveformName.textContent = overlayState.waveform_name || "待机中";
  overlayEventWaveformName.textContent = overlayWaveformName.textContent;
  overlayDeviceName.textContent = overlayState.device_name || "未连接设备";
  overlayHighlightDeviceName.textContent = overlayDeviceName.textContent;
  overlayBatteryValue.textContent = formatBatteryLevel(overlayState.battery_level);
  overlayHighlightBatteryValue.textContent = overlayBatteryValue.textContent;

  renderDeviceTypeUI();

  if (toy) {
    overlayChannelAValue.textContent = String(clampStrength(overlayState.motor_a, maxVal));
    overlayChannelBValue.textContent = String(clampStrength(overlayState.motor_b, maxVal));
    overlayChannelCValue.textContent = String(clampStrength(overlayState.motor_c, maxVal));
    overlayChannelABar.style.width = resolveStrengthWidth(overlayState.motor_a, maxVal);
    overlayChannelBBar.style.width = resolveStrengthWidth(overlayState.motor_b, maxVal);
    overlayChannelCBar.style.width = resolveStrengthWidth(overlayState.motor_c, maxVal);
  } else {
    overlayChannelAValue.textContent = String(clampStrength(overlayState.channel_a, maxVal));
    overlayChannelBValue.textContent = String(clampStrength(overlayState.channel_b, maxVal));
    overlayChannelABar.style.width = resolveStrengthWidth(overlayState.channel_a, maxVal);
    overlayChannelBBar.style.width = resolveStrengthWidth(overlayState.channel_b, maxVal);
  }

  drawOverlayHistory(overlayState.history || []);
  renderOverlayHighlight(overlayState.recent_events || []);
  renderOverlayDanmaku(overlayState.recent_events || []);
}

async function refreshOverlayStatus() {
  const response = await fetch("/api/bluetooth/overlay/status");
  const payload = await response.json();
  renderOverlay(payload);
}

function connectOverlayStream() {
  const source = new EventSource("/api/bluetooth/overlay/stream");
  source.onmessage = (event) => {
    renderOverlay(JSON.parse(event.data));
  };
  source.onerror = () => {
    source.close();
    setTimeout(connectOverlayStream, 1200);
  };
}

window.addEventListener("resize", () => {
  applyOverlayViewportMode();
  resizeOverlayCanvas();
  drawOverlayHistory(overlayState.history || []);
  renderOverlayDanmaku(overlayState.recent_events || []);
});

applyOverlayViewportMode();
resizeOverlayCanvas();
refreshOverlayStatus();
connectOverlayStream();
