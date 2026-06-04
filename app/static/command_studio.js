const giftRulesContainer = document.getElementById("command-studio-gift-rules");
const fixedLikeIdContainer = document.getElementById("command-studio-like-fixed-id");
const fixedDanmakuIdsContainer = document.getElementById("command-studio-danmaku-fixed-ids");
const saveButton = document.getElementById("command-studio-save-btn");
const messageText = document.getElementById("command-studio-message-text");

const eventTypeLabels = {
  gift: "礼物",
  super_chat: "醒目留言",
  guard_buy: "上舰",
  guard_renew: "续费",
};

const danmakuEventTypeLabels = {
  danmaku: "普通弹幕",
  danmaku_captain: "舰长弹幕",
  danmaku_commander: "提督弹幕",
  danmaku_governor: "总督弹幕",
};

const fixedDanmakuCommandIds = {
  danmaku: "danmaku_trigger",
  danmaku_captain: "danmaku_captain_trigger",
  danmaku_commander: "danmaku_commander_trigger",
  danmaku_governor: "danmaku_governor_trigger",
};
const fixedLikeCommandId = "like_trigger";
const fixedLikeHint = "点赞指令固定，不支持在页面修改。";
const fixedDanmakuHint = "弹幕指令固定，不支持在页面修改。";

