from __future__ import annotations

from typing import Any


DANMAKU_METHODS = {
    "WebcastChatMessage",
    "WebcastEmojiChatMessage",
    "WebcastScreenChatMessage",
    "WebcastPrivilegeScreenChatMessage",
}
GIFT_METHODS = {
    "WebcastGiftMessage",
    "WebcastBindingGiftMessage",
    "WebcastLightGiftMessage",
}
INTERACT_METHODS = {
    "WebcastMemberMessage",
    "WebcastAudienceEntranceMessage",
    "WebcastSocialMessage",
}


def map_douyin_message(message: dict[str, Any], *, room_id: str) -> dict[str, Any] | None:
    method = str(message.get("method", "") or "")
    if not method:
        return _map_system_message(message, room_id=room_id)

    if method in DANMAKU_METHODS:
        user = _read_dict(message, "user")
        return _build_event(
            event_type="danmaku",
            cmd=method,
            room_id=room_id,
            uname=_read_user_name(user),
            open_id=_read_user_open_id(user),
            timestamp=_read_timestamp(message),
            payload={
                "msg": _first_text(message, "content", "defaultContent", "text"),
                "uid": _read_user_id(user),
                "guard_level": 0,
                "guard_label": "",
            },
        )

    if method in GIFT_METHODS:
        # douyinLive 的绑定礼物会把真实 GiftMessage 放在 msg 里，这里先拆出来再按普通礼物处理。
        gift_message = _read_dict(message, "msg") if method == "WebcastBindingGiftMessage" else message
        user = _read_dict(gift_message, "user")
        gift = _read_first_dict(gift_message, "gift", "giftStruct", "gift_struct")
        gift_info = _read_first_dict(gift_message, "giftInfo", "gift_info")
        gift_num = _first_int(gift_message, "repeatCount", "comboCount", "count", "groupCount", fallback=1)
        unit_price = _first_int(gift, "diamondCount", "describeScore", "price") or _first_int(
            gift_info,
            "diamondCount",
            "price",
        )
        total_price = _first_int(
            gift_message,
            "fanTicketCount",
            "totalCount",
            "diamondCount",
            fallback=unit_price * max(1, gift_num),
        )
        gift_id = (
            _first_int(gift_message, "giftId", "gift_id")
            or _first_int(gift, "id", "giftId", "gift_id")
            or _first_int(gift_info, "giftId", "gift_id")
        )
        return _build_event(
            event_type="gift",
            cmd=method,
            room_id=room_id,
            uname=_read_user_name(user),
            open_id=_read_user_open_id(user),
            timestamp=_read_timestamp(gift_message) or _read_timestamp(message),
            payload={
                "gift_id": gift_id,
                "gift_name": _first_text(gift, "name", "describe", "displayName") or "抖音礼物",
                "gift_num": max(1, gift_num),
                "price": unit_price,
                "r_price": total_price,
                "guard_level": 0,
                "guard_label": "",
            },
        )

    if method == "WebcastLikeMessage":
        user = _read_dict(message, "user")
        like_delta = _first_int(message, "count", fallback=1)
        like_count = _first_int(message, "total", "totalCount", fallback=like_delta)
        return _build_event(
            event_type="like",
            cmd=method,
            room_id=room_id,
            uname=_read_user_name(user),
            open_id=_read_user_open_id(user),
            timestamp=_read_timestamp(message),
            payload={
                "like_text": "点赞了直播间",
                "like_count": like_count,
                "like_delta": like_delta,
            },
        )

    if method in INTERACT_METHODS:
        user = _read_dict(message, "user")
        interact_type = _resolve_interact_type(method, message)
        return _build_event(
            event_type="interact",
            cmd=method,
            room_id=room_id,
            uname=_read_user_name(user),
            open_id=_read_user_open_id(user),
            timestamp=_read_timestamp(message),
            payload={
                "uid": _read_user_id(user) or _first_int(message, "userId", "user_id"),
                "msg_type": _first_int(message, "action", "enterType", "enter_type"),
                "interact_type": interact_type,
                "interact_label": _interact_type_to_label(interact_type),
            },
        )

    return None


def _map_system_message(message: dict[str, Any], *, room_id: str) -> dict[str, Any] | None:
    if str(message.get("type", "") or "") != "system":
        return None
    return _build_event(
        event_type="system",
        cmd=str(message.get("event", "") or "system"),
        room_id=room_id,
        uname="",
        open_id="",
        timestamp=0,
        payload={
            "live": bool(message.get("live", False)),
            "message": str(message.get("message", "") or ""),
            "ended": bool(message.get("ended", False)),
            "retry_interval_seconds": _first_int(message, "retry_interval_seconds", "retryIntervalSeconds"),
        },
    )


def _build_event(
    *,
    event_type: str,
    cmd: str,
    room_id: str,
    uname: str,
    open_id: str,
    timestamp: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source": "douyin_ws",
        "event_type": event_type,
        "cmd": cmd,
        "room_id": room_id,
        "open_id": open_id,
        "uname": uname,
        "timestamp": timestamp,
        "payload": payload,
    }


def _resolve_interact_type(method: str, message: dict[str, Any]) -> str:
    if method in {"WebcastMemberMessage", "WebcastAudienceEntranceMessage"}:
        return "enter"
    action_text = str(message.get("actionDescription", "") or message.get("action_description", "") or "")
    if "关注" in action_text:
        return "follow"
    if "分享" in action_text:
        return "share"
    return "follow" if method == "WebcastSocialMessage" else "unknown"


def _interact_type_to_label(interact_type: str) -> str:
    return {
        "enter": "进房",
        "follow": "关注",
        "share": "分享",
    }.get(str(interact_type or ""), "互动")


def _read_user_name(user: dict[str, Any]) -> str:
    return _first_text(user, "nickname", "displayId", "display_id")


def _read_user_id(user: dict[str, Any]) -> int:
    return _first_int(user, "id", "shortId", "short_id")


def _read_user_open_id(user: dict[str, Any]) -> str:
    return _first_text(user, "openId", "open_id", "secUid", "sec_uid", "webcastUid", "webcast_uid")


def _read_timestamp(message: dict[str, Any]) -> int:
    common = _read_dict(message, "common")
    return _first_int(message, "eventTime", "event_time", "sendTime", "send_time") or _first_int(
        common,
        "createTime",
        "create_time",
    )


def _read_dict(container: dict[str, Any], key: str) -> dict[str, Any]:
    value = container.get(key)
    return value if isinstance(value, dict) else {}


def _read_first_dict(container: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = _read_dict(container, key)
        if value:
            return value
    return {}


def _first_text(container: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = container.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _first_int(container: dict[str, Any], *keys: str, fallback: int = 0) -> int:
    for key in keys:
        if key not in container:
            continue
        try:
            return int(container.get(key) or 0)
        except (TypeError, ValueError):
            continue
    return fallback
