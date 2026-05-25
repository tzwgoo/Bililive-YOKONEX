from __future__ import annotations

import json
from pathlib import Path

from app.bluetooth.models import BluetoothConfigPayload
from app.bluetooth.models import BluetoothEventRule
from app.bluetooth.models import BluetoothSettings
from app.bluetooth.models import EmsWaveform
from app.bluetooth.models import EmsWaveformStep
from app.bluetooth.models import build_default_payload
from app.bluetooth.models import payload_to_dict


class BluetoothSettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> BluetoothConfigPayload:
        if not self.path.exists():
            return build_default_payload()

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        defaults = build_default_payload()

        settings_data = payload.get("bluetooth_settings", {})
        settings = BluetoothSettings(
            enabled=bool(settings_data.get("enabled", defaults.bluetooth_settings.enabled)),
            scan_timeout_seconds=max(1, int(settings_data.get("scan_timeout_seconds", defaults.bluetooth_settings.scan_timeout_seconds))),
            auto_reconnect=bool(settings_data.get("auto_reconnect", defaults.bluetooth_settings.auto_reconnect)),
            last_connected_device_id=str(settings_data.get("last_connected_device_id", "")),
            last_connected_device_name=str(settings_data.get("last_connected_device_name", "")),
            default_target_device_id=str(settings_data.get("default_target_device_id", "")),
        )

        waveforms = [
            _normalize_waveform(item)
            for item in payload.get("ems_waveforms", [])
            if isinstance(item, dict)
        ]
        if not waveforms:
            waveforms = defaults.ems_waveforms

        rules = [
            _normalize_rule(item)
            for item in payload.get("bluetooth_event_rules", [])
            if isinstance(item, dict)
        ]
        if not rules:
            rules = defaults.bluetooth_event_rules

        return BluetoothConfigPayload(
            bluetooth_settings=settings,
            ems_waveforms=waveforms,
            bluetooth_event_rules=rules,
        )

    def save(self, payload: BluetoothConfigPayload) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload_to_dict(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _normalize_waveform(item: dict) -> EmsWaveform:
    steps = item.get("steps", [])
    normalized_steps = [
        EmsWaveformStep(
            duration_ms=max(1, int(step.get("duration_ms", 200))),
            channel_a=max(0, int(step.get("channel_a", 40))),
            channel_b=max(0, int(step.get("channel_b", 40))),
        )
        for step in steps
        if isinstance(step, dict)
    ]
    if not normalized_steps:
        normalized_steps = [EmsWaveformStep()]
    return EmsWaveform(
        id=str(item.get("id", "custom-wave")),
        name=str(item.get("name", "自定义波形")),
        builtin=bool(item.get("builtin", False)),
        editable=bool(item.get("editable", True)),
        steps=normalized_steps,
    )


def _normalize_rule(item: dict) -> BluetoothEventRule:
    filters = item.get("filters", {})
    return BluetoothEventRule(
        id=str(item.get("id", "rule-default")),
        enabled=bool(item.get("enabled", False)),
        event_type=str(item.get("event_type", "gift")),
        waveform_id=str(item.get("waveform_id", "")),
        cooldown_seconds=max(0, int(item.get("cooldown_seconds", 0))),
        filters=filters if isinstance(filters, dict) else {},
    )

