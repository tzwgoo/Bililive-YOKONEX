<template>
  <div class="event-config-tabs" role="tablist" aria-label="事件配置标签">
    <Button
      v-for="tab in tabs"
      :key="tab.key"
      :data-testid="`event-tab-${tab.key}`"
      class="event-config-tab"
      :type="activeTab === tab.key ? 'primary' : 'default'"
      @click="emit('update:activeTab', tab.key)"
    >
      {{ tab.label }}
    </Button>
  </div>
</template>

<script setup lang="ts">
import { Button } from "ant-design-vue";

defineProps<{
  activeTab: string;
  tabs: Array<{
    key: string;
    label: string;
  }>;
}>();

const emit = defineEmits<{
  "update:activeTab": [value: string];
}>();
</script>

<style scoped>
.event-config-tabs {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 10px;
}

.event-config-tab {
  min-width: 88px;
  border-radius: 999px;
}
</style>
