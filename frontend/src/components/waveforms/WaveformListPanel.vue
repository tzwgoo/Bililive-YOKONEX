<template>
  <ACard :bordered="false" class="waveform-library-panel" :style="DESKTOP_PANEL_STYLE">
    <template #extra>
      <span class="section-count">{{ waveforms.length }} 个</span>
    </template>
    <div
      data-testid="waveform-library-scroll"
      class="waveform-library"
      :style="SCROLL_CONTAINER_STYLE"
    >
      <div
        v-for="waveform in waveforms"
        :key="waveform.id"
        :data-testid="`waveform-card-${waveform.id}`"
        class="waveform-card"
        :class="{ 'is-active': waveform.id === selectedWaveformId }"
        role="button"
        tabindex="0"
        :aria-pressed="waveform.id === selectedWaveformId ? 'true' : 'false'"
        @click="emit('select', waveform.id)"
        @keydown.enter.prevent="emit('select', waveform.id)"
        @keydown.space.prevent="emit('select', waveform.id)"
      >
        <span class="waveform-card-copy">
          <strong>{{ waveform.name }}</strong>
          <small>{{ waveform.builtin ? "内置" : "自定义" }} · {{ waveform.steps.length }} 步</small>
          <small v-if="isToy">{{ resolveMaxToyStrength(waveform as ToyWaveform) }}</small>
          <small v-else>最大强度 {{ resolveMaxEmsStrength(waveform as BluetoothWaveform) }}</small>
        </span>
        <span :data-testid="`waveform-preview-${waveform.id}`" class="waveform-card-preview">
          <span
            v-for="(step, index) in waveform.steps"
            :key="`${waveform.id}-preview-${index}`"
            class="waveform-preview-step"
            :style="{ flexGrow: normalizeDuration(step.duration_ms) }"
          >
            <span class="waveform-preview-bars" :style="{ height: `${PREVIEW_HEIGHT_PX}px` }">
              <template v-if="isToy">
                <span class="waveform-preview-bar is-a" :style="{ height: `${resolveToyPreviewBarHeight(waveform as ToyWaveform, (step as ToyWaveformStep).motor_a)}px` }"></span>
                <span class="waveform-preview-bar is-b" :style="{ height: `${resolveToyPreviewBarHeight(waveform as ToyWaveform, (step as ToyWaveformStep).motor_b)}px` }"></span>
                <span class="waveform-preview-bar is-c" :style="{ height: `${resolveToyPreviewBarHeight(waveform as ToyWaveform, (step as ToyWaveformStep).motor_c)}px` }"></span>
              </template>
              <template v-else>
                <span class="waveform-preview-bar is-a" :style="{ height: `${resolveEmsPreviewBarHeight(waveform as BluetoothWaveform, (step as BluetoothWaveformStep).channel_a)}px` }"></span>
                <span class="waveform-preview-bar is-b" :style="{ height: `${resolveEmsPreviewBarHeight(waveform as BluetoothWaveform, (step as BluetoothWaveformStep).channel_b)}px` }"></span>
              </template>
            </span>
          </span>
        </span>
      </div>
    </div>
  </ACard>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Card as ACard } from "ant-design-vue";
import type { BluetoothWaveform, BluetoothWaveformStep, ToyWaveform, ToyWaveformStep } from "@/types/bluetooth";

const props = defineProps<{
  waveforms: (BluetoothWaveform | ToyWaveform)[];
  selectedWaveformId: string;
  deviceType: "ems" | "toy";
}>();

const emit = defineEmits<{
  select: [waveformId: string];
}>();

const isToy = computed(() => props.deviceType === "toy");

const PREVIEW_HEIGHT_PX = 64;
const EMS_PREVIEW_MAX_STRENGTH = 180;
const DESKTOP_PANEL_STYLE = {
  height: "clamp(560px, calc(100vh - 220px), 820px)",
};
const SCROLL_CONTAINER_STYLE = {
  overflowY: "auto",
};

function normalizeStrength(value: number) {
  return Math.max(0, Math.min(180, Math.round(Number(value || 0))));
}

function normalizeToySpeed(value: number) {
  return Math.max(0, Math.min(20, Math.round(Number(value || 0))));
}

function normalizeDuration(value: number) {
  return Math.max(1, Math.round(Number(value || 0)));
}

