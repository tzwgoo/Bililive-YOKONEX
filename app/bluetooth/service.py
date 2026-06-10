from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any
import time
import uuid

from app.bluetooth.gift_tiers import GIFT_TIER_BY_RULE_ID
from app.bluetooth.models import BluetoothConnectionStatus
from app.bluetooth.models import BluetoothConfigPayload
from app.bluetooth.models import BluetoothDevice
from app.bluetooth.models import BluetoothEventRule
from app.bluetooth.models import EmsWaveform
from app.bluetooth.models import EmsWaveformStep
from app.bluetooth.models import ToyWaveform
from app.bluetooth.models import ToyWaveformStep
from app.bluetooth.models import payload_to_dict
from app.bluetooth.price_tiers import PRICE_FILTER_EVENT_TYPES
from app.bluetooth.price_tiers import SPECIAL_PRICE_TIER_BY_RULE_ID
from app.bluetooth.runtime.base import BluetoothRuntime
from app.bluetooth.runtime.memory_runtime import MemoryBluetoothRuntime
from app.bluetooth.storage import BluetoothSettingsStore
from app.models import is_danmaku_event_type


logger = logging.getLogger(__name__)

RULE_GROUP_LABELS = {
    "gift": "礼物事件",
    "like": "点赞事件",
    "danmaku": "普通弹幕",
    "danmaku_captain": "舰长弹幕",
    "danmaku_commander": "提督弹幕",
    "danmaku_governor": "总督弹幕",
    "super_chat": "醒目留言",
    "guard_buy": "上舰",
    "guard_renew": "续费",
    "interact": "互动事件",
}
PRICE_FILTER_EVENT_TYPES = {"gift", "super_chat", "guard_buy", "guard_renew"}


