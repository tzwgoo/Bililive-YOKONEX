<template>
  <main class="studio-page waveform-library-page">
    <ACard :bordered="false" data-testid="workspace-summary-card">
      <div class="workspace-summary">
        <div class="workspace-summary-header">
          <h1>波形库</h1>
          <div class="workspace-summary-actions">
            <StatusPill :state="bluetoothStore.status.connected ? 'connected' : 'idle'" />
            <Button @click="handleCreateWaveform">新建空白波形</Button>
          </div>
        </div>
        <div class="workspace-overview workspace-overview-metrics-only">
          <div class="hero-metrics">
            <article class="hero-metric">
              <strong>{{ currentWaveforms.length }}</strong>
              <span>{{ activeTab === "ems" ? "EMS 波形" : "Toy 波形" }}</span>
            </article>
            <article class="hero-metric">
              <strong>{{ editableWaveformCount }}</strong>
              <span>可编辑</span>
            </article>
            <article class="hero-metric">
              <strong>{{ selectedWaveform?.steps.length || 0 }}</strong>
              <span>当前步数</span>
            </article>
          </div>
        </div>
      </div>
    </ACard>

    <AAlert v-if="message" :message="message" type="info" show-icon />

    <div class="waveform-tab-bar">
      <button
        class="waveform-tab"
        :class="{ 'is-active': activeTab === 'ems' }"
        @click="switchTab('ems')"
      >EMS 波形</button>
      <button
        class="waveform-tab"
        :class="{ 'is-active': activeTab === 'toy' }"
        @click="switchTab('toy')"
      >Toy 波形</button>
    </div>

    <ARow :gutter="[18, 18]">
      <ACol :xs="24" :xl="8">
        <WaveformListPanel
          :waveforms="currentWaveforms"
          :selected-waveform-id="selectedWaveformId"
          :device-type="activeTab"
          @select="handleSelectWaveform"
        />
      </ACol>

      <ACol :xs="24" :xl="16">
        <WaveformEditorPanel
          :waveform="selectedWaveform"
          :saving-waveform="savingWaveform"
          :previewing="previewingWaveform"
          :connected="bluetoothStore.status.connected"
          :device-type="activeTab"
          @save-waveform="handleSaveWaveform"
          @duplicate-waveform="handleDuplicateWaveform"
          @delete-waveform="handleDeleteWaveform"
          @preview-waveform="handlePreviewWaveform"
          @update-waveform-name="updateWaveformName"
          @update-step="updateStep"
          @add-step="addStep"
          @duplicate-step="duplicateStep"
          @remove-step="removeStep"
        />
      </ACol>
    </ARow>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { Alert as AAlert, Button, Card as ACard, Col as ACol, Row as ARow } from "ant-design-vue";
import StatusPill from "@/components/shared/StatusPill.vue";
import WaveformEditorPanel from "@/components/waveforms/WaveformEditorPanel.vue";
import WaveformListPanel from "@/components/waveforms/WaveformListPanel.vue";
import { useBluetoothStore } from "@/stores/bluetooth";
import type { BluetoothWaveform, BluetoothWaveformStep, ToyWaveform, ToyWaveformStep } from "@/types/bluetooth";

const bluetoothStore = useBluetoothStore();

const message = ref('修改完成后点击"保存波形"。');
const savingWaveform = ref(false);
const previewingWaveform = ref(false);
const selectedWaveformId = ref("");
const activeTab = ref<"ems" | "toy">("ems");

const draftEmsWaveforms = ref<BluetoothWaveform[]>([]);
const draftToyWaveforms = ref<ToyWaveform[]>([]);
const savedEmsSnapshots = ref<Record<string, string>>({});
const savedToySnapshots = ref<Record<string, string>>({});

const currentWaveforms = computed(() =>
  activeTab.value === "toy" ? draftToyWaveforms.value : draftEmsWaveforms.value,
);

const selectedWaveform = computed(() =>
  currentWaveforms.value.find((waveform) => waveform.id === selectedWaveformId.value) || null,
);
const editableWaveformCount = computed(() => currentWaveforms.value.filter((waveform) => !waveform.builtin).length);

watch(
  () => bluetoothStore.studio,
  (studio) => {
    if (!studio) {
      draftEmsWaveforms.value = [];
      draftToyWaveforms.value = [];
      selectedWaveformId.value = "";
      savedEmsSnapshots.value = {};
      savedToySnapshots.value = {};
      return;
    }
    // 测试桩和旧数据可能不会返回完整波形数组，这里统一兜底，避免页面因为 `undefined.map` 直接中断渲染。
    const emsWaveforms = studio.ems_waveforms || studio.waveforms || [];
    const toyWaveforms = studio.toy_waveforms || [];

    draftEmsWaveforms.value = emsWaveforms.map((waveform) => ({
      ...waveform,
      steps: waveform.steps.map((step) => ({ ...step })),
    }));
    savedEmsSnapshots.value = Object.fromEntries(
      emsWaveforms.map((waveform) => [waveform.id, serializeWaveform(waveform)]),
    );
    draftToyWaveforms.value = toyWaveforms.map((waveform) => ({
      ...waveform,
      steps: waveform.steps.map((step) => ({ ...step })),
    }));
    savedToySnapshots.value = Object.fromEntries(
      toyWaveforms.map((waveform) => [waveform.id, serializeToyWaveform(waveform)]),
    );
    if (!selectedWaveformId.value || !currentWaveforms.value.some((item) => item.id === selectedWaveformId.value)) {
      selectedWaveformId.value = currentWaveforms.value[0]?.id || "";
    }
  },
  { immediate: true, deep: true },
);

