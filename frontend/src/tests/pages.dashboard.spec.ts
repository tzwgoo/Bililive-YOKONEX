import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardPage from "@/pages/DashboardPage.vue";
import PageHeaderBar from "@/components/layout/PageHeaderBar.vue";
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
    expect(wrapper.text()).toContain("运行中");
    expect(wrapper.text()).toContain("IM 指令");
    expect(wrapper.text()).toContain("已连接");
    expect(wrapper.text()).toContain("空闲");
    expect(wrapper.text()).not.toContain("礼物 / 点赞触发");
    expect(wrapper.text()).not.toContain("弹幕关键词触发");
    expect(wrapper.text()).not.toContain("集中查看当前运行状态、保留高频监听参数和连接操作，并在首页持续查看实时日志。");
    expect(wrapper.getComponent(PageHeaderBar).props("kicker")).toBeUndefined();
    expect(wrapper.getComponent(PageHeaderBar).props("description")).toBeUndefined();
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

    await wrapper.get('[data-testid="session-value-input"]').setValue("123456");
    await wrapper.get('[data-testid="start-session"]').trigger("click");

    expect(startSessionSpy).toHaveBeenCalledWith({
      mode: "third_party",
      value: "123456",
      douyin_ws_base_url: "ws://127.0.0.1:1088",
      douyin_executable_path: "",
      douyin_cookie: "",
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

  it("renders dashboard session source selector", async () => {
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

    const wrapper = mount(DashboardPage);
    await flushPromises();

    expect(wrapper.text()).toContain("监听来源");
    expect(wrapper.text()).toContain("B 站第三方流");
    expect(wrapper.text()).toContain("房间号 ID");
    expect(wrapper.text()).not.toContain("主播身份码");
  });

  it("renders only the panel overlay entry on dashboard", async () => {
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
      devices: [],
      rules: [],
    });

    const wrapper = mount(DashboardPage);
    await flushPromises();

    const panelOverlayLink = wrapper.get('[data-testid="open-bluetooth-overlay-panel"]');
    expect(panelOverlayLink.attributes("href")).toBe("/bluetooth/overlay?style=panel");
    expect(panelOverlayLink.attributes("target")).toBe("_blank");
    expect(panelOverlayLink.text()).toContain("仪表盘");
    expect(wrapper.find('[data-testid="open-bluetooth-overlay-event"]').exists()).toBe(false);
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

  it("opens bluetooth overlay window before connecting a device", async () => {
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
      devices: [
        {
          device_id: "device-01",
          name: "Pulse Device",
          protocol: "BLE",
          rssi: -55,
          connected: false,
        },
      ],
      rules: [],
    });
    const connectBluetoothSpy = vi.spyOn(bluetoothService, "connectBluetoothDevice").mockResolvedValue({ success: true });
    const overlayWindow = {
      closed: false,
      focus: vi.fn(),
      close: vi.fn(),
      location: {
        replace: vi.fn(),
      },
    };
    const openSpy = vi.spyOn(window, "open").mockReturnValue(overlayWindow as unknown as Window);

    const wrapper = mount(DashboardPage);
    await flushPromises();

    await wrapper.get(".bluetooth-collapse .ant-collapse-header").trigger("click");
    await flushPromises();
    await wrapper.get(".bluetooth-collapse .ant-list-item button").trigger("click");
    await flushPromises();

    expect(openSpy).toHaveBeenCalledWith(
      "/bluetooth/overlay?style=panel",
      "biliLiveBluetoothOverlay",
      "popup=yes,width=1080,height=260,resizable=yes,scrollbars=no",
    );
    expect(connectBluetoothSpy).toHaveBeenCalledWith("device-01");
    expect(overlayWindow.location.replace).toHaveBeenCalledWith("/bluetooth/overlay?style=panel");
    expect(overlayWindow.focus).toHaveBeenCalled();
  });
});
