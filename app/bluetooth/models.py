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
class ToyWaveformStep:
    """飞机杯/跳蛋波形步进 — 最多 3 路马达 (A/B/C)，速度 0-20。"""
    duration_ms: int = 200
    motor_a: int = 0
    motor_b: int = 0
    motor_c: int = 0


@dataclass
class ToyWaveform:
    """飞机杯/跳蛋波形 — 由多个 ToyWaveformStep 组成。"""
    id: str
    name: str
    builtin: bool = False
    editable: bool = True
    loop_count: int = 1
    steps: list[ToyWaveformStep] = field(default_factory=list)


@dataclass
class BluetoothEventRule:
    id: str
    enabled: bool = False
    event_type: str = "gift"
    waveform_id: str = ""
    toy_waveform_id: str = ""
    cooldown_seconds: int = 0
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class BluetoothConfigPayload:
    bluetooth_settings: BluetoothSettings = field(default_factory=BluetoothSettings)
    ems_waveforms: list[EmsWaveform] = field(default_factory=list)
    toy_waveforms: list[ToyWaveform] = field(default_factory=list)
    bluetooth_event_rules: list[BluetoothEventRule] = field(default_factory=list)


@dataclass
class BluetoothConnectionStatus:
    connected: bool = False
    device: BluetoothDevice | None = None
    battery_level: int | None = None
    message: str = "未连接"


BLUETOOTH_DANMAKU_RULE_DEFINITIONS = [
    {"id": "danmaku-normal", "event_type": "danmaku", "waveform_id": "ems-preset-03", "toy_waveform_id": "toy-preset-03", "label": "普通弹幕"},
    {"id": "danmaku-captain", "event_type": "danmaku_captain", "waveform_id": "ems-preset-04", "toy_waveform_id": "toy-preset-04", "label": "舰长弹幕"},
    {"id": "danmaku-commander", "event_type": "danmaku_commander", "waveform_id": "ems-preset-05", "toy_waveform_id": "toy-preset-05", "label": "提督弹幕"},
    {"id": "danmaku-governor", "event_type": "danmaku_governor", "waveform_id": "ems-preset-06", "toy_waveform_id": "toy-preset-06", "label": "总督弹幕"},
]


BLUETOOTH_SPECIAL_EVENT_RULE_DEFINITIONS = [
    {"id": "interact-default", "event_type": "interact", "waveform_id": "ems-preset-02", "toy_waveform_id": "toy-preset-02", "label": "互动事件", "filters": {"interact_types": []}},
]


def build_default_danmaku_rules(*, enabled: bool = True) -> list[BluetoothEventRule]:
    """构建默认弹幕蓝牙规则。"""
    return [
        BluetoothEventRule(
            id=str(item["id"]),
            enabled=bool(enabled),
            event_type=str(item["event_type"]),
            waveform_id=str(item["waveform_id"]),
            toy_waveform_id=str(item.get("toy_waveform_id", "")),
            cooldown_seconds=3,
            filters={"keywords": []},
        )
        for item in BLUETOOTH_DANMAKU_RULE_DEFINITIONS
    ]


def build_default_special_event_rules(*, enabled: bool = True) -> list[BluetoothEventRule]:
    """构建默认 SC、舰队和互动蓝牙规则。"""
    from app.bluetooth.price_tiers import build_default_special_price_rules

    return [
        *(
            BluetoothEventRule(
                id=str(item["id"]),
                enabled=bool(item["enabled"]),
                event_type=str(item["event_type"]),
                waveform_id=str(item["waveform_id"]),
                toy_waveform_id=str(item.get("toy_waveform_id", "")),
                cooldown_seconds=int(item["cooldown_seconds"]),
                filters=dict(item["filters"]),
            )
            for item in build_default_special_price_rules(enabled=enabled)
        ),
        *(
        BluetoothEventRule(
            id=str(item["id"]),
            enabled=bool(enabled),
            event_type=str(item["event_type"]),
            waveform_id=str(item["waveform_id"]),
            toy_waveform_id=str(item.get("toy_waveform_id", "")),
            cooldown_seconds=0,
            filters=dict(item["filters"]),
        )
        for item in BLUETOOTH_SPECIAL_EVENT_RULE_DEFINITIONS
        ),
    ]


def build_default_payload() -> BluetoothConfigPayload:
    from app.bluetooth.gift_tiers import build_default_gift_rules
    from app.bluetooth.ems_builtin_waveforms import create_defaults
    from app.bluetooth.toy_builtin_waveforms import create_toy_defaults

    default_ems_waveforms = create_defaults()
    default_toy_waveforms = create_toy_defaults()
    return BluetoothConfigPayload(
        bluetooth_settings=BluetoothSettings(),
        ems_waveforms=default_ems_waveforms,
        toy_waveforms=default_toy_waveforms,
        bluetooth_event_rules=[
            *[
                BluetoothEventRule(
                    id=str(item["id"]),
                    enabled=bool(item["enabled"]),
                    event_type=str(item["event_type"]),
                    waveform_id=str(item["waveform_id"]),
                    toy_waveform_id=str(item.get("toy_waveform_id", "")),
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
                toy_waveform_id="toy-preset-01",
                cooldown_seconds=0,
                filters={},
            ),
            *build_default_danmaku_rules(enabled=True),
            *build_default_special_event_rules(enabled=True),
        ],
    )


def payload_to_dict(payload: BluetoothConfigPayload) -> dict[str, Any]:
    """把蓝牙配置对象转换成可 JSON 序列化字典。"""
    return asdict(payload)
