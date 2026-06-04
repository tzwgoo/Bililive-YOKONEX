import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import WaveformEditorPanel from "@/components/waveforms/WaveformEditorPanel.vue";

const waveform = {
  id: "custom-wave-01",
  name: "自定义波形 01",
  builtin: false,
  editable: true,
  steps: [
    { duration_ms: 200, channel_a: 20, channel_b: 40 },
    { duration_ms: 400, channel_a: 60, channel_b: 80 },
  ],
};

describe("WaveformEditorPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders one continuous drag track with proportional segments and handles", () => {
    const wrapper = mount(WaveformEditorPanel, {
      props: {
        waveform,
        savingWaveform: false,
      },
    });

    expect(wrapper.find('[data-testid="waveform-drag-track"]').exists()).toBe(true);
    expect(wrapper.find(".waveform-preview").exists()).toBe(false);
    expect(wrapper.findAll(".timeline-segment")).toHaveLength(2);
    expect(wrapper.findAll(".timeline-segment")[0].attributes("style")).toContain("flex-grow: 200");
    expect(wrapper.findAll(".timeline-segment")[1].attributes("style")).toContain("flex-grow: 400");
    expect(wrapper.find('[data-testid="waveform-drag-surface-0"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="waveform-drag-surface-1"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="waveform-handle-channel-a-0"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="waveform-handle-channel-b-0"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="waveform-handle-duration-0"]').exists()).toBe(true);
  });

  it("emits channel strength updates while dragging a strength handle", async () => {
    const wrapper = mount(WaveformEditorPanel, {
      props: {
        waveform,
        savingWaveform: false,
      },
      attachTo: document.body,
    });

    const surface = wrapper.get('[data-testid="waveform-drag-surface-0"]').element as HTMLDivElement;
    vi.spyOn(surface, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      width: 120,
      height: 180,
      top: 0,
      left: 0,
      right: 120,
      bottom: 180,
      toJSON: () => ({}),
    });

    await wrapper.get('[data-testid="waveform-handle-channel-a-0"]').trigger("mousedown", {
      button: 0,
      clientX: 60,
      clientY: 160,
    });

    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 60, clientY: 30, bubbles: true }));
    window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));

    const updates = wrapper.emitted("update-step") || [];
    expect(updates.length).toBeGreaterThan(0);
    expect(updates[0]).toEqual([0, "channel_a", 150]);
  });

  it("emits duration updates while dragging a duration handle", async () => {
    const wrapper = mount(WaveformEditorPanel, {
      props: {
        waveform,
        savingWaveform: false,
      },
      attachTo: document.body,
    });

    const surface = wrapper.get('[data-testid="waveform-drag-surface-0"]').element as HTMLDivElement;
    vi.spyOn(surface, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      width: 120,
      height: 180,
      top: 0,
      left: 0,
      right: 120,
      bottom: 180,
      toJSON: () => ({}),
    });

    await wrapper.get('[data-testid="waveform-handle-duration-0"]').trigger("mousedown", {
      button: 0,
      clientX: 40,
      clientY: 180,
    });

    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 90, clientY: 180, bubbles: true }));
    window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));

    const updates = wrapper.emitted("update-step") || [];
    expect(updates.length).toBeGreaterThan(0);
    expect(updates[0]).toEqual([0, "duration_ms", 360]);
  });
});
