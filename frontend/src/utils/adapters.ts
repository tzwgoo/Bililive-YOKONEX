import type {
  BluetoothDeviceModel,
  BluetoothRuleModel,
  BluetoothStatusModel,
  BluetoothStatusResponse,
} from "@/types/bluetooth";
import type { CommandStatusModel, CommandStatusResponse } from "@/types/command";
import type { SessionStatusModel, SessionStatusResponse } from "@/types/session";

export function adaptSessionStatus(payload: SessionStatusResponse): SessionStatusModel {
  return {
    status: payload.status || "idle",
    roomId: String(payload.room_id || "-"),
    message: payload.message || "",
    anchorName: payload.anchor_name || "",
    lastEventAt: Number(payload.last_event_at || 0),
    canStart: Boolean(payload.can_start),
    canStop: Boolean(payload.can_stop),
    mode: payload.mode || "third_party",
    douyinWsBaseUrl: payload.douyin_ws_base_url || "ws://127.0.0.1:1088",
    douyinExecutablePath: payload.douyin_executable_path || "",
    douyinCookieConfigured: Boolean(payload.douyin_cookie_configured),
    connectionMode: payload.connection_mode || payload.output_mode || "im",
    triggerMode: payload.trigger_mode || "by_quantity",
    likeMultiple: Number(payload.like_multiple || 100),
    danmakuEnabled: Boolean(payload.danmaku_enabled),
    danmakuKeywords: payload.danmaku_keywords || "",
    danmakuCooldownSeconds: Number(payload.danmaku_cooldown_seconds || 0),
    danmakuUserLimitWindowSeconds: Number(payload.danmaku_user_limit_window_seconds || 0),
    danmakuUserLimitMaxTriggers: Number(payload.danmaku_user_limit_max_triggers || 0),
    danmakuMinGuardLevel: Number(payload.danmaku_min_guard_level || 0),
  };
}

export function adaptCommandStatus(payload: CommandStatusResponse): CommandStatusModel {
  return {
    status: payload.status || "idle",
    message: payload.message || "",
    uid: payload.uid || "",
    userId: payload.user_id || "",
    lastLoginAt: Number(payload.last_login_at || 0),
    canConnect: Boolean(payload.can_connect ?? true),
    canDisconnect: Boolean(payload.can_disconnect),
  };
}

function adaptBluetoothDevice(payload: BluetoothStatusResponse["devices"][number]): BluetoothDeviceModel {
  return {
    deviceId: payload?.device_id || "",
    name: payload?.name || "未命名设备",
    deviceType: payload?.device_type || "",
    protocol: payload?.protocol || "",
    rssi: Number(payload?.rssi || 0),
    connected: Boolean(payload?.connected),
  };
}

function adaptBluetoothRule(payload: BluetoothStatusResponse["rules"][number]): BluetoothRuleModel {
  return {
    id: payload?.id || "",
    enabled: Boolean(payload?.enabled),
    waveformId: payload?.waveform_id || "",
    waveformName: payload?.waveform_name || "",
    ruleLabel: payload?.rule_label || payload?.event_label || payload?.event_type || "未命名规则",
    eventType: payload?.event_type || "",
  };
}

export function adaptBluetoothStatus(payload: BluetoothStatusResponse): BluetoothStatusModel {
  return {
    connected: Boolean(payload.connected),
    message: payload.message || "",
    devices: Array.isArray(payload.devices) ? payload.devices.map((item) => adaptBluetoothDevice(item)) : [],
    rules: Array.isArray(payload.rules) ? payload.rules.map((item) => adaptBluetoothRule(item)) : [],
  };
}
