<template>
  <ACard class="snapshot-card" :bordered="false">
    <div class="snapshot-head">
      <div>
        <p class="snapshot-kicker">Runtime Snapshot</p>
        <h2>运行状态</h2>
      </div>
      <StatusPill :state="session.status" />
    </div>
    <ADescriptions :column="2" size="small" bordered>
      <ADescriptionsItem label="房间号">{{ session.roomId }}</ADescriptionsItem>
      <ADescriptionsItem label="主播昵称">{{ session.anchorName || "-" }}</ADescriptionsItem>
      <ADescriptionsItem label="连接方式">{{ session.connectionMode }}</ADescriptionsItem>
      <ADescriptionsItem label="IM 状态">{{ commandStatus }}</ADescriptionsItem>
      <ADescriptionsItem label="蓝牙状态">{{ bluetoothStatus }}</ADescriptionsItem>
      <ADescriptionsItem label="最近事件">{{ formatTimestamp(session.lastEventAt) }}</ADescriptionsItem>
    </ADescriptions>
  </ACard>
</template>

<script setup lang="ts">
import { Card as ACard, Descriptions as ADescriptions } from "ant-design-vue";
import StatusPill from "@/components/shared/StatusPill.vue";
import type { SessionStatusModel } from "@/types/session";
import { formatTimestamp } from "@/utils/format";

defineProps<{
  session: SessionStatusModel;
  commandStatus: string;
  bluetoothStatus: string;
}>();

const ADescriptionsItem = ADescriptions.Item;
</script>

<style scoped>
.snapshot-card {
  display: grid;
  gap: 16px;
}

.snapshot-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.snapshot-head h2,
.snapshot-kicker {
  margin: 0;
}

.snapshot-kicker {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #78716c;
}
</style>
