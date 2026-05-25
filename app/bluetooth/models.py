from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class BluetoothSettings:
    enabled: bool = False
    scan_timeout_seconds: int = 8
    auto_reconnect: bool = False
    last_connected_device_id: str = ""
    last_connected_device_name: str = ""
    default_target_device_id: str = ""


@dataclass
class BluetoothDevice:
    device_id: str
    name: str
    device_type: str = "ems"
    protocol: str = "ems_v1"
    rssi: int = -48
    connected: bool = False


@dataclass
class EmsWaveformStep:
    duration_ms: int = 200
    channel_a: int = 40
    channel_b: int = 40


@dataclass
class EmsWaveform:
    id: str
    name: str
    builtin: bool = False
    editable: bool = True
    steps: list[EmsWaveformStep] = field(default_factory=list)


@dataclass
class BluetoothEventRule:
    id: str
    enabled: bool = False
    event_type: str = "gift"
    waveform_id: str = ""
    cooldown_seconds: int = 0
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class BluetoothConfigPayload:
    bluetooth_settings: BluetoothSettings = field(default_factory=BluetoothSettings)
    ems_waveforms: list[EmsWaveform] = field(default_factory=list)
    bluetooth_event_rules: list[BluetoothEventRule] = field(default_factory=list)


@dataclass
class BluetoothConnectionStatus:
    connected: bool = False
    device: BluetoothDevice | None = None
    message: str = "未连接"


def build_default_payload() -> BluetoothConfigPayload:
    default_waveform = EmsWaveform(
        id="ems-default-pulse",
        name="EMS 默认脉冲",
        builtin=True,
        editable=False,
        steps=[
            EmsWaveformStep(duration_ms=180, channel_a=48, channel_b=48),
            EmsWaveformStep(duration_ms=120, channel_a=0, channel_b=0),
        ],
    )
    return BluetoothConfigPayload(
        bluetooth_settings=BluetoothSettings(),
        ems_waveforms=[default_waveform],
        bluetooth_event_rules=[
            BluetoothEventRule(
                id="gift-default",
                enabled=False,
                event_type="gift",
                waveform_id=default_waveform.id,
                cooldown_seconds=0,
                filters={},
            ),
            BluetoothEventRule(
                id="like-default",
                enabled=False,
                event_type="like",
                waveform_id=default_waveform.id,
                cooldown_seconds=0,
                filters={},
            ),
            BluetoothEventRule(
                id="danmaku-default",
                enabled=False,
                event_type="danmaku",
                waveform_id=default_waveform.id,
                cooldown_seconds=3,
                filters={"keywords": []},
            ),
        ],
    )


def payload_to_dict(payload: BluetoothConfigPayload) -> dict[str, Any]:
    return asdict(payload)

