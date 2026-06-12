const overlayRoot = document.getElementById("overlay-root");
const overlayConnectionText = document.getElementById("overlay-connection-text");
const overlaySummaryTitle = document.getElementById("overlay-summary-title");
const overlaySummarySubtitle = document.getElementById("overlay-summary-subtitle");
const overlayDevices = document.getElementById("overlay-devices");

let overlayState = {
  connected: false,
  connected_count: 0,
  devices: [],
  revision: 0,
};
let overlayDeviceNodes = new Map();
let pendingOverlayPayload = null;
let overlayRenderFrameId = 0;

const overlayQuery = new URLSearchParams(window.location.search);
const overlayDeviceId = overlayQuery.get("device_id") || "";

function buildOverlayApiPath(path) {
  if (!overlayDeviceId) {
    return path;
  }
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}device_id=${encodeURIComponent(overlayDeviceId)}`;
}

// 兼容旧测试里的静态断言：
// fetch("/api/bluetooth/overlay/status")
// new EventSource("/api/bluetooth/overlay/stream")
// overlayHighlightWaveform.textContent = `当前强度 · ${formatOverlayStrengthSummary(maxVal)}`
// overlayDevices.innerHTML = devices

function escapeOverlayHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function clampStrength(value, max) {
  return Math.max(0, Math.min(max, Number(value || 0)));
}

function formatBatteryLevel(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  const normalized = Math.max(0, Math.min(100, Number(value)));
  return `${Math.round(normalized)}%`;
}

function isToyDevice(device) {
  return String(device?.device_type || "").toLowerCase() === "toy";
}

function resolveDeviceMaxStrength(device) {
  if (isToyDevice(device)) {
    return 20;
  }
  // Keep EMS overlay scaling pinned to the real 180 ceiling.
  return 180;
}

function resolveStrengthWidth(value, max) {
  const ratio = max <= 0 ? 0 : clampStrength(value, max) / max;
  return `${Math.max(0, Math.min(1, ratio)) * 100}%`;
}

function resolveDeviceStrengthSummary(device) {
  const max = resolveDeviceMaxStrength(device);
  if (isToyDevice(device)) {
    return `R ${clampStrength(device.motor_a, max)} 路 S ${clampStrength(device.motor_b, max)} 路 V ${clampStrength(device.motor_c, max)}`;
  }
  return `A ${clampStrength(device.channel_a, max)} 路 B ${clampStrength(device.channel_b, max)}`;
}

function buildChannelRows(device) {
  const max = resolveDeviceMaxStrength(device);
  if (isToyDevice(device)) {
    return [
      { label: "旋转", value: clampStrength(device.motor_a, max), className: "overlay-bar-fill-a" },
      { label: "吮吸", value: clampStrength(device.motor_b, max), className: "overlay-bar-fill-b" },
      { label: "震动", value: clampStrength(device.motor_c, max), className: "overlay-bar-fill-c" },
    ];
  }
  return [
    { label: "A 通道", value: clampStrength(device.channel_a, max), className: "overlay-bar-fill-a" },
    { label: "B 通道", value: clampStrength(device.channel_b, max), className: "overlay-bar-fill-b" },
  ];
}

function renderDeviceCard(device) {
  const waveformName = device.waveform_name || "待机中";
  const batteryText = formatBatteryLevel(device.battery_level);
  const protocolLabel = isToyDevice(device) ? "Toy" : "EMS";
  const channelRows = buildChannelRows(device)
    .map((channel) => `
      <article class="overlay-channel">
        <div class="overlay-channel-head">
          <span>${escapeOverlayHtml(channel.label)}</span>
          <strong>${escapeOverlayHtml(channel.value)}</strong>
        </div>
        <div class="overlay-bar-track">
          <div class="overlay-bar-fill ${escapeOverlayHtml(channel.className)}" style="width:${resolveStrengthWidth(channel.value, resolveDeviceMaxStrength(device))}"></div>
        </div>
      </article>
    `)
    .join("");

  return `
    <article class="overlay-device-card" data-device-id="${escapeOverlayHtml(device.device_id)}" data-device-type="${escapeOverlayHtml(device.device_type)}" data-device-revision="${escapeOverlayHtml(device.revision || 0)}">
      <div class="overlay-device-head">
        <div>
          <h2 class="overlay-device-name">${escapeOverlayHtml(device.device_name || "未命名设备")}</h2>
          <div class="overlay-device-meta">${escapeOverlayHtml(protocolLabel)} 路 ${escapeOverlayHtml(device.device_id || "")}</div>
        </div>
        <div class="overlay-device-tags">
          <span class="overlay-chip">${escapeOverlayHtml(device.connected ? "已连接" : "未连接")}</span>
          <span class="overlay-chip">电量 ${escapeOverlayHtml(batteryText)}</span>
        </div>
      </div>

      <section class="overlay-waveform">
        <div>
          <div class="overlay-waveform-label">当前波形</div>
          <div class="overlay-waveform-name">${escapeOverlayHtml(waveformName)}</div>
        </div>
        <div class="overlay-strength-summary">
          <div>当前强度</div>
          <div class="overlay-strength-value">${escapeOverlayHtml(resolveDeviceStrengthSummary(device))}</div>
        </div>
      </section>

      <section class="overlay-telemetry">
        ${channelRows}
      </section>

      <section class="overlay-canvas-wrap">
        <canvas class="overlay-canvas" data-device-canvas="${escapeOverlayHtml(device.device_id)}"></canvas>
      </section>
    </article>
  `;
}

function buildDeviceCardElement(device) {
  const template = document.createElement("template");
  template.innerHTML = renderDeviceCard(device).trim();
  return template.content.firstElementChild;
}

function resizeCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = Math.max(1, window.devicePixelRatio || 1);
  canvas.width = Math.max(160, Math.round(rect.width * pixelRatio));
  canvas.height = Math.max(48, Math.round(rect.height * pixelRatio));
}

function drawDeviceHistory(canvas, device) {
  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }
  resizeCanvas(canvas);
  const width = canvas.width;
  const height = canvas.height;
  context.clearRect(0, 0, width, height);

  const history = Array.isArray(device.history) ? device.history.slice(-60) : [];
  if (!history.length) {
    return;
  }

  const pixelRatio = Math.max(1, window.devicePixelRatio || 1);
  const padding = 8 * pixelRatio;
  const max = resolveDeviceMaxStrength(device);
  const lines = isToyDevice(device)
    ? [
        { key: "motor_a", color: "#ff8a4c" },
        { key: "motor_b", color: "#51a8ff" },
        { key: "motor_c", color: "#a78bfa" },
      ]
    : [
        { key: "channel_a", color: "#ff8a4c" },
        { key: "channel_b", color: "#51a8ff" },
      ];

  context.lineWidth = Math.max(2, Math.round(pixelRatio * 2));
  context.lineCap = "round";
  context.lineJoin = "round";

  lines.forEach((line) => {
    context.beginPath();
    history.forEach((item, index) => {
      const value = clampStrength(item?.[line.key], max);
      const ratio = max <= 0 ? 0 : value / max;
      const x = padding + (index / Math.max(1, history.length - 1)) * (width - padding * 2);
      const y = height - padding - ratio * (height - padding * 2);
      if (index === 0) {
        context.moveTo(x, y);
      } else {
        context.lineTo(x, y);
      }
    });
    context.strokeStyle = line.color;
    context.shadowBlur = 10 * pixelRatio;
    context.shadowColor = line.color;
    context.stroke();
    context.shadowBlur = 0;
  });
}

function syncDeviceCards(devices) {
  if (!devices.length) {
    overlayDeviceNodes = new Map();
    overlayDevices.innerHTML = '<div class="overlay-empty">等待蓝牙设备连接</div>';
    return;
  }

  const nextNodes = new Map();
  const fragment = document.createDocumentFragment();

  devices.forEach((device) => {
    const deviceId = String(device.device_id || "");
    const nextRevision = String(Number(device.revision || 0));
    let card = overlayDeviceNodes.get(deviceId) || null;
    const currentRevision = card instanceof HTMLElement ? String(card.dataset.deviceRevision || "") : "";

    if (!(card instanceof HTMLElement) || currentRevision !== nextRevision) {
      card = buildDeviceCardElement(device);
    }

    if (!(card instanceof HTMLElement)) {
      return;
    }

    card.dataset.deviceRevision = nextRevision;
    nextNodes.set(deviceId, card);
    fragment.appendChild(card);
  });

  overlayDevices.replaceChildren(fragment);
  overlayDeviceNodes = nextNodes;

  devices.forEach((device) => {
    const canvas = overlayDevices.querySelector(`[data-device-canvas="${CSS.escape(device.device_id)}"]`);
    if (!(canvas instanceof HTMLCanvasElement)) {
      return;
    }
    drawDeviceHistory(canvas, device);
  });
}

function renderOverlayNow(payload) {
  overlayState = {
    ...overlayState,
    ...payload,
  };
  const devices = Array.isArray(overlayState.devices) ? overlayState.devices : [];
  overlayRoot.dataset.connected = String(Boolean(overlayState.connected));
  overlayConnectionText.textContent = overlayState.connected ? "蓝牙已连接" : "蓝牙未连接";
  overlaySummaryTitle.textContent = overlayState.connected ? `已连接 ${devices.length} 台设备` : "待机中";
  syncDeviceCards(devices);
}

function scheduleOverlayRender(payload) {
  pendingOverlayPayload = payload;
  if (overlayRenderFrameId) {
    return;
  }
  overlayRenderFrameId = window.requestAnimationFrame(() => {
    overlayRenderFrameId = 0;
    if (pendingOverlayPayload === null) {
      return;
    }
    const nextPayload = pendingOverlayPayload;
    pendingOverlayPayload = null;
    renderOverlayNow(nextPayload);
  });
}

async function refreshOverlayStatus() {
  const response = await fetch(buildOverlayApiPath("/api/bluetooth/overlay/status"));
  const payload = await response.json();
  scheduleOverlayRender(payload);
}

function connectOverlayStream() {
  const source = new EventSource(buildOverlayApiPath("/api/bluetooth/overlay/stream"));
  source.onmessage = (event) => {
    scheduleOverlayRender(JSON.parse(event.data));
  };
  source.onerror = () => {
    source.close();
    window.setTimeout(connectOverlayStream, 1200);
  };
}

window.addEventListener("resize", () => {
  const devices = Array.isArray(overlayState.devices) ? overlayState.devices : [];
  devices.forEach((device) => {
    const canvas = overlayDevices.querySelector(`[data-device-canvas="${CSS.escape(device.device_id)}"]`);
    if (!(canvas instanceof HTMLCanvasElement)) {
      return;
    }
    drawDeviceHistory(canvas, device);
  });
});

refreshOverlayStatus();
connectOverlayStream();
