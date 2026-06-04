<template>
  <main class="studio-page">
    <ACard class="studio-hero" :bordered="false">
      <div>
        <p class="studio-kicker">Bluetooth Studio</p>
        <h1>蓝牙 Studio</h1>
        <p class="studio-subtitle">查看波形库、编辑自定义波形，并给礼物与互动规则绑定对应波形。</p>
      </div>
      <div class="studio-hero-actions">
        <StatusPill :state="bluetoothStore.status.connected ? 'connected' : 'idle'" />
        <Button data-testid="save-rules" type="primary" :loading="savingRules" @click="handleSaveRules">保存规则</Button>
      </div>
    </ACard>

    <AAlert v-if="message" :message="message" type="info" show-icon />

    <ARow :gutter="[18, 18]">
      <ACol :xs="24" :xl="8">
        <ACard title="波形库" :bordered="false">
          <template #extra>
            <Button size="small" @click="handleCreateWaveform">新建空白波形</Button>
          </template>
          <div class="waveform-library">
            <button
              v-for="waveform in draftWaveforms"
              :key="waveform.id"
              type="button"
              class="waveform-card"
              :class="{ 'is-active': waveform.id === selectedWaveformId }"
              @click="selectedWaveformId = waveform.id"
            >
              <strong>{{ waveform.name }}</strong>
              <small>{{ waveform.builtin ? "内置" : "自定义" }} · {{ waveform.steps.length }} 步</small>
              <small>最大强度 {{ resolveMaxStrength(waveform) }}</small>
            </button>
          </div>
        </ACard>
      </ACol>

      <ACol :xs="24" :xl="16">
        <div class="editor-stack">
          <ACard title="波形编辑器" :bordered="false">
            <template #extra>
              <div class="studio-card-actions">
                <Button size="small" @click="handleDuplicateWaveform">复制为自定义</Button>
                <Button size="small" :disabled="!selectedWaveform || selectedWaveform.builtin" @click="handleDeleteWaveform">删除当前波形</Button>
                <Button data-testid="save-waveform" size="small" type="primary" :loading="savingWaveform" @click="handleSaveWaveform">保存波形</Button>
              </div>
            </template>

            <AEmpty v-if="!selectedWaveform" description="暂无波形" />
            <template v-else>
              <div class="editor-meta">
                <label class="field">
                  <span>波形名称</span>
                  <input
                    data-testid="waveform-name"
                    :value="selectedWaveform.name"
                    :disabled="selectedWaveform.builtin"
                    @input="updateWaveformName(($event.target as HTMLInputElement).value)"
                  />
                </label>
                <div class="stats-grid">
                  <article>
                    <span>分段数</span>
                    <strong>{{ selectedWaveform.steps.length }}</strong>
                  </article>
                  <article>
                    <span>总时长</span>
                    <strong>{{ resolveTotalDuration(selectedWaveform) }} ms</strong>
                  </article>
                  <article>
                    <span>最大强度</span>
                    <strong>{{ resolveMaxStrength(selectedWaveform) }}</strong>
                  </article>
                </div>
              </div>

              <div class="waveform-preview">
                <div
                  v-for="(step, index) in selectedWaveform.steps"
                  :key="`${selectedWaveform.id}-preview-${index}`"
                  class="preview-segment"
                >
                  <span class="preview-bar is-a" :style="{ height: `${(step.channel_a / 180) * 100}%` }"></span>
                  <span class="preview-bar is-b" :style="{ height: `${(step.channel_b / 180) * 100}%` }"></span>
                  <small>{{ step.duration_ms }} ms</small>
                </div>
              </div>

              <div class="step-toolbar">
                <Button size="small" :disabled="selectedWaveform.builtin" @click="addStep">新增分段</Button>
              </div>

              <div class="step-list">
                <article v-for="(step, index) in selectedWaveform.steps" :key="`${selectedWaveform.id}-step-${index}`" class="step-row">
                  <strong>{{ index + 1 }}</strong>
                  <label class="field">
                    <span>时长</span>
                    <input
                      :data-testid="`step-duration-${index}`"
                      :value="step.duration_ms"
                      :disabled="selectedWaveform.builtin"
                      type="number"
                      min="1"
                      step="1"
                      @input="updateStep(index, 'duration_ms', Number(($event.target as HTMLInputElement).value))"
                    />
                  </label>
                  <label class="field">
                    <span>A 通道</span>
                    <input
                      :data-testid="`step-channel-a-${index}`"
                      :value="step.channel_a"
                      :disabled="selectedWaveform.builtin"
                      type="number"
                      min="0"
                      max="180"
                      step="1"
                      @input="updateStep(index, 'channel_a', Number(($event.target as HTMLInputElement).value))"
                    />
                  </label>
                  <label class="field">
                    <span>B 通道</span>
                    <input
                      :data-testid="`step-channel-b-${index}`"
                      :value="step.channel_b"
                      :disabled="selectedWaveform.builtin"
                      type="number"
                      min="0"
                      max="180"
                      step="1"
                      @input="updateStep(index, 'channel_b', Number(($event.target as HTMLInputElement).value))"
                    />
                  </label>
                  <div class="step-actions">
                    <Button size="small" :disabled="selectedWaveform.builtin" @click="duplicateStep(index)">复制</Button>
                    <Button size="small" danger :disabled="selectedWaveform.builtin || selectedWaveform.steps.length === 1" @click="removeStep(index)">删除</Button>
                  </div>
                </article>
              </div>
            </template>
          </ACard>

          <ACard title="事件规则" :bordered="false">
            <AEmpty v-if="draftRuleGroups.length === 0" description="暂无规则组" />
            <ACollapse v-else :bordered="false" :default-active-key="draftRuleGroups.map((group) => group.group_id)">
              <ACollapsePanel
                v-for="group in draftRuleGroups"
                :key="group.group_id"
                :header="group.group_label"
              >
                <div class="rule-list">
                  <article v-for="rule in group.rules" :key="rule.id" class="rule-item">
                    <div class="rule-head">
                      <strong>{{ rule.rule_label }}</strong>
                      <label class="toggle-line">
                        <input v-model="rule.enabled" type="checkbox" />
                        <span>启用</span>
                      </label>
                    </div>
                    <div class="rule-grid">
                      <label class="field field-span-2">
                        <span>绑定波形</span>
                        <select
                          :data-testid="`rule-waveform-${rule.id}`"
                          v-model="rule.waveform_id"
                        >
                          <option v-for="waveform in draftWaveforms" :key="waveform.id" :value="waveform.id">
                            {{ waveform.name }}
                          </option>
                        </select>
                      </label>
                      <template v-if="group.group_id === 'gift'">
                        <label class="field">
                          <span>最低价格</span>
                          <input
                            :value="Number(rule.filters?.min_price || 0)"
                            type="number"
                            min="0"
                            step="1"
                            @input="updateGiftFilter(rule.id, 'min_price', Number(($event.target as HTMLInputElement).value))"
                          />
                        </label>
                        <label class="field">
                          <span>最高价格</span>
                          <input
                            :value="rule.filters?.max_price ?? ''"
                            type="number"
                            min="0"
                            step="1"
                            placeholder="留空表示无上限"
                            @input="updateGiftMaxPrice(rule.id, ($event.target as HTMLInputElement).value)"
                          />
                        </label>
                      </template>
                    </div>
                  </article>
                </div>
              </ACollapsePanel>
            </ACollapse>
          </ACard>
        </div>
      </ACol>
    </ARow>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  Alert as AAlert,
  Button,
  Card as ACard,
  Col as ACol,
  Collapse as ACollapse,
  Empty as AEmpty,
  Row as ARow,
} from "ant-design-vue";
import StatusPill from "@/components/shared/StatusPill.vue";
import { useBluetoothStore } from "@/stores/bluetooth";
import type {
  BluetoothRuleGroup,
  BluetoothStudioRule,
  BluetoothWaveform,
  BluetoothWaveformStep,
} from "@/types/bluetooth";

