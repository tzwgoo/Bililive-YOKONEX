<template>
  <main class="dashboard-page">
    <ACard class="hero-card" :bordered="false">
      <div>
        <p class="hero-kicker">Bilibili Live Control Deck</p>
        <h1>直播互动监听控制台</h1>
        <p class="hero-subtitle">Vue + Ant Design Vue 迁移中的第一张业务页面，已接通状态轮询、实时事件流和主控操作。</p>
      </div>
      <StatusPill :state="sessionStore.status.status" />
    </ACard>

    <ARow :gutter="[18, 18]">
      <ACol :xs="24" :xl="16">
        <ACard title="直播监听" :bordered="false">
          <div class="form-grid">
            <label class="field">
              <span>监听模式</span>
              <Select v-model:value="sessionForm.mode" :options="sessionModeSelectOptions" />
            </label>
            <label class="field">
              <span>{{ sessionValueLabel }}</span>
              <Input
                data-testid="session-value-input"
                v-model:value="sessionForm.value"
                :placeholder="sessionValuePlaceholder"
              />
            </label>
            <label class="field">
              <span>连接方式</span>
              <Select v-model:value="sessionForm.connection_mode" :options="connectionModeOptions" />
            </label>
            <label class="field">
              <span>礼物触发模式</span>
              <Select v-model:value="sessionForm.trigger_mode" :options="triggerModeOptions" />
            </label>
            <label class="field">
              <span>点赞倍数</span>
              <InputNumber v-model:value="sessionForm.like_multiple" :min="1" :step="1" class="field-number" />
            </label>
            <label class="field">
              <span>弹幕触发</span>
              <Select v-model:value="danmakuEnabledValue" :options="danmakuEnabledOptions" />
            </label>
            <label class="field field-span-2">
              <span>弹幕关键词</span>
              <Input v-model:value="sessionForm.danmaku_keywords" placeholder="多个关键词用逗号分隔，例如 开火,冲冲冲" />
            </label>
            <label class="field">
              <span>弹幕冷却秒数</span>
              <InputNumber v-model:value="sessionForm.danmaku_cooldown_seconds" :min="0" :step="1" class="field-number" />
            </label>
            <label class="field">
              <span>每用户限流窗口</span>
              <InputNumber v-model:value="sessionForm.danmaku_user_limit_window_seconds" :min="0" :step="1" class="field-number" />
            </label>
            <label class="field">
              <span>窗口内最大触发次数</span>
              <InputNumber v-model:value="sessionForm.danmaku_user_limit_max_triggers" :min="0" :step="1" class="field-number" />
            </label>
            <label class="field">
              <span>最低舰队等级</span>
              <Select v-model:value="sessionForm.danmaku_min_guard_level" :options="guardLevelOptions" />
            </label>
          </div>
          <AAlert v-if="sessionMessage" class="section-alert" :message="sessionMessage" type="info" show-icon />
          <div class="button-row">
            <Button data-testid="start-session" type="primary" :loading="startingSession" @click="handleStartSession">启动监听</Button>
            <Button :disabled="startingSession" @click="handleStopSession">停止监听</Button>
          </div>
        </ACard>
      </ACol>

      <ACol :xs="24" :xl="8">
        <div class="sidebar-stack">
          <ACard title="连接方式" :bordered="false">
            <label class="field">
              <span>输出链路</span>
              <Select v-model:value="sessionForm.connection_mode" :options="connectionModeOptions" />
            </label>

            <template v-if="sessionForm.connection_mode === 'im'">
              <div class="section-head-inline">
                <h3>IM 指令连接</h3>
                <StatusPill :state="commandStore.status.status" />
              </div>
              <label class="field">
                <span>WS URL</span>
                <Input data-testid="command-ws-url" v-model:value="commandForm.ws_url" placeholder="ws://103.236.55.92:43001/" />
              </label>
              <label class="field">
                <span>UID</span>
                <Input data-testid="command-uid" v-model:value="commandForm.uid" placeholder="请输入下游服务 UID" />
              </label>
              <label class="field">
                <span>TOKEN</span>
                <InputPassword data-testid="command-token" v-model:value="commandForm.token" placeholder="请输入下游服务 TOKEN" />
              </label>
              <AAlert v-if="commandMessage" class="section-alert" :message="commandMessage" type="info" show-icon />
              <div class="button-row">
                <Button data-testid="connect-command" type="primary" :loading="connectingCommand" @click="handleConnectCommand">登录指令通道</Button>
                <Button :disabled="connectingCommand" @click="handleDisconnectCommand">退出指令通道</Button>
              </div>
            </template>

            <template v-else>
              <div class="section-head-inline">
                <h3>蓝牙连接</h3>
                <StatusPill :state="bluetoothStore.status.connected ? 'connected' : 'idle'" />
              </div>
              <AAlert v-if="bluetoothMessage" class="section-alert" :message="bluetoothMessage" type="info" show-icon />
              <div class="button-row">
                <Button type="primary" :loading="scanningBluetooth" @click="handleScanBluetooth">扫描设备</Button>
                <Button :disabled="scanningBluetooth" @click="handleDisconnectBluetooth">断开设备</Button>
              </div>
              <ACollapse class="bluetooth-collapse" :bordered="false">
                <ACollapsePanel key="devices" header="设备列表">
                  <AEmpty v-if="bluetoothStore.status.devices.length === 0" description="暂无设备" />
                  <AList v-else :data-source="bluetoothStore.status.devices">
                    <template #renderItem="{ item }">
                      <AListItem>
                        <div class="bluetooth-item-copy">
                          <strong>{{ item.name }}</strong>
                          <small>{{ item.protocol || "-" }} · RSSI {{ item.rssi }}</small>
                        </div>
                        <Button v-if="!item.connected" size="small" @click="handleConnectBluetooth(item.deviceId)">连接</Button>
                        <StatusPill v-else state="connected" />
                      </AListItem>
                    </template>
                  </AList>
                </ACollapsePanel>
                <ACollapsePanel key="rules" header="事件规则预览">
                  <AEmpty v-if="bluetoothStore.status.rules.length === 0" description="暂无规则" />
                  <AList v-else :data-source="bluetoothStore.status.rules">
                    <template #renderItem="{ item }">
                      <AListItem>
                        <div class="bluetooth-item-copy">
                          <strong>{{ item.ruleLabel }}</strong>
                          <small>{{ item.waveformName || item.waveformId || "-" }}</small>
                        </div>
                        <StatusPill :state="item.enabled ? 'running' : 'idle'" />
                      </AListItem>
                    </template>
                  </AList>
                </ACollapsePanel>
              </ACollapse>
            </template>
          </ACard>

          <RuntimeSnapshotCard
            :session="sessionStore.status"
            :command-status="commandStore.status.status"
            :bluetooth-status="bluetoothStore.status.connected ? 'connected' : 'idle'"
          />
        </div>
      </ACol>
    </ARow>

    <ACard class="event-section" title="事件流" :bordered="false">
      <AAlert
        v-if="eventErrorMessage"
        class="section-alert"
        :message="eventErrorMessage"
        type="warning"
        show-icon
      />
      <EventStreamTabs :tabs="eventTabs" />
    </ACard>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
  Alert as AAlert,
  Card as ACard,
  Col as ACol,
  Collapse as ACollapse,
  Empty as AEmpty,
  Input,
  InputNumber,
  List as AList,
  Row as ARow,
  Select,
  Button,
} from "ant-design-vue";
import RuntimeSnapshotCard from "@/components/dashboard/RuntimeSnapshotCard.vue";
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

