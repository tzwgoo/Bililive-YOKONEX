from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class SessionStatus(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    RECONNECTING = "reconnecting"
    STOPPING = "stopping"
    ERROR = "error"


class ServiceStatus(BaseModel):
    status: SessionStatus = SessionStatus.IDLE
    message: str = ""


class EventType(str, Enum):
    GIFT = "gift"
    DANMAKU = "danmaku"
    DANMAKU_CAPTAIN = "danmaku_captain"
    DANMAKU_COMMANDER = "danmaku_commander"
    DANMAKU_GOVERNOR = "danmaku_governor"
    LIKE = "like"
    SYSTEM = "system"


class LiveEvent(BaseModel):
    source: str = "open_live"
    event_type: EventType
    cmd: str
    room_id: int
    open_id: str
    uname: str
    timestamp: int
    payload: dict


DANMAKU_EVENT_TYPES = {
    EventType.DANMAKU.value,
    EventType.DANMAKU_CAPTAIN.value,
    EventType.DANMAKU_COMMANDER.value,
    EventType.DANMAKU_GOVERNOR.value,
}


def resolve_danmaku_event_type(guard_level: int) -> EventType:
    normalized_guard_level = max(0, int(guard_level or 0))
    if normalized_guard_level == 1:
        return EventType.DANMAKU_GOVERNOR
    if normalized_guard_level == 2:
        return EventType.DANMAKU_COMMANDER
    if normalized_guard_level == 3:
        return EventType.DANMAKU_CAPTAIN
    return EventType.DANMAKU


def is_danmaku_event_type(event_type: str) -> bool:
    return str(event_type or "") in DANMAKU_EVENT_TYPES
