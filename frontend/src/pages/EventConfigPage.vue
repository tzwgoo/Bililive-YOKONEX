<template>
  <main class="studio-page event-config-page">
    <ACard :bordered="false" data-testid="workspace-summary-card">
      <div class="workspace-summary">
        <div class="workspace-summary-header">
          <h1>事件配置</h1>
        </div>
        <div class="workspace-overview workspace-overview-metrics-only">
          <div class="hero-metrics">
            <article class="hero-metric">
              <strong>{{ commandRuleCount }}</strong>
              <span>IM 档位</span>
            </article>
            <article class="hero-metric">
              <strong>{{ bluetoothRuleCount }}</strong>
              <span>蓝牙规则</span>
            </article>
            <article class="hero-metric">
              <strong>{{ waveformCount }}</strong>
              <span>可选波形</span>
            </article>
          </div>
        </div>
      </div>
    </ACard>

    <AAlert v-if="message" :message="message" type="info" show-icon />

    <section class="event-config-layout">
      <div class="event-config-main">
        <ACard :bordered="false" class="editor-shell">
          <div class="editor-shell-header">
            <div>
              <p class="editor-shell-eyebrow">{{ currentSectionLabel }}</p>
              <h2>{{ currentPanelTitle }}</h2>
            </div>
            <Button
              :data-testid="currentSaveButtonTestId"
              type="primary"
              :loading="currentSaveLoading"
              @click="handlePrimarySave"
            >
              {{ currentSaveLabel }}
            </Button>
          </div>
        </ACard>

        <SharedEventSettingsPanel
          v-if="activeTab === 'shared'"
          :selected-config="selectedSharedConfig"
          :session-draft="sessionDraft"
        />

        <ImRuleGroupsPanel
          v-else-if="activeTab === 'im'"
          :group="currentImGroup"
          :command-slot-options="commandSlotOptions"
          :studio="commandStore.studio"
          @add-rule="addRule"
          @sort-rules="sortRules"
          @remove-rule="removeRule"
          @update-max-price="updateMaxPrice"
        />

        <BluetoothEventRulePanel
          v-else-if="activeTab === 'bluetooth'"
          :rule-group="currentBluetoothGroup"
          :ems-waveform-options="emsWaveformOptions"
          :toy-waveform-options="toyWaveformOptions"
          @update-min-price="updateMinPrice"
          @update-max-price="updateMaxPriceFilter"
          @update-guard-waveform="updateGuardWaveform"
        />

        <ACard v-else title="抖音直播接入" :bordered="false" class="douyin-config-panel">
          <div class="douyin-config-grid">
            <label class="douyin-field">
              <span>douyinLive 服务地址</span>
              <Input
                v-model:value="sessionDraft.douyin_ws_base_url"
                data-testid="douyin-ws-base-url"
                placeholder="ws://127.0.0.1:1088"
              />
            </label>
            <label class="douyin-field">
              <span>直播间标识</span>
              <Input
                v-model:value="sessionDraft.value"
                data-testid="douyin-room-id"
                placeholder="live.douyin.com 后面的那段 ID"
              />
            </label>
            <label class="douyin-field douyin-field-full">
              <span>douyinLive.exe 路径</span>
              <Input
                v-model:value="sessionDraft.douyin_executable_path"
                data-testid="douyin-executable-path"
                placeholder="留空使用项目内置 douyinLive.exe，也可填写自定义路径"
              />
            </label>
            <label class="douyin-field douyin-field-full">
              <span>抖音 Cookie</span>
              <Input
                v-model:value="sessionDraft.douyin_cookie"
                data-testid="douyin-cookie"
                placeholder="可选。礼物收不到时，填 live.douyin.com 登录后的完整 Cookie"
              />
            </label>
          </div>
          <div class="douyin-event-map">
            <article>
              <strong>弹幕</strong>
              <span>WebcastChatMessage -> 普通弹幕</span>
            </article>
            <article>
              <strong>礼物</strong>
              <span>WebcastGiftMessage -> 礼物档位</span>
            </article>
            <article>
              <strong>点赞</strong>
              <span>WebcastLikeMessage -> 点赞触发</span>
            </article>
            <article>
              <strong>互动</strong>
              <span>进场 / 关注 -> 互动事件</span>
            </article>
          </div>
        </ACard>
      </div>

      <ASidebarCard :bordered="false" class="event-config-sidebar">
        <EventConfigTabs v-model:active-tab="activeTab" :tabs="tabs" />

        <div class="event-list-header">
          <strong>事件列表</strong>
          <span>{{ currentEventItems.length }} 项</span>
        </div>

        <AEmpty v-if="currentEventItems.length === 0" description="暂无可配置事件" />

        <div v-else class="event-list">
          <button
            v-for="item in currentEventItems"
            :key="item.key"
            type="button"
            class="event-list-item"
            :class="{ 'event-list-item-active': item.key === currentSelectedKey }"
            :data-testid="`event-item-${item.key}`"
            @click="handleSelectEvent(item.key)"
          >
            <div class="event-list-item-copy">
              <strong>{{ item.label }}</strong>
              <span>{{ item.description }}</span>
            </div>
            <div v-if="item.toggleable" class="event-list-switch" @click.stop>
              <Switch
                :checked="item.enabled"
                size="small"
                @change="handleToggleEvent(item.key, Boolean($event))"
              />
            </div>
            <span v-else class="event-list-static-tag">通用</span>
          </button>
        </div>
      </ASidebarCard>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { Alert as AAlert, Button, Card as ACard, Empty as AEmpty, Input, Switch } from "ant-design-vue";
