<template>
  <div class="app-shell">
    <AppSidebarMenu />
    <section class="app-main">
      <RouterView />
    </section>
  </div>
</template>

<script setup lang="ts">
import AppSidebarMenu from "@/components/layout/AppSidebarMenu.vue";
import { RouterView } from "vue-router";
</script>
