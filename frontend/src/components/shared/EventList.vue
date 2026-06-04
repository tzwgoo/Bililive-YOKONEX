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

function resolveTimestamp(event: EventRecord) {
  return formatTimestamp(Number(event.timestamp || 0));
}

function resolveTitle(event: EventRecord) {
  const eventType = String(event.event_type || event.type || "event");
  const uname = String(event.uname || "");
  if (uname) {
    return `${uname} · ${eventType}`;
  }
  return eventType;
}

function resolveDescription(event: EventRecord) {
  const payload = (event.payload || {}) as Record<string, unknown>;
  return String(
    payload.msg
      || payload.message
      || payload.gift_name
      || payload.interact_label
      || payload.like_text
      || JSON.stringify(event),
  );
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
</style>