import BluetoothEventRulePanel from "@/components/events/BluetoothEventRulePanel.vue";
import EventConfigTabs from "@/components/events/EventConfigTabs.vue";
import ImRuleGroupsPanel from "@/components/events/ImRuleGroupsPanel.vue";
import SharedEventSettingsPanel from "@/components/events/SharedEventSettingsPanel.vue";
import { useLocalDraft } from "@/composables/useLocalDraft";
import { useBluetoothStore } from "@/stores/bluetooth";
import { useCommandStore } from "@/stores/command";
import type { BluetoothRuleGroup, BluetoothStudioRule } from "@/types/bluetooth";
import type { CommandStudioRule } from "@/types/command";
import type { SessionStartPayload } from "@/types/session";

const ASidebarCard = ACard;

type EventTabKey = "shared" | "im" | "bluetooth" | "douyin";
type SharedConfigKey = "like" | "danmaku";
type DouyinConfigKey = "connection" | "events";

type EventListItem = {
  key: string;
  label: string;
  enabled: boolean;
  description: string;
  toggleable: boolean;
};

const defaultSessionDraft: SessionStartPayload = {
  mode: "third_party",
  value: "",
  douyin_ws_base_url: "ws://127.0.0.1:1088",
  douyin_executable_path: "",
  douyin_cookie: "",
  trigger_mode: "by_quantity",
  like_multiple: 100,
  danmaku_enabled: false,
  danmaku_keywords: "",
  danmaku_cooldown_seconds: 0,
  danmaku_user_limit_window_seconds: 0,
  danmaku_user_limit_max_triggers: 0,
  danmaku_min_guard_level: 0,
};

const props = withDefaults(
  defineProps<{
    initialTab?: EventTabKey;
  }>(),
  {
    initialTab: "shared",
  },
);

const commandStore = useCommandStore();
const bluetoothStore = useBluetoothStore();
const activeTabStorage = useLocalDraft<EventTabKey>("biliLive.eventConfigTab", props.initialTab);
const sessionDraftStorage = useLocalDraft<SessionStartPayload>("biliLive.sessionDraft", defaultSessionDraft);

const activeTab = ref<EventTabKey>(activeTabStorage.load());
const message = ref("规则修改后可分别保存到通用监听草稿、IM 配置和蓝牙配置。");
const savingSharedConfig = ref(false);
const savingCommandRules = ref(false);
const savingBluetoothRules = ref(false);
const draftRules = ref<CommandStudioRule[]>([]);
const draftRuleGroups = ref<BluetoothRuleGroup[]>([]);
const sessionDraft = reactive(sessionDraftStorage.load());
const selectedSharedConfig = ref<SharedConfigKey>("like");
const selectedDouyinConfig = ref<DouyinConfigKey>("connection");
const selectedImEventType = ref("");
const selectedBluetoothGroupId = ref("");

