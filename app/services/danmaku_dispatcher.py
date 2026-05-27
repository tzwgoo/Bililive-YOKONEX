from __future__ import annotations

import logging
import time
from typing import Any


LOGGER = logging.getLogger("bili_live.danmaku_dispatcher")


class DanmakuCommandDispatcher:
    def __init__(self, *, command_session: Any | None) -> None:
        self.command_session = command_session
        self.enabled = False
        self.keywords: list[str] = []
        self.command_id = ""
        self.cooldown_seconds = 0
        self._last_trigger_at: dict[tuple[str, int, str], float] = {}

    @property
    def is_enabled(self) -> bool:
        return bool(self.command_session is not None and getattr(self.command_session, "is_connected", False))

    def configure(
        self,
        *,
        enabled: bool,
        keywords: str,
        command_id: str,
        cooldown_seconds: int,
    ) -> None:
        self.enabled = bool(enabled)
        normalized_keywords = [item.strip() for item in str(keywords).replace("\n", ",").split(",")]
        self.keywords = [item for item in normalized_keywords if item]
        self.command_id = str(command_id).strip()
        self.cooldown_seconds = max(0, int(cooldown_seconds))

    def reset_runtime_state(self) -> None:
        self._last_trigger_at.clear()

    async def dispatch(self, event: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {
                "matched": False,
                "command_id": "",
                "success": False,
                "message": "弹幕关键词触发未开启",
                "trigger_count": 0,
                "sent_count": 0,
            }

        if not self.keywords or not self.command_id:
            return {
                "matched": False,
                "command_id": "",
                "success": False,
                "message": "弹幕关键词触发未配置",
                "trigger_count": 0,
                "sent_count": 0,
            }

        payload = event.get("payload", {})
        msg = str(payload.get("msg", ""))
        matched_keywords = [keyword for keyword in self.keywords if keyword in msg]
        if not matched_keywords:
            return {
                "matched": False,
                "command_id": "",
                "success": False,
                "message": "弹幕未命中关键词",
                "trigger_count": 0,
                "sent_count": 0,
            }

        cooldown_key = self._build_cooldown_key(event, command_id=self.command_id)
        now = time.monotonic()
        last_trigger_at = self._last_trigger_at.get(cooldown_key, 0.0)
        if self.cooldown_seconds > 0 and (now - last_trigger_at) < self.cooldown_seconds:
            remaining_seconds = self.cooldown_seconds - (now - last_trigger_at)
            return {
                "matched": True,
                "command_id": self.command_id,
                "success": True,
                "message": f"弹幕命中关键词，但仍处于冷却中，剩余约 {int(remaining_seconds) + 1} 秒",
                "trigger_count": 0,
                "sent_count": 0,
                "matched_keywords": matched_keywords,
            }

        if not self.is_enabled or self.command_session is None:
            LOGGER.warning("弹幕已命中关键词，但下游指令通道未登录 command_id=%s", self.command_id)
            return {
                "matched": True,
                "command_id": self.command_id,
                "success": False,
                "message": "下游指令通道未登录",
                "trigger_count": 1,
                "sent_count": 0,
                "matched_keywords": matched_keywords,
            }

        try:
            result = await self.command_session.send_command(command_id=self.command_id)
            success = bool(result.get("success"))
            message = result.get("message") or ("指令发送成功" if success else "指令发送失败")
            if success:
                self._last_trigger_at[cooldown_key] = now
                LOGGER.info(
                    "弹幕关键词指令发送成功 command_id=%s keywords=%s",
                    self.command_id,
                    ",".join(matched_keywords),
                )
            else:
                LOGGER.warning("弹幕关键词指令发送失败 command_id=%s message=%s", self.command_id, message)
            return {
                "matched": True,
                "command_id": self.command_id,
                "success": success,
                "message": message,
                "trigger_count": 1,
                "sent_count": 1 if success else 0,
                "matched_keywords": matched_keywords,
            }
        except Exception as exc:  # pragma: no cover - 真实网络路径
            message = f"指令发送失败: {exc}"
            LOGGER.exception("弹幕关键词指令发送异常 command_id=%s", self.command_id)
            return {
                "matched": True,
                "command_id": self.command_id,
                "success": False,
                "message": message,
                "trigger_count": 1,
                "sent_count": 0,
                "matched_keywords": matched_keywords,
            }

    def _build_cooldown_key(self, event: dict[str, Any], *, command_id: str) -> tuple[str, int, str]:
        return (
            str(event.get("source", "")),
            self._normalize_count(event.get("room_id"), default=0),
            command_id,
        )

    def _normalize_count(self, value: Any, *, default: int) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = default
        return max(0, normalized)
