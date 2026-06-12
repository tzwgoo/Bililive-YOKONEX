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
// overlayHighlightWaveform.textContent = `褰撳墠寮哄害 路 ${formatOverlayStrengthSummary(maxVal)}`
// overlayHighlightWaveform.textContent = `輝念膿業 ， ${formatOverlayStrengthSummary(maxVal)}`
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

function isGcqToyDevice(device) {
  return String(device?.protocol || "").toLowerCase() === "yiskj_gcq_toy_013";
}

function resolveToyChannelLabels(device) {
  if (isGcqToyDevice(device)) {
    return {
      a: "气阀",
      b: "气泵",
      c: "水泵",
      summaryA: "阀",
      summaryB: "气",
      summaryC: "水",
    };
  }
  return {
    a: "旋转",
    b: "吮吸",
    c: "震动",
    summaryA: "R",
    summaryB: "S",
    summaryC: "V",
  };
}

function resolveDeviceMaxStrength(device) {
  if (isGcqToyDevice(device)) {
    return 5;
  }
  if (isToyDevice(device)) {
    return 20;
  }
  // 保持 EMS 叠加层按真实 180 上限缩放，避免视觉误导。
  return 180;
}

function resolveStrengthRatio(value, max) {
  const ratio = max <= 0 ? 0 : clampStrength(value, max) / max;
  return Math.max(0, Math.min(1, ratio));
}

function resolveDeviceStrengthSummary(device) {
  if (isGcqToyDevice(device)) {
    return `阀 ${Number(device.motor_a) > 0 ? "开" : "关"} · 气 ${clampStrength(device.motor_b, 5)} 档 · 水 ${clampStrength(device.motor_c, 5)} 档`;
  }
  const max = resolveDeviceMaxStrength(device);
  if (isToyDevice(device)) {
    const labels = resolveToyChannelLabels(device);
    return `${labels.summaryA} ${clampStrength(device.motor_a, max)} · ${labels.summaryB} ${clampStrength(device.motor_b, max)} · ${labels.summaryC} ${clampStrength(device.motor_c, max)}`;
  }
  return `A ${clampStrength(device.channel_a, max)} · B ${clampStrength(device.channel_b, max)}`;
}

function buildChannelRows(device) {
  if (isGcqToyDevice(device)) {
    const labels = resolveToyChannelLabels(device);
    const valveOpen = Number(device.motor_a) > 0;
    return [
      { label: labels.a, value: valveOpen ? 1 : 0, textValue: valveOpen ? "开" : "关", max: 1, className: "overlay-bar-fill-a" },
      { label: labels.b, value: clampStrength(device.motor_b, 5), textValue: `${clampStrength(device.motor_b, 5)} 档`, max: 5, className: "overlay-bar-fill-b" },
      { label: labels.c, value: clampStrength(device.motor_c, 5), textValue: `${clampStrength(device.motor_c, 5)} 档`, max: 5, className: "overlay-bar-fill-c" },
    ];
  }

  const max = resolveDeviceMaxStrength(device);
  if (isToyDevice(device)) {
    const labels = resolveToyChannelLabels(device);
    return [
      { label: labels.a, value: clampStrength(device.motor_a, max), textValue: clampStrength(device.motor_a, max), max, className: "overlay-bar-fill-a" },
      { label: labels.b, value: clampStrength(device.motor_b, max), textValue: clampStrength(device.motor_b, max), max, className: "overlay-bar-fill-b" },
      { label: labels.c, value: clampStrength(device.motor_c, max), textValue: clampStrength(device.motor_c, max), max, className: "overlay-bar-fill-c" },
    ];
  }

  return [
    { label: "A 通道", value: clampStrength(device.channel_a, max), textValue: clampStrength(device.channel_a, max), max, className: "overlay-bar-fill-a" },
    { label: "B 通道", value: clampStrength(device.channel_b, max), textValue: clampStrength(device.channel_b, max), max, className: "overlay-bar-fill-b" },
  ];
}

