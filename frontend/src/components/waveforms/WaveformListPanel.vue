<template>
  <ACard title="波形库" :bordered="false">
    <template #extra>
      <span class="section-count">{{ waveforms.length }} 个</span>
    </template>
    <div class="waveform-library">
      <Button
        v-for="waveform in waveforms"
        :key="waveform.id"
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

function resolveMaxStrength(waveform: BluetoothWaveform) {
  return waveform.steps.reduce(
    (maxValue, step) => Math.max(maxValue, normalizeStrength(step.channel_a), normalizeStrength(step.channel_b)),
    0,
  );
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