let studioState = {
  rules: [],
  like_command_id: fixedLikeCommandId,
  danmaku_command_ids: {},
  command_slots: [],
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildCommandSlotOptions(selectedValue, allowBlank = false) {
  const options = [];
  if (allowBlank) {
    options.push(`<option value="">使用固定槽位</option>`);
  }
  return options
    .concat(
      studioState.command_slots.map(
        (slot) => `<option value="${escapeHtml(slot)}"${slot === selectedValue ? " selected" : ""}>${escapeHtml(slot)}</option>`
      )
    )
    .join("");
}

function renderGiftRuleGroups() {
  const grouped = Object.keys(eventTypeLabels).map((eventType) => ({
    eventType,
    label: eventTypeLabels[eventType],
    rules: studioState.rules.filter((rule) => rule.event_type === eventType),
  }));
  giftRulesContainer.innerHTML = grouped
    .map(
      (group) => `
        <section class="studio-rule-group" data-event-type="${escapeHtml(group.eventType)}">
          <div class="stream-head">
            <h3>${escapeHtml(group.label)}</h3>
            <div class="studio-waveform-actions">
              <button class="secondary mini-action" data-action="sort-gift-rules" data-event-type="${escapeHtml(group.eventType)}">按价格升序整理</button>
              <button class="secondary mini-action" data-action="add-gift-rule" data-event-type="${escapeHtml(group.eventType)}">新增档位</button>
            </div>
          </div>
          <div class="studio-rule-list">
            ${group.rules
              .map(
                (rule) => `
                  <article class="studio-rule-item" data-rule-id="${escapeHtml(rule.id)}">
                    <div class="studio-rule-main">
                      <strong>${escapeHtml(group.label)} 档位</strong>
                      <label class="studio-toggle">
                        <input type="checkbox" data-role="enabled"${rule.enabled ? " checked" : ""} />
                        <span>启用</span>
                      </label>
                    </div>
                    <div class="control-grid session-grid">
                      <label class="studio-rule-select">
                        <span>最低价格</span>
                        <input type="number" min="0" step="1" data-role="min-price" value="${escapeHtml(rule.min_price)}" />
                      </label>
                      <label class="studio-rule-select">
                        <span>最高价格</span>
                        <input type="number" min="0" step="1" data-role="max-price" value="${rule.max_price ?? ""}" placeholder="留空表示无上限" />
                      </label>
                      <label class="studio-rule-select">
                        <span>指令槽位</span>
                        <select data-role="command-slot">${buildCommandSlotOptions(rule.command_slot)}</select>
                      </label>
                    </div>
                    <div class="studio-waveform-actions">
                      <button class="secondary mini-action" data-action="remove-gift-rule" data-rule-id="${escapeHtml(rule.id)}">删除</button>
                    </div>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>
      `
    )
    .join("");
}

function sortGiftRulesByPrice(eventType) {
  const targetRules = studioState.rules
    .filter((rule) => rule.event_type === eventType)
    .sort((left, right) => {
      const minDelta = Number(left.min_price || 0) - Number(right.min_price || 0);
      if (minDelta !== 0) {
        return minDelta;
      }
      const leftMax = left.max_price == null ? Number.MAX_SAFE_INTEGER : Number(left.max_price);
      const rightMax = right.max_price == null ? Number.MAX_SAFE_INTEGER : Number(right.max_price);
      return leftMax - rightMax;
    });
  const otherRules = studioState.rules.filter((rule) => rule.event_type !== eventType);
  studioState.rules = otherRules.concat(targetRules);
}

function renderFixedLikeCommandId() {
  fixedLikeIdContainer.innerHTML = `
    <article class="studio-rule-item">
      <div class="studio-rule-main">
        <strong>点赞事件</strong>
      </div>
      <label class="studio-rule-select">
        <span>固定指令 ID</span>
        <input type="text" value="${escapeHtml(studioState.like_command_id || fixedLikeCommandId)}" readonly />
      </label>
    </article>
  `;
}

function renderFixedDanmakuCommandIds() {
  const fixedIds = Object.keys(danmakuEventTypeLabels).map((eventType) => ({
    eventType,
    label: danmakuEventTypeLabels[eventType],
    commandId: studioState.danmaku_command_ids?.[eventType] || "",
  }));
  fixedDanmakuIdsContainer.innerHTML = fixedIds
    .map(
      (item) => `
        <article class="studio-rule-item">
          <div class="studio-rule-main">
            <strong>${escapeHtml(item.label)}</strong>
          </div>
          <label class="studio-rule-select">
            <span>固定指令 ID</span>
            <input type="text" value="${escapeHtml(item.commandId)}" readonly />
          </label>
        </article>
      `
    )
    .join("");
}

function renderAll() {
  renderGiftRuleGroups();
  renderFixedLikeCommandId();
  renderFixedDanmakuCommandIds();
}

function collectGiftRules() {
  return Array.from(giftRulesContainer.querySelectorAll("[data-rule-id]")).map((element) => ({
    id: element.dataset.ruleId,
    enabled: Boolean(element.querySelector('[data-role="enabled"]')?.checked),
    event_type: element.closest("[data-event-type]")?.dataset.eventType || "gift",
    min_price: Math.max(0, Number(element.querySelector('[data-role="min-price"]')?.value || 0) || 0),
    max_price: normalizeOptionalNumber(element.querySelector('[data-role="max-price"]')?.value),
    command_slot: element.querySelector('[data-role="command-slot"]')?.value || "",
  }));
}

function normalizeOptionalNumber(value) {
  if (value === "" || value == null) {
    return null;
  }
  return Math.max(0, Number(value) || 0);
}

async function refreshStudio() {
  const response = await fetch("/api/command/studio");
  const payload = await response.json();
  studioState = {
    rules: payload.rules || [],
    like_command_id: payload.like_command_id || fixedLikeCommandId,
    danmaku_command_ids: payload.danmaku_command_ids || fixedDanmakuCommandIds,
    command_slots: payload.command_slots || [],
  };
  renderAll();
}

giftRulesContainer.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const action = target.dataset.action;
  if (action === "add-gift-rule") {
    const eventType = target.dataset.eventType || "gift";
    studioState.rules.push({
      id: `${eventType}-rule-${Date.now()}`,
      enabled: true,
      event_type: eventType,
      min_price: 0,
      max_price: null,
      command_slot: studioState.command_slots[0] || "",
    });
    renderGiftRuleGroups();
    return;
  }
  if (action === "sort-gift-rules") {
    const eventType = target.dataset.eventType || "gift";
    sortGiftRulesByPrice(eventType);
    renderGiftRuleGroups();
    messageText.textContent = `${eventTypeLabels[eventType] || "当前"} 档位已按价格升序整理`;
    return;
  }
  if (action === "remove-gift-rule") {
    const ruleId = target.dataset.ruleId || "";
    studioState.rules = studioState.rules.filter((rule) => rule.id !== ruleId);
    renderGiftRuleGroups();
  }
});

saveButton.addEventListener("click", async () => {
  saveButton.disabled = true;
  const response = await fetch("/api/command/studio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      rules: collectGiftRules(),
      like_rules: [],
      danmaku_slot_rules: [],
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    messageText.textContent = payload.detail || "保存失败";
    saveButton.disabled = false;
    return;
  }
  messageText.textContent = "IM 规则已保存";
  await refreshStudio();
  saveButton.disabled = false;
});

refreshStudio();
