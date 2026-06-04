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
      path: "/bluetooth/studio",
      name: "bluetooth-studio",
      component: () => import("@/pages/BluetoothStudioPage.vue"),
    },
    {
      path: "/command/studio",
      name: "command-studio",
      component: () => import("@/pages/CommandStudioPage.vue"),
    },
  ],
});

export default router;
