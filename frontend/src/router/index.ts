import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "dashboard",
      component: () => import("@/pages/DashboardPage.vue"),
    },
    {
      path: "/events",
      name: "events",
      component: () => import("@/pages/EventConfigPage.vue"),
    },
    {
      path: "/waveforms",
      name: "waveforms",
      component: () => import("@/pages/WaveformLibraryPage.vue"),
    },
    {
      path: "/bluetooth/studio",
      redirect: "/waveforms",
    },
    {
      path: "/command/studio",
      redirect: "/events",
    },
  ],
});

export default router;
