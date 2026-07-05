<template>
  <main class="dashboard-page">
    <PageHeaderBar title="直播互动监听控制台">
      <template #actions>
        <StatusPill :state="sessionStore.status.status" />
      </template>
    </PageHeaderBar>

    <StatusSummaryGrid
      :session="sessionStore.status"
      :command-status="commandStore.status"
      :bluetooth-status="bluetoothStore.status"
    />

    <SessionControlPanel
      :session-form="sessionForm"
      :starting-session="startingSession"
      :message="sessionMessage"
      @start="handleStartSession"
      @stop="handleStopSession"
    />

    <ConnectionAndDevicesPanel
      :command-form="commandForm"
      :command-status="commandStore.status"
      :bluetooth-status="bluetoothStore.status"
      :command-message="commandMessage"
      :bluetooth-message="bluetoothMessage"
      :connecting-command="connectingCommand"
      :scanning-bluetooth="scanningBluetooth"
      @connect-command="handleConnectCommand"
      @disconnect-command="handleDisconnectCommand"
      @scan-bluetooth="handleScanBluetooth"
      @disconnect-bluetooth="handleDisconnectBluetooth"
      @connect-bluetooth="handleConnectBluetooth"
    />

    <RuntimeSnapshotCard
      :session="sessionStore.status"
      :command-status="commandStore.status.status"
      :bluetooth-status="bluetoothStore.status.connected ? 'connected' : 'idle'"
    />

    <ACard class="event-section" title="实时日志" :bordered="false">
      <AAlert
        v-if="eventErrorMessage"
        class="section-alert"
        :message="eventErrorMessage"
        type="warning"
        show-icon
      />
      <EventStreamTabs :tabs="eventTabs" storage-key="biliLive.dashboardTab" />
    </ACard>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
  Alert as AAlert,
  Card as ACard,
} from "ant-design-vue";
import ConnectionAndDevicesPanel from "@/components/dashboard/ConnectionAndDevicesPanel.vue";
import SessionControlPanel from "@/components/dashboard/SessionControlPanel.vue";
import StatusSummaryGrid from "@/components/dashboard/StatusSummaryGrid.vue";
import RuntimeSnapshotCard from "@/components/dashboard/RuntimeSnapshotCard.vue";
import PageHeaderBar from "@/components/layout/PageHeaderBar.vue";
import EventStreamTabs from "@/components/shared/EventStreamTabs.vue";
import StatusPill from "@/components/shared/StatusPill.vue";
import { useEventStream } from "@/composables/useEventStream";
import { useLocalDraft } from "@/composables/useLocalDraft";
import { usePolling } from "@/composables/usePolling";
import { useBluetoothStore } from "@/stores/bluetooth";
import { useCommandStore } from "@/stores/command";
import { useSessionStore } from "@/stores/session";
import type { CommandConnectPayload } from "@/types/command";
import type { SessionStartPayload } from "@/types/session";

const sessionStore = useSessionStore();
const commandStore = useCommandStore();
const bluetoothStore = useBluetoothStore();

const sessionStorage = useLocalDraft<SessionStartPayload>("biliLive.sessionDraft", {
  mode: "third_party",
  value: "",
  douyin_ws_base_url: "ws://127.0.0.1:1088",
  trigger_mode: "by_quantity",
  like_multiple: 100,
  danmaku_enabled: false,
  danmaku_keywords: "",
  danmaku_cooldown_seconds: 0,
  danmaku_user_limit_window_seconds: 0,
  danmaku_user_limit_max_triggers: 0,
  danmaku_min_guard_level: 0,
});
const commandStorage = useLocalDraft<CommandConnectPayload>("biliLive.commandDraft", {
  ws_url: "",
  uid: "",
  token: "",
});

const sessionForm = reactive(sessionStorage.load());
const commandForm = reactive(commandStorage.load());

const startingSession = ref(false);
const connectingCommand = ref(false);
const scanningBluetooth = ref(false);
const sessionMessage = ref("等待启动");
const commandMessage = ref("未登录");
const bluetoothMessage = ref("未连接");

const liveEventStream = useEventStream<Record<string, unknown>>("/api/events/stream");
const controlEventStream = useEventStream<Record<string, unknown>>("/api/control/stream");

const eventTabs = computed(() => [
  { key: "gift", label: "礼物事件", events: filterEventsByType(["gift"]) },
  { key: "danmaku", label: "弹幕事件", events: filterEventsByType(["danmaku", "danmaku_captain", "danmaku_commander", "danmaku_governor"]) },
  { key: "like", label: "点赞事件", events: filterEventsByType(["like"]) },
  { key: "interact", label: "互动事件", events: filterEventsByType(["interact"]) },
  { key: "control", label: "控制日志", events: controlEventStream.events.value },
]);
const eventErrorMessage = computed(() => liveEventStream.errorMessage.value || controlEventStream.errorMessage.value);

