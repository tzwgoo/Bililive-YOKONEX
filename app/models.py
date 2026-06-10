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
    # 当前运行态只保留第三方消息流，这里默认沿用第三方事件源标识。
    source: str = "third_party_ws"
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


def normalize_event_type_value(event_type: object) -> str:
    """统一提取事件类型值，兼容字符串、str 枚举和其他历史传参。"""
    if isinstance(event_type, Enum):
        return str(event_type.value or "").strip()
    return str(event_type or "").strip()


def resolve_incoming_danmaku_event_type(event_type: object, guard_level: object) -> str:
    """按弹幕守护等级纠正事件类型，避免第三方链路把专属弹幕降级成普通弹幕。"""
    normalized_event_type = normalize_event_type_value(event_type)
    if normalized_event_type and normalized_event_type != EventType.DANMAKU.value and normalized_event_type in DANMAKU_EVENT_TYPES:
        return normalized_event_type
    return resolve_danmaku_event_type(_normalize_guard_level(guard_level)).value


def is_danmaku_event_type(event_type: str | object) -> bool:
    return normalize_event_type_value(event_type) in DANMAKU_EVENT_TYPES


def _normalize_guard_level(guard_level: object) -> int:
    try:
        return max(0, int(guard_level or 0))
    except (TypeError, ValueError):
        return 0
