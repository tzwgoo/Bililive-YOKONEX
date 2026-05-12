from __future__ import annotations

from typing import Any


def map_third_party_message(message: dict[str, Any], *, room_id: int) -> dict[str, Any] | None:
    cmd = str(message.get("cmd", ""))
    if not cmd:
        return None

    if cmd == "SEND_GIFT":
        data = message.get("data", {})
        return {
            "source": "third_party_ws",
            "event_type": "gift",
            "cmd": cmd,
            "room_id": room_id,
            "open_id": "",
            "uname": str(data.get("uname", "")),
            "timestamp": _as_int(data.get("timestamp")),
            "payload": {
                "gift_id": _as_int(data.get("giftId") or data.get("gift_id")),
                "gift_name": str(data.get("giftName") or data.get("gift_name") or ""),
                "gift_num": _as_int(data.get("num") or data.get("gift_num") or 0),
                "price": _as_int(data.get("price")),
                "r_price": _as_int(data.get("total_coin") or data.get("r_price") or data.get("price")),
            },
        }

    if cmd == "DANMU_MSG":
        info = message.get("info", [])
        content = ""
        uname = ""
        timestamp = _as_int(message.get("timestamp"))
        if isinstance(info, list):
            if len(info) > 1:
                content = str(info[1] or "")
            if len(info) > 2 and isinstance(info[2], list) and len(info[2]) > 1:
                uname = str(info[2][1] or "")
            if len(info) > 0 and isinstance(info[0], list) and len(info[0]) > 4:
                timestamp = _as_int(info[0][4])
        return {
            "source": "third_party_ws",
            "event_type": "danmaku",
            "cmd": cmd,
            "room_id": room_id,
            "open_id": "",
            "uname": uname,
            "timestamp": timestamp,
            "payload": {
                "msg": content,
            },
        }

    if cmd in {"LIKE_INFO_V3_CLICK", "LIKE_INFO_V3_UPDATE"}:
        data = message.get("data", {})
        return {
            "source": "third_party_ws",
            "event_type": "like",
            "cmd": cmd,
            "room_id": room_id,
            "open_id": "",
            "uname": str(data.get("uname", "")),
            "timestamp": _as_int(data.get("timestamp")),
            "payload": {
                "like_text": str(data.get("like_text") or "点赞"),
                "like_count": _as_int(data.get("like_count") or data.get("click_count")),
            },
        }

    return None


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
