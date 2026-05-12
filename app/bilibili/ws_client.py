from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

import websockets

from app.bilibili.ws_protocol import (
    OP_AUTH,
    OP_HEARTBEAT,
    OP_SEND_SMS_REPLY,
    decode_packets,
    encode_packet,
    parse_event_message,
    parse_json_body,
)


LOGGER = logging.getLogger("bili_live.ws")


class BilibiliWsClient:
    def __init__(self) -> None:
        self._connection: websockets.WebSocketClientProtocol | None = None
        self._heartbeat_task: asyncio.Task | None = None

    async def connect_and_consume(
        self,
        *,
        wss_links: list[str],
        auth_body: str,
        on_event: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        last_error: Exception | None = None
        for link in wss_links:
            try:
                LOGGER.info("尝试连接官方长连: %s", link)
                await self._consume_single_link(link=link, auth_body=auth_body, on_event=on_event)
                return
            except Exception as exc:  # pragma: no cover - 网络错误在联调中验证
                last_error = exc
                LOGGER.warning("长连地址连接失败: %s", exc)
                await self.disconnect()
        if last_error is not None:
            raise last_error

    async def _consume_single_link(
        self,
        *,
        link: str,
        auth_body: str,
        on_event: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        try:
            async with websockets.connect(link) as websocket:
                self._connection = websocket
                LOGGER.info("官方长连连接成功")
                await websocket.send(encode_packet(operation=OP_AUTH, body=auth_body.encode("utf-8")))
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                async for raw_message in websocket:
                    if isinstance(raw_message, str):
                        raw_message = raw_message.encode("utf-8")
                    for packet in decode_packets(raw_message):
                        if packet.operation != OP_SEND_SMS_REPLY:
                            continue
                        message = parse_json_body(packet.body)
                        event = parse_event_message(message)
                        if event is None:
                            continue
                        await on_event(event.model_dump())
        finally:
            if self._heartbeat_task is not None:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            self._connection = None

    async def _heartbeat_loop(self) -> None:
        while self._connection is not None:
            await self._connection.send(encode_packet(operation=OP_HEARTBEAT))
            await asyncio.sleep(20)

    async def disconnect(self) -> None:
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            LOGGER.info("官方长连已断开")
