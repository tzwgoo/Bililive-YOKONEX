<template>
  <section class="summary-section">
    <div class="section-heading">
      <p class="section-kicker">Overview</p>
      <h2>状态总览</h2>
    </div>
    <div class="summary-grid">
      <article
        v-for="item in summaryItems"
        :key="item.label"
        class="summary-card"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { BluetoothStatusModel } from "@/types/bluetooth";
import type { CommandStatusModel } from "@/types/command";
import type { SessionStatusModel } from "@/types/session";
import { formatModeLabel, formatStatusLabel, formatTimestamp } from "@/utils/format";

const props = defineProps<{
  session: SessionStatusModel;
  commandStatus: CommandStatusModel;
  bluetoothStatus: BluetoothStatusModel;
}>();

const summaryItems = computed(() => [
  { label: "监听状态", value: formatStatusLabel(props.session.status) },
  { label: "输出方式", value: formatModeLabel(props.session.connectionMode) },
  { label: "IM 状态", value: formatStatusLabel(props.commandStatus.status) },
  { label: "蓝牙状态", value: formatStatusLabel(props.bluetoothStatus.connected ? "connected" : "idle") },
  { label: "当前房间", value: props.session.roomId || "-" },
  { label: "主播昵称", value: props.session.anchorName || "-" },
  { label: "最近事件", value: formatTimestamp(props.session.lastEventAt) },
]);
</script>

<style scoped>
.summary-section {
  display: grid;
  gap: 14px;
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 241, 235, 0.98));
  border: 1px solid rgba(120, 113, 108, 0.12);
  box-shadow: 0 14px 28px rgba(28, 25, 23, 0.04);
}

.summary-card span {
  color: #78716c;
  font-size: 12px;
  font-weight: 600;
}

.summary-card strong {
  font-size: 16px;
  line-height: 1.2;
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
