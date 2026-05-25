from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class BluetoothSettings:
    enabled: bool = False
    scan_timeout_seconds: int = 15
    connect_timeout_seconds: int = 20
    auto_reconnect: bool = True
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
    channel_a_mode: int = 1
    channel_a_frequency: int = 10
    channel_a_pulse_width: int = 5
    channel_b: int = 40
    channel_b_mode: int = 1
    channel_b_frequency: int = 10
    channel_b_pulse_width: int = 5


@dataclass
class EmsWaveform:
    id: str
    name: str
    builtin: bool = False
    editable: bool = True
    execution_mode: str = "fixed"
    loop_count: int = 1
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
    battery_level: int | None = None
    message: str = "未连接"


def build_default_payload() -> BluetoothConfigPayload:
    from app.bluetooth.gift_tiers import build_default_gift_rules
    from app.bluetooth.ems_builtin_waveforms import create_defaults

    default_waveforms = create_defaults()
    return BluetoothConfigPayload(
        bluetooth_settings=BluetoothSettings(),
        ems_waveforms=default_waveforms,
        bluetooth_event_rules=[
            *[
                BluetoothEventRule(
                    id=str(item["id"]),
                    enabled=bool(item["enabled"]),
                    event_type=str(item["event_type"]),
                    waveform_id=str(item["waveform_id"]),
                    cooldown_seconds=int(item["cooldown_seconds"]),
                    filters=dict(item["filters"]),
                )
                for item in build_default_gift_rules(enabled=True)
            ],
            BluetoothEventRule(
                id="like-default",
                enabled=True,
                event_type="like",
                waveform_id="ems-preset-01",
                cooldown_seconds=0,
                filters={},
            ),
            BluetoothEventRule(
                id="danmaku-default",
                enabled=True,
                event_type="danmaku",
                waveform_id="ems-preset-03",
                cooldown_seconds=3,
                filters={"keywords": []},
            ),
        ],
    )


def payload_to_dict(payload: BluetoothConfigPayload) -> dict[str, Any]:
    return asdict(payload)
