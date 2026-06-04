<template>
  <header class="page-header-bar">
    <div class="page-header-copy">
      <p v-if="kicker" class="page-header-kicker">{{ kicker }}</p>
      <h1>{{ title }}</h1>
      <p v-if="description" class="page-header-description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
  kicker?: string;
}>();
</script>