const tabs = [
  { key: "shared", label: "通用" },
  { key: "im", label: "IM" },
  { key: "bluetooth", label: "蓝牙" },
  { key: "douyin", label: "抖音" },
] as const;

const groupedRules = computed(() => {
  const groups = commandStore.studio?.event_types || [];
  return groups.map((group) => ({
    eventType: group.value,
    label: group.label,
    rules: draftRules.value.filter((rule) => rule.event_type === group.value),
  }));
});
const commandSlots = computed(() => commandStore.studio?.command_slots || []);
const commandSlotOptions = computed(() => commandSlots.value.map((slot) => ({ label: slot, value: slot })));
const emsWaveformOptions = computed(() =>
  (bluetoothStore.studio?.ems_waveforms || []).map((waveform) => ({ label: waveform.name, value: waveform.id })),
);
const toyWaveformOptions = computed(() =>
  (bluetoothStore.studio?.toy_waveforms || []).map((waveform) => ({ label: waveform.name, value: waveform.id })),
);
const commandRuleCount = computed(() => draftRules.value.length);
const bluetoothRuleCount = computed(() =>
  draftRuleGroups.value.reduce((sum, group) => sum + group.rules.length, 0),
);
const waveformCount = computed(() =>
  (bluetoothStore.studio?.ems_waveforms?.length || 0) + (bluetoothStore.studio?.toy_waveforms?.length || 0),
);
const priceFilterGroupIds = new Set(["gift", "super_chat", "guard_buy", "guard_renew"]);

const sharedEventItems = computed<EventListItem[]>(() => [
  {
    key: "like",
    label: "点赞触发",
    enabled: true,
    description: `当前倍率 ${sessionDraft.like_multiple || 1} 倍`,
    toggleable: false,
  },
  {
    key: "danmaku",
    label: "弹幕触发",
    enabled: sessionDraft.danmaku_enabled,
    description: sessionDraft.danmaku_keywords ? `关键词：${sessionDraft.danmaku_keywords}` : "暂未配置关键词",
    toggleable: true,
  },
]);
const imEventItems = computed<EventListItem[]>(() =>
  groupedRules.value.map((group) => ({
    key: group.eventType,
    label: group.label,
    enabled: group.rules.length > 0 && group.rules.some((rule) => rule.enabled),
    description: group.rules.length > 0 ? `${group.rules.length} 条档位规则` : "暂无档位规则",
    toggleable: true,
  })),
);
const bluetoothEventItems = computed<EventListItem[]>(() =>
  draftRuleGroups.value.map((group) => ({
    key: group.group_id,
    label: group.group_label,
    enabled: group.rules.length > 0 && group.rules.some((rule) => rule.enabled),
    description: `${group.rules.length} 条波形规则`,
    toggleable: true,
  })),
);
const douyinEventItems = computed<EventListItem[]>(() => [
  {
    key: "connection",
    label: "连接服务",
    enabled: Boolean(sessionDraft.douyin_ws_base_url && sessionDraft.value),
    description: sessionDraft.douyin_executable_path ? "使用自定义 exe 自动拉起" : "使用内置 exe 自动拉起",
    toggleable: false,
  },
  {
    key: "events",
    label: "事件映射",
    enabled: true,
    description: "弹幕、礼物、点赞、互动",
    toggleable: false,
  },
]);
const currentEventItems = computed(() => {
  if (activeTab.value === "shared") {
    return sharedEventItems.value;
  }
  if (activeTab.value === "im") {
    return imEventItems.value;
  }
  return activeTab.value === "bluetooth" ? bluetoothEventItems.value : douyinEventItems.value;
});
const currentSelectedKey = computed(() => {
  if (activeTab.value === "shared") {
    return selectedSharedConfig.value;
  }
  if (activeTab.value === "im") {
    return selectedImEventType.value;
  }
  return activeTab.value === "bluetooth" ? selectedBluetoothGroupId.value : selectedDouyinConfig.value;
});
const currentImGroup = computed(() =>
  groupedRules.value.find((group) => group.eventType === selectedImEventType.value) || null,
);
const currentBluetoothGroup = computed(() =>
  draftRuleGroups.value.find((group) => group.group_id === selectedBluetoothGroupId.value) || null,
);
const currentSectionLabel = computed(() => {
  if (activeTab.value === "shared") {
    return "通用事件";
  }
  if (activeTab.value === "im") {
    return "IM 事件";
  }
  return activeTab.value === "bluetooth" ? "蓝牙事件" : "抖音接入";
});
const currentPanelTitle = computed(() => {
  if (activeTab.value === "shared") {
    return selectedSharedConfig.value === "like" ? "点赞触发配置" : "弹幕触发配置";
  }
  if (activeTab.value === "im") {
    return currentImGroup.value?.label || "请选择 IM 事件";
  }
  if (activeTab.value === "bluetooth") {
    return currentBluetoothGroup.value?.group_label || "请选择蓝牙事件";
  }
  return selectedDouyinConfig.value === "connection" ? "连接服务配置" : "抖音事件映射";
});
const currentSaveLabel = computed(() => {
  if (activeTab.value === "shared") {
    return "保存通用配置";
  }
  if (activeTab.value === "im") {
    return "保存 IM 规则";
  }
  return activeTab.value === "bluetooth" ? "保存蓝牙规则" : "保存抖音配置";
});
const currentSaveButtonTestId = computed(() => {
  if (activeTab.value === "shared") {
    return "save-shared-config";
  }
  if (activeTab.value === "im") {
    return "command-save";
  }
  return activeTab.value === "bluetooth" ? "save-rules" : "save-douyin-config";
});
const currentSaveLoading = computed(() => {
  if (activeTab.value === "shared") {
    return savingSharedConfig.value;
  }
  if (activeTab.value === "im") {
    return savingCommandRules.value;
  }
  return activeTab.value === "bluetooth" ? savingBluetoothRules.value : savingSharedConfig.value;
});

