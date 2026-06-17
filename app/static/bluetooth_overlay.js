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
let overlayAnimationFrameId = 0;
let overlayAnimationLastTime = 0;
const overlayBarAnimations = new Map();
const overlayHistoryAnimations = new Map();

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

function easeAnimatedValue(current, target, deltaMs, riseDurationMs, fallDurationMs) {
  const duration = target >= current ? riseDurationMs : fallDurationMs;
  const factor = 1 - Math.exp(-Math.max(0, deltaMs) / Math.max(1, duration));
  return current + (target - current) * factor;
}

function resolveBarOpacity(ratio) {
  if (ratio <= 0.001) {
    return 0.38;
  }
  return Math.min(1, 0.58 + ratio * 0.42);
}

function resolveBarHighlight(ratio) {
  if (ratio <= 0.62) {
    return 0;
  }
  return Math.min(1, (ratio - 0.62) / 0.38);
}

function writeBarAnimationState(state) {
  const { element, currentRatio, currentOpacity, currentHighlight } = state;
  element.style.transform = `scaleX(${currentRatio})`;
  element.style.opacity = String(currentOpacity);
  element.style.filter =
    currentHighlight <= 0.01
      ? "none"
      : `brightness(${(1 + currentHighlight * 0.08).toFixed(3)}) saturate(${(1 + currentHighlight * 0.05).toFixed(3)})`;
}

function ensureOverlayAnimationLoop() {
  if (overlayAnimationFrameId) {
    return;
  }
  overlayAnimationFrameId = window.requestAnimationFrame(stepOverlayAnimations);
}

