from __future__ import annotations

from app.third_party.event_mapper import map_third_party_message


def test_map_send_gift_to_standard_gift_event() -> None:
    message = {
        "cmd": "SEND_GIFT",
        "data": {
            "giftId": 1,
            "giftName": "辣条",
            "num": 1,
            "uname": "用户A",
            "price": 100,
            "timestamp": 1714113037,
        },
    }

    event = map_third_party_message(message, room_id=123)

    assert event["event_type"] == "gift"
    assert event["source"] == "third_party_ws"
    assert event["payload"]["gift_name"] == "辣条"


def test_map_combo_send_to_standard_gift_event() -> None:
    event = map_third_party_message(
        {
            "cmd": "COMBO_SEND",
            "data": {
                "gift_id": 31039,
                "gift_name": "牛哇牛哇",
                "combo_num": 3,
                "uname": "测试用户",
                "price": 100,
                "combo_total_coin": 300,
                "timestamp": 1714113037,
            },
        },
        room_id=123456,
    )

    assert event is not None
    assert event["event_type"] == "gift"
    assert event["cmd"] == "COMBO_SEND"
    assert event["payload"]["gift_name"] == "牛哇牛哇"
    assert event["payload"]["gift_num"] == 3
    assert event["payload"]["r_price"] == 300
    assert event["payload"]["price"] == 100


def test_map_guard_buy_to_standard_gift_event() -> None:
    event = map_third_party_message(
        {
            "cmd": "GUARD_BUY",
            "data": {
                "uid": 1,
                "username": "大航海用户",
                "gift_name": "舰长",
                "num": 2,
                "price": 138000,
                "start_time": 1714113037,
            },
        },
        room_id=123456,
    )

    assert event is not None
    assert event["event_type"] == "gift"
    assert event["cmd"] == "GUARD_BUY"
    assert event["uname"] == "大航海用户"
    assert event["payload"]["gift_name"] == "舰长"
    assert event["payload"]["gift_num"] == 2
    assert event["payload"]["price"] == 138000
    assert event["payload"]["r_price"] == 138000


def test_map_super_chat_to_standard_gift_event() -> None:
    event = map_third_party_message(
        {
            "cmd": "SUPER_CHAT_MESSAGE",
            "data": {
                "price": 100,
                "message": "测试 SC",
                "ts": 1714113037,
                "gift": {
                    "gift_id": 12000,
                    "gift_name": "醒目留言",
                    "num": 1,
                },
                "user_info": {
                    "uname": "SC用户",
                },
            },
        },
        room_id=123456,
    )

    assert event is not None
    assert event["event_type"] == "gift"
    assert event["cmd"] == "SUPER_CHAT_MESSAGE"
    assert event["uname"] == "SC用户"
    assert event["payload"]["gift_id"] == 12000
    assert event["payload"]["gift_name"] == "醒目留言"
    assert event["payload"]["gift_num"] == 1
    assert event["payload"]["price"] == 100
    assert event["payload"]["message"] == "测试 SC"


def test_map_user_toast_msg_to_standard_gift_event() -> None:
    event = map_third_party_message(
        {
            "cmd": "USER_TOAST_MSG",
            "data": {
                "username": "续费用户",
                "role_name": "舰长",
                "num": 1,
                "price": 50000,
                "toast_msg": "<%续费用户%>续费了舰长1个月",
                "start_time": 1714113037,
            },
        },
        room_id=123456,
    )

    assert event is not None
    assert event["event_type"] == "gift"
    assert event["cmd"] == "USER_TOAST_MSG"
    assert event["uname"] == "续费用户"
    assert event["payload"]["gift_name"] == "舰长"
    assert event["payload"]["gift_num"] == 1
    assert event["payload"]["price"] == 50000
    assert event["payload"]["toast_msg"] == "<%续费用户%>续费了舰长1个月"


def test_map_danmaku_to_standard_event() -> None:
    message = {
        "cmd": "DANMU_MSG",
        "info": [
            [],
            "这是一条弹幕",
            [123, "弹幕用户"],
        ],
    }

    event = map_third_party_message(message, room_id=456)

    assert event["event_type"] == "danmaku"
    assert event["source"] == "third_party_ws"
    assert event["payload"]["msg"] == "这是一条弹幕"


def test_map_like_click_to_standard_event() -> None:
    message = {
        "cmd": "LIKE_INFO_V3_CLICK",
        "data": {
            "uname": "点赞用户",
            "like_text": "点赞了直播间",
            "timestamp": 1714113037,
        },
    }

    event = map_third_party_message(message, room_id=789)

    assert event["event_type"] == "like"
    assert event["source"] == "third_party_ws"
    assert event["payload"]["like_count"] == 0
    assert event["payload"]["like_delta"] == 1


def test_map_like_update_to_standard_event_uses_click_count() -> None:
    message = {
        "cmd": "LIKE_INFO_V3_UPDATE",
        "data": {
            "click_count": 3227,
        },
    }

    event = map_third_party_message(message, room_id=789)

    assert event["event_type"] == "like"
    assert event["source"] == "third_party_ws"
    assert event["payload"]["like_count"] == 3227
    assert event["payload"]["like_delta"] == 0
