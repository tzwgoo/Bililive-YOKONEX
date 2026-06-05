import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import EventConfigPage from "@/pages/EventConfigPage.vue";
import * as commandService from "@/services/command";
import * as bluetoothService from "@/services/bluetooth";

describe("EventConfigPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    window.localStorage.clear();
  });

  it("renders IM and bluetooth tabs with IM rules loaded by default", async () => {
    vi.spyOn(commandService, "fetchCommandStudio").mockResolvedValue({
      rules: [
        {
          id: "gift-rule-1",
          enabled: true,
          event_type: "gift",
          min_price: 100,
          max_price: 500,
          command_slot: "command_one",
        },
      ],
      like_command_id: "like_trigger",
      danmaku_command_ids: {
        danmaku: "danmaku_trigger",
      },
      command_slots: ["command_one", "command_two"],
      event_types: [{ value: "gift", label: "礼物" }],
      danmaku_event_types: [{ value: "danmaku", label: "普通弹幕", guard_level: 0 }],
    });
    vi.spyOn(bluetoothService, "fetchBluetoothStudio").mockResolvedValue({
      waveforms: [
        {
          id: "custom-wave-01",
          name: "自定义波形 01",
          builtin: false,
          editable: true,
          execution_mode: "fixed",
          loop_count: 1,
          steps: [{ duration_ms: 200, channel_a: 20, channel_b: 40 }],
        },
      ],
      rule_groups: [
        {
          group_id: "gift",
          group_label: "礼物事件",
          rules: [
            {
              id: "gift-tier-01",
              event_type: "gift",
              rule_label: "礼物档位 01 · 0-99",
              enabled: true,
              waveform_id: "custom-wave-01",
              waveform_name: "自定义波形 01",
              filters: { min_price: 0, max_price: 99 },
            },
          ],
        },
        {
          group_id: "super_chat",
          group_label: "醒目留言",
          rules: [
            {
              id: "super-chat-tier-01",
              event_type: "super_chat",
              rule_label: "醒目留言档位 01 · 30-49",
              enabled: true,
              waveform_id: "custom-wave-01",
              waveform_name: "自定义波形 01",
              filters: { min_price: 30, max_price: 49 },
            },
          ],
        },
      ],
    });

    const wrapper = mount(EventConfigPage);
    await flushPromises();

    expect(wrapper.text()).toContain("事件配置");
    expect(wrapper.text()).toContain("IM");
    expect(wrapper.text()).toContain("蓝牙");
    expect(wrapper.text()).toContain("固定点赞指令 ID");
    expect(wrapper.text()).toContain("礼物");
    expect(wrapper.findComponent({ name: "PageHeaderBar" }).exists()).toBe(false);
    expect(wrapper.get('[data-testid="workspace-summary-card"]').text()).toContain("事件配置");
    expect(wrapper.get('[data-testid="workspace-summary-card"]').text()).toContain("保存 IM 规则");

    await wrapper.get('[data-testid="event-tab-bluetooth"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("蓝牙事件规则");
    expect(wrapper.text()).toContain("醒目留言档位 01 · 30-49");
    expect(wrapper.text()).toContain("最低价格");
    expect(wrapper.text()).toContain("最高价格");
  });

  it("restores the last active event-config tab from localStorage", async () => {
    window.localStorage.setItem("biliLive.eventConfigTab", JSON.stringify("bluetooth"));

    vi.spyOn(commandService, "fetchCommandStudio").mockResolvedValue({
      rules: [],
      like_command_id: "like_trigger",
      danmaku_command_ids: {
        danmaku: "danmaku_trigger",
      },
      command_slots: ["command_one"],
      event_types: [{ value: "gift", label: "礼物" }],
      danmaku_event_types: [{ value: "danmaku", label: "普通弹幕", guard_level: 0 }],
    });
    vi.spyOn(bluetoothService, "fetchBluetoothStudio").mockResolvedValue({
      waveforms: [
        {
          id: "custom-wave-01",
          name: "自定义波形 01",
          builtin: false,
          editable: true,
          execution_mode: "fixed",
          loop_count: 1,
          steps: [{ duration_ms: 200, channel_a: 20, channel_b: 40 }],
        },
      ],
      rule_groups: [
        {
          group_id: "gift",
          group_label: "礼物事件",
          rules: [
            {
              id: "gift-tier-01",
              event_type: "gift",
              rule_label: "礼物档位 01 · 0-99",
              enabled: true,
              waveform_id: "custom-wave-01",
              waveform_name: "自定义波形 01",
              filters: { min_price: 0, max_price: 99 },
            },
          ],
        },
      ],
    });

    const wrapper = mount(EventConfigPage);
    await flushPromises();

    expect(wrapper.text()).toContain("蓝牙事件规则");
    expect(wrapper.text()).not.toContain("固定点赞指令 ID");
  });
});
