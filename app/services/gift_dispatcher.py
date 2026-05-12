from __future__ import annotations

import logging
from typing import Any

from app.command_gateway.mapping import GiftCommandMapper


LOGGER = logging.getLogger("bili_live.gift_dispatcher")


class GiftCommandDispatcher:
    def __init__(
        self,
        *,
        mapper: GiftCommandMapper,
        command_session: Any | None,
    ) -> None:
        self.mapper = mapper
        self.command_session = command_session

    @property
    def is_enabled(self) -> bool:
        return bool(self.command_session is not None and getattr(self.command_session, "is_connected", False))

    async def dispatch_gift_event(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = event.get("payload", {})
        command_id = self.mapper.resolve_command_id(payload)
        if not command_id:
            gift_name = payload.get("gift_name") or payload.get("gift_id") or "未知礼物"
            message = f"礼物 {gift_name} 未命中指令映射"
            LOGGER.info(message)
            return {
                "matched": False,
                "command_id": "",
                "success": False,
                "message": message,
            }

        if not self.is_enabled or self.command_session is None:
            LOGGER.warning("礼物已命中映射，但下游指令通道未登录 command_id=%s", command_id)
            return {
                "matched": True,
                "command_id": command_id,
                "success": False,
                "message": "下游指令通道未登录",
            }

        try:
            result = await self.command_session.send_command(command_id=command_id)
            success = bool(result.get("success"))
            message = result.get("message") or ("指令发送成功" if success else "指令发送失败")
            if success:
                LOGGER.info("礼物指令发送成功 command_id=%s", command_id)
            else:
                LOGGER.warning("礼物指令发送失败 command_id=%s message=%s", command_id, message)
            return {
                "matched": True,
                "command_id": command_id,
                "success": success,
                "message": message,
            }
        except Exception as exc:  # pragma: no cover - 真实网络路径
            message = f"指令发送失败: {exc}"
            LOGGER.exception("礼物指令发送异常 command_id=%s", command_id)
            return {
                "matched": True,
                "command_id": command_id,
                "success": False,
                "message": message,
            }
