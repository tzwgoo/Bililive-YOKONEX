export interface LiveEvent {
  [key: string]: unknown;
}

export interface UseEventStreamResult<TEvent> {
  events: { value: TEvent[] };
  status: { value: "connecting" | "open" | "error" };
  errorMessage: { value: string };
  stop: () => void;
}
