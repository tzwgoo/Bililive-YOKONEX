from __future__ import annotations

from app.services.event_hub import EventHub


def test_event_hub_keeps_recent_events_only() -> None:
    hub = EventHub(max_events=2)
    hub.publish({"id": 1})
    hub.publish({"id": 2})
    hub.publish({"id": 3})

    assert hub.snapshot() == [{"id": 2}, {"id": 3}]
