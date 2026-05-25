from __future__ import annotations

from typing import Any


def map_third_party_message(message: dict[str, Any], *, room_id: int) -> dict[str, Any] | None:
    cmd = str(message.get("cmd", ""))
    if not cmd:
        return None

    if cmd in {"SEND_GIFT", "COMBO_SEND"}:
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
                "gift_num": _as_int(data.get("combo_num") or data.get("num") or data.get("gift_num") or 0),
                "price": _as_int(data.get("price")),
                "r_price": _as_int(
                    data.get("combo_total_coin")
                    or data.get("total_coin")
                    or data.get("r_price")
                    or data.get("price")
                ),
            },
        }

    if cmd == "GUARD_BUY":
        data = message.get("data", {})
        return _build_gift_event(
            cmd=cmd,
            room_id=room_id,
            uname=str(data.get("username") or data.get("uname") or ""),
            timestamp=_as_int(data.get("start_time") or data.get("timestamp")),
            payload={
                "gift_id": _as_int(data.get("gift_id") or data.get("giftId")),
                "gift_name": str(data.get("gift_name") or data.get("giftName") or data.get("role_name") or "大航海"),
                "gift_num": _as_int(data.get("num") or 1),
                "price": _as_int(data.get("price")),
                "r_price": _as_int(data.get("price")),
            },
        )

    if cmd in {"SUPER_CHAT_MESSAGE", "SUPER_CHAT_MESSAGE_JPN"}:
        data = message.get("data", {})
        gift = data.get("gift", {})
        user_info = data.get("user_info", {})
        uinfo = data.get("uinfo", {})
        base_info = uinfo.get("base", {}) if isinstance(uinfo, dict) else {}
        return _build_gift_event(
            cmd=cmd,
            room_id=room_id,
            uname=str(user_info.get("uname") or base_info.get("name") or base_info.get("uname") or ""),
            timestamp=_as_int(data.get("ts") or data.get("start_time") or data.get("send_time")),
            payload={
                "gift_id": _as_int(gift.get("gift_id") or 12000),
                "gift_name": str(gift.get("gift_name") or "醒目留言"),
                "gift_num": _as_int(gift.get("num") or 1),
                "price": _as_int(data.get("price")),
                "r_price": _as_int(data.get("price")),
                "message": str(data.get("message") or ""),
            },
        )

    if cmd == "USER_TOAST_MSG":
        data = message.get("data", {})
        return _build_gift_event(
            cmd=cmd,
            room_id=room_id,
            uname=str(data.get("username") or data.get("uname") or ""),
            timestamp=_as_int(data.get("start_time") or data.get("timestamp")),
            payload={
                "gift_id": _as_int(data.get("gift_id") or data.get("giftId")),
                "gift_name": str(data.get("gift_name") or data.get("giftName") or data.get("role_name") or "庆祝消息"),
                "gift_num": _as_int(data.get("num") or 1),
                "price": _as_int(data.get("price")),
                "r_price": _as_int(data.get("price")),
                "toast_msg": str(data.get("toast_msg") or ""),
            },
        )

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
        like_count = _resolve_like_count(data)
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
                "like_count": like_count,
                "like_delta": 1 if cmd == "LIKE_INFO_V3_CLICK" else 0,
            },
        }

    return None


def _build_gift_event(
    *,
    cmd: str,
    room_id: int,
    uname: str,
    timestamp: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source": "third_party_ws",
        "event_type": "gift",
        "cmd": cmd,
        "room_id": room_id,
        "open_id": "",
        "uname": uname,
        "timestamp": timestamp,
        "payload": payload,
    }


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _resolve_like_count(data: dict[str, Any]) -> int:
    for key in ("like_count", "click_count", "count"):
        if key in data:
            return _as_int(data.get(key))
    return 0
