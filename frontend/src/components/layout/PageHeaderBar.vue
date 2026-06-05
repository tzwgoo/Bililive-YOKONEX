<template>
  <header class="page-header-bar">
    <div class="page-header-copy">
      <h1>{{ title }}</h1>
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>
