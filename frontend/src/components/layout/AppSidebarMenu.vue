<template>
  <aside class="app-sidebar">
    <RouterLink class="brand" to="/">BiliLive YOKONEX</RouterLink>
    <nav class="app-menu" aria-label="主导航">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        class="app-menu-link"
        :to="item.to"
      >
        <span class="app-menu-title">{{ item.label }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";

const navItems = [
  { to: "/", label: "主控台" },
  { to: "/events", label: "事件配置" },
  { to: "/waveforms", label: "波形库" },
];
</script>
