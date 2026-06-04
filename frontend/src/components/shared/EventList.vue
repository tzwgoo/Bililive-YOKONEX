<template>
  <AEmpty v-if="events.length === 0" description="暂无事件" />
  <AList v-else class="event-list" :data-source="events" item-layout="vertical">
    <template #renderItem="{ item }">
      <AListItem class="event-item">
        <div class="event-item-head">
          <strong>{{ resolveTitle(item) }}</strong>
          <small>{{ resolveTimestamp(item) }}</small>
        </div>
        <p class="event-item-text">{{ resolveDescription(item) }}</p>
        <small v-if="resolveMeta(item)" class="event-item-meta">{{ resolveMeta(item) }}</small>
      </AListItem>
    </template>
  </AList>
</template>

<script setup lang="ts">
import { Empty as AEmpty, List as AList } from "ant-design-vue";
import { formatTimestamp } from "@/utils/format";

defineProps<{
  events: Array<Record<string, unknown>>;
}>();

type EventRecord = Record<string, unknown>;
const AListItem = AList.Item;
const eventTypeLabels: Record<string, string> = {
  gift: "礼物事件",
  like: "点赞事件",
  interact: "互动事件",
  danmaku: "普通弹幕",
  danmaku_captain: "舰长弹幕",
  danmaku_commander: "提督弹幕",
  danmaku_governor: "总督弹幕",
  command_send: "IM 指令",
  command_connect: "IM 登录",
  command_disconnect: "IM 断开",
  bluetooth_trigger: "蓝牙触发",
};
const danmakuGuardLabels: Record<number, string> = {
  1: "总督",
  2: "提督",
  3: "舰长",
};

function resolveTimestamp(event: EventRecord) {
  return formatTimestamp(Number(event.timestamp || 0));
}

function resolveTitle(event: EventRecord) {
  const eventType = String(event.event_type || event.type || "event");
  const translatedEventType = eventTypeLabels[eventType] || eventType;
  const uname = String(event.uname || "");
  if (uname) {
    return `${uname} · ${translatedEventType}`;
  }
  return translatedEventType;
}

function resolveDescription(event: EventRecord) {
  const payload = (event.payload || {}) as Record<string, unknown>;
  const eventType = String(event.event_type || event.type || "event");
  if (eventType === "gift") {
    return `${String(payload.gift_name || "礼物")} x ${Number(payload.gift_num || 0) || 0}`;
  }
  if (eventType === "like") {
    return `${String(payload.like_text || "点赞")} (${Number(payload.like_count || 0) || 0})`;
  }
  if (eventType === "interact") {
    return String(payload.interact_label || "互动");
  }
  if (eventType === "danmaku" || eventType === "danmaku_captain" || eventType === "danmaku_commander" || eventType === "danmaku_governor") {
    return String(payload.msg || payload.message || "");
  }
  return String(
    payload.msg
      || payload.message
      || payload.gift_name
      || payload.interact_label
      || payload.like_text
      || JSON.stringify(event),
  );
}

function resolveMeta(event: EventRecord) {
  const payload = (event.payload || {}) as Record<string, unknown>;
  const eventType = String(event.event_type || event.type || "event");
  if (eventType === "danmaku" || eventType === "danmaku_captain" || eventType === "danmaku_commander" || eventType === "danmaku_governor") {
    const directLabel = String(payload.guard_label || "").trim();
    if (directLabel) {
      return directLabel;
    }
    const guardLevel = Math.max(0, Number(payload.guard_level || 0) || 0);
    return danmakuGuardLabels[guardLevel] || "";
  }
  if (eventType !== "gift") {
    return "";
  }
  const giftNum = Number(payload.gift_num || 0) || 0;
  const unitPrice = Number(payload.price || 0) || 0;
  const totalPrice = Number(payload.r_price || 0) || 0;
  if (giftNum > 1 && unitPrice > 0 && totalPrice > 0) {
    return `单价 ${unitPrice} · 总价值 ${totalPrice}`;
  }
  if (unitPrice > 0) {
    return `价值 ${unitPrice}`;
  }
  if (totalPrice > 0) {
    return `价值 ${totalPrice}`;
  }
  return "价值 0";
}
</script>

<style scoped>
.event-item {
  padding: 8px 0;
}

.event-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.event-item-text {
  margin: 0;
  color: #57534e;
  word-break: break-word;
}

.event-item-meta {
  color: #78716c;
}
</style>
