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

      <div class="waveform-timeline">
        <article
          v-for="(step, index) in waveform.steps"
          :key="`${waveform.id}-drag-${index}`"
          class="timeline-segment"
          :style="{ flexGrow: Math.max(1, step.duration_ms) }"
        >
          <div
            :data-testid="`waveform-drag-surface-${index}`"
            class="timeline-surface"
          >
            <span class="timeline-grid"></span>
            <span
              class="timeline-bar is-a"
              :style="{ height: `${(step.channel_a / 180) * 100}%` }"
            ></span>
            <span
              class="timeline-bar is-b"
              :style="{ height: `${(step.channel_b / 180) * 100}%` }"
            ></span>
            <button
              :data-testid="`waveform-handle-channel-a-${index}`"
              type="button"
              class="timeline-handle is-a"
              :class="{ 'is-disabled': waveform.builtin }"
              :style="{ bottom: `${(step.channel_a / 180) * 100}%` }"
              :disabled="waveform.builtin"
              @mousedown="startDrag(index, 'channel_a', $event)"
            >
              A
            </button>
            <button
              :data-testid="`waveform-handle-channel-b-${index}`"
              type="button"
              class="timeline-handle is-b"
              :class="{ 'is-disabled': waveform.builtin }"
              :style="{ bottom: `${(step.channel_b / 180) * 100}%` }"
              :disabled="waveform.builtin"
              @mousedown="startDrag(index, 'channel_b', $event)"
            >
              B
            </button>
            <button
              :data-testid="`waveform-handle-duration-${index}`"
              type="button"
              class="timeline-duration-handle"
              :class="{ 'is-disabled': waveform.builtin }"
              :disabled="waveform.builtin"
              @mousedown="startDrag(index, 'duration_ms', $event)"
            >
              {{ step.duration_ms }} ms
            </button>
          </div>
        </article>
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
import { onBeforeUnmount, ref } from "vue";
import { Button, Card as ACard, Empty as AEmpty, Input, InputNumber } from "ant-design-vue";
import type { BluetoothWaveform, BluetoothWaveformStep } from "@/types/bluetooth";

const props = defineProps<{
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

type DragField = keyof BluetoothWaveformStep;

const dragState = ref<{
  index: number;
  field: DragField;
  startX: number;
  startValue: number;
  surface: HTMLElement;
} | null>(null);

const DURATION_DRAG_FACTOR = 3.2;

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

function startDrag(index: number, field: DragField, event: MouseEvent) {
  if (!props.waveform || props.waveform.builtin || event.button !== 0) {
    return;
  }
  const surface = (event.currentTarget as HTMLElement | null)?.closest(".timeline-surface") as HTMLElement | null;
  if (!surface) {
    return;
  }
  const step = props.waveform.steps[index];
  if (!step) {
    return;
  }
  dragState.value = {
    index,
    field,
    startX: event.clientX,
    startValue: Number(step[field]),
    surface,
  };
  window.addEventListener("mousemove", handleDragMove);
  window.addEventListener("mouseup", stopDrag);
  event.preventDefault();
}

function handleDragMove(event: MouseEvent) {
  if (!dragState.value) {
    return;
  }
  const { index, field, startX, startValue, surface } = dragState.value;
  if (field === "duration_ms") {
    const deltaX = event.clientX - startX;
    emit("update-step", index, field, normalizeDuration(startValue + deltaX * DURATION_DRAG_FACTOR));
    return;
  }
  const rect = surface.getBoundingClientRect();
  const offsetY = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
  const ratio = rect.height === 0 ? 0 : (rect.height - offsetY) / rect.height;
  emit("update-step", index, field, normalizeStrength(ratio * 180));
}

function stopDrag() {
  dragState.value = null;
  window.removeEventListener("mousemove", handleDragMove);
  window.removeEventListener("mouseup", stopDrag);
}

onBeforeUnmount(() => {
  stopDrag();
});
</script>

<style scoped>
.editor-meta,
.step-list {
  display: grid;
  gap: 14px;
}

.waveform-timeline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.timeline-segment {
  min-width: 0;
}

.timeline-surface {
  position: relative;
  min-height: 220px;
  padding: 16px 12px 42px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(241,236,229,0.96));
  border: 1px solid rgba(120, 113, 108, 0.12);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
  overflow: hidden;
}

.timeline-grid {
  position: absolute;
  inset: 12px 12px 40px;
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(120, 113, 108, 0.06), rgba(120, 113, 108, 0) 1px) 0 0 / 100% 25%,
    linear-gradient(90deg, rgba(120, 113, 108, 0.06), rgba(120, 113, 108, 0) 1px) 0 0 / 25% 100%;
  pointer-events: none;
}

.timeline-bar {
  position: absolute;
  bottom: 40px;
  width: calc(50% - 18px);
  min-height: 8px;
  border-radius: 16px 16px 10px 10px;
  box-shadow: 0 12px 20px rgba(28, 25, 23, 0.08);
}

.timeline-bar.is-a {
  left: 12px;
  background: linear-gradient(180deg, #fb923c, #f97316);
}

.timeline-bar.is-b {
  right: 12px;
  background: linear-gradient(180deg, #60a5fa, #2563eb);
}

.timeline-handle,
.timeline-duration-handle {
  position: absolute;
  border: 0;
  cursor: grab;
  user-select: none;
}

.timeline-handle {
  z-index: 1;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  color: #fafaf9;
  font-size: 11px;
  font-weight: 700;
  box-shadow: 0 10px 18px rgba(28, 25, 23, 0.16);
  transform: translateY(50%);
}

.timeline-handle.is-a {
  left: 22px;
  background: #ea580c;
}

.timeline-handle.is-b {
  right: 22px;
  background: #1d4ed8;
}

.timeline-duration-handle {
  left: 12px;
  right: 12px;
  bottom: 10px;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(120, 113, 108, 0.16);
  color: #44403c;
  font-size: 12px;
  font-weight: 700;
}

.timeline-handle.is-disabled,
.timeline-duration-handle.is-disabled {
  cursor: not-allowed;
  opacity: 0.55;
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

  .waveform-timeline {
    grid-template-columns: 1fr;
  }
}
</style>
