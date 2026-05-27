const waveformLibrary = document.getElementById("studio-waveform-library");
const ruleGroupsContainer = document.getElementById("studio-rule-groups");
const saveButton = document.getElementById("studio-save-btn");
const studioMessageText = document.getElementById("studio-message-text");
const waveformEditor = document.getElementById("studio-waveform-editor");
const waveformMessageText = document.getElementById("studio-waveform-message-text");
const waveformNameInput = document.getElementById("studio-waveform-name-input");
const waveformCanvas = document.getElementById("studio-waveform-canvas");
const waveformSteps = document.getElementById("studio-waveform-steps");
const waveformStepCount = document.getElementById("studio-waveform-step-count");
const waveformDurationTotal = document.getElementById("studio-waveform-duration-total");
const waveformMaxStrength = document.getElementById("studio-waveform-max-strength");
const dirtyIndicator = document.getElementById("studio-dirty-indicator");
const newWaveformButton = document.getElementById("studio-new-waveform-btn");
const duplicateWaveformButton = document.getElementById("studio-duplicate-waveform-btn");
const deleteWaveformButton = document.getElementById("studio-delete-waveform-btn");
const saveWaveformButton = document.getElementById("studio-save-waveform-btn");
const addStepButton = document.getElementById("studio-add-step-btn");

let studioWaveforms = [];
let studioRuleGroups = [];
let selectedWaveformId = "";
let draftWaveform = null;
let draftDirty = false;
let activeDragHandle = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function clampStrength(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return 0;
  }
  return Math.max(0, Math.min(180, Math.round(numericValue)));
}

function normalizeDuration(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return 1;
  }
  return Math.max(1, Math.round(numericValue));
}

function cloneWaveformStep(step) {
  return {
    duration_ms: normalizeDuration(step.duration_ms),
    channel_a: clampStrength(step.channel_a),
    channel_b: clampStrength(step.channel_b),
  };
}

function cloneWaveform(waveform) {
  return {
    id: waveform.id,
    name: waveform.name,
    builtin: Boolean(waveform.builtin),
    editable: Boolean(waveform.editable),
    execution_mode: waveform.execution_mode || "fixed",
    loop_count: Number(waveform.loop_count || 1),
    steps: Array.isArray(waveform.steps) ? waveform.steps.map(cloneWaveformStep) : [],
  };
}

function getDefaultWaveformName() {
  return "自定义波形";
}

function resolveWaveformMaxStrength(waveform) {
  const steps = Array.isArray(waveform.steps) ? waveform.steps : [];
  return Math.max(
    0,
    ...steps.flatMap((step) => [Number(step.channel_a || 0), Number(step.channel_b || 0)])
  );
}

function resolveWaveformTotalDuration(waveform) {
  const steps = Array.isArray(waveform.steps) ? waveform.steps : [];
  return steps.reduce((sum, step) => sum + normalizeDuration(step.duration_ms), 0);
}

function buildWaveformPreviewSvg(waveform) {
  const steps = Array.isArray(waveform.steps) ? waveform.steps : [];
  if (!steps.length) {
    return '<svg viewBox="0 0 240 88" class="waveform-preview"></svg>';
  }
  const width = 240;
  const height = 88;
  const padding = 8;
  const totalDuration = Math.max(1, resolveWaveformTotalDuration(waveform));
  const maxStrength = Math.max(1, resolveWaveformMaxStrength(waveform));

  const buildLinePath = (key) => {
    let elapsed = 0;
    const points = [`${padding},${height - padding}`];
    steps.forEach((step) => {
      const duration = normalizeDuration(step.duration_ms);
      const value = clampStrength(step[key]);
      const x1 = padding + (elapsed / totalDuration) * (width - padding * 2);
      const y = height - padding - (value / maxStrength) * (height - padding * 2);
      points.push(`${x1},${y}`);
      elapsed += duration;
      const x2 = padding + (elapsed / totalDuration) * (width - padding * 2);
      points.push(`${x2},${y}`);
    });
    return points.join(" ");
  };

  const aPoints = buildLinePath("channel_a");
  const bPoints = buildLinePath("channel_b");
  return `
    <svg viewBox="0 0 240 88" class="waveform-preview" preserveAspectRatio="none">
      <rect x="0" y="0" width="240" height="88" rx="16" fill="rgba(255,255,255,0.72)"></rect>
      <polyline points="${aPoints}" fill="none" stroke="#ff7a3d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
      <polyline points="${bPoints}" fill="none" stroke="#2f7ef7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.75"></polyline>
    </svg>
  `;
}

