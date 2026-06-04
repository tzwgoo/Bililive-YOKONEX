from __future__ import annotations

import time
from typing import Any

from app.bluetooth.gift_tiers import match_gift_tier_rule
from app.bluetooth.price_tiers import PRICE_FILTER_EVENT_TYPES
from app.models import is_danmaku_event_type


class BluetoothDispatcher:
    def __init__(self, *, bluetooth_service: Any | None) -> None:
        self.bluetooth_service = bluetooth_service
        self._danmaku_enabled = False
        self._danmaku_keywords: list[str] = []
        self._danmaku_min_guard_level = 0
        self._danmaku_user_limit_window_seconds = 0
        self._danmaku_user_limit_max_triggers = 0
        self._user_trigger_history: dict[tuple[str, int, str], list[float]] = {}

    def configure(
        self,
        *,
        danmaku_enabled: bool,
        danmaku_keywords: str,
        danmaku_cooldown_seconds: int = 0,
        danmaku_user_limit_window_seconds: int = 0,
        danmaku_user_limit_max_triggers: int = 0,
        danmaku_min_guard_level: int = 0,
    ) -> None:
        self._danmaku_enabled = bool(danmaku_enabled)
        normalized_keywords = [item.strip() for item in str(danmaku_keywords or "").replace("\n", ",").split(",")]
        self._danmaku_keywords = [item for item in normalized_keywords if item]
        self._danmaku_user_limit_window_seconds = max(0, int(danmaku_user_limit_window_seconds))
        self._danmaku_user_limit_max_triggers = max(0, int(danmaku_user_limit_max_triggers))
        self._danmaku_min_guard_level = max(0, int(danmaku_min_guard_level))

    def reset_runtime_state(self) -> None:
        self._user_trigger_history.clear()

    async def dispatch(self, event: dict[str, Any]) -> dict[str, Any]:
        if self.bluetooth_service is None:
            return {
                "matched": False,
                "success": False,
                "message": "蓝牙服务不可用",
            }

        payload = getattr(self.bluetooth_service, "payload", None)
        if payload is None:
            return {
                "matched": False,
                "success": False,
                "message": "蓝牙配置不可用",
            }

        original_event_type = str(event.get("event_type", "") or "")
        payload_data = event.get("payload", {})
        if is_danmaku_event_type(original_event_type):
            session_match_result = self._match_session_danmaku_keywords(event, payload_data)
            if session_match_result is not None:
                return session_match_result
        for rule in payload.bluetooth_event_rules:
            if not rule.enabled or not self._rule_matches_event_type(rule.event_type, original_event_type):
                continue
            if original_event_type in PRICE_FILTER_EVENT_TYPES and not self._match_price_rule(
                event_type=original_event_type,
                filters=rule.filters,
                payload=payload_data,
            ):
                continue
            if is_danmaku_event_type(original_event_type):
                danmaku_rule_result = self._match_danmaku_rule(rule.filters, payload_data)
                if danmaku_rule_result is not None:
                    return danmaku_rule_result
            return await self.bluetooth_service.trigger_waveform(
                event_type=original_event_type,
                waveform_id=rule.waveform_id,
            )

        return {
            "matched": False,
            "success": False,
            "message": "未命中蓝牙规则",
        }

    def _rule_matches_event_type(self, rule_event_type: str, original_event_type: str) -> bool:
        normalized_rule_event_type = str(rule_event_type or "")
        normalized_original_event_type = str(original_event_type or "")
        if normalized_rule_event_type == normalized_original_event_type:
            return True
        if is_danmaku_event_type(normalized_original_event_type) and normalized_rule_event_type == "danmaku":
            return True
        return False

    def _match_session_danmaku_keywords(
        self,
        event: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self._danmaku_enabled:
            return {
                "matched": False,
                "success": False,
                "message": "弹幕关键词触发未开启",
            }
        msg = str(payload.get("msg", ""))
        if not any(keyword in msg for keyword in self._danmaku_keywords):
            return {
                "matched": False,
                "success": False,
                "message": "弹幕未命中关键词",
            }

        guard_level = self._coerce_int(payload.get("guard_level")) or 0
        if not _meets_min_guard_level(
            guard_level=guard_level,
            min_guard_level=self._danmaku_min_guard_level,
        ):
            return {
                "matched": False,
                "success": False,
                "message": "弹幕命中关键词，但舰队等级不足",
            }

        user_limit_result = self._apply_user_limit(event, payload)
        if user_limit_result is not None:
            return user_limit_result
        return None

    def _match_danmaku_keywords(self, filters: dict[str, Any], payload: dict[str, Any]) -> bool:
        keywords = filters.get("keywords", [])
        if not keywords:
            return True
        msg = str(payload.get("msg", ""))
        return any(str(keyword) in msg for keyword in keywords)

    def _match_danmaku_rule(self, filters: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self._match_danmaku_keywords(filters, payload):
            return {
                "matched": False,
                "success": False,
                "message": "弹幕未命中规则关键词",
            }

        min_guard_level = self._coerce_int(filters.get("min_guard_level"))
        guard_level = self._coerce_int(payload.get("guard_level")) or 0
        if not _meets_min_guard_level(guard_level=guard_level, min_guard_level=min_guard_level or 0):
            return {
                "matched": False,
                "success": False,
                "message": "弹幕命中关键词，但舰队等级不足",
            }

        return None

    def _match_price_rule(self, *, event_type: str, filters: dict[str, Any], payload: dict[str, Any]) -> bool:
        price = self._coerce_int(payload.get("price", payload.get("r_price")))
        if price is None:
            return False
        min_price = self._coerce_int(filters.get("min_price"))
        max_price = self._coerce_int(filters.get("max_price"), allow_none=True)
        if min_price is None and max_price is None:
            if event_type == "gift":
                tier = match_gift_tier_rule(price)
                return tier is not None
            return True
        if min_price is not None and price < min_price:
            return False
        if max_price is not None and price > max_price:
            return False
        return True

    def _coerce_int(self, value: Any, *, allow_none: bool = False) -> int | None:
        if value in (None, ""):
            return None if allow_none else None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _apply_user_limit(
        self,
        event: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        if self._danmaku_user_limit_window_seconds <= 0 or self._danmaku_user_limit_max_triggers <= 0:
            return None

        user_key = self._build_user_limit_key(event, payload)
        if user_key is None:
            return None

        history = self._user_trigger_history.setdefault(user_key, [])
        now = time.monotonic()
        window_start = now - float(self._danmaku_user_limit_window_seconds)
        history[:] = [timestamp for timestamp in history if timestamp >= window_start]
        if len(history) >= self._danmaku_user_limit_max_triggers:
            return {
                "matched": False,
                "success": False,
                "message": "弹幕命中关键词，但已触发用户限流",
            }

        history.append(now)
        return None

    def _build_user_limit_key(
        self,
        event: dict[str, Any],
        payload: dict[str, Any],
    ) -> tuple[str, int, str] | None:
        raw_user_id = payload.get("uid") or event.get("open_id") or event.get("uname") or ""
        user_id = str(raw_user_id).strip()
        if not user_id:
            return None
        return (
            str(event.get("source", "")),
            self._coerce_int(event.get("room_id")) or 0,
            user_id,
        )


def _meets_min_guard_level(*, guard_level: int, min_guard_level: int) -> bool:
    normalized_min_guard_level = max(0, int(min_guard_level or 0))
    normalized_guard_level = max(0, int(guard_level or 0))
    if normalized_min_guard_level <= 0:
        return True
    if normalized_guard_level <= 0:
        return False
    return normalized_guard_level <= normalized_min_guard_level
