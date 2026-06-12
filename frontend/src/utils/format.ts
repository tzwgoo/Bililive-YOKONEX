export function formatTimestamp(value?: number | null): string {
  if (!value) {
    return "-";
  }
  return new Date(value * 1000).toLocaleString("zh-CN", { hour12: false });
}

const statusLabelMap: Record<string, string> = {
  idle: "空闲",
  running: "运行中",
  connected: "已连接",
  disconnected: "未连接",
  connecting: "连接中",
  error: "异常",
  success: "成功",
};

const modeLabelMap: Record<string, string> = {
  im: "IM 指令",
  bluetooth: "蓝牙",
  third_party: "第三方消息流",
};

export function formatStatusLabel(value?: string | null): string {
  if (!value) {
    return "-";
  }
  return statusLabelMap[value] || value;
}

export function formatModeLabel(value?: string | null): string {
  if (!value) {
    return "-";
  }
  return modeLabelMap[value] || value;
}