const InputPassword = Input.Password;
const AListItem = AList.Item;
const ACollapsePanel = ACollapse.Panel;

const sessionStorage = useLocalDraft<SessionStartPayload>("biliLive.sessionDraft", {
  mode: "open_live",
  value: "",
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

const sessionModeSelectOptions = [
  { label: "官方 open-live", value: "open_live" },
  { label: "第三方房间消息流", value: "third_party" },
];
const connectionModeOptions = [
  { label: "IM 指令", value: "im" },
  { label: "蓝牙", value: "bluetooth" },
];
const triggerModeOptions = [
  { label: "按礼物数量触发", value: "by_quantity" },
  { label: "单次触发", value: "single" },
];
const danmakuEnabledOptions = [
  { label: "关闭", value: "false" },
  { label: "开启", value: "true" },
];
const guardLevelOptions = [
  { label: "不限", value: 0 },
  { label: "舰长及以上", value: 3 },
  { label: "提督及以上", value: 2 },
  { label: "总督", value: 1 },
];

const sessionValueLabel = computed(() => (sessionForm.mode === "third_party" ? "房间长 ID" : "主播身份码"));
const sessionValuePlaceholder = computed(() =>
  sessionForm.mode === "third_party" ? "请输入直播间房间长 ID room_id" : "请输入主播身份码 code",
);
const danmakuEnabledValue = computed({
  get: () => (sessionForm.danmaku_enabled ? "true" : "false"),
  set: (value: string) => {
    sessionForm.danmaku_enabled = value === "true";
  },
});

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
    value.output_mode = value.connection_mode;
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
      sessionForm.connection_mode = status.connectionMode;
      sessionForm.output_mode = status.connectionMode;
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
  try {
    await bluetoothStore.connectDevice(deviceId);
    bluetoothMessage.value = "蓝牙连接成功";
  } catch (error) {
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
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 24px 40px;
  display: grid;
  gap: 18px;
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.hero-kicker,
.hero-card h1 {
  margin: 0;
}

.hero-kicker {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #78716c;
  margin-bottom: 8px;
}

.hero-subtitle {
  margin: 8px 0 0;
  color: #57534e;
}

.sidebar-stack {
  display: grid;
  gap: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 16px;
}

.field {
  display: grid;
  gap: 8px;
  color: #44403c;
  font-size: 13px;
  font-weight: 600;
}

.field :deep(.ant-input),
.field :deep(.ant-input-number),
.field :deep(.ant-select-selector) {
  border-radius: 12px;
}

.field-number {
  width: 100%;
}

.field-span-2 {
  grid-column: span 2;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 18px;
}

.section-head-inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 18px 0 12px;
}

.section-head-inline h3 {
  margin: 0;
  font-size: 16px;
}

.section-alert {
  margin-top: 16px;
}

.bluetooth-collapse {
  margin-top: 16px;
}

.bluetooth-item-copy {
  display: grid;
  gap: 4px;
}

.bluetooth-item-copy small {
  color: #78716c;
}

.event-section :deep(.ant-card-body) {
  display: grid;
  gap: 16px;
}

@media (max-width: 900px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .field-span-2 {
    grid-column: span 1;
  }
}
</style>