function findWaveformById(waveformId) {
  return studioWaveforms.find((item) => item.id === waveformId) || null;
}

function isSelectedWaveformEditable() {
  return Boolean(draftWaveform && !draftWaveform.builtin && draftWaveform.editable !== false);
}

function ensureDraftWaveform() {
  if (draftWaveform) {
    return draftWaveform;
  }
  const fallbackWaveform = findWaveformById(selectedWaveformId) || studioWaveforms[0] || null;
  if (!fallbackWaveform) {
    return null;
  }
  draftWaveform = cloneWaveform(fallbackWaveform);
  selectedWaveformId = fallbackWaveform.id;
  return draftWaveform;
}

function markDraftDirty() {
  draftDirty = true;
  renderWaveformEditor();
}

function replaceWaveforms(nextWaveforms) {
  studioWaveforms = Array.isArray(nextWaveforms) ? nextWaveforms : [];
}

function updateSelectedWaveform(waveformId, options = {}) {
  if (!waveformId) {
    selectedWaveformId = "";
    draftWaveform = null;
    draftDirty = false;
    activeDragHandle = null;
    renderWaveformLibrary(studioWaveforms);
    renderWaveformEditor();
    return;
  }
  if (draftDirty && !options.force && selectedWaveformId && selectedWaveformId !== waveformId) {
    const shouldDiscard = window.confirm("当前波形还有未保存更改，是否放弃修改并切换？");
    if (!shouldDiscard) {
      return;
    }
  }
  const waveform = findWaveformById(waveformId);
  if (!waveform) {
    return;
  }
  selectedWaveformId = waveformId;
  draftWaveform = cloneWaveform(waveform);
  draftDirty = false;
  activeDragHandle = null;
  renderWaveformLibrary(studioWaveforms);
  renderWaveformEditor();
}

function renderWaveformLibrary(waveforms) {
  if (!Array.isArray(waveforms) || !waveforms.length) {
    waveformLibrary.innerHTML = '<p class="mini-empty">暂无波形。</p>';
    return;
  }
  waveformLibrary.innerHTML = waveforms
    .map((waveform) => {
      const tag = waveform.builtin ? "内置" : "自定义";
      const steps = Array.isArray(waveform.steps) ? waveform.steps.length : 0;
      const maxStrength = resolveWaveformMaxStrength(waveform);
      const isSelected = waveform.id === selectedWaveformId;
      return `
        <article class="studio-waveform-card${isSelected ? " is-selected" : ""}" data-waveform-id="${escapeHtml(waveform.id)}">
          <div class="studio-waveform-head">
            <div>
              <h3>${escapeHtml(waveform.name)}</h3>
              <p>${escapeHtml(tag)} · ${steps} 步 · 最大强度 ${maxStrength}</p>
            </div>
          </div>
          ${buildWaveformPreviewSvg(waveform)}
          <div class="studio-waveform-actions">
            <button class="secondary" data-action="edit" data-waveform-id="${escapeHtml(waveform.id)}">查看 / 编辑</button>
            <button class="secondary" data-action="duplicate" data-waveform-id="${escapeHtml(waveform.id)}">复制为自定义</button>
            ${waveform.builtin ? "" : `<button class="secondary" data-action="delete" data-waveform-id="${escapeHtml(waveform.id)}">删除</button>`}
          </div>
        </article>
      `;
    })
    .join("");
}

function buildWaveformOptions(selectedValue) {
  return studioWaveforms
    .map((waveform) => `<option value="${escapeHtml(waveform.id)}"${waveform.id === selectedValue ? " selected" : ""}>${escapeHtml(waveform.name)}</option>`)
    .join("");
}

