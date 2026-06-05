import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
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

  it("renders one continuous drag track with proportional segments and draggable bars", () => {
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
    expect(wrapper.find('[data-testid="waveform-bar-channel-a-0"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="waveform-bar-channel-b-0"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="waveform-handle-channel-a-0"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="waveform-handle-channel-b-0"]').exists()).toBe(false);
    expect(wrapper.findAll(".timeline-axis-label").map((item) => item.text())).toEqual(["A", "B", "A", "B"]);
    expect(wrapper.find('[data-testid="waveform-handle-duration-0"]').exists()).toBe(true);
  });

  it("emits channel strength updates while dragging a waveform bar", async () => {
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

    await wrapper.get('[data-testid="waveform-bar-channel-a-0"]').trigger("mousedown", {
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

  it("collapses the step list by default and toggles it on demand", async () => {
    const wrapper = mount(WaveformEditorPanel, {
      props: {
        waveform,
        savingWaveform: false,
      },
    });

    expect(wrapper.find('[data-testid="step-list"]').exists()).toBe(false);

    await wrapper.get('[data-testid="toggle-step-list"]').trigger("click");
    expect(wrapper.find('[data-testid="step-list"]').exists()).toBe(true);

    await wrapper.get('[data-testid="toggle-step-list"]').trigger("click");
    expect(wrapper.find('[data-testid="step-list"]').exists()).toBe(false);
  });

  it("marks the active segment and renders a guide line while dragging", async () => {
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

    await wrapper.get('[data-testid="waveform-bar-channel-a-0"]').trigger("mousedown", {
      button: 0,
      clientX: 60,
      clientY: 160,
    });

    expect(wrapper.get('[data-testid="timeline-segment-0"]').classes()).toContain("is-active");
    expect(wrapper.find('[data-testid="timeline-guide-line-0"]').exists()).toBe(true);

    window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  });

  it("shows live numeric labels on handles while dragging", async () => {
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
    await nextTick();

    expect(wrapper.get('[data-testid="waveform-handle-duration-0"]').text()).toContain("360 ms");

    window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  });

  it("keeps the editor panel at a fixed desktop height and scrolls inside the content area", () => {
    const wrapper = mount(WaveformEditorPanel, {
      props: {
        waveform: {
          ...waveform,
          steps: Array.from({ length: 8 }, (_, index) => ({
            duration_ms: 160 + index * 20,
            channel_a: 20 + index * 10,
            channel_b: 30 + index * 10,
          })),
        },
        savingWaveform: false,
      },
      attachTo: document.body,
    });

    const panel = wrapper.get(".waveform-editor-panel");
    const scrollContainer = wrapper.get('[data-testid="waveform-editor-scroll"]').element as HTMLElement;

    expect(panel.attributes("style")).toContain("height:");
    expect(scrollContainer.style.overflowY).toBe("auto");
  });
});