const bluetoothStore = useBluetoothStore();
const ACollapsePanel = ACollapse.Panel;

const message = ref("修改完成后点击“保存规则”或“保存波形”。");
const savingWaveform = ref(false);
const savingRules = ref(false);
const selectedWaveformId = ref("");
const draftWaveforms = ref<BluetoothWaveform[]>([]);
const draftRuleGroups = ref<BluetoothRuleGroup[]>([]);

const selectedWaveform = computed(() =>
  draftWaveforms.value.find((waveform) => waveform.id === selectedWaveformId.value) || null,
);

watch(
  () => bluetoothStore.studio,
  (studio) => {
    if (!studio) {
      draftWaveforms.value = [];
      draftRuleGroups.value = [];
      selectedWaveformId.value = "";
      return;
    }
    draftWaveforms.value = studio.waveforms.map((waveform) => ({
      ...waveform,
      steps: waveform.steps.map((step) => ({ ...step })),
    }));
    draftRuleGroups.value = studio.rule_groups.map((group) => ({
      ...group,
      rules: group.rules.map((rule) => ({
        ...rule,
        filters: { ...(rule.filters || {}) },
      })),
    }));
    if (!selectedWaveformId.value || !draftWaveforms.value.some((item) => item.id === selectedWaveformId.value)) {
      selectedWaveformId.value = draftWaveforms.value[0]?.id || "";
    }
  },
  { immediate: true, deep: true },
);

