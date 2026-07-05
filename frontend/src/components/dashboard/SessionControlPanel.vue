<template>
  <section class="panel-section">
    <div class="section-heading">
      <p class="section-kicker">Session Core</p>
      <h2>监听主参数</h2>
    </div>

    <ACard title="监听主参数" :bordered="false">
      <div class="session-inline-wrap">
        <div class="session-inline-row">
        <label class="field session-mode-field">
          <span>监听来源</span>
          <Select
            data-testid="session-mode-select"
            v-model:value="sessionForm.mode"
            :options="modeOptions"
          />
        </label>
        <label class="field session-room-field">
          <span>{{ roomFieldLabel }}</span>
          <Input
            data-testid="session-value-input"
            v-model:value="sessionForm.value"
            :placeholder="roomFieldPlaceholder"
          />
        </label>
        <div class="session-actions">
          <Button data-testid="start-session" type="primary" :loading="startingSession" @click="$emit('start')">启动监听</Button>
          <Button :disabled="startingSession" @click="$emit('stop')">停止监听</Button>
        </div>
      </div>
      </div>
      <AAlert v-if="message" class="section-alert" :message="message" type="info" show-icon />
    </ACard>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Alert as AAlert, Button, Card as ACard, Input, Select } from "ant-design-vue";
import type { SessionStartPayload } from "@/types/session";

const props = defineProps<{
  sessionForm: SessionStartPayload;
  startingSession: boolean;
  message: string;
}>();

defineEmits<{
  start: [];
  stop: [];
}>();

const modeOptions = [
  { label: "B 站第三方流", value: "third_party" },
  { label: "抖音直播", value: "douyin" },
];

const roomFieldLabel = computed(() => (props.sessionForm.mode === "douyin" ? "抖音直播间标识" : "房间号 ID"));
const roomFieldPlaceholder = computed(() =>
  props.sessionForm.mode === "douyin"
    ? "请输入 live.douyin.com 后面的直播间标识"
    : "请输入直播间房间号 ID room_id",
);
</script>

<style scoped>
.panel-section {
  display: grid;
  gap: 16px;
}

.section-heading h2,
.section-kicker {
  margin: 0;
}

.section-kicker {
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #78716c;
}

.session-inline-wrap {
  display: flex;
  justify-content: flex-start;
}

.session-inline-row {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  width: min(100%, 980px);
}

.session-room-field {
  flex: 1 1 640px;
}

.session-mode-field {
  flex: 0 0 180px;
}

.field {
  display: grid;
  gap: 8px;
  color: #44403c;
  font-size: 13px;
  font-weight: 600;
}

.field :deep(.ant-input) {
  border-radius: 12px;
}

.field :deep(.ant-select-selector) {
  border-radius: 12px;
}

.session-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.section-alert {
  margin-top: 16px;
}

@media (max-width: 900px) {
  .session-inline-wrap {
    display: block;
  }

  .session-inline-row {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
  }

  .session-actions {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
