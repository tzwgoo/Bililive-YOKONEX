import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardPage from "@/pages/DashboardPage.vue";
import * as sessionService from "@/services/session";
import * as commandService from "@/services/command";
import * as bluetoothService from "@/services/bluetooth";

describe("DashboardPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    window.localStorage.clear();
    vi.stubGlobal(
      "EventSource",
      class {
        onmessage: ((event: MessageEvent<string>) => void) | null = null;
        onerror: (() => void) | null = null;

        constructor(public readonly url: string) {}

        close() {}
      },
    );
  });

  it("renders dashboard route content and runtime snapshot", async () => {
    vi.spyOn(sessionService, "fetchSessionStatus").mockResolvedValue({
      status: "running",
      room_id: 123,
      anchor_name: "主播A",
      connection_mode: "im",
    });
    vi.spyOn(commandService, "fetchCommandStatus").mockResolvedValue({
      status: "connected",
    });
    vi.spyOn(bluetoothService, "fetchBluetoothStatus").mockResolvedValue({
      connected: false,
    });

    const wrapper = mount(DashboardPage);
    await flushPromises();

    expect(wrapper.text()).toContain("直播互动监听控制台");
    expect(wrapper.text()).toContain("状态总览");
    expect(wrapper.text()).toContain("监听主参数");
    expect(wrapper.text()).toContain("蓝牙设备");
    expect(wrapper.text()).toContain("实时日志");
    expect(wrapper.text()).toContain("123");
    expect(wrapper.text()).toContain("主播A");
  });

  it("submits session start payload from dashboard form", async () => {
    vi.spyOn(sessionService, "fetchSessionStatus").mockResolvedValue({
      status: "idle",
      can_start: true,
      can_stop: false,
    });
    vi.spyOn(commandService, "fetchCommandStatus").mockResolvedValue({
      status: "idle",
      can_connect: true,
      can_disconnect: false,
    });
    vi.spyOn(bluetoothService, "fetchBluetoothStatus").mockResolvedValue({
      connected: false,
    });
    const startSessionSpy = vi.spyOn(sessionService, "startSession").mockResolvedValue({ success: true });

    const wrapper = mount(DashboardPage);
    await flushPromises();

    await wrapper.get('[data-testid="session-value-input"]').setValue("主播身份码123");
    await wrapper.get('[data-testid="start-session"]').trigger("click");

    expect(startSessionSpy).toHaveBeenCalledWith({
      mode: "open_live",
      value: "主播身份码123",
      connection_mode: "im",
      output_mode: "im",
      trigger_mode: "by_quantity",
      like_multiple: 100,
      danmaku_enabled: false,
      danmaku_keywords: "",
      danmaku_cooldown_seconds: 0,
      danmaku_user_limit_window_seconds: 0,
      danmaku_user_limit_max_triggers: 0,
      danmaku_min_guard_level: 0,
    });
  });

  it("submits command connect payload from dashboard form", async () => {
    vi.spyOn(sessionService, "fetchSessionStatus").mockResolvedValue({
      status: "idle",
      can_start: true,
      can_stop: false,
    });
    vi.spyOn(commandService, "fetchCommandStatus").mockResolvedValue({
      status: "idle",
      can_connect: true,
      can_disconnect: false,
    });
    vi.spyOn(bluetoothService, "fetchBluetoothStatus").mockResolvedValue({
      connected: false,
    });
    const connectCommandSpy = vi.spyOn(commandService, "connectCommand").mockResolvedValue({ success: true });

    const wrapper = mount(DashboardPage);
    await flushPromises();

    await wrapper.get('[data-testid="command-ws-url"]').setValue("ws://127.0.0.1:43001");
    await wrapper.get('[data-testid="command-uid"]').setValue("uid-001");
    await wrapper.get('[data-testid="command-token"]').setValue("token-001");
    await wrapper.get('[data-testid="connect-command"]').trigger("click");

    expect(connectCommandSpy).toHaveBeenCalledWith({
      ws_url: "ws://127.0.0.1:43001",
      uid: "uid-001",
      token: "token-001",
    });
  });
});