watch(activeTab, (value) => {
  activeTabStorage.save(value);
});

watch(
  () => commandStore.studio,
  (studio) => {
    if (!studio) {
      return;
    }
    draftRules.value = studio.rules.map((rule) => ({ ...rule }));
  },
  { immediate: true },
);

watch(
  () => bluetoothStore.studio,
  (studio) => {
    if (!studio) {
      draftRuleGroups.value = [];
      return;
    }
    draftRuleGroups.value = (studio.rule_groups || []).map((group) => ({
      ...group,
      rules: group.rules.map((rule) => ({
        ...rule,
        filters: { ...(rule.filters || {}) },
      })),
    }));
  },
  { immediate: true, deep: true },
);

watch(
  groupedRules,
  (groups) => {
    // IM 配置改成单事件编辑后，需要保证左侧始终落在一个有效事件上。
    if (groups.length === 0) {
      selectedImEventType.value = "";
      return;
    }
    if (!groups.some((group) => group.eventType === selectedImEventType.value)) {
      selectedImEventType.value = groups[0].eventType;
    }
  },
  { immediate: true },
);

watch(
  draftRuleGroups,
  (groups) => {
    // 蓝牙事件切换后仍保持当前上下文，避免保存后回到空白页。
    if (groups.length === 0) {
      selectedBluetoothGroupId.value = "";
      return;
    }
    if (!groups.some((group) => group.group_id === selectedBluetoothGroupId.value)) {
      selectedBluetoothGroupId.value = groups[0].group_id;
    }
  },
  { immediate: true, deep: true },
);

function normalizeNonNegative(value: number) {
  return Math.max(0, Math.round(Number(value || 0)));
}

