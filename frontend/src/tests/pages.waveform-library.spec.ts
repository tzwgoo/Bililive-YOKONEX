import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import WaveformLibraryPage from "@/pages/WaveformLibraryPage.vue";
import * as bluetoothService from "@/services/bluetooth";

describe("WaveformLibraryPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    window.localStorage.clear();
  });

  it("renders waveform-only workspace without bluetooth rule editor", async () => {
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

    const wrapper = mount(WaveformLibraryPage);
    await flushPromises();

    expect(wrapper.text()).toContain("波形库");
    expect(wrapper.text()).toContain("波形编辑器");
    expect(wrapper.text()).not.toContain("礼物事件");
    expect(wrapper.text()).not.toContain("绑定波形");
    expect(wrapper.text()).not.toContain("蓝牙 Studio");
  });

  it("renders waveform card previews in the library list", async () => {
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
          steps: [{ duration_ms: 200, channel_a: 20, channel_b: 40 }],
        },
      ],
      rule_groups: [],
    });

    const wrapper = mount(WaveformLibraryPage);
    await flushPromises();

    expect(wrapper.find('[data-testid="waveform-preview-custom-wave-01"]').exists()).toBe(true);
  });

  it("confirms before switching away from an unsaved waveform draft", async () => {
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
          steps: [{ duration_ms: 200, channel_a: 20, channel_b: 40 }],
        },
        {
          id: "custom-wave-02",
          name: "自定义波形 02",
          builtin: false,
          editable: true,
          execution_mode: "fixed",
          loop_count: 1,
          steps: [{ duration_ms: 300, channel_a: 50, channel_b: 60 }],
        },
      ],
      rule_groups: [],
    });
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    const wrapper = mount(WaveformLibraryPage);
    await flushPromises();

    await wrapper.get('[data-testid="waveform-name-input"] input').setValue("尚未保存的波形名");
    await wrapper.findAll(".waveform-library .waveform-card")[1].trigger("click");
    await flushPromises();

    expect(confirmSpy).toHaveBeenCalledWith("当前波形还有未保存更改，是否放弃修改并切换？");
    expect((wrapper.get('[data-testid="waveform-name-input"] input').element as HTMLInputElement).value).toBe("尚未保存的波形名");
  });
});
