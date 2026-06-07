<template>
  <ACard title="蓝牙事件规则" :bordered="false">
    <AEmpty v-if="ruleGroups.length === 0" description="暂无规则组" />
    <ACollapse v-else :bordered="false" :default-active-key="ruleGroups.map((group) => group.group_id)">
      <ACollapsePanel
        v-for="group in ruleGroups"
        :key="group.group_id"
        :header="group.group_label"
      >
        <div class="rule-list">
          <article v-for="rule in group.rules" :key="rule.id" class="rule-item">
            <div class="rule-head">
              <div>
                <strong>{{ rule.rule_label }}</strong>
                <p class="rule-caption">波形与价格过滤器会一并保存到当前蓝牙规则组。</p>
              </div>
              <Checkbox v-model:checked="rule.enabled">启用</Checkbox>
            </div>
            <div class="rule-grid">
              <label class="field">
                <span>EMS 波形</span>
                <Select
                  :data-testid="`rule-waveform-${rule.id}`"
                  v-model:value="rule.waveform_id"
                  :options="emsWaveformOptions"
                />
              </label>
              <label class="field">
                <span>Toy 波形</span>
                <Select
                  :data-testid="`rule-toy-waveform-${rule.id}`"
                  v-model:value="rule.toy_waveform_id"
                  :options="toyWaveformOptions"
                  allow-clear
                  placeholder="可选"
                />
              </label>
              <template v-if="priceFilterGroupIds.has(group.group_id)">
                <label class="field">
                  <span>最低价格</span>
                  <InputNumber
                    :value="Number(rule.filters?.min_price || 0)"
                    :min="0"
                    :step="1"
                    class="field-number"
                    @update:value="emit('update-min-price', rule.id, Number($event ?? 0))"
                  />
                </label>
                <label class="field">
                  <span>最高价格</span>
                  <InputNumber
                    :value="rule.filters?.max_price ?? null"
                    :min="0"
                    :step="1"
                    class="field-number"
                    placeholder="留空表示无上限"
                    @update:value="emit('update-max-price', rule.id, $event as number | null)"
                  />
                </label>
              </template>
            </div>
          </article>
        </div>
      </ACollapsePanel>
    </ACollapse>
  </ACard>
</template>

<script setup lang="ts">
import {
  Card as ACard,
  Checkbox,
  Collapse as ACollapse,
  Empty as AEmpty,
  InputNumber,
  Select,
} from "ant-design-vue";
import type { BluetoothRuleGroup } from "@/types/bluetooth";

defineProps<{
  ruleGroups: BluetoothRuleGroup[];
  emsWaveformOptions: Array<{
    label: string;
    value: string;
  }>;
  toyWaveformOptions: Array<{
    label: string;
    value: string;
  }>;
}>();

const emit = defineEmits<{
  "update-min-price": [ruleId: string, value: number];
  "update-max-price": [ruleId: string, value: number | null];
}>();

const ACollapsePanel = ACollapse.Panel;
const priceFilterGroupIds = new Set(["gift", "super_chat", "guard_buy", "guard_renew"]);
</script>

<style scoped>
.rule-list {
  display: grid;
  gap: 12px;
}

.rule-item {
  display: grid;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 241, 235, 0.98));
  border: 1px solid rgba(120, 113, 108, 0.12);
  box-shadow: 0 10px 24px rgba(28, 25, 23, 0.04);
}

.rule-head {
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

@media (max-width: 900px) {
  .rule-grid {
    grid-template-columns: 1fr;
  }

  .field-span-2 {
    grid-column: span 1;
  }
}
</style>
