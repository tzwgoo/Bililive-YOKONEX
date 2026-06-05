import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import WaveformListPanel from "@/components/waveforms/WaveformListPanel.vue";

describe("WaveformListPanel", () => {
  it("uses an explicit preview drawing height so bar percentages render correctly", () => {
    const wrapper = mount(WaveformListPanel, {
      props: {
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
              { duration_ms: 400, channel_a: 100, channel_b: 60 },
            ],
          },
        ],
        selectedWaveformId: "custom-wave-01",
      },
      attachTo: document.body,
    });

    const previewBars = wrapper.get(".waveform-preview-bars").element as HTMLElement;
    const previewBarStyles = wrapper.findAll(".waveform-preview-bar").map((item) => item.attributes("style"));

    expect(getComputedStyle(previewBars).height).toBe("52px");
    expect(previewBarStyles[0]).toContain("height: 10px;");
    expect(previewBarStyles[1]).toContain("height: 21px;");
    expect(previewBarStyles[2]).toContain("height: 52px;");
    expect(previewBarStyles[3]).toContain("height: 31px;");
  });

  it("keeps the library panel at a fixed desktop height and scrolls inside the list container", () => {
    const wrapper = mount(WaveformListPanel, {
      props: {
        waveforms: Array.from({ length: 12 }, (_, index) => ({
          id: `custom-wave-${index + 1}`,
          name: `自定义波形 ${index + 1}`,
          builtin: false,
          editable: true,
          execution_mode: "fixed",
          loop_count: 1,
          steps: [{ duration_ms: 200, channel_a: 20 + index, channel_b: 40 + index }],
        })),
        selectedWaveformId: "custom-wave-1",
      },
      attachTo: document.body,
    });

    const panel = wrapper.get(".waveform-library-panel");
    const scrollContainer = wrapper.get('[data-testid="waveform-library-scroll"]').element as HTMLElement;

    expect(panel.attributes("style")).toContain("height:");
    expect(getComputedStyle(scrollContainer).overflowY).toBe("auto");
  });

  it("does not render waveform cards with ant button container classes that clip card height", () => {
    const wrapper = mount(WaveformListPanel, {
      props: {
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
        selectedWaveformId: "custom-wave-01",
      },
    });

    expect(wrapper.get(".waveform-card").classes()).not.toContain("ant-btn");
  });

  it("renders waveform cards as generic button-role containers instead of native button elements", () => {
    const wrapper = mount(WaveformListPanel, {
      props: {
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
        selectedWaveformId: "custom-wave-01",
      },
    });

    const card = wrapper.get(".waveform-card");
    expect(card.element.tagName).toBe("DIV");
    expect(card.attributes("role")).toBe("button");
  });

  it("does not hide overflow on waveform cards so preview content can determine card height", () => {
    const wrapper = mount(WaveformListPanel, {
      props: {
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
        selectedWaveformId: "custom-wave-01",
      },
      attachTo: document.body,
    });

    expect(getComputedStyle(wrapper.get(".waveform-card").element as HTMLElement).overflow).not.toBe("hidden");
  });
});
