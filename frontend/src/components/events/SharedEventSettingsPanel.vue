<template>
  <section class="shared-settings-stack">
    <ACard v-if="selectedConfig === 'like'" title="点赞触发配置" :bordered="false">
      <div class="form-grid">
        <label class="field">
          <span>礼物触发模式</span>
          <Select v-model:value="sessionDraft.trigger_mode" :options="triggerModeOptions" />
        </label>
        <label class="field">
          <span>点赞倍率</span>
          <InputNumber
            v-model:value="sessionDraft.like_multiple"
            :min="1"
            :step="1"
            class="field-number"
          />
        </label>
      </div>
      <p class="form-hint">该配置会同时影响 IM 指令触发和蓝牙事件触发。</p>
    </ACard>

    <ACard v-else-if="selectedConfig === 'danmaku'" title="弹幕触发配置" :bordered="false">
      <div class="form-grid">
        <label class="field">
          <span>触发开关</span>
          <Select v-model:value="danmakuEnabledValue" :options="danmakuEnabledOptions" />
        </label>
        <label class="field">
          <span>弹幕冷却秒数</span>
          <InputNumber
            v-model:value="sessionDraft.danmaku_cooldown_seconds"
            :min="0"
            :step="1"
            class="field-number"
          />
        </label>
        <label class="field">
          <span>每用户限流窗口</span>
          <InputNumber
            v-model:value="sessionDraft.danmaku_user_limit_window_seconds"
            :min="0"
            :step="1"
            class="field-number"
          />
        </label>
        <label class="field">
          <span>窗口内最大触发次数</span>
          <InputNumber
            v-model:value="sessionDraft.danmaku_user_limit_max_triggers"
            :min="0"
            :step="1"
            class="field-number"
          />
        </label>
        <label class="field">
          <span>最低舰队等级</span>
          <Select v-model:value="sessionDraft.danmaku_min_guard_level" :options="guardLevelOptions" />
        </label>
        <label class="field field-span-2">
          <span>弹幕关键词</span>
          <Input
            v-model:value="sessionDraft.danmaku_keywords"
            placeholder="多个关键词用逗号分隔，例如：游戏,互动,测试"
          />
        </label>
      </div>
      <p class="form-hint">弹幕关键词命中后，会按当前保存的通用规则同时驱动 IM 和蓝牙事件链路。</p>
    </ACard>

    <ACard v-else :bordered="false">
      <AEmpty description="请先从右侧选择通用事件配置" />
    </ACard>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Card as ACard, Empty as AEmpty, Input, InputNumber, Select } from "ant-design-vue";
import type { SessionStartPayload } from "@/types/session";

const props = defineProps<{
  selectedConfig: "like" | "danmaku" | "";
  sessionDraft: SessionStartPayload;
}>();

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

const danmakuEnabledValue = computed({
  get: () => (props.sessionDraft.danmaku_enabled ? "true" : "false"),
  set: (value: string) => {
    props.sessionDraft.danmaku_enabled = value === "true";
  },
});
</script>

<style scoped>
.shared-settings-stack {
  display: grid;
  gap: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 16px;
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
.field :deep(.ant-select),
.field-number {
  width: 100%;
}

.field-span-2 {
  grid-column: span 2;
}

.form-hint {
  margin: 16px 0 0;
  color: #78716c;
  font-size: 12px;
}

@media (max-width: 900px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .field-span-2 {
    grid-column: span 1;
  }
}
</style>
