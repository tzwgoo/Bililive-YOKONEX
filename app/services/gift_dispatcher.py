from __future__ import annotations

import logging
from typing import Any

from app.command_gateway.mapping import GiftCommandMapper


LOGGER = logging.getLogger("bili_live.gift_dispatcher")

TRIGGER_MODE_SINGLE = "single"
TRIGGER_MODE_BY_QUANTITY = "by_quantity"
ALLOWED_TRIGGER_MODES = {
    TRIGGER_MODE_SINGLE,
    TRIGGER_MODE_BY_QUANTITY,
}


def normalize_trigger_mode(trigger_mode: str | None) -> str:
    normalized = str(trigger_mode or TRIGGER_MODE_BY_QUANTITY).strip()
    if normalized not in ALLOWED_TRIGGER_MODES:
        raise ValueError("不支持的触发模式")
    return normalized


class GiftCommandDispatcher:
    def __init__(
        self,
        *,
        mapper: GiftCommandMapper,
        command_session: Any | None,
        trigger_mode: str = TRIGGER_MODE_BY_QUANTITY,
    ) -> None:
        self.mapper = mapper
        self.command_session = command_session
        self.trigger_mode = normalize_trigger_mode(trigger_mode)

    @property
    def is_enabled(self) -> bool:
        return bool(self.command_session is not None and getattr(self.command_session, "is_connected", False))

    def set_trigger_mode(self, trigger_mode: str) -> None:
        self.trigger_mode = normalize_trigger_mode(trigger_mode)

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
                "trigger_count": 0,
                "sent_count": 0,
            }

        trigger_count = self._resolve_trigger_count(payload)
        if not self.is_enabled or self.command_session is None:
            LOGGER.warning("礼物已命中映射，但下游指令通道未登录 command_id=%s", command_id)
            return {
                "matched": True,
                "command_id": command_id,
                "success": False,
                "message": "下游指令通道未登录",
                "trigger_count": trigger_count,
                "sent_count": 0,
            }

        try:
            result: dict[str, Any] = {}
            success = True
            message = "指令发送成功"
            sent_count = 0
            for _ in range(trigger_count):
                result = await self.command_session.send_command(command_id=command_id)
                sent_count += 1
                success = bool(result.get("success"))
                message = result.get("message") or ("指令发送成功" if success else "指令发送失败")
                if not success:
                    break
            if success:
                LOGGER.info("礼物指令发送成功 command_id=%s trigger_count=%s", command_id, trigger_count)
            else:
                LOGGER.warning("礼物指令发送失败 command_id=%s message=%s", command_id, message)
            return {
                "matched": True,
                "command_id": command_id,
                "success": success,
                "message": message,
                "trigger_count": trigger_count,
                "sent_count": sent_count,
            }
        except Exception as exc:  # pragma: no cover - 真实网络路径
            message = f"指令发送失败: {exc}"
            LOGGER.exception("礼物指令发送异常 command_id=%s", command_id)
            return {
                "matched": True,
                "command_id": command_id,
                "success": False,
                "message": message,
                "trigger_count": trigger_count,
                "sent_count": 0,
            }

    def _resolve_trigger_count(self, payload: dict[str, Any]) -> int:
        if self.trigger_mode == TRIGGER_MODE_SINGLE:
            return 1
        gift_num = payload.get("gift_num", 1)
        try:
            normalized_count = int(gift_num)
        except (TypeError, ValueError):
            normalized_count = 1
        return max(1, normalized_count)
