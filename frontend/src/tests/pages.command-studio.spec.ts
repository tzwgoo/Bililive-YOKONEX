import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CommandStudioPage from "@/pages/CommandStudioPage.vue";
import * as commandService from "@/services/command";
import * as bluetoothService from "@/services/bluetooth";

describe("CommandStudioPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders command studio and saves edited rules", async () => {
    const fetchStudioSpy = vi.spyOn(commandService, "fetchCommandStudio").mockResolvedValue({
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
    const saveStudioSpy = vi.spyOn(commandService, "saveCommandStudio").mockResolvedValue({
      rules: [],
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
      waveforms: [],
      rule_groups: [],
    });

    const wrapper = mount(CommandStudioPage);
    await flushPromises();

    expect(fetchStudioSpy).toHaveBeenCalled();
    expect(wrapper.text()).toContain("事件配置");
    expect(wrapper.text()).toContain("IM");
    expect(wrapper.text()).toContain("固定点赞指令 ID");
    expect(wrapper.text()).toContain("固定互动指令 ID");

    await wrapper.get('[data-testid="command-min-price-gift-rule-1"] input').setValue("200");
    await wrapper.get('[data-testid="command-save"]').trigger("click");

    expect(saveStudioSpy).toHaveBeenCalledWith({
      rules: [
        {
          id: "gift-rule-1",
          enabled: true,
          event_type: "gift",
          min_price: 200,
          max_price: 500,
          command_slot: "command_one",
        },
      ],
      like_rules: [],
      danmaku_slot_rules: [],
    });
  });
});
