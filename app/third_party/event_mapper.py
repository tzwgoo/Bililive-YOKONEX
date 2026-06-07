from __future__ import annotations

from typing import Any

from app.models import resolve_danmaku_event_type


def map_third_party_message(message: dict[str, Any], *, room_id: int) -> dict[str, Any] | None:
    cmd = str(message.get("cmd", ""))
    if not cmd:
        return None

    if cmd in {"SEND_GIFT", "COMBO_SEND"}:
        data = message.get("data", {})
        guard_level = _resolve_gift_guard_level(data)
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
                "guard_level": guard_level,
                "guard_label": _guard_level_to_label(guard_level),
            },
        }

    if cmd == "GUARD_BUY":
        data = message.get("data", {})
        return _build_gift_event(
            event_type="guard_buy",
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
                "guard_level": _resolve_guard_level_from_name(
                    data.get("gift_name") or data.get("giftName") or data.get("role_name")
                ),
                "guard_label": str(data.get("gift_name") or data.get("giftName") or data.get("role_name") or "大航海"),
            },
        )

    if cmd in {"SUPER_CHAT_MESSAGE", "SUPER_CHAT_MESSAGE_JPN"}:
        data = message.get("data", {})
        gift = data.get("gift", {})
        user_info = data.get("user_info", {})
        uinfo = data.get("uinfo", {})
        base_info = uinfo.get("base", {}) if isinstance(uinfo, dict) else {}
        return _build_gift_event(
            event_type="super_chat",
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
            event_type="guard_renew",
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
                "guard_level": _resolve_guard_level_from_name(
                    data.get("gift_name") or data.get("giftName") or data.get("role_name")
                ),
                "guard_label": str(data.get("gift_name") or data.get("giftName") or data.get("role_name") or "庆祝消息"),
            },
        )

    if cmd == "DANMU_MSG":
        info = message.get("info", [])
        content = ""
        uname = ""
        timestamp = _as_int(message.get("timestamp"))
        uid = 0
        guard_level = 0
        if isinstance(info, list):
            if len(info) > 1:
                content = str(info[1] or "")
            if len(info) > 2 and isinstance(info[2], list) and len(info[2]) > 1:
                uid = _as_int(info[2][0] if len(info[2]) > 0 else 0)
                uname = str(info[2][1] or "")
            if len(info) > 0 and isinstance(info[0], list) and len(info[0]) > 4:
                timestamp = _as_int(info[0][4])
            guard_level = _extract_danmaku_guard_level(info)
            if uid <= 0:
                uid = _extract_danmaku_uid(info)
        return {
            "source": "third_party_ws",
            "event_type": resolve_danmaku_event_type(guard_level).value,
            "cmd": cmd,
            "room_id": room_id,
            "open_id": "",
            "uname": uname,
            "timestamp": timestamp,
            "payload": {
                "msg": content,
                "uid": uid,
                "guard_level": guard_level,
                "guard_label": _guard_level_to_label(guard_level),
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

    if cmd in {"INTERACT_WORD", "INTERACT_WORD_V2"}:
        data = _resolve_interact_data(message.get("data", {}))
        msg_type = _as_int(data.get("msg_type"))
        interact_type = _resolve_interact_type(msg_type)
        return {
            "source": "third_party_ws",
            "event_type": "interact",
            "cmd": cmd,
            "room_id": room_id,
            "open_id": "",
            "uname": str(data.get("uname", "")),
            "timestamp": _as_int(data.get("timestamp") or data.get("trigger_time")),
            "payload": {
                "uid": _as_int(data.get("uid")),
                "msg_type": msg_type,
                "interact_type": interact_type,
                "interact_label": _interact_type_to_label(interact_type),
            },
        }

    return None


def _build_gift_event(
    *,
    event_type: str = "gift",
    cmd: str,
    room_id: int,
    uname: str,
    timestamp: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source": "third_party_ws",
        "event_type": event_type,
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


def _resolve_interact_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    pb_decoded = data.get("pb_decoded")
    if isinstance(pb_decoded, dict) and pb_decoded:
        return pb_decoded
    return data


def _extract_danmaku_uid(info: list[Any]) -> int:
    nested_user = _read_nested_dict(info, 0, 15, "user")
    if isinstance(nested_user, dict):
        return _as_int(nested_user.get("uid"))
    return 0


def _extract_danmaku_guard_level(info: list[Any]) -> int:
    if len(info) > 7:
        direct_guard_level = _as_int(info[7])
        if direct_guard_level > 0:
            return direct_guard_level

    if len(info) > 3 and isinstance(info[3], list) and len(info[3]) > 10:
        medal_guard_level = _as_int(info[3][10])
        if medal_guard_level > 0:
            return medal_guard_level

    nested_medal = _read_nested_dict(info, 0, 15, "user", "medal")
    if isinstance(nested_medal, dict):
        return _as_int(nested_medal.get("guard_level"))

    return 0


def _guard_level_to_label(guard_level: int) -> str:
    return {
        1: "总督",
        2: "提督",
        3: "舰长",
    }.get(_as_int(guard_level), "")


def _resolve_gift_guard_level(data: dict[str, Any]) -> int:
    """从礼物数据中提取用户舰队等级。"""
    direct_level = _as_int(data.get("guard_level"))
    if direct_level > 0:
        return direct_level

    medal_info = data.get("medal_info")
    if isinstance(medal_info, dict):
        medal_level = _as_int(medal_info.get("guard_level"))
        if medal_level > 0:
            return medal_level

    uinfo = data.get("uinfo")
    if isinstance(uinfo, dict):
        uinfo_level = _as_int(uinfo.get("guard_level"))
        if uinfo_level > 0:
            return uinfo_level

    return 0


def _resolve_guard_level_from_name(value: Any) -> int:
    normalized = str(value or "").strip()
    if "总督" in normalized:
        return 1
    if "提督" in normalized:
        return 2
    if "舰长" in normalized:
        return 3
    return 0


def _resolve_interact_type(msg_type: int) -> str:
    """把第三方互动数字类型转成稳定英文类型。"""
    return {
        1: "enter",
        2: "follow",
        3: "share",
        4: "special_follow",
    }.get(_as_int(msg_type), "unknown")


def _interact_type_to_label(interact_type: str) -> str:
    """把互动英文类型转成页面展示用中文标签。"""
    return {
        "enter": "进房",
        "follow": "关注",
        "share": "分享",
        "special_follow": "特别关注",
    }.get(str(interact_type or ""), "互动")


def _read_nested_dict(container: list[Any], *path: Any) -> dict[str, Any] | None:
    current: Any = container
    for key in path:
        if isinstance(key, int):
            if not isinstance(current, list) or key >= len(current):
                return None
            current = current[key]
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, dict) else None
