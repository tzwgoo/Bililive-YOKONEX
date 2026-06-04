<template>
  <ATabs v-model:activeKey="activeKey" class="event-stream-tabs" @change="handleTabChange">
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
  storageKey?: string;
}>();

function loadInitialActiveKey() {
  if (!props.storageKey) {
    return props.tabs[0]?.key || "";
  }
  const rawValue = window.localStorage.getItem(props.storageKey);
  if (!rawValue) {
    return props.tabs[0]?.key || "";
  }
  try {
    const nextKey = JSON.parse(rawValue) as string;
    return props.tabs.some((tab) => tab.key === nextKey) ? nextKey : (props.tabs[0]?.key || "");
  } catch {
    return props.tabs[0]?.key || "";
  }
}

const activeKey = ref(loadInitialActiveKey());
const ATabPane = ATabs.TabPane;

function persistActiveKey(value: string) {
  if (!props.storageKey || !value) {
    return;
  }
  window.localStorage.setItem(props.storageKey, JSON.stringify(value));
}

watch(
  () => props.tabs,
  (tabs) => {
    if (!tabs.some((tab) => tab.key === activeKey.value)) {
      activeKey.value = tabs[0]?.key || "";
    }
  },
  { deep: true },
);

watch(activeKey, (value) => {
  persistActiveKey(value);
});

function handleTabChange(value: string) {
  activeKey.value = value;
  persistActiveKey(value);
}
</script>

<style scoped>
.event-tab-count {
  margin-left: 6px;
  color: #78716c;
}
</style>
