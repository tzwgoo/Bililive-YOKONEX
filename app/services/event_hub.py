from __future__ import annotations

import asyncio
from collections import deque
from typing import Any


class EventHub:
    def __init__(self, max_events: int = 200) -> None:
        # 直播事件缓冲，用于首页礼物、弹幕、点赞事件回放。
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        # 直播事件订阅者集合，用于向 SSE 客户端推送新事件。
        self._subscribers: set[asyncio.Queue] = set()
        # 控制日志缓冲，用于记录 IM 指令和蓝牙波形触发结果。
        self._control_events: deque[dict[str, Any]] = deque(maxlen=max_events)
        # 控制日志订阅者集合，用于独立推送执行结果。
        self._control_subscribers: set[asyncio.Queue] = set()

    def publish(self, event: dict[str, Any]) -> None:
        """发布一条直播事件并推送给订阅者。"""
        self._events.append(event)
        for queue in tuple(self._subscribers):
            queue.put_nowait(event)

    def snapshot(self) -> list[dict[str, Any]]:
        """返回当前直播事件快照。"""
        return list(self._events)

    def subscribe(self) -> asyncio.Queue:
        """订阅直播事件 SSE 队列。"""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """取消直播事件 SSE 队列订阅。"""
        self._subscribers.discard(queue)

    def publish_control(self, event: dict[str, Any]) -> None:
        """发布一条控制日志并推送给订阅者。"""
        self._control_events.append(event)
        for queue in tuple(self._control_subscribers):
            queue.put_nowait(event)

    def control_snapshot(self) -> list[dict[str, Any]]:
        """返回当前控制日志快照。"""
        return list(self._control_events)

    def subscribe_control(self) -> asyncio.Queue:
        """订阅控制日志 SSE 队列。"""
        queue: asyncio.Queue = asyncio.Queue()
        self._control_subscribers.add(queue)
        return queue

    def unsubscribe_control(self, queue: asyncio.Queue) -> None:
        """取消控制日志 SSE 队列订阅。"""
        self._control_subscribers.discard(queue)
