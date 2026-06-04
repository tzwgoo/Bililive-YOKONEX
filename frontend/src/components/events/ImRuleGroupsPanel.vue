<template>
  <section class="studio-stack">
    <ACard v-for="group in groups" :key="group.eventType" :title="group.label" :bordered="false">
      <template #extra>
        <div class="studio-card-actions">
          <span class="section-count">{{ group.rules.length }} 条</span>
          <Button size="small" @click="emit('sort-rules', group.eventType)">按价格升序整理</Button>
          <Button size="small" @click="emit('add-rule', group.eventType)">新增档位</Button>
        </div>
      </template>
      <AEmpty v-if="group.rules.length === 0" description="暂无档位规则" />
      <div v-else class="rule-list">
        <article v-for="rule in group.rules" :key="rule.id" class="rule-item">
          <div class="rule-head">
            <div>
              <strong>{{ group.label }}档位</strong>
              <p class="rule-caption">价格区间和指令槽位会在保存后立即写回后端配置。</p>
            </div>
            <Checkbox v-model:checked="rule.enabled">启用</Checkbox>
          </div>
          <div class="rule-grid">
            <label class="field">
              <span>最低价格</span>
              <div :data-testid="`command-min-price-${rule.id}`">
                <InputNumber
                  :value="rule.min_price"
                  :min="0"
                  :step="1"
                  class="field-number"
                  @update:value="rule.min_price = normalizeNonNegative(Number($event ?? 0))"
                />
              </div>
            </label>
            <label class="field">
              <span>最高价格</span>
              <InputNumber
                :value="rule.max_price"
                :min="0"
                :step="1"
                class="field-number"
                placeholder="留空表示无上限"
                @update:value="emit('update-max-price', rule, $event as number | null)"
              />
            </label>
            <label class="field field-span-2">
              <span>指令槽位</span>
              <Select v-model:value="rule.command_slot" :options="commandSlotOptions" />
            </label>
          </div>
          <div class="rule-footer">
            <Button danger size="small" @click="emit('remove-rule', rule.id)">删除</Button>
          </div>
        </article>
      </div>
    </ACard>

    <ARow :gutter="[18, 18]">
      <ACol :xs="24" :xl="12">
        <ACard title="固定点赞指令 ID" :bordered="false">
          <div class="fixed-list">
            <article class="fixed-item">
              <strong>点赞事件</strong>
              <code>{{ studio?.like_command_id || "-" }}</code>
            </article>
          </div>
        </ACard>
      </ACol>
      <ACol :xs="24" :xl="12">
        <ACard title="固定弹幕指令 ID" :bordered="false">
          <div class="fixed-list">
            <article
              v-for="item in studio?.danmaku_event_types || []"
              :key="item.value"
              class="fixed-item"
            >
              <strong>{{ item.label }}</strong>
              <code>{{ studio?.danmaku_command_ids?.[item.value] || "-" }}</code>
            </article>
          </div>
        </ACard>
      </ACol>
    </ARow>
  </section>
</template>

<script setup lang="ts">
import {
  Button,
  Card as ACard,
  Checkbox,
  Col as ACol,
  Empty as AEmpty,
  InputNumber,
  Row as ARow,
  Select,
} from "ant-design-vue";
import type { CommandStudioResponse, CommandStudioRule } from "@/types/command";

defineProps<{
  groups: Array<{
    eventType: string;
    label: string;
    rules: CommandStudioRule[];
  }>;
  commandSlotOptions: Array<{
    label: string;
    value: string;
  }>;
  studio: CommandStudioResponse | null;
}>();

const emit = defineEmits<{
  "add-rule": [eventType: string];
  "sort-rules": [eventType: string];
  "remove-rule": [ruleId: string];
  "update-max-price": [rule: CommandStudioRule, value: number | null];
}>();

function normalizeNonNegative(value: number) {
  return Math.max(0, Math.round(Number(value || 0)));
}
</script>

<style scoped>
.rule-list {
  display: grid;
  gap: 12px;
}

.rule-item {
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 241, 235, 0.98));
  border: 1px solid rgba(120, 113, 108, 0.12);
  box-shadow: 0 10px 24px rgba(28, 25, 23, 0.04);
}

.rule-head,
.rule-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.rule-caption {
  margin: 6px 0 0;
  color: #78716c;
  font-size: 12px;
  font-weight: 500;
}

.rule-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
}

.field {
  display: grid;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #57534e;
}

.field :deep(.ant-input-number),
.field :deep(.ant-select),
.field-number {
  width: 100%;
}

.field-span-2 {
  grid-column: span 2;
}

.fixed-list {
  display: grid;
  gap: 10px;
}

.fixed-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 241, 235, 0.98));
  border: 1px solid rgba(120, 113, 108, 0.12);
}

.section-count {
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  min-height: 28px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(120, 113, 108, 0.12);
  font-size: 12px;
  color: #78716c;
}

@media (max-width: 900px) {
  .rule-grid {
    grid-template-columns: 1fr;
  }

  .field-span-2 {
    grid-column: span 1;
  }
}
</style>
