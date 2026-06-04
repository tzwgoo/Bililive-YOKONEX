import { describe, expect, it, vi } from "vitest";
import { useEventStream } from "@/composables/useEventStream";

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  public onmessage: ((event: MessageEvent<string>) => void) | null = null;
  public onerror: (() => void) | null = null;
  public readonly url: string;
  public closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }
}

describe("useEventStream", () => {
  it("pushes incoming SSE events into reactive list", () => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);

    const { events } = useEventStream("/api/events/stream");
    const source = FakeEventSource.instances[0];

    source.onmessage?.({ data: JSON.stringify({ type: "gift", id: 1 }) } as MessageEvent<string>);

    expect(events.value).toHaveLength(1);
    expect(events.value[0]).toEqual({ type: "gift", id: 1 });
  });
});
