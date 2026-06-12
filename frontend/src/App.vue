<template>
  <AConfigProvider :theme="themeConfig">
    <AppShell />
  </AConfigProvider>
</template>

<script setup lang="ts">
import { ConfigProvider as AConfigProvider } from "ant-design-vue";
import AppShell from "@/layouts/AppShell.vue";

// 黑粉主题统一覆盖 Ant Design 的主色和基础圆角，避免组件残留默认蓝色。
const themeConfig = {
  token: {
    colorPrimary: "#d98aa8",
    colorInfo: "#d98aa8",
    colorSuccess: "#e3a0bb",
    colorWarning: "#efb3c8",
    colorError: "#d9879f",
    borderRadius: 16,
    colorLink: "#d98aa8",
  },
};
</script>