function switchTab(tab: "ems" | "toy") {
  if (activeTab.value === tab) return;
  if (selectedWaveformId.value && isWaveformDirty(selectedWaveformId.value)) {
    const shouldDiscard = window.confirm("当前波形还有未保存更改，是否放弃修改并切换？");
    if (!shouldDiscard) return;
    restoreWaveformDraft(selectedWaveformId.value);
  }
  activeTab.value = tab;
  selectedWaveformId.value = currentWaveforms.value[0]?.id || "";
}

function normalizeDuration(value: number) {
  return Math.max(1, Math.round(Number(value || 0)));
}

function normalizeStrength(value: number) {
  return Math.max(0, Math.min(180, Math.round(Number(value || 0))));
}

function normalizeToySpeed(value: number) {
  return Math.max(0, Math.min(20, Math.round(Number(value || 0))));
}

function cloneWaveform(waveform: BluetoothWaveform): BluetoothWaveform {
  return {
    ...waveform,
    steps: waveform.steps.map((step) => ({ ...step })),
  };
}

function cloneToyWaveform(waveform: ToyWaveform): ToyWaveform {
  return {
    ...waveform,
    steps: waveform.steps.map((step) => ({ ...step })),
  };
}

function serializeWaveform(waveform: BluetoothWaveform) {
  return JSON.stringify({
    id: waveform.id,
    name: waveform.name,
    builtin: Boolean(waveform.builtin),
    editable: Boolean(waveform.editable),
    execution_mode: waveform.execution_mode || "fixed",
    loop_count: Number(waveform.loop_count || 1),
    steps: waveform.steps.map((step) => ({
      duration_ms: normalizeDuration(step.duration_ms),
      channel_a: normalizeStrength(step.channel_a),
      channel_b: normalizeStrength(step.channel_b),
    })),
  });
}

function serializeToyWaveform(waveform: ToyWaveform) {
  return JSON.stringify({
    id: waveform.id,
    name: waveform.name,
    builtin: Boolean(waveform.builtin),
    editable: Boolean(waveform.editable),
    loop_count: Number(waveform.loop_count || 1),
    steps: waveform.steps.map((step) => ({
      duration_ms: normalizeDuration(step.duration_ms),
      motor_a: normalizeToySpeed(step.motor_a),
      motor_b: normalizeToySpeed(step.motor_b),
      motor_c: normalizeToySpeed(step.motor_c),
    })),
  });
}

function restoreWaveformDraft(waveformId: string) {
  if (activeTab.value === "toy") {
    const saved = bluetoothStore.studio?.toy_waveforms.find((w) => w.id === waveformId);
    if (!saved) return;
    const idx = draftToyWaveforms.value.findIndex((w) => w.id === waveformId);
    if (idx === -1) return;
    draftToyWaveforms.value.splice(idx, 1, cloneToyWaveform(saved));
  } else {
    const saved = bluetoothStore.studio?.ems_waveforms.find((w) => w.id === waveformId);
    if (!saved) return;
    const idx = draftEmsWaveforms.value.findIndex((w) => w.id === waveformId);
    if (idx === -1) return;
    draftEmsWaveforms.value.splice(idx, 1, cloneWaveform(saved));
  }
}

function isWaveformDirty(waveformId: string) {
  const isToy = activeTab.value === "toy";
  const draft = isToy
    ? draftToyWaveforms.value.find((w) => w.id === waveformId)
    : draftEmsWaveforms.value.find((w) => w.id === waveformId);
  if (!draft || draft.builtin) return false;
  const snapshot = isToy ? savedToySnapshots.value[waveformId] : savedEmsSnapshots.value[waveformId];
  const serialized = isToy ? serializeToyWaveform(draft as ToyWaveform) : serializeWaveform(draft as BluetoothWaveform);
  return serialized !== snapshot;
}

function updateWaveformName(name: string) {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) return;
  selectedWaveform.value.name = name;
}

