import { getCurrentScope, onScopeDispose } from "vue";

export function usePolling(callback: () => Promise<void> | void, intervalMs: number) {
  let timer: number | null = null;

  const start = () => {
    if (timer !== null) {
      return;
    }
    timer = window.setInterval(() => {
      void callback();
    }, intervalMs);
  };

  const stop = () => {
    if (timer !== null) {
      window.clearInterval(timer);
      timer = null;
    }
  };

  if (getCurrentScope()) {
    onScopeDispose(stop);
  }

  return {
    start,
    stop,
  };
}
