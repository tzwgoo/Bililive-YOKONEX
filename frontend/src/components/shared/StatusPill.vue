<template>
  <ATag class="status-pill" :color="color">{{ normalizedState }}</ATag>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Tag as ATag } from "ant-design-vue";

const props = defineProps<{
  state?: string;
}>();

const normalizedState = computed(() => props.state || "idle");
const color = computed(() => {
  if (normalizedState.value === "running" || normalizedState.value === "connected") {
    return "success";
  }
  if (normalizedState.value === "error") {
    return "error";
  }
  if (normalizedState.value === "connecting") {
    return "processing";
  }
  return "default";
});
</script>

<style scoped>
.status-pill {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