function renderChannelRow(channel) {
  return `
    <article class="overlay-channel">
      <div class="overlay-channel-head">
        <span data-channel-label>${escapeOverlayHtml(channel.label)}</span>
        <strong data-channel-value>${escapeOverlayHtml(channel.textValue)}</strong>
      </div>
      <div class="overlay-bar-track">
        <div
          class="overlay-bar-fill ${escapeOverlayHtml(channel.className)}"
          data-channel-fill
          data-channel-max="${escapeOverlayHtml(channel.max)}"
          style="transform:scaleX(${resolveStrengthRatio(channel.value, channel.max)})"
        ></div>
      </div>
    </article>
  `;
}

function renderDeviceCard(device) {
  const waveformName = device.waveform_name || "待命中";
  const batteryText = formatBatteryLevel(device.battery_level);
  const protocolLabel = isGcqToyDevice(device) ? "灌肠机" : (isToyDevice(device) ? "Toy" : "EMS");
  const channelRows = buildChannelRows(device)
    .map((channel) => renderChannelRow(channel))
    .join("");

  return `
    <article class="overlay-device-card" data-device-id="${escapeOverlayHtml(device.device_id)}" data-device-type="${escapeOverlayHtml(device.device_type)}" data-device-revision="${escapeOverlayHtml(device.revision || 0)}">
      <div class="overlay-device-head">
        <div>
          <h2 class="overlay-device-name" data-device-name>${escapeOverlayHtml(device.device_name || "未命名设备")}</h2>
          <div class="overlay-device-meta" data-device-meta>${escapeOverlayHtml(protocolLabel)} · ${escapeOverlayHtml(device.device_id || "")}</div>
        </div>
        <div class="overlay-device-tags">
          <span class="overlay-chip" data-device-connection>${escapeOverlayHtml(device.connected ? "已连接" : "未连接")}</span>
          <span class="overlay-chip" data-device-battery>电量 ${escapeOverlayHtml(batteryText)}</span>
        </div>
      </div>

      <section class="overlay-waveform">
        <div>
          <div class="overlay-waveform-label">当前波形</div>
          <div class="overlay-waveform-name" data-waveform-name>${escapeOverlayHtml(waveformName)}</div>
        </div>
        <div class="overlay-strength-summary">
          <div>当前强度</div>
          <div class="overlay-strength-value" data-strength-summary>${escapeOverlayHtml(resolveDeviceStrengthSummary(device))}</div>
        </div>
      </section>

      <section class="overlay-telemetry" data-device-telemetry>
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

function applyStrengthFill(fillElement, value, max) {
  if (!(fillElement instanceof HTMLElement)) {
    return;
  }
  const ratio = resolveStrengthRatio(value, max);
  fillElement.style.transform = `scaleX(${ratio})`;
  fillElement.style.opacity = ratio <= 0 ? "0.52" : "1";
  // 高强度时补一点高光，减轻快速刷新时“生硬截断”的感觉。
  fillElement.style.filter = ratio >= 0.82 ? "brightness(1.08) saturate(1.04)" : "none";
}

function updateChannelRows(telemetryElement, device) {
  if (!(telemetryElement instanceof HTMLElement)) {
    return;
  }
  const channels = buildChannelRows(device);
  const currentRows = Array.from(telemetryElement.querySelectorAll(".overlay-channel"));
  const needsRebuild =
    currentRows.length !== channels.length ||
    channels.some((channel, index) => {
      const fillElement = currentRows[index]?.querySelector("[data-channel-fill]");
      return !(fillElement instanceof HTMLElement) || !fillElement.classList.contains(channel.className);
    });

  // 只有通道结构变化时才重建，普通强度刷新只改文本和 transform，保证横条动画连续。
  if (needsRebuild) {
    telemetryElement.innerHTML = channels.map((channel) => renderChannelRow(channel)).join("");
  }

  const nextRows = Array.from(telemetryElement.querySelectorAll(".overlay-channel"));
  channels.forEach((channel, index) => {
    const row = nextRows[index];
    if (!(row instanceof HTMLElement)) {
      return;
    }
    const labelElement = row.querySelector("[data-channel-label]");
    const valueElement = row.querySelector("[data-channel-value]");
    const fillElement = row.querySelector("[data-channel-fill]");
    if (labelElement instanceof HTMLElement) {
      labelElement.textContent = channel.label;
    }
    if (valueElement instanceof HTMLElement) {
      valueElement.textContent = String(channel.textValue);
    }
    if (fillElement instanceof HTMLElement) {
      fillElement.className = `overlay-bar-fill ${channel.className}`;
      fillElement.dataset.channelMax = String(channel.max);
      applyStrengthFill(fillElement, channel.value, channel.max);
    }
  });
}

function updateDeviceCard(card, device) {
  if (!(card instanceof HTMLElement)) {
    return;
  }

  const waveformName = device.waveform_name || "待命中";
  const batteryText = formatBatteryLevel(device.battery_level);
  const protocolLabel = isGcqToyDevice(device) ? "灌肠机" : (isToyDevice(device) ? "Toy" : "EMS");

  card.dataset.deviceType = String(device.device_type || "");
  card.dataset.deviceRevision = String(Number(device.revision || 0));

  const deviceNameElement = card.querySelector("[data-device-name]");
  const deviceMetaElement = card.querySelector("[data-device-meta]");
  const connectionElement = card.querySelector("[data-device-connection]");
  const batteryElement = card.querySelector("[data-device-battery]");
  const waveformNameElement = card.querySelector("[data-waveform-name]");
  const strengthSummaryElement = card.querySelector("[data-strength-summary]");
  const telemetryElement = card.querySelector("[data-device-telemetry]");

  if (deviceNameElement instanceof HTMLElement) {
    deviceNameElement.textContent = device.device_name || "未命名设备";
  }
  if (deviceMetaElement instanceof HTMLElement) {
    deviceMetaElement.textContent = `${protocolLabel} · ${device.device_id || ""}`;
  }
  if (connectionElement instanceof HTMLElement) {
    connectionElement.textContent = device.connected ? "已连接" : "未连接";
  }
  if (batteryElement instanceof HTMLElement) {
    batteryElement.textContent = `电量 ${batteryText}`;
  }
  if (waveformNameElement instanceof HTMLElement) {
    waveformNameElement.textContent = waveformName;
  }
  if (strengthSummaryElement instanceof HTMLElement) {
    strengthSummaryElement.textContent = resolveDeviceStrengthSummary(device);
  }

  updateChannelRows(telemetryElement, device);
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
        // 灌肠机气阀只有开/关，历史图里把“开”拉满显示，避免在 0-5 量程下几乎看不见。
        { key: "motor_a", color: "#ff8a4c", normalize: (value) => (isGcqToyDevice(device) ? (Number(value) > 0 ? max : 0) : value) },
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
      const rawValue = typeof line.normalize === "function" ? line.normalize(item?.[line.key]) : item?.[line.key];
      const value = clampStrength(rawValue, max);
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

function resolveOverlaySubtitle(devices) {
  if (!devices.length) {
    return "当前没有已连接设备";
  }
  const names = devices
    .map((device) => String(device.device_name || "").trim())
    .filter(Boolean);
  if (!names.length) {
    return `已连接 ${devices.length} 台设备`;
  }
  return names.slice(0, 2).join(" / ");
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
    let card = overlayDeviceNodes.get(deviceId) || null;

    if (!(card instanceof HTMLElement)) {
      card = buildDeviceCardElement(device);
    }
    if (!(card instanceof HTMLElement)) {
      return;
    }

    updateDeviceCard(card, device);
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
  overlaySummaryTitle.textContent = overlayState.connected ? `已连接 ${devices.length} 台设备` : "待命中";
  overlaySummarySubtitle.textContent = resolveOverlaySubtitle(devices);
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
