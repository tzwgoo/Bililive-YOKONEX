<template>
  <ACard title="波形编辑器" :bordered="false" class="waveform-editor-panel" :style="DESKTOP_PANEL_STYLE">
    <template #extra>
      <div class="studio-card-actions">
        <Button size="small" @click="emit('duplicate-waveform')">复制为自定义</Button>
        <Button size="small" :disabled="!waveform || waveform.builtin" @click="emit('delete-waveform')">删除当前波形</Button>
        <Button data-testid="save-waveform" size="small" type="primary" :loading="savingWaveform" @click="emit('save-waveform')">保存波形</Button>
      </div>
    </template>
    <div
      data-testid="waveform-editor-scroll"
      class="waveform-editor-scroll"
      :style="SCROLL_CONTAINER_STYLE"
    >
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
          <div
            data-testid="waveform-drag-track"
            class="waveform-track"
            :class="{ 'is-dragging': activeSegmentIndex !== null }"
          >
            <article
              v-for="(step, index) in waveform.steps"
              :key="`${waveform.id}-drag-${index}`"
              class="timeline-segment"
              :data-testid="`timeline-segment-${index}`"
              :class="{ 'is-active': activeSegmentIndex === index }"
              :style="{ flexGrow: Math.max(1, resolveStepDuration(step, index)) }"
            >
              <div
                :data-testid="`waveform-drag-surface-${index}`"
                class="timeline-surface"
              >
                <span class="timeline-grid"></span>
                <span
                  v-if="activeSegmentIndex === index"
                  :data-testid="`timeline-guide-line-${index}`"
                  class="timeline-guide-line"
                  :style="{ bottom: `${resolveGuideLineBottom(step, index)}%` }"
                ></span>
                <span class="timeline-axis-label is-a">A</span>
                <span class="timeline-axis-label is-b">B</span>
                <button
                  :data-testid="`waveform-bar-channel-a-${index}`"
                  type="button"
                  class="timeline-bar is-a"
                  :class="{
                    'is-disabled': waveform.builtin,
                    'is-active': activeSegmentIndex === index && dragField === 'channel_a',
                  }"
                  :style="{ height: `${(resolveStepStrength(step, index, 'channel_a') / 180) * 100}%` }"
                  :disabled="waveform.builtin"
                  @mousedown="startDrag(index, 'channel_a', $event)"
                ></button>
                <button
                  :data-testid="`waveform-bar-channel-b-${index}`"
                  type="button"
                  class="timeline-bar is-b"
                  :class="{
                    'is-disabled': waveform.builtin,
                    'is-active': activeSegmentIndex === index && dragField === 'channel_b',
                  }"
                  :style="{ height: `${(resolveStepStrength(step, index, 'channel_b') / 180) * 100}%` }"
                  :disabled="waveform.builtin"
                  @mousedown="startDrag(index, 'channel_b', $event)"
                ></button>
                <button
                  :data-testid="`waveform-handle-duration-${index}`"
                  type="button"
                  class="timeline-duration-handle"
                  :class="{
                    'is-disabled': waveform.builtin,
                    'is-active': activeSegmentIndex === index && dragField === 'duration_ms',
                  }"
                  :disabled="waveform.builtin"
                  @mousedown="startDrag(index, 'duration_ms', $event)"
                >
                  {{ resolveHandleLabel(step, index, "duration_ms") }}
                </button>
              </div>
            </article>
          </div>
        </div>

        <div class="step-toolbar">
          <Button data-testid="toggle-step-list" size="small" @click="toggleStepList">
            {{ isStepListExpanded ? "收起分段配置" : "展开分段配置" }}
          </Button>
          <Button size="small" :disabled="waveform.builtin" @click="emit('add-step')">新增分段</Button>
        </div>

        <div v-if="isStepListExpanded" data-testid="step-list" class="step-list">
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
    </div>
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
  currentValue: number;
  surface: HTMLElement;
} | null>(null);
const activeSegmentIndex = ref<number | null>(null);
const dragField = ref<DragField | null>(null);
const isStepListExpanded = ref(false);

const DURATION_DRAG_FACTOR = 3.2;
const DESKTOP_PANEL_STYLE = {
  height: "clamp(560px, calc(100vh - 220px), 820px)",
};
const SCROLL_CONTAINER_STYLE = {
  overflowY: "auto",
};

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

function resolvePreviewValue(index: number, field: DragField, fallbackValue: number) {
  if (dragState.value && dragState.value.index === index && dragState.value.field === field) {
    return dragState.value.currentValue;
  }
  return fallbackValue;
}

function resolveStepStrength(step: BluetoothWaveformStep, index: number, field: "channel_a" | "channel_b") {
  return normalizeStrength(resolvePreviewValue(index, field, Number(step[field])));
}

function resolveStepDuration(step: BluetoothWaveformStep, index: number) {
  return normalizeDuration(resolvePreviewValue(index, "duration_ms", Number(step.duration_ms)));
}

function resolveHandleLabel(step: BluetoothWaveformStep, index: number, field: DragField) {
  if (field !== "duration_ms") {
    return "";
  }
  return `${resolveStepDuration(step, index)} ms`;
}

function resolveGuideLineBottom(step: BluetoothWaveformStep, index: number) {
  const strengthField = dragField.value === "channel_b" ? "channel_b" : "channel_a";
  return (resolveStepStrength(step, index, strengthField) / 180) * 100;
}