watch(
  sessionForm,
  (value) => {
    sessionStorage.save({ ...value });
  },
  { deep: true },
);
watch(
  commandForm,
  (value) => {
    commandStorage.save({ ...value });
  },
  { deep: true },
);
watch(
  () => sessionStore.status,
  (status) => {
    sessionMessage.value = status.message || (status.canStop ? "监听运行中" : "等待启动");
    if (status.canStop) {
      sessionForm.mode = status.mode;
      sessionForm.douyin_ws_base_url = status.douyinWsBaseUrl;
      sessionForm.trigger_mode = status.triggerMode;
      sessionForm.like_multiple = status.likeMultiple;
      sessionForm.danmaku_enabled = status.danmakuEnabled;
      sessionForm.danmaku_keywords = status.danmakuKeywords;
      sessionForm.danmaku_cooldown_seconds = status.danmakuCooldownSeconds;
      sessionForm.danmaku_user_limit_window_seconds = status.danmakuUserLimitWindowSeconds;
      sessionForm.danmaku_user_limit_max_triggers = status.danmakuUserLimitMaxTriggers;
      sessionForm.danmaku_min_guard_level = status.danmakuMinGuardLevel;
    }
  },
  { deep: true },
);
watch(
  () => commandStore.status,
  (status) => {
    commandMessage.value = status.message || (status.canDisconnect ? "已连接" : "未登录");
    if (!commandForm.uid && status.uid) {
      commandForm.uid = status.uid;
    }
  },
  { deep: true },
);
watch(
  () => bluetoothStore.status,
  (status) => {
    bluetoothMessage.value = status.message || (status.connected ? "蓝牙已连接" : "未连接");
  },
  { deep: true },
);

function filterEventsByType(types: string[]) {
  return liveEventStream.events.value.filter((event) => types.includes(String(event.event_type || "")));
}

async function refreshDashboard() {
  await Promise.all([sessionStore.fetchStatus(), commandStore.fetchStatus(), bluetoothStore.fetchStatus()]);
}

const polling = usePolling(refreshDashboard, 5000);

function openBluetoothOverlayWindow(style: "event" | "panel" = "panel") {
  return window.open(
    `/bluetooth/overlay?style=${style}`,
    "biliLiveBluetoothOverlay",
    "popup=yes,width=1080,height=260,resizable=yes,scrollbars=no",
  );
}

async function handleStartSession() {
  startingSession.value = true;
  try {
    await sessionStore.startSession({
      ...sessionForm,
      value: sessionForm.value.trim(),
      like_multiple: Number(sessionForm.like_multiple || 100),
      danmaku_cooldown_seconds: Number(sessionForm.danmaku_cooldown_seconds || 0),
      danmaku_user_limit_window_seconds: Number(sessionForm.danmaku_user_limit_window_seconds || 0),
      danmaku_user_limit_max_triggers: Number(sessionForm.danmaku_user_limit_max_triggers || 0),
      danmaku_min_guard_level: Number(sessionForm.danmaku_min_guard_level || 0),
    });
    sessionMessage.value = "监听已启动";
  } catch (error) {
    sessionMessage.value = error instanceof Error ? error.message : "监听启动失败";
  } finally {
    startingSession.value = false;
  }
}

async function handleStopSession() {
  startingSession.value = true;
  try {
    await sessionStore.stopSession();
    sessionMessage.value = "监听已停止";
  } catch (error) {
    sessionMessage.value = error instanceof Error ? error.message : "监听停止失败";
  } finally {
    startingSession.value = false;
  }
}

async function handleConnectCommand() {
  connectingCommand.value = true;
  try {
    await commandStore.connectCommand({
      ws_url: commandForm.ws_url.trim(),
      uid: commandForm.uid.trim(),
      token: commandForm.token,
    });
    commandMessage.value = "指令通道登录成功";
  } catch (error) {
    commandMessage.value = error instanceof Error ? error.message : "指令通道登录失败";
  } finally {
    connectingCommand.value = false;
  }
}

async function handleDisconnectCommand() {
  connectingCommand.value = true;
  try {
    await commandStore.disconnectCommand();
    commandMessage.value = "指令通道已退出";
  } catch (error) {
    commandMessage.value = error instanceof Error ? error.message : "退出指令通道失败";
  } finally {
    connectingCommand.value = false;
  }
}

async function handleScanBluetooth() {
  scanningBluetooth.value = true;
  try {
    await bluetoothStore.scanDevices();
    bluetoothMessage.value = "蓝牙扫描完成";
  } catch (error) {
    bluetoothMessage.value = error instanceof Error ? error.message : "蓝牙扫描失败";
  } finally {
    scanningBluetooth.value = false;
  }
}

async function handleConnectBluetooth(deviceId: string) {
  scanningBluetooth.value = true;
  // 连接蓝牙时优先打开仪表盘样式，避免再弹出已经下线的旧演出小窗。
  const overlayWindow = openBluetoothOverlayWindow("panel");
  try {
    await bluetoothStore.connectDevice(deviceId);
    if (overlayWindow && !overlayWindow.closed) {
      overlayWindow.location.replace("/bluetooth/overlay?style=panel");
      overlayWindow.focus();
    }
    bluetoothMessage.value = "蓝牙连接成功";
  } catch (error) {
    if (overlayWindow && !overlayWindow.closed) {
      overlayWindow.close();
    }
    bluetoothMessage.value = error instanceof Error ? error.message : "蓝牙连接失败";
  } finally {
    scanningBluetooth.value = false;
  }
}

async function handleDisconnectBluetooth() {
  scanningBluetooth.value = true;
  try {
    await bluetoothStore.disconnectDevice();
    bluetoothMessage.value = "蓝牙已断开";
  } catch (error) {
    bluetoothMessage.value = error instanceof Error ? error.message : "蓝牙断开失败";
  } finally {
    scanningBluetooth.value = false;
  }
}

onMounted(async () => {
  await refreshDashboard();
  polling.start();
});
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 18px;
  padding: 24px 28px 40px;
}

.event-section :deep(.ant-card-body) {
  display: grid;
  gap: 16px;
}

@media (max-width: 900px) {
  .dashboard-page {
    padding: 18px 16px 32px;
  }
}
</style>
