<template>
  <section class="panel-section">
    <div class="section-heading">
      <p class="section-kicker">Session Core</p>
      <h2>监听主参数</h2>
    </div>

    <ARow :gutter="[16, 16]">
      <ACol :xs="24" :xl="10">
        <ACard title="监听主参数" :bordered="false">
          <div class="form-grid two-columns">
            <label class="field">
              <span>监听模式</span>
              <Select v-model:value="sessionForm.mode" :options="sessionModeSelectOptions" />
            </label>
            <label class="field">
              <span>{{ sessionValueLabel }}</span>
              <Input
                data-testid="session-value-input"
                v-model:value="sessionForm.value"
                :placeholder="sessionValuePlaceholder"
              />
            </label>
          </div>
        </ACard>
      </ACol>

      <ACol :xs="24" :xl="14">
        <ACard title="礼物 / 点赞触发" :bordered="false">
          <div class="form-grid">
            <label class="field">
              <span>礼物触发模式</span>
              <Select v-model:value="sessionForm.trigger_mode" :options="triggerModeOptions" />
            </label>
            <label class="field">
              <span>点赞倍数</span>
              <InputNumber v-model:value="sessionForm.like_multiple" :min="1" :step="1" class="field-number" />
            </label>
          </div>
        </ACard>
      </ACol>
    </ARow>

    <ACard title="弹幕关键词触发" :bordered="false">
      <div class="form-grid">
        <label class="field">
          <span>触发开关</span>
          <Select v-model:value="danmakuEnabledValue" :options="danmakuEnabledOptions" />
        </label>
        <label class="field">
          <span>弹幕冷却秒数</span>
          <InputNumber v-model:value="sessionForm.danmaku_cooldown_seconds" :min="0" :step="1" class="field-number" />
        </label>
        <label class="field">
          <span>每用户限流窗口</span>
          <InputNumber v-model:value="sessionForm.danmaku_user_limit_window_seconds" :min="0" :step="1" class="field-number" />
        </label>
        <label class="field">
          <span>窗口内最大触发次数</span>
          <InputNumber v-model:value="sessionForm.danmaku_user_limit_max_triggers" :min="0" :step="1" class="field-number" />
        </label>
        <label class="field">
          <span>最低舰队等级</span>
          <Select v-model:value="sessionForm.danmaku_min_guard_level" :options="guardLevelOptions" />
        </label>
        <label class="field field-span-2">
          <span>弹幕关键词</span>
          <Input v-model:value="sessionForm.danmaku_keywords" placeholder="多个关键词用逗号分隔，例如 游戏,意思,玩" />
        </label>
      </div>
      <AAlert v-if="message" class="section-alert" :message="message" type="info" show-icon />
      <div class="button-row">
        <Button data-testid="start-session" type="primary" :loading="startingSession" @click="$emit('start')">启动监听</Button>
        <Button :disabled="startingSession" @click="$emit('stop')">停止监听</Button>
      </div>
    </ACard>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  Alert as AAlert,
  Button,
  Card as ACard,
  Col as ACol,
  Input,
  InputNumber,
  Row as ARow,
  Select,
} from "ant-design-vue";
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

const sessionModeSelectOptions = [
  { label: "官方 open-live", value: "open_live" },
  { label: "第三方房间消息流", value: "third_party" },
];
const triggerModeOptions = [
  { label: "按礼物数量触发", value: "by_quantity" },
  { label: "单次触发", value: "single" },
];
const danmakuEnabledOptions = [
  { label: "关闭", value: "false" },
  { label: "开启", value: "true" },
];
const guardLevelOptions = [
  { label: "不限", value: 0 },
  { label: "舰长及以上", value: 3 },
  { label: "提督及以上", value: 2 },
  { label: "总督", value: 1 },
];

const sessionValueLabel = computed(() => (props.sessionForm.mode === "third_party" ? "房间长 ID" : "主播身份码"));
const sessionValuePlaceholder = computed(() =>
  props.sessionForm.mode === "third_party" ? "请输入直播间房间长 ID room_id" : "请输入主播身份码 code",
);
const danmakuEnabledValue = computed({
  get: () => (props.sessionForm.danmaku_enabled ? "true" : "false"),
  set: (value: string) => {
    props.sessionForm.danmaku_enabled = value === "true";
  },
});
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

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px 16px;
}

.form-grid.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
  display: grid;
  gap: 8px;
  color: #44403c;
  font-size: 13px;
  font-weight: 600;
}

.field :deep(.ant-input),
.field :deep(.ant-input-number),
.field :deep(.ant-select-selector) {
  border-radius: 12px;
}

.field-number {
  width: 100%;
}

.field-span-2 {
  grid-column: span 2;
}

.section-alert {
  margin-top: 16px;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 18px;
}

@media (max-width: 900px) {
  .form-grid,
  .form-grid.two-columns {
    grid-template-columns: 1fr;
  }

  .field-span-2 {
    grid-column: span 1;
  }
}
</style>
