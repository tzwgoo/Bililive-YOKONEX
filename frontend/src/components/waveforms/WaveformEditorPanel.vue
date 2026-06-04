<template>
  <ACard title="波形编辑器" :bordered="false">
    <template #extra>
      <div class="studio-card-actions">
        <Button size="small" @click="emit('duplicate-waveform')">复制为自定义</Button>
        <Button size="small" :disabled="!waveform || waveform.builtin" @click="emit('delete-waveform')">删除当前波形</Button>
        <Button data-testid="save-waveform" size="small" type="primary" :loading="savingWaveform" @click="emit('save-waveform')">保存波形</Button>
      </div>
    </template>

    <AEmpty v-if="!waveform" description="暂无波形" />
    <template v-else>
      <div class="editor-meta">
        <label class="field">
          <span>波形名称</span>
          <div data-testid="waveform-name-input">
            <Input
              :value="waveform.name"
              :disabled="waveform.builtin"
              @update:value="emit('update-waveform-name', String($event ?? ''))"
            />
          </div>
        </label>
        <div class="stats-grid">
          <article>
            <span>分段数</span>
            <strong>{{ waveform.steps.length }}</strong>
          </article>
          <article>
            <span>总时长</span>
            <strong>{{ resolveTotalDuration(waveform) }} ms</strong>
          </article>
          <article>
            <span>最大强度</span>
            <strong>{{ resolveMaxStrength(waveform) }}</strong>
          </article>
        </div>
      </div>

      <div class="waveform-preview">
        <div
          v-for="(step, index) in waveform.steps"
          :key="`${waveform.id}-preview-${index}`"
          class="preview-segment"
        >
          <span class="preview-bar is-a" :style="{ height: `${(step.channel_a / 180) * 100}%` }"></span>
          <span class="preview-bar is-b" :style="{ height: `${(step.channel_b / 180) * 100}%` }"></span>
          <small>{{ step.duration_ms }} ms</small>
        </div>
      </div>

      <div class="step-toolbar">
        <Button size="small" :disabled="waveform.builtin" @click="emit('add-step')">新增分段</Button>
      </div>

      <div class="step-list">
        <article v-for="(step, index) in waveform.steps" :key="`${waveform.id}-step-${index}`" class="step-row">
          <strong>{{ index + 1 }}</strong>
          <label class="field">
            <span>时长</span>
            <div :data-testid="`step-duration-${index}`">
              <InputNumber
                :value="step.duration_ms"
                :disabled="waveform.builtin"
                :min="1"
                :step="1"
                class="field-number"
                @update:value="emit('update-step', index, 'duration_ms', Number($event ?? 0))"
              />
            </div>
          </label>
          <label class="field">
            <span>A 通道</span>
            <div :data-testid="`step-channel-a-${index}`">
              <InputNumber
                :value="step.channel_a"
                :disabled="waveform.builtin"
                :min="0"
                :max="180"
                :step="1"
                class="field-number"
                @update:value="emit('update-step', index, 'channel_a', Number($event ?? 0))"
              />
            </div>
          </label>
          <label class="field">
            <span>B 通道</span>
            <div :data-testid="`step-channel-b-${index}`">
              <InputNumber
                :value="step.channel_b"
                :disabled="waveform.builtin"
                :min="0"
                :max="180"
                :step="1"
                class="field-number"
                @update:value="emit('update-step', index, 'channel_b', Number($event ?? 0))"
              />
            </div>
          </label>
          <div class="step-actions">
            <Button size="small" :disabled="waveform.builtin" @click="emit('duplicate-step', index)">复制</Button>
            <Button
              size="small"
              danger
              :disabled="waveform.builtin || waveform.steps.length === 1"
              @click="emit('remove-step', index)"
            >
              删除
            </Button>
          </div>
        </article>
      </div>
    </template>
  </ACard>
</template>

<script setup lang="ts">
import { Button, Card as ACard, Empty as AEmpty, Input, InputNumber } from "ant-design-vue";
import type { BluetoothWaveform, BluetoothWaveformStep } from "@/types/bluetooth";

defineProps<{
  waveform: BluetoothWaveform | null;
  savingWaveform: boolean;
}>();

const emit = defineEmits<{
  "save-waveform": [];
  "duplicate-waveform": [];
  "delete-waveform": [];
  "update-waveform-name": [name: string];
  "update-step": [index: number, field: keyof BluetoothWaveformStep, value: number];
  "add-step": [];
  "duplicate-step": [index: number];
  "remove-step": [index: number];
}>();

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
  return waveform.steps.reduce(
    (maxValue, step) => Math.max(maxValue, normalizeStrength(step.channel_a), normalizeStrength(step.channel_b)),
    0,
  );
}
</script>

<style scoped>
.editor-meta,
.step-list {
  display: grid;
  gap: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.stats-grid article,
.step-row {
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 241, 235, 0.98));
  border: 1px solid rgba(120, 113, 108, 0.12);
  box-shadow: 0 10px 24px rgba(28, 25, 23, 0.04);
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
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(240,236,230,0.95));
  border: 1px solid rgba(120, 113, 108, 0.12);
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
  gap: 6px;
  flex: 1 1 140px;
  font-size: 12px;
  font-weight: 600;
  color: #57534e;
}

.field :deep(.ant-input),
.field :deep(.ant-input-number),
.field-number {
  width: 100%;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
