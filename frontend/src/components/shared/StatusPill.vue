<template>
  <ATag class="status-pill" :color="color">{{ normalizedState }}</ATag>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Tag as ATag } from "ant-design-vue";
import { formatStatusLabel } from "@/utils/format";

const props = defineProps<{
  state?: string;
}>();

const rawState = computed(() => props.state || "idle");
const normalizedState = computed(() => formatStatusLabel(rawState.value));
const color = computed(() => {
  if (rawState.value === "running" || rawState.value === "connected") {
    return "success";
  }
  if (rawState.value === "error") {
    return "error";
  }
  if (rawState.value === "connecting") {
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
  text-transform: none;
}
</style>
