<template>
  <ATabs v-model:activeKey="activeKey" class="event-stream-tabs">
    <ATabPane v-for="tab in tabs" :key="tab.key">
      <template #tab>
        {{ tab.label }}<span class="event-tab-count">{{ tab.events.length }}</span>
      </template>
      <EventList :events="tab.events" />
    </ATabPane>
  </ATabs>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { Tabs as ATabs } from "ant-design-vue";
import EventList from "@/components/shared/EventList.vue";

interface EventTabItem {
  key: string;
  label: string;
  events: Array<Record<string, unknown>>;
}

const props = defineProps<{
  tabs: EventTabItem[];
}>();

const activeKey = ref(props.tabs[0]?.key || "");
const ATabPane = ATabs.TabPane;

watch(
  () => props.tabs,
  (tabs) => {
    if (!tabs.some((tab) => tab.key === activeKey.value)) {
      activeKey.value = tabs[0]?.key || "";
    }
  },
  { deep: true },
);
</script>

<style scoped>
.event-tab-count {
  margin-left: 6px;
  color: #78716c;
}
</style>
