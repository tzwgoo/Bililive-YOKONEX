from __future__ import annotations

from typing import Any

from app.services.danmaku_settings import FIXED_DANMAKU_COMMAND_ID
from app.services.danmaku_settings import FIXED_DANMAKU_COMMAND_IDS
from app.services.gift_dispatcher import normalize_trigger_mode


class LiveSessionManager:
    MODE_OPEN_LIVE = "open_live"
    MODE_THIRD_PARTY = "third_party"
    OUTPUT_MODE_IM = "im"
    OUTPUT_MODE_BLUETOOTH = "bluetooth"

    MODE_LABELS = {
        MODE_OPEN_LIVE: "官方 open-live",
        MODE_THIRD_PARTY: "第三方房间消息流",
    }

    OUTPUT_MODE_LABELS = {
        OUTPUT_MODE_IM: "IM 指令",
        OUTPUT_MODE_BLUETOOTH: "蓝牙",
    }

    def __init__(
        self,
        *,
        open_live_session: Any,
        third_party_session: Any,
        command_session: Any | None = None,
        bluetooth_service: Any | None = None,
    ) -> None:
        self.open_live_session = open_live_session
        self.third_party_session = third_party_session
        self.command_session = command_session
        self.bluetooth_service = bluetooth_service
        self.mode = self.MODE_OPEN_LIVE
        self._active_mode: str | None = None
        self.output_mode = self.OUTPUT_MODE_IM
        self.trigger_mode = "by_quantity"
        self.like_multiple = 100
        self.danmaku_enabled = False
        self.danmaku_keywords = ""
        self.danmaku_command_id = FIXED_DANMAKU_COMMAND_ID
        self.danmaku_cooldown_seconds = 0
        self.danmaku_user_limit_window_seconds = 0
        self.danmaku_user_limit_max_triggers = 0
        self.danmaku_min_guard_level = 0

    async def start(
        self,
        *,
        mode: str,
        value: str,
        output_mode: str = "",
        trigger_mode: str = "by_quantity",
        like_multiple: int = 100,
        danmaku_enabled: bool = False,
        danmaku_keywords: str = "",
        danmaku_command_id: str = "",
        danmaku_cooldown_seconds: int = 0,
        danmaku_user_limit_window_seconds: int = 0,
        danmaku_user_limit_max_triggers: int = 0,
        danmaku_min_guard_level: int = 0,
    ) -> None:
        normalized_mode = self._normalize_mode(mode)
        normalized_value = value.strip()
        normalized_output_mode = self._resolve_output_mode(output_mode)
        normalized_trigger_mode = normalize_trigger_mode(trigger_mode)
        normalized_like_multiple = max(1, int(like_multiple))
        normalized_danmaku_enabled = bool(danmaku_enabled)
        normalized_danmaku_keywords = str(danmaku_keywords or "").strip()
        normalized_danmaku_command_id = FIXED_DANMAKU_COMMAND_ID
        normalized_danmaku_cooldown_seconds = max(0, int(danmaku_cooldown_seconds))
        normalized_danmaku_user_limit_window_seconds = max(0, int(danmaku_user_limit_window_seconds))
        normalized_danmaku_user_limit_max_triggers = max(0, int(danmaku_user_limit_max_triggers))
        normalized_danmaku_min_guard_level = max(0, int(danmaku_min_guard_level))
        if not normalized_value:
            raise ValueError("启动参数不能为空")
        if normalized_danmaku_enabled and not normalized_danmaku_keywords:
            raise ValueError("已开启弹幕关键词触发时，关键词不能为空")

        if self._active_mode is not None and self._active_mode != normalized_mode:
            await self.stop()

        self.mode = normalized_mode
        self.output_mode = normalized_output_mode
        self.trigger_mode = normalized_trigger_mode
        self.like_multiple = normalized_like_multiple
        self.danmaku_enabled = normalized_danmaku_enabled
        self.danmaku_keywords = normalized_danmaku_keywords
        self.danmaku_command_id = normalized_danmaku_command_id
        self.danmaku_cooldown_seconds = normalized_danmaku_cooldown_seconds
        self.danmaku_user_limit_window_seconds = normalized_danmaku_user_limit_window_seconds
        self.danmaku_user_limit_max_triggers = normalized_danmaku_user_limit_max_triggers
        self.danmaku_min_guard_level = normalized_danmaku_min_guard_level
        await self._get_service(normalized_mode).start(
            value=normalized_value,
            output_mode=normalized_output_mode,
            trigger_mode=normalized_trigger_mode,
            like_multiple=normalized_like_multiple,
            danmaku_enabled=normalized_danmaku_enabled,
            danmaku_keywords=normalized_danmaku_keywords,
            danmaku_command_id=normalized_danmaku_command_id,
            danmaku_cooldown_seconds=normalized_danmaku_cooldown_seconds,
            danmaku_user_limit_window_seconds=normalized_danmaku_user_limit_window_seconds,
            danmaku_user_limit_max_triggers=normalized_danmaku_user_limit_max_triggers,
            danmaku_min_guard_level=normalized_danmaku_min_guard_level,
        )
        self._active_mode = normalized_mode

    async def stop(self) -> None:
        if self._active_mode is None:
            return
        await self._get_service(self._active_mode).stop()
        self._active_mode = None

    def handle_bluetooth_connected(self) -> None:
        if self._active_mode is None:
            return
        self._set_output_mode(self.OUTPUT_MODE_BLUETOOTH)

    def get_status_payload(self) -> dict[str, Any]:
        service_mode = self._active_mode or self.mode
        payload = dict(self._get_service(service_mode).get_status_payload())
        payload["mode"] = self.mode
        payload["mode_label"] = self.MODE_LABELS[self.mode]
        payload["output_mode"] = self.output_mode
        payload["output_mode_label"] = self.OUTPUT_MODE_LABELS[self.output_mode]
        payload["trigger_mode"] = self.trigger_mode
        payload["like_multiple"] = self.like_multiple
        payload["danmaku_enabled"] = self.danmaku_enabled
        payload["danmaku_keywords"] = self.danmaku_keywords
        payload["danmaku_command_id"] = self.danmaku_command_id
        payload["danmaku_command_ids"] = dict(FIXED_DANMAKU_COMMAND_IDS)
        payload["danmaku_cooldown_seconds"] = self.danmaku_cooldown_seconds
        payload["danmaku_user_limit_window_seconds"] = self.danmaku_user_limit_window_seconds
        payload["danmaku_user_limit_max_triggers"] = self.danmaku_user_limit_max_triggers
        payload["danmaku_min_guard_level"] = self.danmaku_min_guard_level
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

    def _normalize_output_mode(self, output_mode: str) -> str:
        normalized_output_mode = str(output_mode or "").strip()
        if normalized_output_mode not in self.OUTPUT_MODE_LABELS:
            raise ValueError("不支持的输出方式")
        return normalized_output_mode

    def _set_output_mode(self, output_mode: str) -> None:
        normalized_output_mode = self._normalize_output_mode(output_mode)
        self.output_mode = normalized_output_mode
        if self._active_mode is None:
            return
        active_service = self._get_service(self._active_mode)
        if hasattr(active_service, "output_mode"):
            active_service.output_mode = normalized_output_mode

    def _resolve_output_mode(self, output_mode: str) -> str:
        normalized_output_mode = str(output_mode or "").strip()
        if normalized_output_mode:
            return self._normalize_output_mode(normalized_output_mode)
        if self._is_bluetooth_connected():
            return self.OUTPUT_MODE_BLUETOOTH
        if self._is_command_connected():
            return self.OUTPUT_MODE_IM
        return self.OUTPUT_MODE_IM

    def _is_command_connected(self) -> bool:
        return bool(getattr(self.command_session, "is_connected", False))

    def _is_bluetooth_connected(self) -> bool:
        if self.bluetooth_service is None or not hasattr(self.bluetooth_service, "get_status_payload"):
            return False
        try:
            payload = self.bluetooth_service.get_status_payload()
        except Exception:
            return False
        if not isinstance(payload, dict):
            return False
        return bool(payload.get("connected"))
