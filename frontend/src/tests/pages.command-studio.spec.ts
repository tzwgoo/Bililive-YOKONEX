import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CommandStudioPage from "@/pages/CommandStudioPage.vue";
import * as commandService from "@/services/command";

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
      danmaku_command_ids: {
        danmaku: "danmaku_trigger",
      },
      command_slots: ["command_one", "command_two"],
      event_types: [{ value: "gift", label: "礼物" }],
      danmaku_event_types: [{ value: "danmaku", label: "普通弹幕", guard_level: 0 }],
    });

    const wrapper = mount(CommandStudioPage);
    await flushPromises();

    expect(fetchStudioSpy).toHaveBeenCalled();
    expect(wrapper.text()).toContain("IM 规则中心");
    expect(wrapper.text()).toContain("固定点赞指令 ID");

    await wrapper.get('input[type="number"]').setValue("200");
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
