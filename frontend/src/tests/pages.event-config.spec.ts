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

  it("renders shared, IM and bluetooth event configuration views", async () => {
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
      interact_command_id: "interact_trigger",
      danmaku_command_ids: {
        danmaku: "danmaku_trigger",
      },
      command_slots: ["command_one", "command_two"],
      event_types: [{ value: "gift", label: "礼物" }],
      danmaku_event_types: [{ value: "danmaku", label: "普通弹幕", guard_level: 0 }],
    });
    vi.spyOn(bluetoothService, "fetchBluetoothStudio").mockResolvedValue({
      ems_waveforms: [
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
      toy_waveforms: [],
      rule_groups: [
        {
          group_id: "gift",
          group_label: "礼物事件",
          rules: [
            {
              id: "gift-tier-01",
              event_type: "gift",
              rule_label: "礼物档位 01 / 0-99",
              enabled: true,
              waveform_id: "custom-wave-01",
              toy_waveform_id: "",
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
              rule_label: "醒目留言档位 01 / 30-49",
              enabled: true,
              waveform_id: "custom-wave-01",
              toy_waveform_id: "",
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
    expect(wrapper.text()).toContain("通用");
    expect(wrapper.text()).toContain("IM");
    expect(wrapper.text()).toContain("蓝牙");
    expect(wrapper.find('[data-testid="event-tab-douyin"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="workspace-summary-card"]').text()).toContain("事件配置");
    expect(wrapper.get('[data-testid="save-shared-config"]').text()).toContain("保存通用配置");
    expect(wrapper.get('[data-testid="event-item-like"]').text()).toContain("点赞触发");
    expect(wrapper.get('[data-testid="event-item-danmaku"]').text()).toContain("弹幕触发");

    await wrapper.get('[data-testid="event-tab-im"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-testid="command-save"]').text()).toContain("保存 IM 规则");
    expect(wrapper.text()).toContain("固定点赞指令 ID");
    expect(wrapper.get('[data-testid="event-item-gift"]').text()).toContain("礼物");

    await wrapper.get('[data-testid="event-tab-bluetooth"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("礼物事件");
    expect(wrapper.text()).toContain("最低价格");
    expect(wrapper.text()).toContain("最高价格");
    expect(wrapper.get('[data-testid="event-item-super_chat"]').text()).toContain("醒目留言");

    await wrapper.get('[data-testid="event-tab-douyin"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-testid="save-douyin-config"]').text()).toContain("保存抖音配置");
    expect(wrapper.get('[data-testid="event-item-connection"]').text()).toContain("连接服务");
    expect(wrapper.text()).toContain("WebcastChatMessage");
  });

  it("restores the last active event-config tab from localStorage", async () => {
    window.localStorage.setItem("biliLive.eventConfigTab", JSON.stringify("bluetooth"));

    vi.spyOn(commandService, "fetchCommandStudio").mockResolvedValue({
      rules: [],
      like_command_id: "like_trigger",
      interact_command_id: "interact_trigger",
      danmaku_command_ids: {
        danmaku: "danmaku_trigger",
      },
      command_slots: ["command_one"],
      event_types: [{ value: "gift", label: "礼物" }],
      danmaku_event_types: [{ value: "danmaku", label: "普通弹幕", guard_level: 0 }],
    });
    vi.spyOn(bluetoothService, "fetchBluetoothStudio").mockResolvedValue({
      ems_waveforms: [
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
      toy_waveforms: [],
      rule_groups: [
        {
          group_id: "gift",
          group_label: "礼物事件",
          rules: [
            {
              id: "gift-tier-01",
              event_type: "gift",
              rule_label: "礼物档位 01 / 0-99",
              enabled: true,
              waveform_id: "custom-wave-01",
              toy_waveform_id: "",
              waveform_name: "自定义波形 01",
              filters: { min_price: 0, max_price: 99 },
            },
          ],
        },
      ],
    });

    const wrapper = mount(EventConfigPage);
    await flushPromises();

    expect(wrapper.text()).toContain("礼物事件");
    expect(wrapper.text()).not.toContain("固定点赞指令 ID");
  });

  it("saves shared event settings back to the session draft", async () => {
    vi.spyOn(commandService, "fetchCommandStudio").mockResolvedValue({
      rules: [],
      like_command_id: "like_trigger",
      interact_command_id: "interact_trigger",
      danmaku_command_ids: {},
      command_slots: ["command_one"],
      event_types: [],
      danmaku_event_types: [],
    });
    vi.spyOn(bluetoothService, "fetchBluetoothStudio").mockResolvedValue({
      ems_waveforms: [],
      toy_waveforms: [],
      rule_groups: [],
    });

    const wrapper = mount(EventConfigPage);
    await flushPromises();

    await wrapper.get('[data-testid="event-item-danmaku"]').trigger("click");
    const danmakuSwitch = wrapper.get(".ant-switch");
    await danmakuSwitch.trigger("click");
    await wrapper.get('[data-testid="save-shared-config"]').trigger("click");

    expect(JSON.parse(window.localStorage.getItem("biliLive.sessionDraft") || "{}")).toMatchObject({
      mode: "third_party",
      douyin_ws_base_url: "ws://127.0.0.1:1088",
      danmaku_enabled: true,
    });
    expect(wrapper.text()).toContain("通用事件配置已保存");
  });

  it("saves douyin settings back to the session draft", async () => {
    vi.spyOn(commandService, "fetchCommandStudio").mockResolvedValue({
      rules: [],
      like_command_id: "like_trigger",
      interact_command_id: "interact_trigger",
      danmaku_command_ids: {},
      command_slots: ["command_one"],
      event_types: [],
      danmaku_event_types: [],
    });
    vi.spyOn(bluetoothService, "fetchBluetoothStudio").mockResolvedValue({
      ems_waveforms: [],
      toy_waveforms: [],
      rule_groups: [],
    });

    const wrapper = mount(EventConfigPage);
    await flushPromises();

    await wrapper.get('[data-testid="event-tab-douyin"]').trigger("click");
    await wrapper.get('[data-testid="douyin-ws-base-url"]').setValue("ws://127.0.0.1:1088");
    await wrapper.get('[data-testid="douyin-room-id"]').setValue("516466932480");
    await wrapper.get('[data-testid="douyin-executable-path"]').setValue("D:\\tools\\douyinLive\\douyinLive.exe");
    await wrapper.get('[data-testid="save-douyin-config"]').trigger("click");

    expect(JSON.parse(window.localStorage.getItem("biliLive.sessionDraft") || "{}")).toMatchObject({
      mode: "douyin",
      value: "516466932480",
      douyin_ws_base_url: "ws://127.0.0.1:1088",
      douyin_executable_path: "D:\\tools\\douyinLive\\douyinLive.exe",
    });
    expect(wrapper.text()).toContain("抖音配置已保存");
  });
});