function renderRuleGroups(ruleGroups) {
  if (!Array.isArray(ruleGroups) || !ruleGroups.length) {
    ruleGroupsContainer.innerHTML = '<p class="mini-empty">暂无规则。</p>';
    return;
  }
  ruleGroupsContainer.innerHTML = ruleGroups
    .map((group) => `
      <section class="studio-rule-group">
        <div class="stream-head">
          <h3>${escapeHtml(group.group_label)}</h3>
        </div>
        <div class="studio-rule-list">
          ${(group.rules || [])
            .map((rule) => `
              <article class="studio-rule-item" data-rule-id="${escapeHtml(rule.id)}">
                <div class="studio-rule-main">
                  <strong>${escapeHtml(rule.rule_label || rule.event_type)}</strong>
                  <label class="studio-toggle">
                    <input type="checkbox" data-role="enabled"${rule.enabled ? " checked" : ""} />
                    <span>启用</span>
                  </label>
                </div>
                <label class="studio-rule-select">
                  <span>对应波形</span>
                  <select data-role="waveform-id">${buildWaveformOptions(rule.waveform_id)}</select>
                </label>
              </article>
            `)
            .join("")}
        </div>
      </section>
    `)
    .join("");
}

function renderWaveformEditorCanvas(waveform) {
  if (!waveform || !Array.isArray(waveform.steps) || !waveform.steps.length) {
    waveformCanvas.innerHTML = '<p class="mini-empty">新建波形后，可在这里直接拖动 A / B 通道强度。</p>';
    return;
  }
  const totalDuration = Math.max(1, resolveWaveformTotalDuration(waveform));
  const editable = isSelectedWaveformEditable();
  waveformCanvas.innerHTML = `
    <div class="studio-editor-grid" data-role="waveform-grid">
      ${waveform.steps
        .map((step, index) => {
          const widthRatio = `${(normalizeDuration(step.duration_ms) / totalDuration) * 100}%`;
          const aBottom = `${(clampStrength(step.channel_a) / 180) * 100}%`;
          const bBottom = `${(clampStrength(step.channel_b) / 180) * 100}%`;
          return `
            <div class="studio-editor-segment" style="width:${widthRatio}">
              <div class="studio-editor-fill studio-editor-fill-a" style="height:${aBottom}"></div>
              <div class="studio-editor-fill studio-editor-fill-b" style="height:${bBottom}"></div>
              <button
                type="button"
                class="studio-editor-handle is-a"
                data-role="waveform-handle"
                data-step-index="${index}"
                data-channel="channel_a"
                style="bottom:${aBottom}"
                ${editable ? "" : "disabled"}
              >
                A${clampStrength(step.channel_a)}
              </button>
              <button
                type="button"
                class="studio-editor-handle is-b"
                data-role="waveform-handle"
                data-step-index="${index}"
                data-channel="channel_b"
                style="bottom:${bBottom}"
                ${editable ? "" : "disabled"}
              >
                B${clampStrength(step.channel_b)}
              </button>
              <span class="studio-editor-duration">${normalizeDuration(step.duration_ms)} ms</span>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderWaveformStepsTable(waveform) {
  if (!waveform || !Array.isArray(waveform.steps) || !waveform.steps.length) {
    waveformSteps.innerHTML = '<p class="mini-empty">暂无分段。</p>';
    return;
  }
  const editable = isSelectedWaveformEditable();
  waveformSteps.innerHTML = `
    <div class="studio-waveform-step-table">
      <div class="studio-waveform-step-head">
        <span>分段</span>
        <span>时长 ms</span>
        <span>A</span>
        <span>B</span>
        <span>操作</span>
      </div>
      ${waveform.steps
        .map((step, index) => `
          <div class="studio-waveform-step-row" data-step-index="${index}">
            <strong>${index + 1}</strong>
            <input type="number" min="1" step="1" data-field="duration_ms" value="${normalizeDuration(step.duration_ms)}" ${editable ? "" : "disabled"} />
            <input type="number" min="0" max="180" step="1" data-field="channel_a" value="${clampStrength(step.channel_a)}" ${editable ? "" : "disabled"} />
            <input type="number" min="0" max="180" step="1" data-field="channel_b" value="${clampStrength(step.channel_b)}" ${editable ? "" : "disabled"} />
            <div class="studio-step-actions">
              <button class="secondary" data-action="copy-step" data-step-index="${index}" ${editable ? "" : "disabled"}>复制</button>
              <button class="secondary" data-action="delete-step" data-step-index="${index}" ${editable ? "" : "disabled"}>删除</button>
            </div>
          </div>
        `)
        .join("")}
    </div>
  `;
}

function renderWaveformEditor() {
  const waveform = ensureDraftWaveform();
  if (!waveform) {
    waveformEditor.classList.add("is-empty");
    waveformNameInput.value = "";
    waveformNameInput.disabled = true;
    duplicateWaveformButton.disabled = true;
    deleteWaveformButton.disabled = true;
    saveWaveformButton.disabled = true;
    addStepButton.disabled = true;
    waveformStepCount.textContent = "0";
    waveformDurationTotal.textContent = "0 ms";
    waveformMaxStrength.textContent = "0";
    dirtyIndicator.classList.remove("is-visible");
    waveformMessageText.textContent = "选择一个波形，或新建后开始编辑。";
    renderWaveformEditorCanvas(null);
    renderWaveformStepsTable(null);
    return;
  }

  waveformEditor.classList.remove("is-empty");
  const editable = isSelectedWaveformEditable();
  const maxStrength = resolveWaveformMaxStrength(waveform);
  waveformNameInput.value = waveform.name || "";
  waveformNameInput.disabled = !editable;
  duplicateWaveformButton.disabled = false;
  deleteWaveformButton.disabled = !editable;
  saveWaveformButton.disabled = !editable;
  addStepButton.disabled = !editable;
  waveformStepCount.textContent = String((waveform.steps || []).length);
  waveformDurationTotal.textContent = `${resolveWaveformTotalDuration(waveform)} ms`;
  waveformMaxStrength.textContent = String(maxStrength);
  dirtyIndicator.classList.toggle("is-visible", draftDirty);
  waveformMessageText.textContent = editable
    ? `当前波形可编辑，最大强度 ${maxStrength}。`
    : `当前为内置波形，只读查看。最大强度 ${maxStrength}。`;
  renderWaveformEditorCanvas(waveform);
  renderWaveformStepsTable(waveform);
}

function collectRulePayload() {
  return Array.from(ruleGroupsContainer.querySelectorAll("[data-rule-id]")).map((item) => ({
    id: item.getAttribute("data-rule-id"),
    enabled: item.querySelector('[data-role="enabled"]').checked,
    waveform_id: item.querySelector('[data-role="waveform-id"]').value,
  }));
}

async function refreshStudio() {
  const response = await fetch("/api/bluetooth/studio");
  const payload = await response.json();
  replaceWaveforms(payload.waveforms || []);
  studioRuleGroups = payload.rule_groups || [];
  renderRuleGroups(studioRuleGroups);
  if (!selectedWaveformId && studioWaveforms.length) {
    selectedWaveformId = studioWaveforms[0].id;
  }
  const stillExists = selectedWaveformId && findWaveformById(selectedWaveformId);
  if (stillExists) {
    draftWaveform = cloneWaveform(stillExists);
  } else if (studioWaveforms.length) {
    selectedWaveformId = studioWaveforms[0].id;
    draftWaveform = cloneWaveform(studioWaveforms[0]);
  } else {
    selectedWaveformId = "";
    draftWaveform = null;
  }
  draftDirty = false;
  activeDragHandle = null;
  renderWaveformLibrary(studioWaveforms);
  renderWaveformEditor();
}

function updateDraftStep(stepIndex, field, value) {
  const waveform = ensureDraftWaveform();
  if (!waveform || !waveform.steps[stepIndex] || !isSelectedWaveformEditable()) {
    return;
  }
  if (field === "duration_ms") {
    waveform.steps[stepIndex].duration_ms = normalizeDuration(value);
  } else if (field === "channel_a" || field === "channel_b") {
    waveform.steps[stepIndex][field] = clampStrength(value);
  }
  draftDirty = true;
  renderWaveformEditor();
}

function addDraftStep() {
  const waveform = ensureDraftWaveform();
  if (!waveform || !isSelectedWaveformEditable()) {
    return;
  }
  waveform.steps.push({ duration_ms: 200, channel_a: 0, channel_b: 0 });
  markDraftDirty();
}

function duplicateDraftStep(stepIndex) {
  const waveform = ensureDraftWaveform();
  if (!waveform || !waveform.steps[stepIndex] || !isSelectedWaveformEditable()) {
    return;
  }
  waveform.steps.splice(stepIndex + 1, 0, cloneWaveformStep(waveform.steps[stepIndex]));
  markDraftDirty();
}

function deleteDraftStep(stepIndex) {
  const waveform = ensureDraftWaveform();
  if (!waveform || !waveform.steps[stepIndex] || !isSelectedWaveformEditable()) {
    return;
  }
  if (waveform.steps.length === 1) {
    waveformMessageText.textContent = "波形至少需要保留一个分段。";
    return;
  }
  waveform.steps.splice(stepIndex, 1);
  markDraftDirty();
}

function beginDragHandle(pointerEvent, handleElement) {
  if (!isSelectedWaveformEditable()) {
    return;
  }
  const stepIndex = Number(handleElement.getAttribute("data-step-index"));
  const channel = handleElement.getAttribute("data-channel");
  const gridElement = waveformCanvas.querySelector('[data-role="waveform-grid"]');
  if (!Number.isInteger(stepIndex) || !channel || !gridElement) {
    return;
  }
  activeDragHandle = {
    pointerId: pointerEvent.pointerId,
    stepIndex,
    channel,
  };
  handleElement.setPointerCapture?.(pointerEvent.pointerId);
  updateDraftStrengthFromPointer(pointerEvent.clientY, gridElement);
}

function updateDraftStrengthFromPointer(clientY, gridElement) {
  if (!activeDragHandle || !draftWaveform || !draftWaveform.steps[activeDragHandle.stepIndex]) {
    return;
  }
  const rect = gridElement.getBoundingClientRect();
  if (!rect.height) {
    return;
  }
  const offset = Math.max(0, Math.min(rect.height, rect.bottom - clientY));
  const percent = offset / rect.height;
  draftWaveform.steps[activeDragHandle.stepIndex][activeDragHandle.channel] = clampStrength(percent * 180);
  draftDirty = true;
  renderWaveformEditor();
}

async function createWaveform() {
  newWaveformButton.disabled = true;
  const response = await fetch("/api/bluetooth/waveforms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: getDefaultWaveformName() }),
  });
  const payload = await response.json().catch(() => ({}));
  newWaveformButton.disabled = false;
  if (!response.ok) {
    waveformMessageText.textContent = payload.detail || "创建波形失败";
    return;
  }
  replaceWaveforms(payload.waveforms || []);
  renderRuleGroups(studioRuleGroups);
  updateSelectedWaveform(payload.waveform?.id || "", { force: true });
}

