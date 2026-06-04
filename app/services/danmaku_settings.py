from __future__ import annotations

from app.models import is_danmaku_event_type
from app.models import resolve_danmaku_event_type


FIXED_DANMAKU_COMMAND_ID = "danmaku_trigger"
FIXED_LIKE_COMMAND_ID = "like_trigger"
FIXED_DANMAKU_COMMAND_IDS = {
    "danmaku": FIXED_DANMAKU_COMMAND_ID,
    "danmaku_captain": "danmaku_captain_trigger",
    "danmaku_commander": "danmaku_commander_trigger",
    "danmaku_governor": "danmaku_governor_trigger",
}


def resolve_fixed_danmaku_command_id(*, event_type: str, guard_level: int = 0) -> str:
    normalized_event_type = str(event_type or "").strip()
    if not is_danmaku_event_type(normalized_event_type):
        normalized_event_type = resolve_danmaku_event_type(guard_level).value
    return FIXED_DANMAKU_COMMAND_IDS.get(normalized_event_type, FIXED_DANMAKU_COMMAND_ID)
