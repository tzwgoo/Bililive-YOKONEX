from __future__ import annotations

from typing import Any


class LiveSessionManager:
    MODE_OPEN_LIVE = "open_live"
    MODE_THIRD_PARTY = "third_party"

    MODE_LABELS = {
        MODE_OPEN_LIVE: "官方 open-live",
        MODE_THIRD_PARTY: "第三方房间消息流",
    }

    def __init__(self, *, open_live_session: Any, third_party_session: Any) -> None:
        self.open_live_session = open_live_session
        self.third_party_session = third_party_session
        self.mode = self.MODE_OPEN_LIVE
        self._active_mode: str | None = None

    async def start(self, *, mode: str, value: str) -> None:
        normalized_mode = self._normalize_mode(mode)
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("启动参数不能为空")

        if self._active_mode is not None and self._active_mode != normalized_mode:
            await self.stop()

        self.mode = normalized_mode
        await self._get_service(normalized_mode).start(value=normalized_value)
        self._active_mode = normalized_mode

    async def stop(self) -> None:
        if self._active_mode is None:
            return
        await self._get_service(self._active_mode).stop()
        self._active_mode = None

    def get_status_payload(self) -> dict[str, Any]:
        service_mode = self._active_mode or self.mode
        payload = dict(self._get_service(service_mode).get_status_payload())
        payload["mode"] = self.mode
        payload["mode_label"] = self.MODE_LABELS[self.mode]
        return payload

    def _get_service(self, mode: str) -> Any:
        if mode == self.MODE_OPEN_LIVE:
            return self.open_live_session
        if mode == self.MODE_THIRD_PARTY:
            return self.third_party_session
        raise ValueError("不支持的监听模式")

    def _normalize_mode(self, mode: str) -> str:
        normalized_mode = mode.strip()
        if normalized_mode not in self.MODE_LABELS:
            raise ValueError("不支持的监听模式")
        return normalized_mode
