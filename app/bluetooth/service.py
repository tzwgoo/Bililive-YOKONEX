from __future__ import annotations

import logging
from pathlib import Path
import uuid

from app.bluetooth.gift_tiers import GIFT_TIER_BY_RULE_ID
from app.bluetooth.models import BluetoothConnectionStatus
from app.bluetooth.models import BluetoothConfigPayload
from app.bluetooth.models import BluetoothDevice
from app.bluetooth.models import BluetoothEventRule
from app.bluetooth.models import EmsWaveform
from app.bluetooth.models import EmsWaveformStep
from app.bluetooth.models import payload_to_dict
from app.bluetooth.runtime.base import BluetoothRuntime
from app.bluetooth.runtime.memory_runtime import MemoryBluetoothRuntime
from app.bluetooth.storage import BluetoothSettingsStore


logger = logging.getLogger(__name__)

RULE_GROUP_LABELS = {
    "gift": "礼物事件",
    "like": "点赞事件",
    "danmaku": "弹幕事件",
}


class BluetoothService:
    def __init__(
        self,
        *,
        store: BluetoothSettingsStore,
        runtime: BluetoothRuntime,
        payload: BluetoothConfigPayload | None = None,
    ) -> None:
        self.store = store
        self.runtime = runtime
        self.payload = payload or self.store.load()

    @classmethod
    def create_default(cls, *, config_path: Path) -> "BluetoothService":
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
        )

    async def scan(self) -> list[BluetoothDevice]:
        devices = await self.runtime.scan()
        return devices

    async def connect(self, device_id: str) -> BluetoothConnectionStatus:
        status = await self.runtime.connect(device_id)
        if status.device is not None:
            self.payload.bluetooth_settings.last_connected_device_id = status.device.device_id
            self.payload.bluetooth_settings.last_connected_device_name = status.device.name
            self.payload.bluetooth_settings.default_target_device_id = status.device.device_id
            self.store.save(self.payload)
        return status

    async def disconnect(self) -> BluetoothConnectionStatus:
        return await self.runtime.disconnect()

    async def trigger_waveform(self, *, event_type: str, waveform_id: str) -> dict:
        waveform = next((item for item in self.payload.ems_waveforms if item.id == waveform_id), None)
        if waveform is None:
            return {
                "matched": True,
                "event_type": event_type,
                "waveform_id": waveform_id,
                "success": False,
                "message": "目标波形不存在",
            }
        try:
            await self.runtime.play_waveform(waveform)
        except Exception as exc:
            return {
                "matched": True,
                "event_type": event_type,
                "waveform_id": waveform_id,
                "success": False,
                "message": f"波形执行失败: {exc}",
            }
        return {
            "matched": True,
            "event_type": event_type,
            "waveform_id": waveform_id,
            "success": True,
            "message": f"{event_type} 已触发波形 {waveform.name}",
        }

    def get_status_payload(self) -> dict:
        status = self.runtime.get_status()
        waveform_name_map = {
            item.id: item.name
            for item in self.payload.ems_waveforms
        }
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
            "waveforms": payload_to_dict(self.payload)["ems_waveforms"],
            "rules": [
                {
                    **item,
                    "event_label": RULE_GROUP_LABELS.get(str(item.get("event_type", "")), str(item.get("event_type", "unknown"))),
                    "rule_label": _build_rule_label(item),
                    "waveform_name": waveform_name_map.get(str(item.get("waveform_id", "")), str(item.get("waveform_id", "-") or "-")),
                }
                for item in payload_to_dict(self.payload)["bluetooth_event_rules"]
            ],
        }

    def get_overlay_payload(self) -> dict:
        payload = self.runtime.get_overlay_payload()
        return {
            "connected": bool(payload.get("connected", False)),
            "device_name": str(payload.get("device_name", "") or ""),
            "waveform_name": str(payload.get("waveform_name", "") or ""),
            "battery_level": _normalize_battery_level(payload.get("battery_level")),
            "channel_a": max(0, int(payload.get("channel_a", 0) or 0)),
            "channel_b": max(0, int(payload.get("channel_b", 0) or 0)),
            "step_index": max(0, int(payload.get("step_index", 0) or 0)),
            "step_count": max(0, int(payload.get("step_count", 0) or 0)),
            "updated_at": float(payload.get("updated_at", 0) or 0),
            "history": [
                {
                    "channel_a": max(0, int(item.get("channel_a", 0) or 0)),
                    "channel_b": max(0, int(item.get("channel_b", 0) or 0)),
                }
                for item in payload.get("history", [])
                if isinstance(item, dict)
            ][-90:],
            "revision": max(0, int(payload.get("revision", 0) or 0)),
        }

    def get_studio_payload(self) -> dict:
        waveforms = payload_to_dict(self.payload)["ems_waveforms"]
        waveform_name_map = {
            item.id: item.name
            for item in self.payload.ems_waveforms
        }
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
            "waveforms": waveforms,
            "rule_groups": grouped_rules,
        }

    def save_rules(self, rules: list[dict]) -> dict:
        waveform_ids = {item.id for item in self.payload.ems_waveforms}
        rule_map = {item.id: item for item in self.payload.bluetooth_event_rules}
        updated_count = 0
        for item in rules:
            rule_id = str(item.get("id", "") or "")
            waveform_id = str(item.get("waveform_id", "") or "")
            if rule_id not in rule_map:
                raise ValueError(f"未找到规则: {rule_id}")
            if waveform_id not in waveform_ids:
                raise ValueError(f"未找到波形: {waveform_id}")
            current = rule_map[rule_id]
            current.enabled = bool(item.get("enabled", current.enabled))
            current.waveform_id = waveform_id
            updated_count += 1
        self.store.save(self.payload)
        return {
            "success": True,
            "updated_count": updated_count,
            "rule_groups": self.get_studio_payload()["rule_groups"],
        }

    def create_waveform(self, *, name: str) -> dict:
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
        source = self._find_waveform(source_waveform_id)
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
        waveform = self._find_waveform(waveform_id)
        if waveform.builtin:
            raise ValueError("内置波形不支持直接编辑")
        normalized_name = str(name or "").strip()
        if not normalized_name:
            raise ValueError("波形名称不能为空")
        normalized_steps = _merge_editable_steps(existing_steps=waveform.steps, incoming_steps=steps)
        waveform.name = normalized_name
        waveform.steps = normalized_steps
        self.store.save(self.payload)
        return _build_waveform_mutation_response(self.payload, waveform)

    def delete_waveform(self, waveform_id: str) -> dict:
        waveform = self._find_waveform(waveform_id)
        if waveform.builtin:
            raise ValueError("内置波形不支持删除")
        if any(rule.waveform_id == waveform_id for rule in self.payload.bluetooth_event_rules):
            raise ValueError("请先修改规则绑定后再删除该波形")
        self.payload.ems_waveforms = [item for item in self.payload.ems_waveforms if item.id != waveform_id]
        self.store.save(self.payload)
        return {
            "success": True,
            "deleted_waveform_id": waveform_id,
            "waveforms": payload_to_dict(self.payload)["ems_waveforms"],
        }

    def _find_waveform(self, waveform_id: str) -> EmsWaveform:
        waveform = next((item for item in self.payload.ems_waveforms if item.id == waveform_id), None)
        if waveform is None:
            raise ValueError(f"未找到波形: {waveform_id}")
        return waveform


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
    if rule_id in GIFT_TIER_BY_RULE_ID:
        tier = GIFT_TIER_BY_RULE_ID[rule_id]
        if tier.max_price is None:
            return f"{tier.label} · {tier.min_price}+"
        return f"{tier.label} · {tier.min_price}-{tier.max_price}"
    event_type = str(rule.get("event_type", "") or "")
    return RULE_GROUP_LABELS.get(event_type, event_type or "unknown")


def _normalize_battery_level(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return max(0, min(int(value), 100))
    except (TypeError, ValueError):
        return None


def _generate_custom_waveform_id(payload: BluetoothConfigPayload) -> str:
    existing_ids = {item.id for item in payload.ems_waveforms}
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


def _normalize_waveform_strength(value) -> int:
    return max(0, min(int(value), 180))


def _build_waveform_mutation_response(payload: BluetoothConfigPayload, waveform: EmsWaveform) -> dict:
    waveform_data = next(item for item in payload_to_dict(payload)["ems_waveforms"] if item["id"] == waveform.id)
    return {
        "success": True,
        "waveform": waveform_data,
        "waveforms": payload_to_dict(payload)["ems_waveforms"],
    }
