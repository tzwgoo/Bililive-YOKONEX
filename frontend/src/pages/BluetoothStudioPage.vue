<template>
  <main class="studio-page">
    <ACard class="studio-hero" :bordered="false">
      <div>
        <p class="studio-kicker">Bluetooth Studio</p>
        <h1>蓝牙 Studio</h1>
        <p class="studio-subtitle">这一页先迁入波形库和事件规则的只读预览，下一步继续补上波形编辑器与拖拽强度编辑。</p>
      </div>
      <StatusPill :state="bluetoothStore.status.connected ? 'connected' : 'idle'" />
    </ACard>

    <AAlert
      message="当前是迁移中的第一版：已接入后端数据与路由，可查看波形库和规则分组；编辑器将在下一阶段继续补齐。"
      type="warning"
      show-icon
    />

    <ARow :gutter="[18, 18]">
      <ACol :xs="24" :xl="10">
        <ACard title="波形库" :bordered="false">
          <AList :data-source="bluetoothStore.studio?.waveforms || []">
            <template #renderItem="{ item }">
              <AListItem>
                <div class="waveform-item">
                  <strong>{{ item.name || item.id }}</strong>
                  <small>{{ item.builtin ? '内置' : '自定义' }} · {{ item.steps?.length || 0 }} 步</small>
                </div>
              </AListItem>
            </template>
          </AList>
        </ACard>
      </ACol>
      <ACol :xs="24" :xl="14">
        <ACard title="事件规则预览" :bordered="false">
          <AEmpty v-if="!ruleGroups.length" description="暂无规则组" />
          <ACollapse v-else :bordered="false">
            <ACollapsePanel
              v-for="group in ruleGroups"
              :key="group.group_id"
              :header="group.group_label || group.group_id"
            >
              <AList :data-source="group.rules || []">
                <template #renderItem="{ item }">
                  <AListItem>
                    <div class="waveform-item">
                      <strong>{{ item.rule_label || item.event_type }}</strong>
                      <small>{{ item.waveform_name || item.waveform_id || '-' }}</small>
                    </div>
                    <StatusPill :state="item.enabled ? 'running' : 'idle'" />
                  </AListItem>
                </template>
              </AList>
            </ACollapsePanel>
          </ACollapse>
        </ACard>
      </ACol>
    </ARow>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import {
  Alert as AAlert,
  Card as ACard,
  Col as ACol,
  Collapse as ACollapse,
  Empty as AEmpty,
  List as AList,
  Row as ARow,
} from "ant-design-vue";
import StatusPill from "@/components/shared/StatusPill.vue";
import { useBluetoothStore } from "@/stores/bluetooth";

const bluetoothStore = useBluetoothStore();
const AListItem = AList.Item;
const ACollapsePanel = ACollapse.Panel;

const ruleGroups = computed(() => {
  const studio = bluetoothStore.studio as { rule_groups?: Array<Record<string, unknown>> } | null;
  return Array.isArray(studio?.rule_groups) ? studio.rule_groups : [];
});

onMounted(async () => {
  await Promise.all([bluetoothStore.fetchStatus(), bluetoothStore.fetchStudio()]);
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

.waveform-item {
  display: grid;
  gap: 4px;
}

.waveform-item small {
  color: #78716c;
}

@media (max-width: 900px) {
  .studio-hero {
    flex-direction: column;
  }
}
</style>