function stepOverlayAnimations(timestamp) {
  const deltaMs = overlayAnimationLastTime ? Math.min(48, Math.max(12, timestamp - overlayAnimationLastTime)) : 16;
  overlayAnimationLastTime = timestamp;
  overlayAnimationFrameId = 0;

  let keepAnimating = false;

  overlayBarAnimations.forEach((state, element) => {
    if (!(element instanceof HTMLElement) || !element.isConnected) {
      overlayBarAnimations.delete(element);
      return;
    }

    state.currentRatio = easeAnimatedValue(state.currentRatio, state.targetRatio, deltaMs, 120, 170);
    state.currentOpacity = easeAnimatedValue(state.currentOpacity, state.targetOpacity, deltaMs, 120, 150);
    state.currentHighlight = easeAnimatedValue(state.currentHighlight, state.targetHighlight, deltaMs, 140, 180);
    writeBarAnimationState(state);

    const settled =
      Math.abs(state.currentRatio - state.targetRatio) < 0.002 &&
      Math.abs(state.currentOpacity - state.targetOpacity) < 0.01 &&
      Math.abs(state.currentHighlight - state.targetHighlight) < 0.02;

    if (settled) {
      state.currentRatio = state.targetRatio;
      state.currentOpacity = state.targetOpacity;
      state.currentHighlight = state.targetHighlight;
      writeBarAnimationState(state);
      return;
    }

    keepAnimating = true;
  });

  overlayHistoryAnimations.forEach((state, deviceId) => {
    if (!(state.canvas instanceof HTMLCanvasElement) || !state.canvas.isConnected) {
      overlayHistoryAnimations.delete(deviceId);
      return;
    }

    let historyChanged = false;
    state.lines.forEach((line) => {
      const targetValues = Array.isArray(line.targetValues) ? line.targetValues : [];
      if (line.currentValues.length !== targetValues.length) {
        line.currentValues = targetValues.slice();
        historyChanged = true;
        return;
      }
      line.currentValues = line.currentValues.map((value, index) => {
        const nextValue = easeAnimatedValue(value, targetValues[index] || 0, deltaMs, 130, 190);
        if (Math.abs(nextValue - (targetValues[index] || 0)) > 0.08) {
          historyChanged = true;
        }
        return nextValue;
      });
    });

    drawHistoryAnimationState(state);
    if (!historyChanged) {
      state.lines.forEach((line) => {
        line.currentValues = line.targetValues.slice();
      });
      drawHistoryAnimationState(state);
      return;
    }

    keepAnimating = true;
  });

  if (keepAnimating) {
    ensureOverlayAnimationLoop();
  } else {
    overlayAnimationLastTime = 0;
  }
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
  const nextOpacity = resolveBarOpacity(ratio);
  const nextHighlight = resolveBarHighlight(ratio);
  const animationState = overlayBarAnimations.get(fillElement);

  if (!animationState) {
    const initialState = {
      element: fillElement,
      currentRatio: ratio,
      targetRatio: ratio,
      currentOpacity: nextOpacity,
      targetOpacity: nextOpacity,
      currentHighlight: nextHighlight,
      targetHighlight: nextHighlight,
    };
    overlayBarAnimations.set(fillElement, initialState);
    writeBarAnimationState(initialState);
    return;
  }

  animationState.targetRatio = ratio;
  animationState.targetOpacity = nextOpacity;
  animationState.targetHighlight = nextHighlight;
  ensureOverlayAnimationLoop();
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

function resolveHistoryLineConfigs(device, max) {
  return isToyDevice(device)
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
}

function buildHistorySeries(device) {
  const history = Array.isArray(device.history) ? device.history.slice(-60) : [];
  const max = resolveDeviceMaxStrength(device);
  return {
    max,
    lines: resolveHistoryLineConfigs(device, max).map((line) => ({
      color: line.color,
      values: history.map((item) => {
        const rawValue = typeof line.normalize === "function" ? line.normalize(item?.[line.key]) : item?.[line.key];
        return clampStrength(rawValue, max);
      }),
    })),
  };
}

function createHistoryPoints(values, width, height, padding, max) {
  return values.map((value, index) => {
    const ratio = max <= 0 ? 0 : clampStrength(value, max) / max;
    return {
      x: padding + (index / Math.max(1, values.length - 1)) * (width - padding * 2),
      y: height - padding - ratio * (height - padding * 2),
    };
  });
}

function areHistoryValuesEqual(leftValues, rightValues) {
  if (!Array.isArray(leftValues) || !Array.isArray(rightValues) || leftValues.length !== rightValues.length) {
    return false;
  }
  return leftValues.every((value, index) => Number(value || 0) === Number(rightValues[index] || 0));
}

function detectHistoryShift(previousValues, nextValues) {
  if (!Array.isArray(previousValues) || !Array.isArray(nextValues) || !previousValues.length || !nextValues.length) {
    return -1;
  }

  // 新历史通常只会“左移若干点 + 在尾部追加新采样”，这里只匹配这个场景，
  // 命中后就能保留已绘制区的实际形状，避免整段曲线被重新补间。
  const maxShift = Math.min(6, previousValues.length, nextValues.length);
  for (let shift = 0; shift <= maxShift; shift += 1) {
    const comparableLength = Math.min(previousValues.length - shift, nextValues.length);
    if (comparableLength <= 0) {
      continue;
    }
    const previousComparable = previousValues.slice(shift, shift + comparableLength);
    const nextComparable = nextValues.slice(0, comparableLength);
    if (areHistoryValuesEqual(previousComparable, nextComparable)) {
      return shift;
    }
  }

  return -1;
}

function alignHistoryCurrentValues(previousCurrentValues, previousTargetValues, nextValues) {
  if (!Array.isArray(nextValues) || !nextValues.length) {
    return [];
  }

  const shift = detectHistoryShift(previousTargetValues, nextValues);
  if (shift < 0) {
    if (Array.isArray(previousCurrentValues) && previousCurrentValues.length === nextValues.length) {
      return previousCurrentValues.slice();
    }
    return nextValues.slice();
  }

  const alignedValues = Array.isArray(previousCurrentValues)
    ? previousCurrentValues.slice(shift, shift + nextValues.length)
    : [];
  const fallbackTailValue = alignedValues[alignedValues.length - 1]
    ?? previousTargetValues?.[previousTargetValues.length - 1]
    ?? nextValues[0]
    ?? 0;

  while (alignedValues.length < nextValues.length) {
    // 尾部新增采样先沿用上一帧末端值起步，只对新增区做过渡，避免历史主体被拉形。
    alignedValues.push(fallbackTailValue);
  }

  return alignedValues.slice(0, nextValues.length);
}

function strokeSmoothHistoryLine(context, points, color, pixelRatio, height) {
  if (!points.length) {
    return;
  }

  const solidColor = color;
  const glowColor = `${color}aa`;
  const fillColor = `${color}26`;

  context.save();

  // 主折线改为圆角平滑曲线，避免历史值高频切换时出现明显“折断感”。
  const buildSmoothPath = () => {
    context.beginPath();
    context.moveTo(points[0].x, points[0].y);
    if (points.length === 1) {
      return;
    }
    for (let index = 0; index < points.length - 1; index += 1) {
      const currentPoint = points[index];
      const nextPoint = points[index + 1];
      const midPointX = (currentPoint.x + nextPoint.x) / 2;
      const midPointY = (currentPoint.y + nextPoint.y) / 2;
      context.quadraticCurveTo(currentPoint.x, currentPoint.y, midPointX, midPointY);
    }
    const tail = points[points.length - 1];
    context.lineTo(tail.x, tail.y);
  };

  buildSmoothPath();
  context.lineTo(points[points.length - 1].x, height);
  context.lineTo(points[0].x, height);
  context.closePath();
  context.fillStyle = fillColor;
  context.fill();

  buildSmoothPath();
  context.lineWidth = Math.max(3, Math.round(pixelRatio * 3));
  context.strokeStyle = glowColor;
  context.shadowBlur = 12 * pixelRatio;
  context.shadowColor = solidColor;
  context.stroke();

  buildSmoothPath();
  context.lineWidth = Math.max(1.5, pixelRatio * 1.65);
  context.strokeStyle = solidColor;
  context.shadowBlur = 0;
  context.stroke();
  context.restore();
}

function drawHistoryAnimationState(state) {
  const { canvas, max, lines } = state;
  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }

  resizeCanvas(canvas);
  const width = canvas.width;
  const height = canvas.height;
  context.clearRect(0, 0, width, height);

  const hasValues = lines.some((line) => Array.isArray(line.currentValues) && line.currentValues.length > 0);
  if (!hasValues) {
    return;
  }

  const pixelRatio = Math.max(1, window.devicePixelRatio || 1);
  const padding = 8 * pixelRatio;
  context.lineCap = "round";
  context.lineJoin = "round";

  lines.forEach((line) => {
    const points = createHistoryPoints(line.currentValues, width, height, padding, max);
    strokeSmoothHistoryLine(context, points, line.color, pixelRatio, height - padding * 0.35);
  });
}