function handleSelectEvent(key: string) {
  if (activeTab.value === "shared") {
    selectedSharedConfig.value = key as SharedConfigKey;
    return;
  }
  if (activeTab.value === "im") {
    selectedImEventType.value = key;
    return;
  }
  if (activeTab.value === "douyin") {
    selectedDouyinConfig.value = key as DouyinConfigKey;
    return;
  }
  selectedBluetoothGroupId.value = key;
}

function handleToggleEvent(key: string, enabled: boolean) {
  if (activeTab.value === "shared") {
    setSharedEventEnabled(key as SharedConfigKey, enabled);
    return;
  }
  if (activeTab.value === "im") {
    setImGroupEnabled(key, enabled);
    return;
  }
  if (activeTab.value === "douyin") {
    return;
  }
  setBluetoothGroupEnabled(key, enabled);
}

function updateMaxPrice(rule: CommandStudioRule, value: number | null) {
  rule.max_price = value == null ? null : normalizeNonNegative(Number(value));
}

function addRule(eventType: string) {
  draftRules.value.push({
    id: `${eventType}-rule-${Date.now()}`,
    enabled: true,
    event_type: eventType,
    min_price: 0,
    max_price: null,
    command_slot: commandSlots.value[0] || "",
  });
}

function sortRules(eventType: string) {
  const current = [...draftRules.value];
  const sortedTarget = current
    .filter((rule) => rule.event_type === eventType)
    .sort((left, right) => {
      const minDelta = normalizeNonNegative(left.min_price) - normalizeNonNegative(right.min_price);
      if (minDelta !== 0) {
        return minDelta;
      }
      const leftMax = left.max_price == null ? Number.MAX_SAFE_INTEGER : normalizeNonNegative(left.max_price);
      const rightMax = right.max_price == null ? Number.MAX_SAFE_INTEGER : normalizeNonNegative(right.max_price);
      return leftMax - rightMax;
    });
  draftRules.value = current.filter((rule) => rule.event_type !== eventType).concat(sortedTarget);
  message.value = `${groupedRules.value.find((item) => item.eventType === eventType)?.label || "当前"}档位已按价格升序整理`;
}

function removeRule(ruleId: string) {
  draftRules.value = draftRules.value.filter((rule) => rule.id !== ruleId);
}

function updateMinPrice(ruleId: string, value: number) {
  for (const group of draftRuleGroups.value) {
    const rule = group.rules.find((item) => item.id === ruleId);
    if (!rule) {
      continue;
    }
    rule.filters = {
      ...(rule.filters || {}),
      min_price: Math.max(0, Math.round(Number(value || 0))),
    };
  }
}

function updateMaxPriceFilter(ruleId: string, value: number | null) {
  for (const group of draftRuleGroups.value) {
    const rule = group.rules.find((item) => item.id === ruleId);
    if (!rule) {
      continue;
    }
    rule.filters = {
      ...(rule.filters || {}),
      max_price: value == null ? null : Math.max(0, Math.round(Number(value || 0))),
    };
  }
}

function updateGuardWaveform(ruleId: string, guardLevel: string, field: string, value: string) {
  for (const group of draftRuleGroups.value) {
    const rule = group.rules.find((item) => item.id === ruleId);
    if (!rule) {
      continue;
    }
    const currentFilters = { ...(rule.filters || {}) };
    const currentGuardWfMap: Record<string, any> = { ...(currentFilters.guard_waveforms || {}) };
    const currentOverride = { ...(currentGuardWfMap[guardLevel] || {}) };

    if (value) {
      currentOverride[field] = value;
    } else {
      delete currentOverride[field];
    }

    if (Object.keys(currentOverride).length > 0) {
      currentGuardWfMap[guardLevel] = currentOverride;
    } else {
      delete currentGuardWfMap[guardLevel];
    }

    rule.filters = {
      ...currentFilters,
      guard_waveforms: currentGuardWfMap,
    };
  }
}

function setSharedEventEnabled(key: SharedConfigKey, enabled: boolean) {
  // 通用配置里只有弹幕存在独立开关，点赞始终参与公共触发链路。
  if (key === "danmaku") {
    sessionDraft.danmaku_enabled = enabled;
  }
}