function normalizeDuration(value: number) {
  return Math.max(1, Math.round(Number(value || 0)));
}

function normalizeStrength(value: number) {
  return Math.max(0, Math.min(180, Math.round(Number(value || 0))));
}

function resolveTotalDuration(waveform: BluetoothWaveform) {
  return waveform.steps.reduce((sum, step) => sum + normalizeDuration(step.duration_ms), 0);
}

function resolveMaxStrength(waveform: BluetoothWaveform) {
  return waveform.steps.reduce((maxValue, step) => Math.max(maxValue, normalizeStrength(step.channel_a), normalizeStrength(step.channel_b)), 0);
}

function updateWaveformName(name: string) {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) {
    return;
  }
  selectedWaveform.value.name = name;
}

function updateStep(index: number, field: keyof BluetoothWaveformStep, value: number) {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) {
    return;
  }
  const step = selectedWaveform.value.steps[index];
  if (!step) {
    return;
  }
  if (field === "duration_ms") {
    step.duration_ms = normalizeDuration(value);
    return;
  }
  step[field] = normalizeStrength(value);
}

function addStep() {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) {
    return;
  }
  selectedWaveform.value.steps.push({ duration_ms: 200, channel_a: 0, channel_b: 0 });
}

function duplicateStep(index: number) {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) {
    return;
  }
  const step = selectedWaveform.value.steps[index];
  if (!step) {
    return;
  }
  selectedWaveform.value.steps.splice(index + 1, 0, { ...step });
}

function removeStep(index: number) {
  if (!selectedWaveform.value || selectedWaveform.value.builtin || selectedWaveform.value.steps.length === 1) {
    return;
  }
  selectedWaveform.value.steps.splice(index, 1);
}

function updateGiftFilter(ruleId: string, field: "min_price", value: number) {
  for (const group of draftRuleGroups.value) {
    const rule = group.rules.find((item) => item.id === ruleId);
    if (!rule) {
      continue;
    }
    rule.filters = {
      ...(rule.filters || {}),
      [field]: Math.max(0, Math.round(Number(value || 0))),
    };
  }
}

function updateGiftMaxPrice(ruleId: string, rawValue: string) {
  for (const group of draftRuleGroups.value) {
    const rule = group.rules.find((item) => item.id === ruleId);
    if (!rule) {
      continue;
    }
    rule.filters = {
      ...(rule.filters || {}),
      max_price: rawValue === "" ? null : Math.max(0, Math.round(Number(rawValue || 0))),
    };
  }
}

async function handleCreateWaveform() {
  try {
    const response = await bluetoothStore.createWaveform("自定义波形");
    selectedWaveformId.value = response.waveform.id;
    message.value = "已新建空白波形";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "新建波形失败";
  }
}

async function handleDuplicateWaveform() {
  if (!selectedWaveform.value) {
    return;
  }
  try {
    const response = await bluetoothStore.duplicateWaveform(selectedWaveform.value.id, `${selectedWaveform.value.name} - 副本`);
    selectedWaveformId.value = response.waveform.id;
    message.value = "已复制为自定义波形";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "复制波形失败";
  }
}

async function handleDeleteWaveform() {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) {
    return;
  }
  try {
    await bluetoothStore.deleteWaveform(selectedWaveform.value.id);
    selectedWaveformId.value = draftWaveforms.value[0]?.id || "";
    message.value = "波形已删除";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "删除波形失败";
  }
}

