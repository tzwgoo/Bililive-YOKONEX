import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import EventStreamTabs from "@/components/shared/EventStreamTabs.vue";

describe("EventStreamTabs", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("restores the last active dashboard event tab from localStorage", async () => {
    window.localStorage.setItem("biliLive.dashboardTab", JSON.stringify("control"));

    const wrapper = mount(EventStreamTabs, {
      props: {
        storageKey: "biliLive.dashboardTab",
        tabs: [
          { key: "gift", label: "礼物事件", events: [{ id: "gift-1" }] },
          { key: "control", label: "控制日志", events: [{ id: "control-1" }] },
        ],
      },
    });

    expect((wrapper.vm as unknown as { activeKey: string }).activeKey).toBe("control");
  });

  it("persists the active dashboard event tab after switching", async () => {
    const wrapper = mount(EventStreamTabs, {
      props: {
        storageKey: "biliLive.dashboardTab",
        tabs: [
          { key: "gift", label: "礼物事件", events: [{ id: "gift-1" }] },
          { key: "control", label: "控制日志", events: [{ id: "control-1" }] },
        ],
      },
      attachTo: document.body,
    });

    await wrapper.findAll('[role="tab"]')[1].trigger("click");

    expect(window.localStorage.getItem("biliLive.dashboardTab")).toBe(JSON.stringify("control"));
  });
});
