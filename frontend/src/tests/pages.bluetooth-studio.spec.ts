import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import BluetoothStudioPage from "@/pages/BluetoothStudioPage.vue";
import * as bluetoothService from "@/services/bluetooth";

describe("BluetoothStudioPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders bluetooth studio and submits waveform plus rules updates", async () => {
    vi.spyOn(bluetoothService, "fetchBluetoothStatus").mockResolvedValue({
      connected: false,
      message: "未连接",
      devices: [],
      rules: [],
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
          steps: [
            { duration_ms: 200, channel_a: 20, channel_b: 40 },
          ],
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
    const updateWaveformSpy = vi.spyOn(bluetoothService, "updateBluetoothWaveform").mockResolvedValue({
      success: true,
      waveform: {
        id: "custom-wave-01",
        name: "重命名波形",
        builtin: false,
        editable: true,
        execution_mode: "fixed",
        loop_count: 1,
        steps: [{ duration_ms: 240, channel_a: 60, channel_b: 80 }],
      },
      waveforms: [
        {
          id: "custom-wave-01",
          name: "重命名波形",
          builtin: false,
          editable: true,
          execution_mode: "fixed",
          loop_count: 1,
          steps: [{ duration_ms: 240, channel_a: 60, channel_b: 80 }],
        },
      ],
    });
    const saveRulesSpy = vi.spyOn(bluetoothService, "saveBluetoothRules").mockResolvedValue({
      success: true,
      updated_count: 1,
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
              waveform_name: "重命名波形",
              filters: { min_price: 0, max_price: 99 },
            },
          ],
        },
      ],
    });

    const wrapper = mount(BluetoothStudioPage);
    await flushPromises();

    expect(wrapper.text()).toContain("蓝牙 Studio");
    expect(wrapper.text()).toContain("自定义波形 01");

    await wrapper.get('[data-testid="waveform-name"]').setValue("重命名波形");
    await wrapper.get('[data-testid="step-duration-0"]').setValue("240");
    await wrapper.get('[data-testid="step-channel-a-0"]').setValue("60");
    await wrapper.get('[data-testid="step-channel-b-0"]').setValue("80");
    await wrapper.get('[data-testid="save-waveform"]').trigger("click");

    expect(updateWaveformSpy).toHaveBeenCalledWith("custom-wave-01", {
      name: "重命名波形",
      steps: [{ duration_ms: 240, channel_a: 60, channel_b: 80 }],
    });

    await wrapper.get('[data-testid="rule-waveform-gift-tier-01"]').setValue("custom-wave-01");
    await wrapper.get('[data-testid="save-rules"]').trigger("click");

    expect(saveRulesSpy).toHaveBeenCalledWith({
      rules: [
        {
          id: "gift-tier-01",
          enabled: true,
          waveform_id: "custom-wave-01",
          min_price: 0,
          max_price: 99,
        },
      ],
    });
  });
});