function toggleStepList() {
  isStepListExpanded.value = !isStepListExpanded.value;
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
    currentValue: Number(step[field]),
    surface,
  };
  activeSegmentIndex.value = index;
  dragField.value = field;
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
    const nextValue = normalizeDuration(startValue + deltaX * DURATION_DRAG_FACTOR);
    dragState.value.currentValue = nextValue;
    emit("update-step", index, field, nextValue);
    return;
  }
  const rect = surface.getBoundingClientRect();
  const offsetY = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
  const ratio = rect.height === 0 ? 0 : (rect.height - offsetY) / rect.height;
  const nextValue = normalizeStrength(ratio * 180);
  dragState.value.currentValue = nextValue;
  emit("update-step", index, field, nextValue);
}

function stopDrag() {
  dragState.value = null;
  activeSegmentIndex.value = null;
  dragField.value = null;
  window.removeEventListener("mousemove", handleDragMove);
  window.removeEventListener("mouseup", stopDrag);
}

onBeforeUnmount(() => {
  stopDrag();
});
</script>

<style scoped>
.waveform-editor-panel {
  display: flex;
  flex-direction: column;
}

.waveform-editor-panel :deep(.ant-card-body) {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  padding-top: 0;
}

.waveform-editor-scroll {
  display: grid;
  flex: 1 1 auto;
  min-height: 0;
  gap: 18px;
  align-content: start;
  padding-top: 18px;
  padding-right: 6px;
}

.editor-meta,
.step-list {
  display: grid;
  gap: 14px;
}

.waveform-timeline {
  display: grid;
  gap: 12px;
}

.waveform-track {
  display: flex;
  align-items: stretch;
  min-height: 280px;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(241,236,229,0.96));
  border: 1px solid rgba(120, 113, 108, 0.12);
  box-shadow: 0 10px 24px rgba(28, 25, 23, 0.04);
  overflow: hidden;
}

.waveform-track.is-dragging .timeline-segment:not(.is-active) {
  opacity: 0.56;
}

.timeline-segment {
  min-width: 0;
  flex-basis: 0;
  border-right: 1px solid rgba(120, 113, 108, 0.12);
  transition: opacity 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.timeline-segment.is-active {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(255, 247, 237, 0.98));
  box-shadow: inset 0 0 0 1px rgba(249, 115, 22, 0.14);
}

.timeline-segment:last-child {
  border-right: 0;
}

.timeline-surface {
  position: relative;
  min-height: 280px;
  height: 100%;
  padding: 18px 14px 48px;
  overflow: hidden;
}

.timeline-grid {
  position: absolute;
  inset: 16px 14px 44px;
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(120, 113, 108, 0.06), rgba(120, 113, 108, 0) 1px) 0 0 / 100% 25%,
    linear-gradient(90deg, rgba(120, 113, 108, 0.06), rgba(120, 113, 108, 0) 1px) 0 0 / 25% 100%;
  pointer-events: none;
}

.timeline-guide-line {
  position: absolute;
  left: 14px;
  right: 14px;
  z-index: 1;
  border-top: 1px dashed rgba(249, 115, 22, 0.42);
  pointer-events: none;
}

.timeline-axis-label {
  position: absolute;
  top: 18px;
  z-index: 1;
  width: calc(50% - 22px);
  font-size: 11px;
  font-weight: 700;
  text-align: center;
  color: rgba(68, 64, 60, 0.72);
  pointer-events: none;
}

.timeline-axis-label.is-a {
  left: 14px;
}

.timeline-axis-label.is-b {
  right: 14px;
}

.timeline-bar {
  position: absolute;
  bottom: 48px;
  width: calc(50% - 22px);
  min-height: 8px;
  border: 0;
  border-radius: 16px 16px 10px 10px;
  box-shadow: 0 12px 20px rgba(28, 25, 23, 0.08);
  cursor: ns-resize;
  user-select: none;
  transition: box-shadow 0.16s ease, transform 0.16s ease, opacity 0.16s ease;
}

.timeline-bar.is-a {
  left: 14px;
  background: linear-gradient(180deg, #fb923c, #f97316);
}

.timeline-bar.is-b {
  right: 14px;
  background: linear-gradient(180deg, #60a5fa, #2563eb);
}

.timeline-duration-handle {
  position: absolute;
  border: 0;
  cursor: grab;
  user-select: none;
}

.timeline-duration-handle {
  left: 14px;
  right: 14px;
  bottom: 14px;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(120, 113, 108, 0.16);
  color: #44403c;
  font-size: 12px;
  font-weight: 700;
  transition: box-shadow 0.16s ease, transform 0.16s ease, opacity 0.16s ease;
}

.timeline-bar.is-disabled,
.timeline-duration-handle.is-disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.timeline-bar.is-active,
.timeline-duration-handle.is-active {
  box-shadow: 0 14px 28px rgba(28, 25, 23, 0.22);
}

.timeline-bar.is-active {
  transform: scale(1.02);
}

.timeline-duration-handle.is-active {
  transform: scale(1.02);
  border-color: rgba(249, 115, 22, 0.32);
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

.step-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
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
  .waveform-editor-panel {
    height: auto !important;
  }

  .waveform-editor-panel :deep(.ant-card-body) {
    padding-top: 0;
  }

  .waveform-editor-scroll {
    overflow-y: visible !important;
    padding-right: 0;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .waveform-timeline {
    overflow-x: auto;
  }

  .waveform-track {
    min-width: 720px;
  }
}
</style>
