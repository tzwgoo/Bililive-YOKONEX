from __future__ import annotations

from typing import Any


class BluetoothDispatcher:
    def __init__(self, *, bluetooth_service: Any | None) -> None:
        self.bluetooth_service = bluetooth_service

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
        for rule in payload.bluetooth_event_rules:
            if not rule.enabled or rule.event_type != event_type:
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

    def _match_danmaku_keywords(self, filters: dict[str, Any], payload: dict[str, Any]) -> bool:
        keywords = filters.get("keywords", [])
        if not keywords:
            return True
        msg = str(payload.get("msg", ""))
        return any(str(keyword) in msg for keyword in keywords)
