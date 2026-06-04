<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink class="brand" to="/">BiliLive YOKONEX</RouterLink>
      <nav class="app-nav">
        <RouterLink class="app-nav-link" to="/">主控台</RouterLink>
        <RouterLink class="app-nav-link" to="/bluetooth/studio">蓝牙 Studio</RouterLink>
        <RouterLink class="app-nav-link" to="/command/studio">IM 规则</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";
</script>
