from __future__ import annotations

import asyncio
from collections import deque
from typing import Any


class EventHub:
    def __init__(self, max_events: int = 200) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._subscribers: set[asyncio.Queue] = set()

    def publish(self, event: dict[str, Any]) -> None:
        self._events.append(event)
        for queue in tuple(self._subscribers):
            queue.put_nowait(event)

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self._events)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)
