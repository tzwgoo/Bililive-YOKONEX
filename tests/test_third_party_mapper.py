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
            "like_count": 3,
            "timestamp": 1714113037,
        },
    }

    event = map_third_party_message(message, room_id=789)

    assert event["event_type"] == "like"
    assert event["source"] == "third_party_ws"
    assert event["payload"]["like_count"] == 3