function updateStep(index: number, field: keyof BluetoothWaveformStep | keyof ToyWaveformStep, value: number) {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) return;
  const step = selectedWaveform.value.steps[index];
  if (!step) return;
  if (field === "duration_ms") {
    step.duration_ms = normalizeDuration(value);
    return;
  }
  if (activeTab.value === "toy") {
    (step as ToyWaveformStep)[field as keyof ToyWaveformStep] = normalizeToySpeed(value);
  } else {
    (step as BluetoothWaveformStep)[field as keyof BluetoothWaveformStep] = normalizeStrength(value);
  }
}

function addStep() {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) return;
  if (activeTab.value === "toy") {
    (selectedWaveform.value as ToyWaveform).steps.push({ duration_ms: 200, motor_a: 0, motor_b: 0, motor_c: 0 });
  } else {
    (selectedWaveform.value as BluetoothWaveform).steps.push({ duration_ms: 200, channel_a: 0, channel_b: 0 });
  }
}

function duplicateStep(index: number) {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) return;
  const step = selectedWaveform.value.steps[index];
  if (!step) return;
  selectedWaveform.value.steps.splice(index + 1, 0, { ...step });
}

function removeStep(index: number) {
  if (!selectedWaveform.value || selectedWaveform.value.builtin || selectedWaveform.value.steps.length === 1) return;
  selectedWaveform.value.steps.splice(index, 1);
}

function handleSelectWaveform(nextWaveformId: string) {
  if (!nextWaveformId || nextWaveformId === selectedWaveformId.value) return;
  if (selectedWaveformId.value && isWaveformDirty(selectedWaveformId.value)) {
    const shouldDiscard = window.confirm("当前波形还有未保存更改，是否放弃修改并切换？");
    if (!shouldDiscard) return;
    restoreWaveformDraft(selectedWaveformId.value);
    message.value = "已放弃当前波形的未保存修改";
  }
  selectedWaveformId.value = nextWaveformId;
}

async function handleCreateWaveform() {
  try {
    const deviceType = activeTab.value;
    const response = await bluetoothStore.createWaveform("自定义波形", deviceType);
    selectedWaveformId.value = response.waveform.id;
    message.value = `已新建空白${deviceType === "toy" ? " Toy" : ""}波形`;
  } catch (error) {
    message.value = error instanceof Error ? error.message : "新建波形失败";
  }
}

async function handleDuplicateWaveform() {
  if (!selectedWaveform.value) return;
  try {
    const response = await bluetoothStore.duplicateWaveform(
      selectedWaveform.value.id,
      `${selectedWaveform.value.name} - 副本`,
    );
    selectedWaveformId.value = response.waveform.id;
    message.value = "已复制为自定义波形";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "复制波形失败";
  }
}

async function handleDeleteWaveform() {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) return;
  try {
    await bluetoothStore.deleteWaveform(selectedWaveform.value.id);
    selectedWaveformId.value = currentWaveforms.value[0]?.id || "";
    message.value = "波形已删除";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "删除波形失败";
  }
}

async function handlePreviewWaveform() {
  if (!selectedWaveform.value) return;
  previewingWaveform.value = true;
  try {
    const result = await bluetoothStore.previewWaveform(selectedWaveform.value.id);
    message.value = result.message || "试播已发送";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "试播失败";
  } finally {
    previewingWaveform.value = false;
  }
}

async function handleSaveWaveform() {
  if (!selectedWaveform.value || selectedWaveform.value.builtin) return;
  savingWaveform.value = true;
  try {
    if (activeTab.value === "toy") {
      const toyWf = selectedWaveform.value as ToyWaveform;
      await bluetoothStore.updateWaveform(toyWf.id, {
        name: toyWf.name.trim(),
        steps: toyWf.steps.map((step) => ({
          duration_ms: normalizeDuration(step.duration_ms),
          motor_a: normalizeToySpeed(step.motor_a),
          motor_b: normalizeToySpeed(step.motor_b),
          motor_c: normalizeToySpeed(step.motor_c),
        })),
      });
    } else {
      const emsWf = selectedWaveform.value as BluetoothWaveform;
      await bluetoothStore.updateWaveform(emsWf.id, {
        name: emsWf.name.trim(),
        steps: emsWf.steps.map((step) => ({
          duration_ms: normalizeDuration(step.duration_ms),
          channel_a: normalizeStrength(step.channel_a),
          channel_b: normalizeStrength(step.channel_b),
        })),
      });
    }
    message.value = "波形已保存";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "保存波形失败";
  } finally {
    savingWaveform.value = false;
  }
}

onMounted(async () => {
  await Promise.all([bluetoothStore.fetchStatus(), bluetoothStore.fetchStudio()]);
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

.waveform-tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 2px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 4px;
}

.waveform-tab {
  padding: 10px 24px;
  border: 0;
  background: transparent;
  font-size: 14px;
  font-weight: 600;
  color: var(--app-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.18s ease, border-color 0.18s ease;
}

.waveform-tab:hover {
  color: var(--app-text);
}

.waveform-tab.is-active {
  color: var(--app-accent-soft);
  border-bottom-color: var(--app-accent);
}

.waveform-library-page {
  max-width: none;
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