class BluetoothService:
    def __init__(
        self,
        *,
        store: BluetoothSettingsStore,
        runtime: BluetoothRuntime,
        payload: BluetoothConfigPayload | None = None,
        event_hub: Any | None = None,
    ) -> None:
        # 蓝牙配置存储，用于持久化设备、波形和事件规则。
        self.store = store
        # 蓝牙运行时，用于扫描、连接和执行波形。
        self.runtime = runtime
        # 当前蓝牙配置快照，页面和调度器共用此对象。
        self.payload = payload or self.store.load()
        # 控制日志事件中心，用于记录波形触发结果。
        self.event_hub = event_hub
        # 波形执行锁，用于保证同一时刻只保留一个有效波形任务。
        self._waveform_lock = asyncio.Lock()
        self._active_waveform_task: asyncio.Task[None] | None = None
        self._active_waveform_request_id = ""
        self._active_waveform_id = ""
        self._active_waveform_strength = -1
        self._active_waveform_deadline = 0.0

    @classmethod
    def create_default(cls, *, config_path: Path, event_hub: Any | None = None) -> "BluetoothService":
        store = BluetoothSettingsStore(config_path)
        payload = store.load()
        try:
            runtime = create_real_bluetooth_runtime(
                scan_timeout_seconds=payload.bluetooth_settings.scan_timeout_seconds,
                connect_timeout_seconds=payload.bluetooth_settings.connect_timeout_seconds,
                auto_reconnect=payload.bluetooth_settings.auto_reconnect,
            )
        except Exception as exc:  # pragma: no cover - verified through factory fallback test
            logger.warning("真实蓝牙运行时初始化失败，已降级到内存运行时: %s", exc)
            runtime = MemoryBluetoothRuntime()
        return cls(
            store=store,
            runtime=runtime,
            payload=payload,
            event_hub=event_hub,
        )

    async def scan(self) -> list[BluetoothDevice]:
        try:
            devices = await self.runtime.scan()
        except TimeoutError:
            raise RuntimeError("蓝牙扫描超时，请重试") from None
        except Exception as exc:
            raise RuntimeError(_resolve_scan_error_message(exc)) from exc
        return devices

    async def connect(self, device_id: str) -> BluetoothConnectionStatus:
        try:
            status = await self.runtime.connect(device_id)
        except Exception as exc:
            self._publish_bluetooth_connection_control(
                success=False,
                device_id=device_id,
                device_name="",
                message=str(exc) or "蓝牙连接失败",
            )
            raise
        if status.device is not None:
            self.payload.bluetooth_settings.last_connected_device_id = status.device.device_id
            self.payload.bluetooth_settings.last_connected_device_name = status.device.name
            self.payload.bluetooth_settings.default_target_device_id = status.device.device_id
            self.store.save(self.payload)
        self._publish_bluetooth_connection_control(
            success=True,
            device_id="" if status.device is None else status.device.device_id,
            device_name="" if status.device is None else status.device.name,
            message=status.message,
        )
        return status

    async def disconnect(self) -> BluetoothConnectionStatus:
        return await self.runtime.disconnect()

    async def trigger_waveform(self, *, event_type: str, waveform_id: str) -> dict:
        waveform = self._find_waveform_any(waveform_id)
        waveform_strength = _resolve_waveform_max_strength(waveform)
        waveform_duration_seconds = _resolve_waveform_duration_seconds(waveform)
        request_id = uuid.uuid4().hex
        task_to_await: asyncio.Task[None] | None = None
        async with self._waveform_lock:
            self._cleanup_finished_waveform_task()
            now = time.monotonic()
            if self._active_waveform_task is not None:
                # 新事件只在强度更高时抢占当前波形；强度相同或更弱时直接忽略。
                if waveform_strength <= self._active_waveform_strength:
                    if waveform_id == self._active_waveform_id:
                        # 相同波形直接续一整轮时长，避免连续命中时被截断。
                        self._active_waveform_deadline = max(self._active_waveform_deadline, now) + waveform_duration_seconds
                        result = {
                            "matched": True,
                            "event_type": event_type,
                            "waveform_id": waveform_id,
                            "waveform_name": waveform.name,
                            "max_strength": waveform_strength,
                            "success": True,
                            "message": f"{event_type} 已为当前波形追加 {waveform_duration_seconds:.2f} 秒时长",
                        }
                        self._publish_bluetooth_control(result)
                        return result
                    result = {
                        "matched": True,
                        "event_type": event_type,
                        "waveform_id": waveform_id,
                        "waveform_name": waveform.name,
                        "max_strength": waveform_strength,
                        "success": True,
                        "message": f"当前已有更高强度波形执行中，已忽略 {event_type} 触发",
                    }
                    self._publish_bluetooth_control(result)
                    return result
                previous_task = self._active_waveform_task
                self._active_waveform_request_id = request_id
                self._active_waveform_id = waveform_id
                self._active_waveform_strength = waveform_strength
                self._active_waveform_deadline = now + waveform_duration_seconds
                task_to_await = asyncio.create_task(self._run_waveform_until_deadline(waveform, request_id=request_id))
                self._active_waveform_task = task_to_await
                previous_task.cancel()
            else:
                self._active_waveform_request_id = request_id
                self._active_waveform_id = waveform_id
                self._active_waveform_strength = waveform_strength
                self._active_waveform_deadline = now + waveform_duration_seconds
                task_to_await = asyncio.create_task(self._run_waveform_until_deadline(waveform, request_id=request_id))
                self._active_waveform_task = task_to_await
        try:
            await task_to_await
        except asyncio.CancelledError:
            # 这里表示当前波形被更高强度的新事件抢占，不视为执行失败。
            if self._active_waveform_request_id != request_id:
                result = {
                    "matched": True,
                    "event_type": event_type,
                    "waveform_id": waveform_id,
                    "waveform_name": waveform.name,
                    "max_strength": waveform_strength,
                    "success": True,
                    "message": f"{event_type} 波形已被更高强度事件抢占",
                }
                self._publish_bluetooth_control(result)
                return result
            raise
        except Exception as exc:
            result = {
                "matched": True,
                "event_type": event_type,
                "waveform_id": waveform_id,
                "waveform_name": waveform.name,
                "max_strength": waveform_strength,
                "success": False,
                "message": f"波形执行失败: {exc}",
            }
            self._publish_bluetooth_control(result)
            return result
        finally:
            async with self._waveform_lock:
                if self._active_waveform_request_id == request_id:
                    self._active_waveform_task = None
                    self._active_waveform_request_id = ""
                    self._active_waveform_id = ""
                    self._active_waveform_strength = -1
                    self._active_waveform_deadline = 0.0
        result = {
            "matched": True,
            "event_type": event_type,
            "waveform_id": waveform_id,
            "waveform_name": waveform.name,
            "max_strength": waveform_strength,
            "success": True,
            "message": f"{event_type} 已触发波形 {waveform.name}",
        }
        self._publish_bluetooth_control(result)
        return result

    async def preview_waveform(self, waveform_id: str) -> dict:
        waveform = self._find_waveform_any(waveform_id)
        if waveform is None:
            result = {
                "matched": True,
                "event_type": "waveform_preview",
                "waveform_id": waveform_id,
                "success": False,
                "message": "目标波形不存在",
            }
            self._publish_bluetooth_control(result)
            return result
        try:
            await self.runtime.play_waveform(waveform)
        except Exception as exc:
            result = {
                "matched": True,
                "event_type": "waveform_preview",
                "waveform_id": waveform_id,
                "waveform_name": waveform.name,
                "max_strength": _resolve_waveform_max_strength(waveform),
                "success": False,
                "message": f"测试播放失败: {exc}",
            }
            self._publish_bluetooth_control(result)
            return result
        result = {
            "matched": True,
            "event_type": "waveform_preview",
            "waveform_id": waveform_id,
            "waveform_name": waveform.name,
            "max_strength": _resolve_waveform_max_strength(waveform),
            "success": True,
            "message": f"已测试播放波形 {waveform.name}",
        }
        self._publish_bluetooth_control(result)
        return result

    def get_status_payload(self) -> dict:
        status = self.runtime.get_status()
        waveform_name_map = {
            item.id: item.name
            for item in self.payload.ems_waveforms
        }
        waveform_name_map.update({
            item.id: item.name
            for item in self.payload.toy_waveforms
        })
        payload_dict = payload_to_dict(self.payload)
        return {
            "runtime_backend": getattr(self.runtime, "backend_name", "unknown"),
            "enabled": self.payload.bluetooth_settings.enabled,
            "connected": status.connected,
            "battery_level": status.battery_level,
            "message": status.message,
            "device": None if status.device is None else {
                "device_id": status.device.device_id,
                "name": status.device.name,
                "device_type": status.device.device_type,
                "protocol": status.device.protocol,
                "rssi": status.device.rssi,
            },
            "devices": [
                {
                    "device_id": item.device_id,
                    "name": item.name,
                    "device_type": item.device_type,
                    "protocol": item.protocol,
                    "rssi": item.rssi,
                    "connected": item.connected,
                }
                for item in self.runtime.get_devices()
            ],
            "ems_waveforms": payload_dict["ems_waveforms"],
            "toy_waveforms": payload_dict["toy_waveforms"],
            "rules": [
                {
                    **item,
                    "event_label": RULE_GROUP_LABELS.get(str(item.get("event_type", "")), str(item.get("event_type", "unknown"))),
                    "rule_label": _build_rule_label(item),
                    "waveform_name": waveform_name_map.get(str(item.get("waveform_id", "")), str(item.get("waveform_id", "-") or "-")),
                }
                for item in payload_dict["bluetooth_event_rules"]
            ],
        }

    def get_overlay_payload(self) -> dict:
        payload = self.runtime.get_overlay_payload()
        return {
            "connected": bool(payload.get("connected", False)),
            "device_name": str(payload.get("device_name", "") or ""),
            "device_type": str(payload.get("device_type", "") or ""),
            "waveform_name": str(payload.get("waveform_name", "") or ""),
            "battery_level": _normalize_battery_level(payload.get("battery_level")),
            # 仅用于 OBS 叠加窗视觉缩放，避免中低档位在画面里看起来过小。
            "display_max_strength": _resolve_overlay_display_max_strength(
                payload=payload,
                active_waveform_strength=self._active_waveform_strength,
            ),
            "channel_a": max(0, int(payload.get("channel_a", 0) or 0)),
            "channel_b": max(0, int(payload.get("channel_b", 0) or 0)),
            "motor_a": max(0, int(payload.get("motor_a", 0) or 0)),
            "motor_b": max(0, int(payload.get("motor_b", 0) or 0)),
            "motor_c": max(0, int(payload.get("motor_c", 0) or 0)),
            "step_index": max(0, int(payload.get("step_index", 0) or 0)),
            "step_count": max(0, int(payload.get("step_count", 0) or 0)),
            "updated_at": float(payload.get("updated_at", 0) or 0),
            "history": [
                {
                    **item,
                    "channel_a": max(0, int(item.get("channel_a", 0) or 0)),
                    "channel_b": max(0, int(item.get("channel_b", 0) or 0)),
                    "motor_a": max(0, int(item.get("motor_a", 0) or 0)),
                    "motor_b": max(0, int(item.get("motor_b", 0) or 0)),
                    "motor_c": max(0, int(item.get("motor_c", 0) or 0)),
                }
                for item in payload.get("history", [])
                if isinstance(item, dict)
            ][-90:],
            "recent_events": _build_overlay_recent_events(self.event_hub),
            "revision": max(0, int(payload.get("revision", 0) or 0)),
        }

    def get_studio_payload(self) -> dict:
        payload_dict = payload_to_dict(self.payload)
        waveform_name_map = {
            item.id: item.name
            for item in self.payload.ems_waveforms
        }
        waveform_name_map.update({
            item.id: item.name
            for item in self.payload.toy_waveforms
        })
        grouped_rules: list[dict] = []
        for event_type, label in RULE_GROUP_LABELS.items():
            rules = [
                {
                    "id": item.id,
                    "event_type": item.event_type,
                    "rule_label": _build_rule_label(
                        {
                            "id": item.id,
                            "event_type": item.event_type,
                            "filters": item.filters,
                        }
                    ),
                    "enabled": item.enabled,
                    "waveform_id": item.waveform_id,
                    "waveform_name": waveform_name_map.get(item.waveform_id, item.waveform_id or "-"),
                    "cooldown_seconds": item.cooldown_seconds,
                    "filters": item.filters,
                }
                for item in self.payload.bluetooth_event_rules
                if item.event_type == event_type
            ]
            grouped_rules.append(
                {
                    "group_id": event_type,
                    "group_label": label,
                    "rules": rules,
                }
            )
        return {
            "ems_waveforms": payload_dict["ems_waveforms"],
            "toy_waveforms": payload_dict["toy_waveforms"],
            "rule_groups": grouped_rules,
        }

    def save_rules(self, rules: list[dict]) -> dict:
        waveform_ids = {item.id for item in self.payload.ems_waveforms} | {item.id for item in self.payload.toy_waveforms}
        rule_map = {item.id: item for item in self.payload.bluetooth_event_rules}
        next_enabled_by_rule_id: dict[str, bool] = {}
        next_waveform_id_by_rule_id: dict[str, str] = {}
        next_toy_waveform_id_by_rule_id: dict[str, str] = {}
        next_filters_by_rule_id: dict[str, dict[str, Any]] = {}
        updated_count = 0
        for item in rules:
            rule_id = str(item.get("id", "") or "")
            waveform_id = str(item.get("waveform_id", "") or "")
            toy_waveform_id = str(item.get("toy_waveform_id", "") or "")
            if rule_id not in rule_map:
                raise ValueError(f"未找到规则: {rule_id}")
            if waveform_id and waveform_id not in waveform_ids:
                raise ValueError(f"未找到波形: {waveform_id}")
            if toy_waveform_id and toy_waveform_id not in waveform_ids:
                raise ValueError(f"未找到 Toy 波形: {toy_waveform_id}")
            current = rule_map[rule_id]
            next_enabled_by_rule_id[rule_id] = bool(item.get("enabled", current.enabled))
            next_waveform_id_by_rule_id[rule_id] = waveform_id or current.waveform_id
            next_toy_waveform_id_by_rule_id[rule_id] = toy_waveform_id or current.toy_waveform_id
            next_filters_by_rule_id[rule_id] = _resolve_updated_filters(current=current, incoming=item)
            updated_count += 1

        _validate_price_rule_overlaps(
            self.payload.bluetooth_event_rules,
            next_filters_by_rule_id,
            next_enabled_by_rule_id,
        )

        for rule_id, filters in next_filters_by_rule_id.items():
            current = rule_map[rule_id]
            current.enabled = next_enabled_by_rule_id[rule_id]
            current.waveform_id = next_waveform_id_by_rule_id[rule_id]
            current.toy_waveform_id = next_toy_waveform_id_by_rule_id.get(rule_id, current.toy_waveform_id)
            current.filters = filters

        self.payload.bluetooth_event_rules = _sort_event_rules(self.payload.bluetooth_event_rules)
        self.store.save(self.payload)
        return {
            "success": True,
            "updated_count": updated_count,
            "rule_groups": self.get_studio_payload()["rule_groups"],
        }

    def create_waveform(self, *, name: str, device_type: str = "ems") -> dict:
        if device_type == "toy":
            waveform = ToyWaveform(
                id=_generate_custom_waveform_id(self.payload),
                name=str(name or "").strip() or "自定义波形",
                builtin=False,
                editable=True,
                loop_count=1,
                steps=[ToyWaveformStep(duration_ms=200, motor_a=0, motor_b=0, motor_c=0)],
            )
            self.payload.toy_waveforms.insert(0, waveform)
        else:
            waveform = EmsWaveform(
                id=_generate_custom_waveform_id(self.payload),
                name=str(name or "").strip() or "自定义波形",
                builtin=False,
                editable=True,
                execution_mode="fixed",
                loop_count=1,
                steps=[EmsWaveformStep(duration_ms=200, channel_a=0, channel_b=0)],
            )
            self.payload.ems_waveforms.insert(0, waveform)
        self.store.save(self.payload)
        return _build_waveform_mutation_response(self.payload, waveform)

    def duplicate_waveform(self, *, source_waveform_id: str, name: str) -> dict:
        source = self._find_waveform_any(source_waveform_id)
        if isinstance(source, ToyWaveform):
            duplicated = ToyWaveform(
                id=_generate_custom_waveform_id(self.payload),
                name=str(name or "").strip() or f"{source.name} - 副本",
                builtin=False,
                editable=True,
                loop_count=source.loop_count,
                steps=[_clone_toy_waveform_step(step) for step in source.steps],
            )
            self.payload.toy_waveforms.insert(0, duplicated)
        else:
            duplicated = EmsWaveform(
                id=_generate_custom_waveform_id(self.payload),
                name=str(name or "").strip() or f"{source.name} - 副本",
                builtin=False,
                editable=True,
                execution_mode=source.execution_mode,
                loop_count=source.loop_count,
                steps=[_clone_waveform_step(step) for step in source.steps],
            )
            self.payload.ems_waveforms.insert(0, duplicated)
        self.store.save(self.payload)
        return _build_waveform_mutation_response(self.payload, duplicated)

    def update_waveform(self, *, waveform_id: str, name: str, steps: list[dict]) -> dict:
        waveform = self._find_waveform_any(waveform_id)
        if waveform.builtin:
            raise ValueError("内置波形不支持直接编辑")
        normalized_name = str(name or "").strip()
        if not normalized_name:
            raise ValueError("波形名称不能为空")
        if isinstance(waveform, ToyWaveform):
            normalized_steps = _merge_toy_editable_steps(existing_steps=waveform.steps, incoming_steps=steps)
        else:
            normalized_steps = _merge_editable_steps(existing_steps=waveform.steps, incoming_steps=steps)
        waveform.name = normalized_name
        waveform.steps = normalized_steps
        self.store.save(self.payload)
        return _build_waveform_mutation_response(self.payload, waveform)

    def delete_waveform(self, waveform_id: str) -> dict:
        waveform = self._find_waveform_any(waveform_id)
        if waveform.builtin:
            raise ValueError("内置波形不支持删除")
        if any(rule.waveform_id == waveform_id or rule.toy_waveform_id == waveform_id for rule in self.payload.bluetooth_event_rules):
            raise ValueError("请先修改规则绑定后再删除该波形")
        if isinstance(waveform, ToyWaveform):
            self.payload.toy_waveforms = [item for item in self.payload.toy_waveforms if item.id != waveform_id]
        else:
            self.payload.ems_waveforms = [item for item in self.payload.ems_waveforms if item.id != waveform_id]
        self.store.save(self.payload)
        payload_dict = payload_to_dict(self.payload)
        return {
            "success": True,
            "deleted_waveform_id": waveform_id,
            "ems_waveforms": payload_dict["ems_waveforms"],
            "toy_waveforms": payload_dict["toy_waveforms"],
        }

    def _find_waveform(self, waveform_id: str) -> EmsWaveform:
        waveform = next((item for item in self.payload.ems_waveforms if item.id == waveform_id), None)
        if waveform is None:
            raise ValueError(f"未找到波形: {waveform_id}")
        return waveform

    def _find_waveform_any(self, waveform_id: str) -> EmsWaveform | ToyWaveform:
        """在 EMS 和 Toy 波形列表中查找波形。"""
        waveform = next((item for item in self.payload.ems_waveforms if item.id == waveform_id), None)
        if waveform is not None:
            return waveform
        waveform = next((item for item in self.payload.toy_waveforms if item.id == waveform_id), None)
        if waveform is not None:
            return waveform
        raise ValueError(f"未找到波形: {waveform_id}")

    def _publish_bluetooth_control(self, payload: dict[str, Any]) -> None:
        """写入蓝牙波形控制日志。"""
        if self.event_hub is None or not hasattr(self.event_hub, "publish_control"):
            return
        self.event_hub.publish_control(
            {
                "type": "bluetooth_trigger",
                "timestamp": int(time.time()),
                "payload": payload,
            }
        )

    def _publish_bluetooth_connection_control(
        self,
        *,
        success: bool,
        device_id: str,
        device_name: str,
        message: str,
    ) -> None:
        """写入蓝牙连接控制日志，便于定位设备连接成功或失败。"""
        if self.event_hub is None or not hasattr(self.event_hub, "publish_control"):
            return
        self.event_hub.publish_control(
            {
                "type": "bluetooth_connect",
                "timestamp": int(time.time()),
                "payload": {
                    "success": bool(success),
                    "device_id": str(device_id or ""),
                    "device_name": str(device_name or ""),
                    "message": str(message or ("蓝牙连接成功" if success else "蓝牙连接失败")),
                },
            }
        )

    def _cleanup_finished_waveform_task(self) -> None:
        """清理已经结束的波形任务，避免历史状态影响后续抢占判断。"""
        if self._active_waveform_task is None or not self._active_waveform_task.done():
            return
        self._active_waveform_task = None
        self._active_waveform_request_id = ""
        self._active_waveform_id = ""
        self._active_waveform_strength = -1
        self._active_waveform_deadline = 0.0

    async def _run_waveform_until_deadline(
        self,
        waveform: EmsWaveform | ToyWaveform,
        *,
        request_id: str,
    ) -> None:
        """按当前截止时间循环执行波形，用于支持同波形续时长。"""
        while True:
            await self.runtime.play_waveform(waveform)
            async with self._waveform_lock:
                # 只有当前活动请求还能继续续播，旧请求被抢占后立即退出。
                if self._active_waveform_request_id != request_id:
                    return
                remaining_seconds = self._active_waveform_deadline - time.monotonic()
            if remaining_seconds <= 0:
                return


