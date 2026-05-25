from __future__ import annotations

import json

from app.bluetooth.storage import BluetoothSettingsStore


def test_store_returns_default_payload_when_file_missing(tmp_path) -> None:
    store = BluetoothSettingsStore(tmp_path / "bluetooth.json")

    payload = store.load()

    assert payload.bluetooth_settings.enabled is False
    assert payload.bluetooth_settings.scan_timeout_seconds == 15
    assert payload.bluetooth_settings.connect_timeout_seconds == 20
    assert payload.bluetooth_settings.auto_reconnect is True
    assert payload.ems_waveforms
    assert payload.bluetooth_event_rules
    assert len(payload.ems_waveforms) == 17
    assert payload.ems_waveforms[0].id == "ems-default-pulse"
    assert payload.ems_waveforms[1].id == "ems-preset-01"
    assert payload.ems_waveforms[1].name == "EMS 预设 01 - 呼吸"
    assert payload.ems_waveforms[6].id == "ems-preset-06"
    assert len(payload.bluetooth_event_rules) == 12
    assert payload.bluetooth_event_rules[0].enabled is True
    assert payload.bluetooth_event_rules[9].enabled is True
    assert payload.bluetooth_event_rules[10].enabled is True
    assert payload.bluetooth_event_rules[11].enabled is True
    assert payload.bluetooth_event_rules[0].id == "gift-tier-01"
    assert payload.bluetooth_event_rules[0].waveform_id == "ems-preset-01"
    assert payload.bluetooth_event_rules[0].filters == {"min_price": 0, "max_price": 99}
    assert payload.bluetooth_event_rules[9].id == "gift-tier-10"
    assert payload.bluetooth_event_rules[9].waveform_id == "ems-preset-10"
    assert payload.bluetooth_event_rules[10].waveform_id == "ems-preset-01"
    assert payload.bluetooth_event_rules[11].waveform_id == "ems-preset-03"


def test_store_loads_existing_payload_and_normalizes_fields(tmp_path) -> None:
    path = tmp_path / "bluetooth.json"
    path.write_text(
        json.dumps(
            {
                "bluetooth_settings": {
                    "enabled": True,
                    "scan_timeout_seconds": 12,
                    "connect_timeout_seconds": 18,
                    "auto_reconnect": True,
                    "last_connected_device_id": "demo-device",
                },
                "ems_waveforms": [
                    {
                        "id": "custom-wave",
                        "name": "自定义波形",
                        "builtin": False,
                        "editable": True,
                        "steps": [
                            {
                                "duration_ms": 180,
                                "channel_a": 45,
                                "channel_b": 60,
                                "channel_a_mode": 6,
                                "channel_b_mode": 6,
                            }
                        ],
                    }
                ],
                "bluetooth_event_rules": [
                    {
                        "id": "gift-default",
                        "enabled": True,
                        "event_type": "gift",
                        "waveform_id": "custom-wave",
                        "cooldown_seconds": 2,
                        "filters": {},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    store = BluetoothSettingsStore(path)

    payload = store.load()

    assert payload.bluetooth_settings.enabled is True
    assert payload.bluetooth_settings.scan_timeout_seconds == 12
    assert payload.bluetooth_settings.connect_timeout_seconds == 18
    assert payload.bluetooth_settings.last_connected_device_id == "demo-device"
    assert payload.ems_waveforms[0].id == "ems-default-pulse"
    custom_wave = next(item for item in payload.ems_waveforms if item.id == "custom-wave")
    assert custom_wave.execution_mode == "fixed"
    assert custom_wave.steps[0].channel_a_mode == 6
    assert custom_wave.steps[0].channel_b_mode == 6
    assert payload.bluetooth_event_rules[0].waveform_id == "custom-wave"


def test_store_migrates_legacy_default_rules_to_enabled(tmp_path) -> None:
    path = tmp_path / "bluetooth.json"
    path.write_text(
        json.dumps(
            {
                "bluetooth_event_rules": [
                    {
                        "id": "gift-default",
                        "enabled": False,
                        "event_type": "gift",
                        "waveform_id": "ems-preset-06",
                        "cooldown_seconds": 0,
                        "filters": {},
                    },
                    {
                        "id": "like-default",
                        "enabled": False,
                        "event_type": "like",
                        "waveform_id": "ems-preset-01",
                        "cooldown_seconds": 0,
                        "filters": {},
                    },
                    {
                        "id": "danmaku-default",
                        "enabled": False,
                        "event_type": "danmaku",
                        "waveform_id": "ems-preset-03",
                        "cooldown_seconds": 3,
                        "filters": {"keywords": []},
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    store = BluetoothSettingsStore(path)

    payload = store.load()

    gift_rules = [rule for rule in payload.bluetooth_event_rules if rule.event_type == "gift"]
    assert len(gift_rules) == 10
    assert all(rule.enabled is True for rule in gift_rules)
    assert gift_rules[0].waveform_id == "ems-preset-01"
    assert gift_rules[-1].waveform_id == "ems-preset-10"


def test_store_save_persists_round_trip_payload(tmp_path) -> None:
    path = tmp_path / "bluetooth.json"
    store = BluetoothSettingsStore(path)
    payload = store.load()
    payload.bluetooth_settings.enabled = True
    payload.bluetooth_settings.default_target_device_id = "demo-device"

    store.save(payload)

    reloaded = store.load()

    assert reloaded.bluetooth_settings.enabled is True
    assert reloaded.bluetooth_settings.default_target_device_id == "demo-device"
