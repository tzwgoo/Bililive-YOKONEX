from __future__ import annotations

from typing import Any

from app.bluetooth.gift_tiers import match_gift_tier_rule


class BluetoothDispatcher:
    def __init__(self, *, bluetooth_service: Any | None) -> None:
        self.bluetooth_service = bluetooth_service
        self._danmaku_enabled = False
        self._danmaku_keywords: list[str] = []

    def configure(self, *, danmaku_enabled: bool, danmaku_keywords: str, danmaku_cooldown_seconds: int = 0) -> None:
        self._danmaku_enabled = bool(danmaku_enabled)
        normalized_keywords = [item.strip() for item in str(danmaku_keywords or "").replace("\n", ",").split(",")]
        self._danmaku_keywords = [item for item in normalized_keywords if item]

    def reset_runtime_state(self) -> None:
        return None

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

        event_type = str(event.get("event_type", "") or "")
        payload_data = event.get("payload", {})
        if event_type == "danmaku":
            session_match_result = self._match_session_danmaku_keywords(payload_data)
            if session_match_result is not None:
                return session_match_result
        for rule in payload.bluetooth_event_rules:
            if not rule.enabled or rule.event_type != event_type:
                continue
            if event_type == "gift" and not self._match_gift_rule(rule.filters, payload_data):
                continue
            if event_type == "danmaku" and not self._match_danmaku_keywords(rule.filters, payload_data):
                continue
            return await self.bluetooth_service.trigger_waveform(
                event_type=event_type,
                waveform_id=rule.waveform_id,
            )

        return {
            "matched": False,
            "success": False,
            "message": "未命中蓝牙规则",
        }

    def _match_session_danmaku_keywords(self, payload: dict[str, Any]) -> dict[str, Any] | None:
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
        return None

    def _match_danmaku_keywords(self, filters: dict[str, Any], payload: dict[str, Any]) -> bool:
        keywords = filters.get("keywords", [])
        if not keywords:
            return True
        msg = str(payload.get("msg", ""))
        return any(str(keyword) in msg for keyword in keywords)

    def _match_gift_rule(self, filters: dict[str, Any], payload: dict[str, Any]) -> bool:
        price = self._coerce_int(payload.get("price", payload.get("r_price")))
        if price is None:
            return False
        min_price = self._coerce_int(filters.get("min_price"))
        max_price = self._coerce_int(filters.get("max_price"), allow_none=True)
        if min_price is None and max_price is None:
            tier = match_gift_tier_rule(price)
            return tier is not None
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