async function duplicateSelectedWaveform() {
  const waveform = ensureDraftWaveform();
  if (!waveform) {
    return;
  }
  duplicateWaveformButton.disabled = true;
  const response = await fetch(`/api/bluetooth/waveforms/${encodeURIComponent(waveform.id)}/duplicate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: waveform.builtin ? `${waveform.name} - 副本` : `${waveform.name} - 复制` }),
  });
  const payload = await response.json().catch(() => ({}));
  duplicateWaveformButton.disabled = false;
  if (!response.ok) {
    waveformMessageText.textContent = payload.detail || "复制波形失败";
    return;
  }
  replaceWaveforms(payload.waveforms || []);
  updateSelectedWaveform(payload.waveform?.id || "", { force: true });
}

async function saveSelectedWaveform() {
  const waveform = ensureDraftWaveform();
  if (!waveform || !isSelectedWaveformEditable()) {
    return;
  }
  saveWaveformButton.disabled = true;
  const response = await fetch(`/api/bluetooth/waveforms/${encodeURIComponent(waveform.id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: String(waveform.name || "").trim(),
      steps: (waveform.steps || []).map((step) => ({
        duration_ms: normalizeDuration(step.duration_ms),
        channel_a: clampStrength(step.channel_a),
        channel_b: clampStrength(step.channel_b),
      })),
    }),
  });
  const payload = await response.json().catch(() => ({}));
  saveWaveformButton.disabled = false;
  if (!response.ok) {
    waveformMessageText.textContent = payload.detail || "保存波形失败";
    return;
  }
  replaceWaveforms(payload.waveforms || []);
  updateSelectedWaveform(payload.waveform?.id || waveform.id, { force: true });
  waveformMessageText.textContent = "波形已保存。";
  renderRuleGroups(studioRuleGroups);
}

