<template>
  <aside class="app-sidebar">
    <RouterLink class="brand" to="/">BiliLive YOKONEX</RouterLink>
    <p class="sidebar-kicker">Workspace</p>
    <nav class="app-menu" aria-label="主导航">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        class="app-menu-link"
        :to="item.to"
      >
        <span class="app-menu-title">{{ item.label }}</span>
        <small class="app-menu-caption">{{ item.caption }}</small>
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";

const navItems = [
  { to: "/", label: "主控台", caption: "运行状态与实时日志" },
  { to: "/events", label: "事件配置", caption: "IM 与蓝牙规则" },
  { to: "/waveforms", label: "波形库", caption: "波形资产与编辑" },
];
</script>