def create_real_bluetooth_runtime(
    *,
    scan_timeout_seconds: int,
    connect_timeout_seconds: int,
    auto_reconnect: bool,
) -> BluetoothRuntime:
    from app.bluetooth.runtime.bleak_runtime import BleakBluetoothRuntime

    return BleakBluetoothRuntime(
        scan_timeout_seconds=scan_timeout_seconds,
        connect_timeout_seconds=connect_timeout_seconds,
        auto_reconnect=auto_reconnect,
    )


def _build_rule_label(rule: dict) -> str:
    rule_id = str(rule.get("id", "") or "")
    tier = _resolve_price_tier_definition(rule_id)
    if tier is not None:
        filters = rule.get("filters", {}) if isinstance(rule.get("filters", {}), dict) else {}
        min_price = _coerce_non_negative_int(filters.get("min_price"), fallback=tier.min_price)
        max_price = _coerce_optional_non_negative_int(filters.get("max_price"))
        if max_price is None:
            return f"{tier.label} · {min_price}+"
        return f"{tier.label} · {min_price}-{max_price}"
    event_type = str(rule.get("event_type", "") or "")
    filters = rule.get("filters", {}) if isinstance(rule.get("filters", {}), dict) else {}
    if event_type in PRICE_FILTER_EVENT_TYPES and (
        filters.get("min_price") not in (None, "")
        or filters.get("max_price") not in (None, "")
    ):
        min_price = _coerce_non_negative_int(filters.get("min_price"))
        max_price = _coerce_optional_non_negative_int(filters.get("max_price"))
        event_label = RULE_GROUP_LABELS.get(event_type, event_type or "事件")
        if max_price is None:
            return f"{event_label}档位 · {min_price}+"
        return f"{event_label}档位 · {min_price}-{max_price}"
    return RULE_GROUP_LABELS.get(event_type, event_type or "unknown")


