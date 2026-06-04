from __future__ import annotations

import logging
import time
from typing import Any

from app.command_gateway.mapping import ALLOWED_COMMAND_SLOTS
from app.models import is_danmaku_event_type, resolve_danmaku_event_type
from app.services.danmaku_settings import resolve_fixed_danmaku_command_id


LOGGER = logging.getLogger("bili_live.danmaku_dispatcher")


class DanmakuCommandDispatcher:
    def __init__(self, *, command_session: Any | None) -> None:
        self.command_session = command_session
        self.enabled = False
        self.keywords: list[str] = []
        self.command_id = ""
        self.cooldown_seconds = 0
        self.user_limit_window_seconds = 0
        self.user_limit_max_triggers = 0
        self.min_guard_level = 0
        self.command_slot_rules: dict[str, str] = {}
        self._last_trigger_at: dict[tuple[str, int, str], float] = {}
        self._user_trigger_history: dict[tuple[str, int, str, str], list[float]] = {}

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
        user_limit_window_seconds: int = 0,
        user_limit_max_triggers: int = 0,
        min_guard_level: int = 0,
    ) -> None:
        self.enabled = bool(enabled)
        normalized_keywords = [item.strip() for item in str(keywords).replace("\n", ",").split(",")]
        self.keywords = [item for item in normalized_keywords if item]
        self.command_id = str(command_id).strip()
        self.cooldown_seconds = max(0, int(cooldown_seconds))
        self.user_limit_window_seconds = max(0, int(user_limit_window_seconds))
        self.user_limit_max_triggers = max(0, int(user_limit_max_triggers))
        self.min_guard_level = max(0, int(min_guard_level))

    def reset_runtime_state(self) -> None:
        self._last_trigger_at.clear()
        self._user_trigger_history.clear()

    def set_command_slot_rules(self, rules: list[dict[str, Any]]) -> None:
        self.command_slot_rules = {}
        for item in rules:
            if not bool(item.get("enabled", False)):
                continue
            command_slot = str(item.get("command_slot", "") or "").strip()
            if command_slot not in ALLOWED_COMMAND_SLOTS:
                continue
            event_type = self._normalize_danmaku_event_type(item)
            if event_type is None:
                continue
            self.command_slot_rules[event_type] = command_slot

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

        guard_level = self._normalize_count(payload.get("guard_level"), default=0)
        resolved_command_id = self._resolve_command_id(
            event_type=str(event.get("event_type", "") or ""),
            guard_level=guard_level,
        )
        if not _meets_min_guard_level(guard_level=guard_level, min_guard_level=self.min_guard_level):
            return {
                "matched": True,
                "command_id": resolved_command_id,
                "success": True,
                "message": "弹幕命中关键词，但舰队等级不足",
                "trigger_count": 0,
                "sent_count": 0,
                "matched_keywords": matched_keywords,
            }

        now = time.monotonic()
        user_limit_result = self._apply_user_limit(event, now=now)
        if user_limit_result is not None:
            user_limit_result["matched_keywords"] = matched_keywords
            user_limit_result["command_id"] = resolved_command_id
            return user_limit_result

        cooldown_key = self._build_cooldown_key(event, command_id=resolved_command_id)
        last_trigger_at = self._last_trigger_at.get(cooldown_key, 0.0)
        if self.cooldown_seconds > 0 and (now - last_trigger_at) < self.cooldown_seconds:
            remaining_seconds = self.cooldown_seconds - (now - last_trigger_at)
            return {
                "matched": True,
                "command_id": resolved_command_id,
                "success": True,
                "message": f"弹幕命中关键词，但仍处于冷却中，剩余约 {int(remaining_seconds) + 1} 秒",
                "trigger_count": 0,
                "sent_count": 0,
                "matched_keywords": matched_keywords,
            }

        if not self.is_enabled or self.command_session is None:
            LOGGER.warning("弹幕已命中关键词，但下游指令通道未登录 command_id=%s", resolved_command_id)
            return {
                "matched": True,
                "command_id": resolved_command_id,
                "success": False,
                "message": "下游指令通道未登录",
                "trigger_count": 1,
                "sent_count": 0,
                "matched_keywords": matched_keywords,
            }

        try:
            result = await self.command_session.send_command(command_id=resolved_command_id)
            success = bool(result.get("success"))
            message = result.get("message") or ("指令发送成功" if success else "指令发送失败")
            if success:
                self._last_trigger_at[cooldown_key] = now
                LOGGER.info(
                    "弹幕关键词指令发送成功 command_id=%s keywords=%s",
                    resolved_command_id,
                    ",".join(matched_keywords),
                )
            else:
                LOGGER.warning("弹幕关键词指令发送失败 command_id=%s message=%s", resolved_command_id, message)
            return {
                "matched": True,
                "command_id": resolved_command_id,
                "success": success,
                "message": message,
                "trigger_count": 1,
                "sent_count": 1 if success else 0,
                "matched_keywords": matched_keywords,
            }
        except Exception as exc:  # pragma: no cover - 真实网络路径
            message = f"指令发送失败: {exc}"
            LOGGER.exception("弹幕关键词指令发送异常 command_id=%s", resolved_command_id)
            return {
                "matched": True,
                "command_id": resolved_command_id,
                "success": False,
                "message": message,
                "trigger_count": 1,
                "sent_count": 0,
                "matched_keywords": matched_keywords,
            }

    def _resolve_command_id(self, *, event_type: str, guard_level: int) -> str:
        normalized_event_type = (
            event_type
            if is_danmaku_event_type(event_type)
            else resolve_danmaku_event_type(guard_level).value
        )
        if normalized_event_type in self.command_slot_rules:
            return self.command_slot_rules[normalized_event_type]
        fallback_event_type = resolve_danmaku_event_type(guard_level).value
        if fallback_event_type in self.command_slot_rules:
            return self.command_slot_rules[fallback_event_type]
        if "danmaku" in self.command_slot_rules:
            return self.command_slot_rules["danmaku"]
        return resolve_fixed_danmaku_command_id(
            event_type=normalized_event_type,
            guard_level=guard_level,
        )

    def _normalize_danmaku_event_type(self, item: dict[str, Any]) -> str | None:
        explicit_event_type = str(item.get("event_type", "") or "").strip()
        if is_danmaku_event_type(explicit_event_type):
            return explicit_event_type
        guard_level = self._normalize_count(item.get("guard_level"), default=-1)
        if guard_level < 0:
            return None
        return resolve_danmaku_event_type(guard_level).value

    def _build_cooldown_key(self, event: dict[str, Any], *, command_id: str) -> tuple[str, int, str]:
        return (
            str(event.get("source", "")),
            self._normalize_count(event.get("room_id"), default=0),
            command_id,
        )

    def _apply_user_limit(self, event: dict[str, Any], *, now: float) -> dict[str, Any] | None:
        if self.user_limit_window_seconds <= 0 or self.user_limit_max_triggers <= 0:
            return None

        user_key = self._build_user_limit_key(event, command_id=self.command_id)
        if user_key is None:
            return None

        history = self._user_trigger_history.setdefault(user_key, [])
        window_start = now - float(self.user_limit_window_seconds)
        history[:] = [timestamp for timestamp in history if timestamp >= window_start]
        if len(history) >= self.user_limit_max_triggers:
            return {
                "matched": True,
                "command_id": self.command_id,
                "success": True,
                "message": "弹幕命中关键词，但已触发用户限流",
                "trigger_count": 0,
                "sent_count": 0,
            }

        history.append(now)
        return None

    def _build_user_limit_key(self, event: dict[str, Any], *, command_id: str) -> tuple[str, int, str, str] | None:
        payload = event.get("payload", {})
        raw_user_id = payload.get("uid") or event.get("open_id") or event.get("uname") or ""
        user_id = str(raw_user_id).strip()
        if not user_id:
            return None
        return (
            str(event.get("source", "")),
            self._normalize_count(event.get("room_id"), default=0),
            user_id,
            command_id,
        )

    def _normalize_count(self, value: Any, *, default: int) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = default
        return max(0, normalized)


def _meets_min_guard_level(*, guard_level: int, min_guard_level: int) -> bool:
    normalized_min_guard_level = max(0, int(min_guard_level or 0))
    normalized_guard_level = max(0, int(guard_level or 0))
    if normalized_min_guard_level <= 0:
        return True
    if normalized_guard_level <= 0:
        return False
    return normalized_guard_level <= normalized_min_guard_level