async function handleSaveWaveform() {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) {
    return;
  }
  savingWaveform.value = true;
  try {
    await bluetoothStore.updateWaveform(selectedWaveform.value.id, {
      name: selectedWaveform.value.name.trim(),
      steps: selectedWaveform.value.steps.map((step) => ({
        duration_ms: normalizeDuration(step.duration_ms),
        channel_a: normalizeStrength(step.channel_a),
        channel_b: normalizeStrength(step.channel_b),
      })),
    });
    message.value = "波形已保存";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "保存波形失败";
  } finally {
    savingWaveform.value = false;
  }
}

async function handleSaveRules() {
  savingRules.value = true;
  try {
    const rulesPayload = draftRuleGroups.value.flatMap((group) =>
      group.rules.map((rule: BluetoothStudioRule) => ({
        id: rule.id,
        enabled: rule.enabled,
        waveform_id: rule.waveform_id,
        min_price: group.group_id === "gift" ? Math.max(0, Math.round(Number(rule.filters?.min_price || 0))) : null,
        max_price: group.group_id === "gift"
          ? (rule.filters?.max_price == null ? null : Math.max(0, Math.round(Number(rule.filters.max_price))))
          : null,
      })),
    );
    const response = await bluetoothStore.saveRules({ rules: rulesPayload });
    message.value = `事件规则已保存，共更新 ${response.updated_count} 项`;
  } catch (error) {
    message.value = error instanceof Error ? error.message : "保存规则失败";
  } finally {
    savingRules.value = false;
  }
}

onMounted(async () => {
  await Promise.all([bluetoothStore.fetchStatus(), bluetoothStore.fetchStudio()]);
});
</script>

<style scoped>
.studio-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 24px 40px;
  display: grid;
  gap: 18px;
}

.studio-hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.studio-kicker,
.studio-hero h1 {
  margin: 0;
}

.studio-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #78716c;
  margin-bottom: 8px;
}

.studio-subtitle {
  margin: 8px 0 0;
  color: #57534e;
}

.studio-hero-actions,
.studio-card-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.editor-stack,
.waveform-library,
.rule-list,
.step-list {
  display: grid;
  gap: 14px;
}

.waveform-card {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 14px 16px;
  text-align: left;
  border: 1px solid rgba(120, 113, 108, 0.18);
  border-radius: 16px;
  background: #fff;
  cursor: pointer;
}

.waveform-card.is-active {
  border-color: #1c1917;
  box-shadow: inset 0 0 0 1px #1c1917;
}

.waveform-card small {
  color: #78716c;
}

.editor-meta {
  display: grid;
  gap: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.stats-grid article,
.rule-item,
.step-row {
  padding: 14px 16px;
  border-radius: 16px;
  background: #f8f6f2;
}

.stats-grid article {
  display: grid;
  gap: 6px;
}

.waveform-preview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 12px;
}

.preview-segment {
  display: grid;
  align-items: end;
  gap: 8px;
  min-height: 160px;
  padding: 12px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(240,236,230,0.95));
}

.preview-bar {
  display: block;
  min-height: 4px;
  border-radius: 999px;
}

.preview-bar.is-a {
  background: #f97316;
}

.preview-bar.is-b {
  background: #2563eb;
}

.step-toolbar {
  display: flex;
  justify-content: flex-start;
}

.step-row,
.rule-head,
.step-actions {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.step-row {
  flex-wrap: wrap;
}

.field {
  display: grid;
  gap: 8px;
  flex: 1 1 140px;
  font-size: 13px;
  font-weight: 600;
}

.field input,
.field select {
  width: 100%;
  min-height: 40px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid #d6d3d1;
  background: #fff;
}

.rule-item {
  display: grid;
  gap: 14px;
  border: 1px solid rgba(120, 113, 108, 0.12);
}

.rule-head {
  justify-content: space-between;
}

.rule-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field-span-2 {
  grid-column: span 2;
}

.toggle-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

@media (max-width: 900px) {
  .studio-hero {
    flex-direction: column;
  }

  .stats-grid,
  .rule-grid {
    grid-template-columns: 1fr;
  }

  .field-span-2 {
    grid-column: span 1;
  }
}
</style>
