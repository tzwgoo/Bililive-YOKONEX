from __future__ import annotations

import json

from app.bluetooth.storage import BluetoothSettingsStore


def test_store_returns_default_payload_when_file_missing(tmp_path) -> None:
    store = BluetoothSettingsStore(tmp_path / "bluetooth.json")

    payload = store.load()

    assert payload.bluetooth_settings.enabled is False
    assert payload.bluetooth_settings.scan_timeout_seconds == 8
    assert payload.ems_waveforms
    assert payload.bluetooth_event_rules


def test_store_loads_existing_payload_and_normalizes_fields(tmp_path) -> None:
    path = tmp_path / "bluetooth.json"
    path.write_text(
        json.dumps(
            {
                "bluetooth_settings": {
                    "enabled": True,
                    "scan_timeout_seconds": 12,
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
    assert payload.bluetooth_settings.last_connected_device_id == "demo-device"
    assert payload.ems_waveforms[0].id == "custom-wave"
    assert payload.bluetooth_event_rules[0].waveform_id == "custom-wave"


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