def _normalize_battery_level(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return max(0, min(int(value), 100))
    except (TypeError, ValueError):
        return None


def _generate_custom_waveform_id(payload: BluetoothConfigPayload) -> str:
    existing_ids = {item.id for item in payload.ems_waveforms} | {item.id for item in payload.toy_waveforms}
    while True:
        waveform_id = f"custom-wave-{uuid.uuid4().hex[:8]}"
        if waveform_id not in existing_ids:
            return waveform_id


def _clone_waveform_step(step: EmsWaveformStep) -> EmsWaveformStep:
    return EmsWaveformStep(
        duration_ms=step.duration_ms,
        channel_a=step.channel_a,
        channel_a_mode=step.channel_a_mode,
        channel_a_frequency=step.channel_a_frequency,
        channel_a_pulse_width=step.channel_a_pulse_width,
        channel_b=step.channel_b,
        channel_b_mode=step.channel_b_mode,
        channel_b_frequency=step.channel_b_frequency,
        channel_b_pulse_width=step.channel_b_pulse_width,
    )


def _clone_toy_waveform_step(step: ToyWaveformStep) -> ToyWaveformStep:
    return ToyWaveformStep(
        duration_ms=step.duration_ms,
        motor_a=step.motor_a,
        motor_b=step.motor_b,
        motor_c=step.motor_c,
    )


def _merge_editable_steps(*, existing_steps: list[EmsWaveformStep], incoming_steps: list[dict]) -> list[EmsWaveformStep]:
    if not incoming_steps:
        raise ValueError("波形至少需要一个分段")
    normalized_steps: list[EmsWaveformStep] = []
    for index, step in enumerate(incoming_steps):
        base_step = existing_steps[index] if index < len(existing_steps) else EmsWaveformStep(channel_a=0, channel_b=0)
        normalized_steps.append(
            EmsWaveformStep(
                duration_ms=max(1, int(step.get("duration_ms", base_step.duration_ms) or base_step.duration_ms)),
                channel_a=_normalize_waveform_strength(step.get("channel_a", base_step.channel_a)),
                channel_a_mode=base_step.channel_a_mode,
                channel_a_frequency=base_step.channel_a_frequency,
                channel_a_pulse_width=base_step.channel_a_pulse_width,
                channel_b=_normalize_waveform_strength(step.get("channel_b", base_step.channel_b)),
                channel_b_mode=base_step.channel_b_mode,
                channel_b_frequency=base_step.channel_b_frequency,
                channel_b_pulse_width=base_step.channel_b_pulse_width,
            )
        )
    return normalized_steps


def _merge_toy_editable_steps(*, existing_steps: list[ToyWaveformStep], incoming_steps: list[dict]) -> list[ToyWaveformStep]:
    if not incoming_steps:
        raise ValueError("波形至少需要一个分段")
    normalized_steps: list[ToyWaveformStep] = []
    for index, step in enumerate(incoming_steps):
        base_step = existing_steps[index] if index < len(existing_steps) else ToyWaveformStep()
        normalized_steps.append(
            ToyWaveformStep(
                duration_ms=max(1, int(step.get("duration_ms", base_step.duration_ms) or base_step.duration_ms)),
                motor_a=_normalize_toy_speed(step.get("motor_a", base_step.motor_a)),
                motor_b=_normalize_toy_speed(step.get("motor_b", base_step.motor_b)),
                motor_c=_normalize_toy_speed(step.get("motor_c", base_step.motor_c)),
            )
        )
    return normalized_steps


def _normalize_toy_speed(value) -> int:
    return max(0, min(int(value), 20))


def _normalize_waveform_strength(value) -> int:
    return max(0, min(int(value), 180))


def _resolve_waveform_max_strength(waveform: EmsWaveform | ToyWaveform) -> int:
    """计算波形在 A/B 通道或马达中的最大强度。"""
    if not waveform.steps:
        return 0
    if isinstance(waveform, ToyWaveform):
        return max(max(step.motor_a, step.motor_b, step.motor_c) for step in waveform.steps)
    return max(max(step.channel_a, step.channel_b) for step in waveform.steps)


def _resolve_overlay_display_max_strength(*, payload: dict[str, Any], active_waveform_strength: int) -> int:
    """给 OBS 小窗一个更贴近当前波形的显示量程，只影响视觉比例，不改变设备输出。"""
    device_type = str(payload.get("device_type", "") or "").lower()
    if device_type == "toy":
        return 20

    if active_waveform_strength > 0:
        return max(1, min(180, int(active_waveform_strength)))

    peak_strength = max(
        [
            max(0, int(payload.get("channel_a", 0) or 0)),
            max(0, int(payload.get("channel_b", 0) or 0)),
            *[
                max(
                    max(0, int(item.get("channel_a", 0) or 0)),
                    max(0, int(item.get("channel_b", 0) or 0)),
                )
                for item in payload.get("history", [])
                if isinstance(item, dict)
            ],
        ],
        default=0,
    )
    if peak_strength > 0:
        return max(50, min(180, peak_strength))
    return 50


def _resolve_waveform_duration_seconds(waveform: EmsWaveform | ToyWaveform) -> float:
    """计算单轮波形总时长，供抢占与续时长策略复用。"""
    total_duration_ms = sum(max(1, int(getattr(step, "duration_ms", 0) or 0)) for step in waveform.steps)
    return max(total_duration_ms / 1000, 0.001)


def _build_overlay_recent_events(event_hub: Any | None) -> list[dict[str, Any]]:
    """汇总 OBS 小窗需要展示的最近直播事件。"""
    if event_hub is None or not hasattr(event_hub, "snapshot"):
        return []
    events = [
        event
        for event in event_hub.snapshot()
        if _is_overlay_recent_event(event)
    ]
    return [_summarize_overlay_event(event) for event in reversed(events[-6:])]


def _is_overlay_recent_event(event: dict[str, Any]) -> bool:
    """判断直播事件是否需要进入 OBS 小窗列表（仅展示命中波形的事件）。"""
    event_type = str(event.get("event_type", "") or "")
    bluetooth_dispatch = event.get("bluetooth_dispatch")
    if not isinstance(bluetooth_dispatch, dict) or not bluetooth_dispatch.get("matched", False):
        return False
    return event_type in {"gift", "super_chat", "guard_buy", "guard_renew", "interact", "like"} or is_danmaku_event_type(event_type)


def _summarize_overlay_event(event: dict[str, Any]) -> dict[str, Any]:
    """把完整直播事件压缩成小窗展示摘要。"""
    event_type = str(event.get("event_type", "") or "")
    payload = event.get("payload", {}) if isinstance(event.get("payload", {}), dict) else {}
    bluetooth_dispatch = event.get("bluetooth_dispatch", {}) if isinstance(event.get("bluetooth_dispatch", {}), dict) else {}
    return {
        "event_type": event_type,
        "event_label": _resolve_overlay_event_label(event_type),
        "uname": str(event.get("uname", "") or ""),
        "timestamp": _coerce_non_negative_int(event.get("timestamp")),
        "msg": _resolve_overlay_event_message(event_type, payload),
        "guard_label": str(payload.get("guard_label", "") or ""),
        "waveform_id": str(bluetooth_dispatch.get("waveform_id", "") or ""),
        "waveform_name": str(bluetooth_dispatch.get("waveform_name", "") or ""),
        "success": bool(bluetooth_dispatch.get("success", False)),
    }


def _resolve_overlay_event_label(event_type: str) -> str:
    """把事件类型转成 OBS 小窗展示标签。"""
    if is_danmaku_event_type(event_type):
        return "弹幕"
    return {
        "gift": "礼物",
        "like": "点赞",
        "super_chat": "醒目留言",
        "guard_buy": "上舰",
        "guard_renew": "续费",
        "interact": "互动",
    }.get(event_type, event_type or "事件")


def _resolve_overlay_event_message(event_type: str, payload: dict[str, Any]) -> str:
    """从不同事件负载中提取 OBS 小窗主文本。"""
    if is_danmaku_event_type(event_type):
        return str(payload.get("msg", "") or "")
    if event_type == "like":
        like_text = str(payload.get("like_text", "") or "点赞")
        like_count = _coerce_non_negative_int(payload.get("like_count"))
        return f"{like_text} ({like_count})" if like_count > 0 else like_text
    if event_type == "super_chat":
        return str(payload.get("message", "") or payload.get("gift_name", "") or "")
    if event_type in {"gift", "guard_buy", "guard_renew"}:
        gift_name = str(payload.get("gift_name", "") or "")
        gift_num = _coerce_non_negative_int(payload.get("gift_num"))
        return f"{gift_name} x {gift_num}" if gift_num > 1 else gift_name
    if event_type == "interact":
        return str(payload.get("interact_label", "") or "")
    return ""


def _build_waveform_mutation_response(payload: BluetoothConfigPayload, waveform: EmsWaveform | ToyWaveform) -> dict:
    payload_dict = payload_to_dict(payload)
    if isinstance(waveform, ToyWaveform):
        waveform_data = next(item for item in payload_dict["toy_waveforms"] if item["id"] == waveform.id)
    else:
        waveform_data = next(item for item in payload_dict["ems_waveforms"] if item["id"] == waveform.id)
    return {
        "success": True,
        "waveform": waveform_data,
        "ems_waveforms": payload_dict["ems_waveforms"],
        "toy_waveforms": payload_dict["toy_waveforms"],
    }


def _resolve_updated_filters(*, current: BluetoothEventRule, incoming: dict[str, Any]) -> dict[str, Any]:
    next_filters = dict(current.filters)
    if current.event_type not in PRICE_FILTER_EVENT_TYPES:
        return next_filters

    min_price = _coerce_non_negative_int(incoming.get("min_price"), fallback=_coerce_non_negative_int(next_filters.get("min_price")))
    max_price = _coerce_optional_non_negative_int(incoming.get("max_price"))
    if max_price is not None and max_price < min_price:
        max_price = min_price
    result = {
        **next_filters,
        "min_price": min_price,
        "max_price": max_price,
    }
    if current.event_type == "gift":
        incoming_guard = incoming.get("guard_waveforms")
        if isinstance(incoming_guard, dict):
            result["guard_waveforms"] = incoming_guard
        else:
            result["guard_waveforms"] = next_filters.get("guard_waveforms", {})
    return result


def _validate_price_rule_overlaps(
    rules: list[BluetoothEventRule],
    next_filters_by_rule_id: dict[str, dict[str, Any]],
    next_enabled_by_rule_id: dict[str, bool],
) -> None:
    for event_type in PRICE_FILTER_EVENT_TYPES:
        enabled_price_rules: list[tuple[str, int, int | None]] = []
        
        for rule in rules:
            if rule.event_type != event_type:
                continue
            is_enabled = next_enabled_by_rule_id.get(rule.id, rule.enabled)
            if not is_enabled:
                continue
            filters = next_filters_by_rule_id.get(rule.id, dict(rule.filters))
            min_price = _coerce_non_negative_int(filters.get("min_price"))
            max_price = _coerce_optional_non_negative_int(filters.get("max_price"))
            enabled_price_rules.append((rule.id, min_price, max_price))

        enabled_price_rules.sort(
            key=lambda item: (
                item[1],
                float("inf") if item[2] is None else item[2],
                item[0],
            )
        )

        previous_rule_id = ""
        previous_max_price: int | None = None
        for rule_id, min_price, max_price in enabled_price_rules:
            if previous_max_price is not None and min_price <= previous_max_price:
                event_label = RULE_GROUP_LABELS.get(event_type, event_type or "事件")
                raise ValueError(f"{event_label}的价格区间重叠: {previous_rule_id} 与 {rule_id}")
            previous_rule_id = rule_id
            previous_max_price = max_price
            if previous_max_price is None:
                break


def _sort_event_rules(rules: list[BluetoothEventRule]) -> list[BluetoothEventRule]:
    grouped_rules: list[BluetoothEventRule] = []
    for event_type in RULE_GROUP_LABELS:
        event_rules = [item for item in rules if item.event_type == event_type]
        if event_type in PRICE_FILTER_EVENT_TYPES:
            event_rules = sorted(
                event_rules,
                key=lambda item: (
                    _coerce_non_negative_int(item.filters.get("min_price")),
                    float("inf") if item.filters.get("max_price") in (None, "") else _coerce_non_negative_int(item.filters.get("max_price")),
                    item.id,
                ),
            )
        grouped_rules.extend(event_rules)
    grouped_rules.extend([item for item in rules if item.event_type not in RULE_GROUP_LABELS])
    return grouped_rules


def _coerce_non_negative_int(value: Any, *, fallback: int = 0) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = fallback
    return max(0, normalized)


def _coerce_optional_non_negative_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return _coerce_non_negative_int(value)


def _resolve_price_tier_definition(rule_id: str):
    if rule_id in GIFT_TIER_BY_RULE_ID:
        return GIFT_TIER_BY_RULE_ID[rule_id]
    return SPECIAL_PRICE_TIER_BY_RULE_ID.get(rule_id)


def _resolve_scan_error_message(error: Exception) -> str:
    raw_message = str(error or "").strip()
    error_name = error.__class__.__name__
    normalized_message = raw_message.lower()
    if error_name == "BleakBluetoothNotAvailableError" or "no bluetooth adapter found" in normalized_message:
        return "当前主机未检测到蓝牙适配器"
    if raw_message:
        return f"蓝牙扫描失败: {raw_message}"
    return "蓝牙扫描失败，请检查蓝牙权限或适配器状态"
