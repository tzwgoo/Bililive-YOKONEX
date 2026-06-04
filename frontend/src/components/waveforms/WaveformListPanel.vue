<template>
  <ACard title="波形库" :bordered="false">
    <template #extra>
      <span class="section-count">{{ waveforms.length }} 个</span>
    </template>
    <div class="waveform-library">
      <Button
        v-for="waveform in waveforms"
        :key="waveform.id"
        :data-testid="`waveform-card-${waveform.id}`"
        block
        class="waveform-card"
        :class="{ 'is-active': waveform.id === selectedWaveformId }"
        @click="emit('select', waveform.id)"
      >
        <span class="waveform-card-copy">
          <strong>{{ waveform.name }}</strong>
          <small>{{ waveform.builtin ? "内置" : "自定义" }} · {{ waveform.steps.length }} 步</small>
          <small>最大强度 {{ resolveMaxStrength(waveform) }}</small>
        </span>
        <span :data-testid="`waveform-preview-${waveform.id}`" class="waveform-card-preview">
          <span
            v-for="(step, index) in waveform.steps"
            :key="`${waveform.id}-preview-${index}`"
            class="waveform-preview-step"
            :style="{ flexGrow: normalizeDuration(step.duration_ms) }"
          >
            <span class="waveform-preview-bars">
              <span class="waveform-preview-bar is-a" :style="{ height: `${resolveHeightRatio(step.channel_a)}%` }"></span>
              <span class="waveform-preview-bar is-b" :style="{ height: `${resolveHeightRatio(step.channel_b)}%` }"></span>
            </span>
          </span>
        </span>
      </Button>
    </div>
  </ACard>
</template>

<script setup lang="ts">
import { Button, Card as ACard } from "ant-design-vue";
import type { BluetoothWaveform } from "@/types/bluetooth";

defineProps<{
  waveforms: BluetoothWaveform[];
  selectedWaveformId: string;
}>();

const emit = defineEmits<{
  select: [waveformId: string];
}>();

function normalizeStrength(value: number) {
  return Math.max(0, Math.min(180, Math.round(Number(value || 0))));
}

function normalizeDuration(value: number) {
  return Math.max(1, Math.round(Number(value || 0)));
}

function resolveMaxStrength(waveform: BluetoothWaveform) {
  return waveform.steps.reduce(
    (maxValue, step) => Math.max(maxValue, normalizeStrength(step.channel_a), normalizeStrength(step.channel_b)),
    0,
  );
}

function resolveHeightRatio(value: number) {
  return (normalizeStrength(value) / 180) * 100;
}
</script>

<style scoped>
.waveform-library {
  display: grid;
  gap: 12px;
}

.waveform-card {
  height: auto;
  padding: 0;
  border-radius: 18px;
  overflow: hidden;
}

.waveform-card.is-active {
  border-color: #1c1917 !important;
  box-shadow: 0 0 0 1px #1c1917 inset, 0 10px 24px rgba(28, 25, 23, 0.08);
}

.waveform-card-copy {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 14px 16px;
  text-align: left;
}

.waveform-card :deep(.ant-btn-icon) {
  display: none;
}

.waveform-card-preview {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  min-height: 72px;
  margin: 0 16px 16px;
  padding: 10px 12px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(250, 248, 244, 0.96), rgba(241, 236, 229, 0.98));
  border: 1px solid rgba(120, 113, 108, 0.1);
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
  min-height: 52px;
}

.waveform-preview-bar {
  flex: 1 1 0;
  min-height: 4px;
  border-radius: 999px;
}

.waveform-preview-bar.is-a {
  background: linear-gradient(180deg, #fb923c, #f97316);
}

.waveform-preview-bar.is-b {
  background: linear-gradient(180deg, #60a5fa, #2563eb);
}

.waveform-card-copy small,
.section-count {
  color: #78716c;
  font-size: 12px;
}

.section-count {
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  min-height: 28px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(120, 113, 108, 0.12);
}
</style>