async function deleteSelectedWaveform(waveformId) {
  const targetWaveformId = waveformId || selectedWaveformId;
  if (!targetWaveformId) {
    return;
  }
  const targetWaveform = findWaveformById(targetWaveformId);
  if (!targetWaveform || targetWaveform.builtin) {
    return;
  }
  const shouldDelete = window.confirm(`确认删除波形“${targetWaveform.name}”吗？`);
  if (!shouldDelete) {
    return;
  }
  deleteWaveformButton.disabled = true;
  const response = await fetch(`/api/bluetooth/waveforms/${encodeURIComponent(targetWaveformId)}`, {
    method: "DELETE",
  });
  const payload = await response.json().catch(() => ({}));
  deleteWaveformButton.disabled = false;
  if (!response.ok) {
    waveformMessageText.textContent = payload.detail || "删除波形失败";
    return;
  }
  replaceWaveforms(payload.waveforms || []);
  const nextWaveform = studioWaveforms[0] || null;
  updateSelectedWaveform(nextWaveform ? nextWaveform.id : "", { force: true });
}

waveformLibrary.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action], [data-waveform-id]");
  if (!target) {
    return;
  }
  const waveformId = target.getAttribute("data-waveform-id");
  const action = target.getAttribute("data-action");
  if (!action) {
    updateSelectedWaveform(waveformId);
    return;
  }
  if (action === "edit") {
    updateSelectedWaveform(waveformId);
    return;
  }
  if (action === "duplicate") {
    if (waveformId && waveformId !== selectedWaveformId) {
      updateSelectedWaveform(waveformId, { force: true });
    }
    await duplicateSelectedWaveform();
    return;
  }
  if (action === "delete") {
    await deleteSelectedWaveform(waveformId);
  }
});