function resolveMaxEmsStrength(waveform: BluetoothWaveform) {
  return waveform.steps.reduce(
    (maxValue, step) => Math.max(maxValue, normalizeStrength(step.channel_a), normalizeStrength(step.channel_b)),
    0,
  );
}

function resolveMaxToyStrength(waveform: ToyWaveform) {
  const maxSpeed = waveform.steps.reduce(
    (maxValue, step) => Math.max(maxValue, normalizeToySpeed(step.motor_a), normalizeToySpeed(step.motor_b), normalizeToySpeed(step.motor_c)),
    0,
  );
  return `最大速度 ${maxSpeed}`;
}

function resolveEmsPreviewBarHeight(waveform: BluetoothWaveform, value: number) {
  // Keep EMS preview cards scaled against the real 180 ceiling.
  return Math.round((normalizeStrength(value) / EMS_PREVIEW_MAX_STRENGTH) * PREVIEW_HEIGHT_PX);
  // EMS 列表预览固定按设备真实 180 上限缩放，避免低强度波形被拉满后产生误导。
  return Math.round((normalizeStrength(value) / EMS_PREVIEW_MAX_STRENGTH) * PREVIEW_HEIGHT_PX);
}

function resolveToyPreviewBarHeight(waveform: ToyWaveform, value: number) {
  const maxSpeed = Math.max(1, waveform.steps.reduce(
    (maxValue, step) => Math.max(maxValue, normalizeToySpeed(step.motor_a), normalizeToySpeed(step.motor_b), normalizeToySpeed(step.motor_c)),
    0,
  ));
  return Math.round((normalizeToySpeed(value) / maxSpeed) * PREVIEW_HEIGHT_PX);
}
</script>

<style scoped>
.waveform-library-panel {
  display: flex;
  flex-direction: column;
}

.waveform-library-panel :deep(.ant-card-body) {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  padding-top: 0;
}

.waveform-library {
  display: grid;
  flex: 1 1 auto;
  gap: 12px;
  min-height: 0;
  overflow-y: auto;
  align-content: start;
  padding-top: 12px;
  padding-right: 6px;
}

.waveform-card {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
  height: auto;
  padding: 0;
  border: 1px solid var(--app-border);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(31, 16, 37, 0.92), rgba(14, 9, 18, 0.96));
  box-shadow: var(--app-shadow);
  cursor: pointer;
  appearance: none;
  text-align: left;
}

.waveform-card.is-active {
  border-color: var(--app-border-strong) !important;
  box-shadow: 0 0 0 1px var(--app-border-strong) inset, var(--app-shadow);
}

.waveform-card-copy {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 14px 16px;
  text-align: left;
}

.waveform-card-preview {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  min-height: 86px;
  margin: 0 16px 16px;
  padding: 12px 14px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.03));
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.waveform-preview-step {
  display: flex;
  min-width: 0;
  flex-basis: 0;
  align-items: flex-end;
}

.waveform-preview-bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  width: 100%;
  height: 64px;
  min-height: 64px;
}

.waveform-preview-bar {
  flex: 1 1 0;
  border-radius: 999px;
  min-height: 6px;
  box-shadow: 0 2px 8px rgba(28, 25, 23, 0.10);
}

.waveform-preview-bar.is-a {
  background: linear-gradient(180deg, #fdba74 0%, #fb923c 35%, #ea580c 80%, #c2410c 100%);
}

.waveform-preview-bar.is-b {
  background: linear-gradient(180deg, #93c5fd 0%, #60a5fa 35%, #2563eb 80%, #1d4ed8 100%);
}

.waveform-preview-bar.is-c {
  background: linear-gradient(180deg, #c4b5fd 0%, #a78bfa 35%, #7c3aed 80%, #6d28d9 100%);
}

.waveform-card-copy small,
.section-count {
  color: var(--app-muted);
  font-size: 12px;
}

.waveform-card-copy strong {
  color: var(--app-text);
}

.section-count {
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  min-height: 28px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

@media (max-width: 1279px) {
  .waveform-library-panel {
    height: auto !important;
  }

  .waveform-library-panel :deep(.ant-card-body) {
    padding-top: 0;
  }

  .waveform-library {
    overflow-y: visible;
    padding-right: 0;
  }
}
</style>
