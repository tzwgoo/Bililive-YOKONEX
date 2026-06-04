import { RouterLinkStub, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import AppShell from "@/layouts/AppShell.vue";
import router from "@/router";

describe("router", () => {
  afterEach(async () => {
    await router.push("/");
  });

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

    expect(wrapper.text()).toContain("主控台");
    expect(wrapper.text()).toContain("事件配置");
    expect(wrapper.text()).toContain("波形库");
  });

  it("registers new top-level routes", () => {
    expect(router.resolve("/events").name).toBe("events");
    expect(router.resolve("/waveforms").name).toBe("waveforms");
  });

  it("redirects legacy studio routes", async () => {
    await router.push("/bluetooth/studio");
    expect(router.currentRoute.value.fullPath).toBe("/waveforms");

    await router.push("/command/studio");
    expect(router.currentRoute.value.fullPath).toBe("/events");
  });
});