waveformNameInput.addEventListener("input", () => {
  const waveform = ensureDraftWaveform();
  if (!waveform || !isSelectedWaveformEditable()) {
    return;
  }
  waveform.name = waveformNameInput.value;
  markDraftDirty();
});

waveformSteps.addEventListener("input", (event) => {
  const input = event.target.closest("input[data-field]");
  if (!input) {
    return;
  }
  const row = input.closest("[data-step-index]");
  const stepIndex = Number(row?.getAttribute("data-step-index"));
  const field = input.getAttribute("data-field");
  if (!Number.isInteger(stepIndex) || !field) {
    return;
  }
  updateDraftStep(stepIndex, field, input.value);
});

waveformSteps.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) {
    return;
  }
  const stepIndex = Number(button.getAttribute("data-step-index"));
  if (!Number.isInteger(stepIndex)) {
    return;
  }
  const action = button.getAttribute("data-action");
  if (action === "copy-step") {
    duplicateDraftStep(stepIndex);
  } else if (action === "delete-step") {
    deleteDraftStep(stepIndex);
  }
});

waveformCanvas.addEventListener("pointerdown", (event) => {
  const handle = event.target.closest('[data-role="waveform-handle"]');
  if (!handle) {
    return;
  }
  beginDragHandle(event, handle);
});

document.addEventListener("pointermove", (event) => {
  if (!activeDragHandle) {
    return;
  }
  const gridElement = waveformCanvas.querySelector('[data-role="waveform-grid"]');
  if (!gridElement) {
    return;
  }
  updateDraftStrengthFromPointer(event.clientY, gridElement);
});

document.addEventListener("pointerup", () => {
  activeDragHandle = null;
});

newWaveformButton.addEventListener("click", createWaveform);
duplicateWaveformButton.addEventListener("click", duplicateSelectedWaveform);
deleteWaveformButton.addEventListener("click", () => deleteSelectedWaveform(selectedWaveformId));
saveWaveformButton.addEventListener("click", saveSelectedWaveform);
addStepButton.addEventListener("click", addDraftStep);

saveButton.addEventListener("click", async () => {
  saveButton.disabled = true;
  const response = await fetch("/api/bluetooth/rules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rules: collectRulePayload() }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    studioMessageText.textContent = payload.detail || "规则保存失败";
    saveButton.disabled = false;
    return;
  }
  studioMessageText.textContent = `规则已保存，共更新 ${payload.updated_count || 0} 项。`;
  studioRuleGroups = payload.rule_groups || studioRuleGroups;
  renderRuleGroups(studioRuleGroups);
  saveButton.disabled = false;
});

refreshStudio().catch((error) => {
  waveformMessageText.textContent = `页面初始化失败: ${error}`;
});
