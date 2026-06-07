<template>
  <main class="studio-page">
    <ACard :bordered="false" data-testid="workspace-summary-card">
      <div class="workspace-summary">
        <div class="workspace-summary-header">
          <h1>事件配置</h1>
          <div class="workspace-summary-actions">
            <Button
              v-if="activeTab === 'im'"
              data-testid="command-save"
              type="primary"
              :loading="savingCommandRules"
              @click="handleSaveImRules"
            >
              保存 IM 规则
            </Button>
            <Button
              v-else
              data-testid="save-rules"
              type="primary"
              :loading="savingBluetoothRules"
              @click="handleSaveBluetoothRules"
            >
              保存蓝牙规则
            </Button>
          </div>
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

    <EventConfigTabs v-model:active-tab="activeTab" :tabs="tabs" />

    <ImRuleGroupsPanel
      v-if="activeTab === 'im'"
      :groups="groupedRules"
      :command-slot-options="commandSlotOptions"
      :studio="commandStore.studio"
      @add-rule="addRule"
      @sort-rules="sortRules"
      @remove-rule="removeRule"
      @update-max-price="updateMaxPrice"
    />

    <BluetoothEventRulePanel
      v-else
      :rule-groups="draftRuleGroups"
      :ems-waveform-options="emsWaveformOptions"
      :toy-waveform-options="toyWaveformOptions"
      @update-min-price="updateMinPrice"
      @update-max-price="updateMaxPriceFilter"
      @update-guard-waveform="updateGuardWaveform"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { Alert as AAlert, Button, Card as ACard } from "ant-design-vue";
import BluetoothEventRulePanel from "@/components/events/BluetoothEventRulePanel.vue";
import EventConfigTabs from "@/components/events/EventConfigTabs.vue";
import ImRuleGroupsPanel from "@/components/events/ImRuleGroupsPanel.vue";
import { useLocalDraft } from "@/composables/useLocalDraft";
import { useBluetoothStore } from "@/stores/bluetooth";
import { useCommandStore } from "@/stores/command";
import type { BluetoothRuleGroup, BluetoothStudioRule, CommandStudioRule } from "@/types";

const props = withDefaults(
  defineProps<{
    initialTab?: "im" | "bluetooth";
  }>(),
  {
    initialTab: "im",
  },
);

const commandStore = useCommandStore();
const bluetoothStore = useBluetoothStore();
const activeTabStorage = useLocalDraft<"im" | "bluetooth">("biliLive.eventConfigTab", props.initialTab);

const activeTab = ref<"im" | "bluetooth">(activeTabStorage.load());
const message = ref("规则修改后可分别保存到 IM 和蓝牙配置。");
const savingCommandRules = ref(false);
const savingBluetoothRules = ref(false);
const draftRules = ref<CommandStudioRule[]>([]);
const draftRuleGroups = ref<BluetoothRuleGroup[]>([]);

const tabs = [
  { key: "im", label: "IM" },
  { key: "bluetooth", label: "蓝牙" },
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
  (bluetoothStore.studio?.ems_waveforms.length || 0) + (bluetoothStore.studio?.toy_waveforms.length || 0),
);
const priceFilterGroupIds = new Set(["gift", "super_chat", "guard_buy", "guard_renew"]);

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
    draftRuleGroups.value = studio.rule_groups.map((group) => ({
      ...group,
      rules: group.rules.map((rule) => ({
        ...rule,
        filters: { ...(rule.filters || {}) },
      })),
    }));
  },
  { immediate: true, deep: true },
);

function normalizeNonNegative(value: number) {
  return Math.max(0, Math.round(Number(value || 0)));
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
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.workspace-summary-header h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.workspace-summary-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
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
  margin-top: 14px;
}

.hero-metric {
  min-width: 88px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(120, 113, 108, 0.12);
  display: grid;
  gap: 2px;
}

.hero-metric strong {
  font-size: 18px;
  line-height: 1;
}

.hero-metric span {
  font-size: 12px;
  color: #78716c;
}

@media (max-width: 900px) {
  .workspace-summary-header {
    flex-direction: column;
  }

  .workspace-summary-actions {
    justify-content: flex-start;
  }

  .workspace-overview {
    flex-direction: column;
  }
}
</style>
