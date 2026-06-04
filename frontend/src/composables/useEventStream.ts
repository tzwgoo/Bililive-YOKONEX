import { getCurrentScope, onScopeDispose, ref } from "vue";

export function useEventStream<TEvent extends Record<string, unknown>>(url: string, limit = 20) {
  const events = ref<TEvent[]>([]);
  const status = ref<"connecting" | "open" | "error">("connecting");
  const errorMessage = ref("");
  const source = new EventSource(url);

  source.onmessage = (event) => {
    status.value = "open";
    events.value.unshift(JSON.parse(event.data) as TEvent);
    if (events.value.length > limit) {
      events.value.splice(limit);
    }
  };

  source.onerror = () => {
    status.value = "error";
    errorMessage.value = "实时事件流连接异常";
  };

  const stop = () => {
    source.close();
  };

  if (getCurrentScope()) {
    onScopeDispose(stop);
  }

  return {
    events,
    status,
    errorMessage,
    stop,
  };
}
