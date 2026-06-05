<template>
  <section class="panel-section">
    <div class="section-heading">
      <p class="section-kicker">Connections</p>
      <h2>连接与设备</h2>
    </div>

    <ARow :gutter="[16, 16]">
      <ACol :xs="24" :xl="12">
        <ACard title="IM 指令连接" :bordered="false">
          <div class="section-head-inline">
            <span class="status-text">{{ commandStatus.status || "idle" }}</span>
          </div>
          <div class="form-grid">
            <label class="field field-span-2">
              <span>WS URL</span>
              <Input data-testid="command-ws-url" v-model:value="commandForm.ws_url" placeholder="ws://127.0.0.1:43001/" />
            </label>
            <label class="field">
              <span>UID</span>
              <Input data-testid="command-uid" v-model:value="commandForm.uid" placeholder="请输入下游服务 UID" />
            </label>
            <label class="field">
              <span>TOKEN</span>
              <InputPassword data-testid="command-token" v-model:value="commandForm.token" placeholder="请输入下游服务 TOKEN" />
            </label>
          </div>
          <AAlert v-if="commandMessage" class="section-alert" :message="commandMessage" type="info" show-icon />
          <div class="button-row">
            <Button data-testid="connect-command" type="primary" :loading="connectingCommand" @click="$emit('connect-command')">登录指令通道</Button>
            <Button :disabled="connectingCommand" @click="$emit('disconnect-command')">退出指令通道</Button>
          </div>
        </ACard>
      </ACol>

      <ACol :xs="24" :xl="12">
        <ACard title="蓝牙设备" :bordered="false">
          <div class="section-head-inline">
            <span class="status-text">{{ bluetoothStatus.connected ? "connected" : "idle" }}</span>
          </div>
          <AAlert v-if="bluetoothMessage" class="section-alert no-top-margin" :message="bluetoothMessage" type="info" show-icon />
          <div class="button-row compact-row">
            <Button type="primary" :loading="scanningBluetooth" @click="$emit('scan-bluetooth')">扫描设备</Button>
            <Button :disabled="scanningBluetooth" @click="$emit('disconnect-bluetooth')">断开设备</Button>
            <Button
              data-testid="open-bluetooth-overlay-event"
              href="/bluetooth/overlay?style=event"
              target="_blank"
              rel="noopener noreferrer"
            >
              OBS 小窗 · 弹幕演出
            </Button>
            <Button
              data-testid="open-bluetooth-overlay-panel"
              href="/bluetooth/overlay?style=panel"
              target="_blank"
              rel="noopener noreferrer"
            >
              OBS 小窗 · 仪表盘
            </Button>
          </div>
          <ACollapse class="bluetooth-collapse" :bordered="false">
            <ACollapsePanel key="devices" header="设备列表">
              <AEmpty v-if="bluetoothStatus.devices.length === 0" description="暂无设备" />
              <AList v-else :data-source="bluetoothStatus.devices">
                <template #renderItem="{ item }">
                  <AListItem>
                    <div class="bluetooth-item-copy">
                      <strong>{{ item.name }}</strong>
                      <small>{{ item.protocol || "-" }} · RSSI {{ item.rssi }}</small>
                    </div>
                    <Button v-if="!item.connected" size="small" @click="$emit('connect-bluetooth', item.deviceId)">连接</Button>
                    <span v-else class="status-chip">已连接</span>
                  </AListItem>
                </template>
              </AList>
            </ACollapsePanel>
            <ACollapsePanel key="rules" header="蓝牙规则预览">
              <AEmpty v-if="bluetoothStatus.rules.length === 0" description="暂无规则" />
              <AList v-else :data-source="bluetoothStatus.rules">
                <template #renderItem="{ item }">
                  <AListItem>
                    <div class="bluetooth-item-copy">
                      <strong>{{ item.ruleLabel }}</strong>
                      <small>{{ item.waveformName || item.waveformId || "-" }}</small>
                    </div>
                    <span class="status-chip" :class="{ active: item.enabled }">
                      {{ item.enabled ? "已启用" : "未启用" }}
                    </span>
                  </AListItem>
                </template>
              </AList>
            </ACollapsePanel>
          </ACollapse>
        </ACard>
      </ACol>
    </ARow>
  </section>
</template>

<script setup lang="ts">
import {
  Alert as AAlert,
  Button,
  Card as ACard,
  Col as ACol,
  Collapse as ACollapse,
  Empty as AEmpty,
  Input,
  List as AList,
  Row as ARow,
} from "ant-design-vue";
import type { BluetoothStatusModel } from "@/types/bluetooth";
import type { CommandConnectPayload, CommandStatusModel } from "@/types/command";

defineProps<{
  commandForm: CommandConnectPayload;
  commandStatus: CommandStatusModel;
  bluetoothStatus: BluetoothStatusModel;
  commandMessage: string;
  bluetoothMessage: string;
  connectingCommand: boolean;
  scanningBluetooth: boolean;
}>();

defineEmits<{
  "connect-command": [];
  "disconnect-command": [];
  "scan-bluetooth": [];
  "disconnect-bluetooth": [];
  "connect-bluetooth": [deviceId: string];
}>();

const InputPassword = Input.Password;
const AListItem = AList.Item;
const ACollapsePanel = ACollapse.Panel;
</script>

<style scoped>
.panel-section {
  display: grid;
  gap: 16px;
}

.section-heading h2,
.section-kicker {
  margin: 0;
}

.section-kicker {
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #78716c;
}

.section-head-inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.status-text {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(120, 113, 108, 0.12);
  color: #57534e;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 16px;
  margin-top: 10px;
}

.field {
  display: grid;
  gap: 8px;
  color: #44403c;
  font-size: 13px;
  font-weight: 600;
}

.field :deep(.ant-input),
.field :deep(.ant-select-selector) {
  border-radius: 12px;
}

.field-span-2 {
  grid-column: span 2;
}

.section-alert {
  margin-top: 16px;
}

.section-alert.no-top-margin {
  margin-top: 12px;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 18px;
}

.compact-row {
  margin-top: 12px;
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

.status-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(120, 113, 108, 0.12);
  color: #57534e;
  font-size: 12px;
  font-weight: 700;
}

.status-chip.active {
  background: rgba(28, 25, 23, 0.92);
  border-color: #1c1917;
  color: #fafaf9;
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
