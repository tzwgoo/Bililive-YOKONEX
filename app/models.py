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
