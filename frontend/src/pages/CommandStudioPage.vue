<template>
  <main class="studio-page">
    <ACard class="studio-hero" :bordered="false">
      <div>
        <p class="studio-kicker">Command Studio</p>
        <h1>IM 规则中心</h1>
        <p class="studio-subtitle">维护礼物、醒目留言和上舰续费的价格档位映射；点赞与弹幕事件保持固定指令槽位。</p>
      </div>
      <div class="studio-actions">
        <Button data-testid="command-save" type="primary" :loading="saving" @click="handleSave">保存 IM 规则</Button>
      </div>
    </ACard>

    <AAlert v-if="message" :message="message" type="info" show-icon />

    <section class="studio-stack">
      <ACard v-for="group in groupedRules" :key="group.eventType" :title="group.label" :bordered="false">
        <template #extra>
          <div class="studio-card-actions">
            <Button size="small" @click="sortRules(group.eventType)">按价格升序整理</Button>
            <Button size="small" @click="addRule(group.eventType)">新增档位</Button>
          </div>
        </template>
        <AEmpty v-if="group.rules.length === 0" description="暂无档位规则" />
        <div v-else class="rule-list">
          <article v-for="rule in group.rules" :key="rule.id" class="rule-item">
            <div class="rule-head">
              <strong>{{ group.label }}档位</strong>
              <label class="toggle-line">
                <input v-model="rule.enabled" type="checkbox" />
                <span>启用</span>
              </label>
            </div>
            <div class="rule-grid">
              <label class="field">
                <span>最低价格</span>
                <input v-model.number="rule.min_price" type="number" min="0" step="1" />
              </label>
              <label class="field">
                <span>最高价格</span>
                <input
                  :value="rule.max_price ?? ''"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="留空表示无上限"
                  @input="updateMaxPrice(rule, $event)"
                />
              </label>
              <label class="field field-span-2">
                <span>指令槽位</span>
                <select v-model="rule.command_slot">
                  <option v-for="slot in commandSlots" :key="slot" :value="slot">{{ slot }}</option>
                </select>
              </label>
            </div>
            <div class="rule-footer">
              <Button danger size="small" @click="removeRule(rule.id)">删除</Button>
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
                <code>{{ commandStore.studio?.like_command_id || "-" }}</code>
              </article>
            </div>
          </ACard>
        </ACol>
        <ACol :xs="24" :xl="12">
          <ACard title="固定弹幕指令 ID" :bordered="false">
            <div class="fixed-list">
              <article
                v-for="item in commandStore.studio?.danmaku_event_types || []"
                :key="item.value"
                class="fixed-item"
              >
                <strong>{{ item.label }}</strong>
                <code>{{ commandStore.studio?.danmaku_command_ids?.[item.value] || "-" }}</code>
              </article>
            </div>
          </ACard>
        </ACol>
      </ARow>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { Alert as AAlert, Button, Card as ACard, Col as ACol, Empty as AEmpty, Row as ARow } from "ant-design-vue";
import { useCommandStore } from "@/stores/command";
import type { CommandStudioRule } from "@/types/command";

const commandStore = useCommandStore();
const saving = ref(false);
const message = ref("修改后点击“保存 IM 规则”立即生效。");
const draftRules = ref<CommandStudioRule[]>([]);

const groupedRules = computed(() => {
  const groups = commandStore.studio?.event_types || [];
  return groups.map((group) => ({
    eventType: group.value,
    label: group.label,
    rules: draftRules.value.filter((rule) => rule.event_type === group.value),
  }));
});
const commandSlots = computed(() => commandStore.studio?.command_slots || []);

watch(
  () => commandStore.studio,
  (studio) => {
    if (!studio) {
      return;
    }
    draftRules.value = studio.rules.map((rule) => ({ ...rule }));
  },
  { immediate: true },
);

function normalizeNonNegative(value: number) {
  return Math.max(0, Math.round(Number(value || 0)));
}

function updateMaxPrice(rule: CommandStudioRule, event: Event) {
  const target = event.target as HTMLInputElement;
  rule.max_price = target.value === "" ? null : normalizeNonNegative(Number(target.value));
}

function addRule(eventType: string) {
  draftRules.value.push({
    id: `${eventType}-rule-${Date.now()}`,
    enabled: true,
    event_type: eventType,
    min_price: 0,
    max_price: null,
    command_slot: commandSlots.value[0] || "",
  });
}

function sortRules(eventType: string) {
  const current = [...draftRules.value];
  const sortedTarget = current
    .filter((rule) => rule.event_type === eventType)
    .sort((left, right) => {
      const minDelta = normalizeNonNegative(left.min_price) - normalizeNonNegative(right.min_price);
      if (minDelta !== 0) {
        return minDelta;
      }
      const leftMax = left.max_price == null ? Number.MAX_SAFE_INTEGER : normalizeNonNegative(left.max_price);
      const rightMax = right.max_price == null ? Number.MAX_SAFE_INTEGER : normalizeNonNegative(right.max_price);
      return leftMax - rightMax;
    });
  draftRules.value = current.filter((rule) => rule.event_type !== eventType).concat(sortedTarget);
  message.value = `${groupedRules.value.find((item) => item.eventType === eventType)?.label || "当前"}档位已按价格升序整理`;
}

function removeRule(ruleId: string) {
  draftRules.value = draftRules.value.filter((rule) => rule.id !== ruleId);
}

async function handleSave() {
  saving.value = true;
  try {
    await commandStore.saveStudio({
      rules: draftRules.value.map((rule) => ({
        ...rule,
        min_price: normalizeNonNegative(rule.min_price),
        max_price: rule.max_price == null ? null : normalizeNonNegative(rule.max_price),
      })),
      like_rules: [],
      danmaku_slot_rules: [],
    });
    message.value = "IM 规则已保存";
  } catch (error) {
    message.value = error instanceof Error ? error.message : "保存 IM 规则失败";
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await commandStore.fetchStudio();
});
</script>

<style scoped>
.studio-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 24px 40px;
  display: grid;
  gap: 18px;
}

.studio-hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.studio-kicker,
.studio-hero h1 {
  margin: 0;
}

.studio-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #78716c;
  margin-bottom: 8px;
}

.studio-subtitle {
  margin: 8px 0 0;
  color: #57534e;
}

.studio-stack {
  display: grid;
  gap: 18px;
}

.studio-card-actions {
  display: flex;
  gap: 8px;
}

.rule-list {
  display: grid;
  gap: 14px;
}

.rule-item {
  padding: 16px;
  border-radius: 16px;
  background: #f8f6f2;
  border: 1px solid rgba(120, 113, 108, 0.15);
}

.rule-head,
.rule-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.rule-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
}

.field input,
.field select {
  width: 100%;
  min-height: 40px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid #d6d3d1;
  background: #fff;
}

.field-span-2 {
  grid-column: span 2;
}

.toggle-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.fixed-list {
  display: grid;
  gap: 12px;
}

.fixed-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #f8f6f2;
}

@media (max-width: 900px) {
  .studio-hero {
    flex-direction: column;
  }

  .rule-grid {
    grid-template-columns: 1fr;
  }

  .field-span-2 {
    grid-column: span 1;
  }
}
</style>
