const waveformLibrary = document.getElementById("studio-waveform-library");
const ruleGroupsContainer = document.getElementById("studio-rule-groups");
const saveButton = document.getElementById("studio-save-btn");
const studioMessageText = document.getElementById("studio-message-text");

let studioWaveforms = [];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function resolveWaveformMaxStrength(waveform) {
  const steps = Array.isArray(waveform.steps) ? waveform.steps : [];
  return Math.max(
    0,
    ...steps.flatMap((step) => [Number(step.channel_a || 0), Number(step.channel_b || 0)])
  );
}

function buildWaveformPreviewSvg(waveform) {
  const steps = Array.isArray(waveform.steps) ? waveform.steps : [];
  if (!steps.length) {
    return '<svg viewBox="0 0 240 88" class="waveform-preview"></svg>';
  }
  const width = 240;
  const height = 88;
  const padding = 8;
  const totalDuration = steps.reduce((sum, step) => sum + Math.max(1, Number(step.duration_ms || 0)), 0);
  const maxStrength = Math.max(1, resolveWaveformMaxStrength(waveform));

  const buildLinePath = (key) => {
    let elapsed = 0;
    const points = [`${padding},${height - padding}`];
    steps.forEach((step) => {
      const duration = Math.max(1, Number(step.duration_ms || 0));
      const value = Math.max(0, Number(step[key] || 0));
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
      return `
        <article class="studio-waveform-card" id="waveform-${escapeHtml(waveform.id)}">
          <div class="studio-waveform-head">
            <div>
              <h3>${escapeHtml(waveform.name)}</h3>
              <p>${escapeHtml(tag)} · ${steps} 步 · 最大强度 ${maxStrength}</p>
            </div>
          </div>
          ${buildWaveformPreviewSvg(waveform)}
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

async function refreshStudio() {
  const response = await fetch("/api/bluetooth/studio");
  const payload = await response.json();
  studioWaveforms = payload.waveforms || [];
  renderWaveformLibrary(studioWaveforms);
  renderRuleGroups(payload.rule_groups || []);
}

function collectRulePayload() {
  return Array.from(ruleGroupsContainer.querySelectorAll("[data-rule-id]")).map((item) => ({
    id: item.getAttribute("data-rule-id"),
    enabled: item.querySelector('[data-role="enabled"]').checked,
    waveform_id: item.querySelector('[data-role="waveform-id"]').value,
  }));
}

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
  await refreshStudio();
  saveButton.disabled = false;
});

refreshStudio();