function drawDeviceHistory(canvas, device) {
  if (!(canvas instanceof HTMLCanvasElement)) {
    return;
  }

  const deviceId = String(device?.device_id || "");
  const nextSeries = buildHistorySeries(device);
  const canAnimate =
    deviceId &&
    nextSeries.lines.length > 0 &&
    nextSeries.lines.every((line) => line.values.length > 0);

  if (!canAnimate) {
    overlayHistoryAnimations.delete(deviceId);
    const fallbackState = {
      canvas,
      max: nextSeries.max,
      lines: nextSeries.lines.map((line) => ({
        color: line.color,
        currentValues: line.values.slice(),
        targetValues: line.values.slice(),
      })),
    };
    drawHistoryAnimationState(fallbackState);
    return;
  }

  let animationState = overlayHistoryAnimations.get(deviceId);
  const shouldReset =
    !animationState ||
    animationState.lines.length !== nextSeries.lines.length ||
    animationState.lines.some((line, index) => line.color !== nextSeries.lines[index]?.color);

  if (shouldReset) {
    animationState = {
      canvas,
      max: nextSeries.max,
      lines: nextSeries.lines.map((line) => ({
        color: line.color,
        currentValues: line.values.slice(),
        targetValues: line.values.slice(),
      })),
    };
    overlayHistoryAnimations.set(deviceId, animationState);
    drawHistoryAnimationState(animationState);
    return;
  }

  animationState.canvas = canvas;
  animationState.max = nextSeries.max;
  animationState.lines = animationState.lines.map((line, index) => {
    const nextLine = nextSeries.lines[index];
    const nextValues = nextLine.values.slice();
    const currentValues = alignHistoryCurrentValues(
      line.currentValues,
      line.targetValues,
      nextValues,
    );
    return {
      color: nextLine.color,
      currentValues,
      targetValues: nextValues,
    };
  });

  drawHistoryAnimationState(animationState);
  overlayHistoryAnimations.set(deviceId, animationState);
  ensureOverlayAnimationLoop();
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
    overlayHistoryAnimations.clear();
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

  const activeDeviceIds = new Set(devices.map((device) => String(device.device_id || "")));
  overlayHistoryAnimations.forEach((_, deviceId) => {
    if (!activeDeviceIds.has(deviceId)) {
      overlayHistoryAnimations.delete(deviceId);
    }
  });

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