function setImGroupEnabled(eventType: string, enabled: boolean) {
  // 右侧开关控制整组 IM 规则，便于一次性启停同类事件。
  draftRules.value = draftRules.value.map((rule) =>
    rule.event_type === eventType
      ? {
          ...rule,
          enabled,
        }
      : rule,
  );
}

function setBluetoothGroupEnabled(groupId: string, enabled: boolean) {
  // 蓝牙配置按事件组批量切换，保证一个事件下所有波形规则状态一致。
  draftRuleGroups.value = draftRuleGroups.value.map((group) =>
    group.group_id === groupId
      ? {
          ...group,
          rules: group.rules.map((rule) => ({
            ...rule,
            enabled,
          })),
        }
      : group,
  );
}

async function handlePrimarySave() {
  if (activeTab.value === "shared") {
    await handleSaveSharedConfig();
    return;
  }
  if (activeTab.value === "im") {
    await handleSaveImRules();
    return;
  }
  if (activeTab.value === "bluetooth") {
    await handleSaveBluetoothRules();
    return;
  }
  await handleSaveDouyinConfig();
}

async function handleSaveSharedConfig() {
  savingSharedConfig.value = true;
  try {
    sessionDraft.like_multiple = Math.max(1, Math.round(Number(sessionDraft.like_multiple || 1)));
    sessionDraft.danmaku_cooldown_seconds = normalizeNonNegative(sessionDraft.danmaku_cooldown_seconds);
    sessionDraft.danmaku_user_limit_window_seconds = normalizeNonNegative(sessionDraft.danmaku_user_limit_window_seconds);
    sessionDraft.danmaku_user_limit_max_triggers = normalizeNonNegative(sessionDraft.danmaku_user_limit_max_triggers);
    sessionDraft.danmaku_min_guard_level = Number(sessionDraft.danmaku_min_guard_level || 0);
    sessionDraftStorage.save({ ...sessionDraft });
    message.value = "通用事件配置已保存，主控台启动监听时会复用这份草稿";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "保存通用事件配置失败";
  } finally {
    savingSharedConfig.value = false;
  }
}

async function handleSaveDouyinConfig() {
  savingSharedConfig.value = true;
  try {
    sessionDraft.mode = "douyin";
    sessionDraft.douyin_ws_base_url = (sessionDraft.douyin_ws_base_url || "ws://127.0.0.1:1088").trim();
    sessionDraft.douyin_executable_path = String(sessionDraft.douyin_executable_path || "").trim();
    sessionDraft.douyin_cookie = String(sessionDraft.douyin_cookie || "").trim();
    sessionDraft.value = String(sessionDraft.value || "").trim();
    sessionDraftStorage.save({ ...sessionDraft });
    message.value = "抖音配置已保存，主控台启动监听时会使用这份配置";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "保存抖音配置失败";
  } finally {
    savingSharedConfig.value = false;
  }
}

async function handleSaveImRules() {
  savingCommandRules.value = true;
  try {
    await commandStore.saveStudio({
      rules: draftRules.value.map((rule) => ({
        ...rule,
        min_price: normalizeNonNegative(rule.min_price),
        max_price: rule.max_price == null ? null : normalizeNonNegative(rule.max_price),
      })),
      like_rules: [],
      danmaku_slot_rules: [],
    });
    message.value = "IM 规则已保存";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "保存 IM 规则失败";
  } finally {
    savingCommandRules.value = false;
  }
}

async function handleSaveBluetoothRules() {
  savingBluetoothRules.value = true;
  try {
    const rulesPayload = draftRuleGroups.value.flatMap((group) =>
      group.rules.map((rule: BluetoothStudioRule) => ({
        id: rule.id,
        enabled: rule.enabled,
        waveform_id: rule.waveform_id,
        toy_waveform_id: rule.toy_waveform_id || "",
        min_price: priceFilterGroupIds.has(group.group_id)
          ? Math.max(0, Math.round(Number(rule.filters?.min_price || 0)))
          : null,
        max_price: priceFilterGroupIds.has(group.group_id)
          ? (rule.filters?.max_price == null ? null : Math.max(0, Math.round(Number(rule.filters.max_price))))
          : null,
        guard_waveforms: group.group_id === "gift"
          ? (rule.filters?.guard_waveforms || null)
          : null,
      })),
    );
    const response = await bluetoothStore.saveRules({ rules: rulesPayload });
    message.value = `蓝牙规则已保存，共更新 ${response.updated_count} 项`;
  } catch (error) {
    message.value = error instanceof Error ? error.message : "保存蓝牙规则失败";
  } finally {
    savingBluetoothRules.value = false;
  }
}

