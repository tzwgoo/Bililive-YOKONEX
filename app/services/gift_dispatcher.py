from __future__ import annotations

import logging
from typing import Any

from app.command_gateway.mapping import GiftCommandMapper
from app.services.danmaku_settings import FIXED_LIKE_COMMAND_ID


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
        self.like_multiple = 100
        self._like_progress: dict[tuple[str, int, str, int], int] = {}

    @property
    def is_enabled(self) -> bool:
        return bool(self.command_session is not None and getattr(self.command_session, "is_connected", False))

    def set_trigger_mode(self, trigger_mode: str) -> None:
        self.trigger_mode = normalize_trigger_mode(trigger_mode)

    def set_like_multiple(self, like_multiple: int) -> None:
        self.like_multiple = max(1, int(like_multiple))

    def reset_runtime_state(self) -> None:
        self._like_progress.clear()

    async def dispatch_gift_event(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = event.get("payload", {})
        command_id = self.mapper.resolve_command_id(
            payload,
            event_type=str(event.get("event_type", "gift") or "gift"),
        )
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
            result = await self._send_command_repeatedly(command_id=command_id, trigger_count=trigger_count)
            if result["success"]:
                LOGGER.info("礼物指令发送成功 command_id=%s trigger_count=%s", command_id, trigger_count)
            else:
                LOGGER.warning("礼物指令发送失败 command_id=%s message=%s", command_id, result["message"])
            return result
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

    async def dispatch_like_event(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = event.get("payload", {})
        command_id = FIXED_LIKE_COMMAND_ID
        like_multiple = max(1, self.like_multiple or 100)
        progress_key = self._build_like_progress_key(event, command_id=command_id, like_multiple=like_multiple)
        last_observed_like_count = self._like_progress.get(progress_key, 0)
        reported_like_count = self._normalize_count(payload.get("like_count"), default=0)
        like_delta = self._normalize_count(payload.get("like_delta"), default=0)
        effective_like_count = self._resolve_effective_like_count(
            reported_like_count=reported_like_count,
            like_delta=like_delta,
            last_observed_like_count=last_observed_like_count,
        )
        if reported_like_count > 0 and effective_like_count < last_observed_like_count:
            last_observed_like_count = 0
        trigger_count = max(0, (effective_like_count // like_multiple) - (last_observed_like_count // like_multiple))
        self._like_progress[progress_key] = effective_like_count
        payload["like_count"] = effective_like_count

        if trigger_count <= 0:
            return {
                "matched": True,
                "command_id": command_id,
                "success": True,
                "message": f"点赞数 {effective_like_count} 尚未跨过新的 {like_multiple} 倍数阈值",
                "trigger_count": 0,
                "sent_count": 0,
            }

        if not self.is_enabled or self.command_session is None:
            LOGGER.warning("点赞已命中映射，但下游指令通道未登录 command_id=%s", command_id)
            return {
                "matched": True,
                "command_id": command_id,
                "success": False,
                "message": "下游指令通道未登录",
                "trigger_count": trigger_count,
                "sent_count": 0,
            }

        try:
            result = await self._send_command_repeatedly(command_id=command_id, trigger_count=trigger_count)
            if result["success"]:
                LOGGER.info(
                    "点赞指令发送成功 command_id=%s like_count=%s trigger_count=%s like_multiple=%s",
                    command_id,
                    effective_like_count,
                    trigger_count,
                    like_multiple,
                )
            else:
                LOGGER.warning("点赞指令发送失败 command_id=%s message=%s", command_id, result["message"])
            return result
        except Exception as exc:  # pragma: no cover - 真实网络路径
            message = f"指令发送失败: {exc}"
            LOGGER.exception("点赞指令发送异常 command_id=%s", command_id)
            return {
                "matched": True,
                "command_id": command_id,
                "success": False,
                "message": message,
                "trigger_count": trigger_count,
                "sent_count": 0,
            }

    def _resolve_effective_like_count(
        self,
        *,
        reported_like_count: int,
        like_delta: int,
        last_observed_like_count: int,
    ) -> int:
        if reported_like_count > 0:
            return reported_like_count
        if like_delta > 0:
            baseline = last_observed_like_count if last_observed_like_count > 0 else 0
            return baseline + like_delta
        return last_observed_like_count

    def _resolve_trigger_count(self, payload: dict[str, Any]) -> int:
        if self.trigger_mode == TRIGGER_MODE_SINGLE:
            return 1
        gift_num = payload.get("gift_num", 1)
        try:
            normalized_count = int(gift_num)
        except (TypeError, ValueError):
            normalized_count = 1
        return max(1, normalized_count)

    async def _send_command_repeatedly(self, *, command_id: str, trigger_count: int) -> dict[str, Any]:
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
        return {
            "matched": True,
            "command_id": command_id,
            "success": success,
            "message": message,
            "trigger_count": trigger_count,
            "sent_count": sent_count,
        }

    def _build_like_progress_key(self, event: dict[str, Any], *, command_id: str, like_multiple: int) -> tuple[str, int, str, int]:
        return (
            str(event.get("source", "")),
            self._normalize_count(event.get("room_id"), default=0),
            command_id,
            like_multiple,
        )

    def _normalize_count(self, value: Any, *, default: int) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = default
        return max(0, normalized)
