<template>
  <aside class="app-sidebar">
    <RouterLink class="brand" to="/" aria-label="返回主控台首页">
      <img class="brand-mark" :src="brandMarkUrl" alt="BiliLive YOKONEX logo" />
      <div class="brand-copy">
        <p class="sidebar-kicker">BILIBILI LIVE SIGNAL</p>
        <strong class="brand-name">BiliLive YOKONEX</strong>
        <span class="brand-tagline">直播互动控制台</span>
      </div>
    </RouterLink>
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
import brandMarkUrl from "@/assets/logo-bilibili-mark.svg";
import { RouterLink } from "vue-router";

// 侧边栏只保留核心工作区入口，保证直播运行时切换路径足够直接。
const navItems = [
  { to: "/", label: "主控台" },
  { to: "/events", label: "事件配置" },
  { to: "/waveforms", label: "波形库" },
];
</script>
