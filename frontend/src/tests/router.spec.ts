import { RouterLinkStub, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import AppShell from "@/layouts/AppShell.vue";
import router from "@/router";

describe("router", () => {
  it("renders dashboard route at slash", () => {
    const result = router.resolve("/");

    expect(result.name).toBe("dashboard");
    expect(result.matched).toHaveLength(1);
  });

  it("renders sidebar links for dashboard, events and waveforms", () => {
    const wrapper = mount(AppShell, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
          RouterView: true,
        },
      },
    });

    expect(wrapper.text()).toContain("BiliLive YOKONEX");
    expect(wrapper.text()).toContain("主控台");
    expect(wrapper.text()).toContain("事件配置");
    expect(wrapper.text()).toContain("波形库");
  });

  it("registers new top-level routes", () => {
    expect(router.resolve("/events").name).toBe("events");
    expect(router.resolve("/waveforms").name).toBe("waveforms");
  });

  it("keeps legacy studio redirects registered", () => {
    const routes = router.getRoutes();
    const bluetoothStudioRoute = routes.find((route) => route.path === "/bluetooth/studio");
    const commandStudioRoute = routes.find((route) => route.path === "/command/studio");

    expect(bluetoothStudioRoute?.redirect).toBe("/waveforms");
    expect(commandStudioRoute?.redirect).toBe("/events");
  });
});
