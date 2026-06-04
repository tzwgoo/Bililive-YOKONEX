from __future__ import annotations

from app.services.event_hub import EventHub


def test_event_hub_keeps_recent_events_only() -> None:
    hub = EventHub(max_events=2)
    hub.publish({"id": 1})
    hub.publish({"id": 2})
    hub.publish({"id": 3})

    assert hub.snapshot() == [{"id": 2}, {"id": 3}]


def test_event_hub_supports_control_log_stream() -> None:
    hub = EventHub(max_events=2)
    hub.publish_control({"type": "command_send", "payload": {"command_id": "command_one"}})
    hub.publish_control({"type": "bluetooth_trigger", "payload": {"waveform_id": "ems-preset-01"}})
    hub.publish_control({"type": "bluetooth_trigger", "payload": {"waveform_id": "ems-preset-02"}})

    assert hub.control_snapshot() == [
        {"type": "bluetooth_trigger", "payload": {"waveform_id": "ems-preset-01"}},
        {"type": "bluetooth_trigger", "payload": {"waveform_id": "ems-preset-02"}},
    ]
