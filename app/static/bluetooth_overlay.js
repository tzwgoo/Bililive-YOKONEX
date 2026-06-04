const overlayRoot = document.getElementById("overlay-root");
const overlayConnectionText = document.getElementById("overlay-connection-text");
const overlayWaveformName = document.getElementById("overlay-waveform-name");
const overlayDeviceName = document.getElementById("overlay-device-name");
const overlayBatteryValue = document.getElementById("overlay-battery-value");
const overlayChannelAValue = document.getElementById("overlay-channel-a-value");
const overlayChannelBValue = document.getElementById("overlay-channel-b-value");
const overlayChannelABar = document.getElementById("overlay-channel-a-bar");
const overlayChannelBBar = document.getElementById("overlay-channel-b-bar");
const overlayWaveformCanvas = document.getElementById("overlay-waveform-canvas");
const overlayDanmakuList = document.getElementById("overlay-danmaku-list");

let overlayState = {
  connected: false,
  device_name: "",
  waveform_name: "",
  battery_level: null,
  channel_a: 0,
  channel_b: 0,
  history: [],
  recent_events: [],
  revision: 0,
};

function clampStrength(value) {
  return Math.max(0, Math.min(180, Number(value || 0)));
}

function resolveStrengthWidth(value) {
  return `${(clampStrength(value) / 180) * 100}%`;
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

  const padding = 8 * window.devicePixelRatio;
  const drawLine = (key, color) => {
    context.beginPath();
    items.forEach((item, index) => {
      const x = padding + (index / Math.max(1, items.length - 1)) * (width - padding * 2);
      const strength = clampStrength(item[key]);
      const y = height - padding - (strength / 180) * (height - padding * 2);
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

  drawLine("channel_a", "#ff8a4c");
  drawLine("channel_b", "#51a8ff");
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
  const items = Array.isArray(recentEvents) ? recentEvents.slice(0, 4) : [];
  if (!items.length) {
    overlayDanmakuList.innerHTML = '<article class="overlay-danmaku-item"><strong>等待事件</strong><span>直播触发后显示</span></article>';
    return;
  }
  overlayDanmakuList.innerHTML = items
    .map((item) => {
      const guardLabel = item.guard_label ? ` · ${item.guard_label}` : "";
      const waveformText = item.waveform_id ? ` · ${item.waveform_id}` : "";
      return `
        <article class="overlay-danmaku-item">
          <strong>${escapeOverlayHtml(item.event_label || "事件")}${escapeOverlayHtml(guardLabel)} · ${escapeOverlayHtml(item.uname || "匿名用户")}</strong>
          <span>${escapeOverlayHtml(item.msg || "-")}${escapeOverlayHtml(waveformText)}</span>
        </article>
      `;
    })
    .join("");
}

function renderOverlay(payload) {
  overlayState = {
    ...overlayState,
    ...payload,
  };
  overlayRoot.dataset.connected = String(Boolean(overlayState.connected));
  overlayConnectionText.textContent = overlayState.connected ? "蓝牙已连接" : "蓝牙未连接";
  overlayWaveformName.textContent = overlayState.waveform_name || "待机中";
  overlayDeviceName.textContent = overlayState.device_name || "未连接设备";
  overlayBatteryValue.textContent = formatBatteryLevel(overlayState.battery_level);
  overlayChannelAValue.textContent = String(clampStrength(overlayState.channel_a));
  overlayChannelBValue.textContent = String(clampStrength(overlayState.channel_b));
  overlayChannelABar.style.width = resolveStrengthWidth(overlayState.channel_a);
  overlayChannelBBar.style.width = resolveStrengthWidth(overlayState.channel_b);
  drawOverlayHistory(overlayState.history || []);
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
  resizeOverlayCanvas();
  drawOverlayHistory(overlayState.history || []);
});

resizeOverlayCanvas();
refreshOverlayStatus();
connectOverlayStream();
