<template>
  <main class="studio-page">
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
              <strong>{{ draftWaveforms.length }}</strong>
              <span>波形总数</span>
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

    <ARow :gutter="[18, 18]">
      <ACol :xs="24" :xl="8">
        <WaveformListPanel
          :waveforms="draftWaveforms"
          :selected-waveform-id="selectedWaveformId"
          @select="handleSelectWaveform"
        />
      </ACol>

      <ACol :xs="24" :xl="16">
        <WaveformEditorPanel
          :waveform="selectedWaveform"
          :saving-waveform="savingWaveform"
          @save-waveform="handleSaveWaveform"
          @duplicate-waveform="handleDuplicateWaveform"
          @delete-waveform="handleDeleteWaveform"
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
import type { BluetoothWaveform, BluetoothWaveformStep } from "@/types/bluetooth";

const bluetoothStore = useBluetoothStore();

const message = ref("修改完成后点击“保存波形”。");
const savingWaveform = ref(false);
const selectedWaveformId = ref("");
const draftWaveforms = ref<BluetoothWaveform[]>([]);
const savedWaveformSnapshots = ref<Record<string, string>>({});

const selectedWaveform = computed(() =>
  draftWaveforms.value.find((waveform) => waveform.id === selectedWaveformId.value) || null,
);
const editableWaveformCount = computed(() => draftWaveforms.value.filter((waveform) => !waveform.builtin).length);

watch(
  () => bluetoothStore.studio,
  (studio) => {
    if (!studio) {
      draftWaveforms.value = [];
      selectedWaveformId.value = "";
      savedWaveformSnapshots.value = {};
      return;
    }
    draftWaveforms.value = studio.waveforms.map((waveform) => ({
      ...waveform,
      steps: waveform.steps.map((step) => ({ ...step })),
    }));
    savedWaveformSnapshots.value = Object.fromEntries(
      studio.waveforms.map((waveform) => [waveform.id, serializeWaveform(waveform)]),
    );
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

function cloneWaveform(waveform: BluetoothWaveform): BluetoothWaveform {
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

function restoreWaveformDraft(waveformId: string) {
  const savedWaveform = bluetoothStore.studio?.waveforms.find((waveform) => waveform.id === waveformId);
  if (!savedWaveform) {
    return;
  }
  const draftIndex = draftWaveforms.value.findIndex((waveform) => waveform.id === waveformId);
  if (draftIndex === -1) {
    return;
  }
  draftWaveforms.value.splice(draftIndex, 1, cloneWaveform(savedWaveform));
}

function isWaveformDirty(waveformId: string) {
  const draftWaveform = draftWaveforms.value.find((waveform) => waveform.id === waveformId);
  if (!draftWaveform || draftWaveform.builtin) {
    return false;
  }
  return serializeWaveform(draftWaveform) !== savedWaveformSnapshots.value[waveformId];
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

function handleSelectWaveform(nextWaveformId: string) {
  if (!nextWaveformId || nextWaveformId === selectedWaveformId.value) {
    return;
  }
  if (selectedWaveformId.value && isWaveformDirty(selectedWaveformId.value)) {
    const shouldDiscard = window.confirm("当前波形还有未保存更改，是否放弃修改并切换？");
    if (!shouldDiscard) {
      return;
    }
    restoreWaveformDraft(selectedWaveformId.value);
    message.value = "已放弃当前波形的未保存修改";
  }
  selectedWaveformId.value = nextWaveformId;
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