onMounted(async () => {
  await Promise.all([commandStore.fetchStudio(), bluetoothStore.fetchStudio()]);
});
</script>

<style scoped>
.workspace-summary {
  display: grid;
  gap: 18px;
}

.workspace-summary-header {
  display: grid;
  gap: 8px;
}

.workspace-summary-header h1,
.editor-shell-header h2 {
  margin: 0;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.workspace-summary-header h1 {
  font-size: 28px;
}

.workspace-summary-header p,
.editor-shell-eyebrow {
  margin: 0;
  color: #78716c;
}

.workspace-overview {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.workspace-overview-metrics-only {
  justify-content: flex-end;
}

.hero-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 6px;
}

.hero-metric {
  min-width: 88px;
  padding: 10px 12px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(31, 16, 37, 0.92), rgba(14, 9, 18, 0.96));
  border: 1px solid var(--app-border);
  display: grid;
  gap: 2px;
}

.hero-metric strong {
  font-size: 18px;
  line-height: 1;
}

.hero-metric span {
  font-size: 12px;
  color: var(--app-muted);
}

.event-config-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: start;
}

.event-config-main {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.editor-shell-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.editor-shell-eyebrow {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
}

.event-config-sidebar {
  display: grid;
  gap: 16px;
  position: sticky;
  top: 0;
}

.event-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: var(--app-muted);
}

.event-list {
  display: grid;
  gap: 10px;
}

.event-list-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid var(--app-border);
  background: linear-gradient(180deg, rgba(31, 16, 37, 0.92), rgba(14, 9, 18, 0.96));
  box-shadow: var(--app-shadow);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.event-list-item:hover {
  transform: translateY(-1px);
  border-color: var(--app-border-strong);
}

.event-list-item-active {
  border-color: var(--app-border-strong);
  box-shadow: 0 14px 28px rgba(217, 138, 168, 0.16);
}

.event-list-item-copy {
  display: grid;
  gap: 4px;
}

.event-list-item-copy strong {
  color: var(--app-text);
}

.event-list-item-copy span {
  font-size: 12px;
  color: var(--app-muted);
}

.event-list-static-tag {
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(217, 138, 168, 0.14);
  color: var(--app-accent-soft);
  font-size: 12px;
  font-weight: 600;
}

.event-list-switch {
  display: inline-flex;
  align-items: center;
}

.event-config-page {
  max-width: none;
}

.douyin-config-panel :deep(.ant-card-body) {
  display: grid;
  gap: 18px;
}

.douyin-config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.douyin-field {
  display: grid;
  gap: 8px;
  color: #44403c;
  font-size: 13px;
  font-weight: 600;
}

.douyin-field :deep(.ant-input) {
  border-radius: 12px;
}

.douyin-field-full {
  grid-column: 1 / -1;
}

.douyin-event-map {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.douyin-event-map article {
  display: grid;
  gap: 4px;
  min-height: 76px;
  padding: 14px;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(31, 16, 37, 0.92), rgba(14, 9, 18, 0.96));
}

.douyin-event-map strong {
  color: var(--app-text);
}

.douyin-event-map span {
  color: var(--app-muted);
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 1100px) {
  .event-config-layout {
    grid-template-columns: 1fr;
  }

  .event-config-sidebar {
    position: static;
  }
}

@media (max-width: 900px) {
  .workspace-overview {
    flex-direction: column;
  }

  .editor-shell-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .douyin-config-grid,
  .douyin-event-map {
    grid-template-columns: 1fr;
  }
}
</style>
