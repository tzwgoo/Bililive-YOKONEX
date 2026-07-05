from __future__ import annotations

from app.douyin.event_mapper import map_douyin_message


def test_map_douyin_chat_message_to_danmaku_event() -> None:
    event = map_douyin_message(
        {
            "method": "WebcastChatMessage",
            "content": "开火",
            "user": {
                "id": 123,
                "nickname": "抖音用户",
                "openId": "open-1",
            },
            "eventTime": 1714113037,
        },
        room_id="516466932480",
    )

    assert event is not None
    assert event["source"] == "douyin_ws"
    assert event["event_type"] == "danmaku"
    assert event["room_id"] == "516466932480"
    assert event["uname"] == "抖音用户"
    assert event["payload"]["msg"] == "开火"
    assert event["payload"]["uid"] == 123


def test_map_douyin_gift_message_to_price_event() -> None:
    event = map_douyin_message(
        {
            "method": "WebcastGiftMessage",
            "giftId": 888,
            "repeatCount": 2,
            "fanTicketCount": 199,
            "user": {
                "nickname": "送礼用户",
            },
            "gift": {
                "name": "小心心",
                "diamondCount": 1,
            },
        },
        room_id="516466932480",
    )

    assert event is not None
    assert event["event_type"] == "gift"
    assert event["payload"]["gift_id"] == 888
    assert event["payload"]["gift_name"] == "小心心"
    assert event["payload"]["gift_num"] == 2
    assert event["payload"]["price"] == 1
    assert event["payload"]["r_price"] == 199


def test_map_douyin_binding_gift_message_to_price_event() -> None:
    event = map_douyin_message(
        {
            "method": "WebcastBindingGiftMessage",
            "msg": {
                "giftId": "889",
                "repeatCount": "3",
                "fanTicketCount": "300",
                "user": {
                    "nickname": "绑定礼物用户",
                },
                "gift": {
                    "name": "粉丝团礼物",
                    "diamondCount": 100,
                },
            },
        },
        room_id="516466932480",
    )

    assert event is not None
    assert event["event_type"] == "gift"
    assert event["cmd"] == "WebcastBindingGiftMessage"
    assert event["uname"] == "绑定礼物用户"
    assert event["payload"]["gift_id"] == 889
    assert event["payload"]["gift_name"] == "粉丝团礼物"
    assert event["payload"]["gift_num"] == 3
    assert event["payload"]["price"] == 100
    assert event["payload"]["r_price"] == 300


def test_map_douyin_light_gift_message_reads_gift_info() -> None:
    event = map_douyin_message(
        {
            "method": "WebcastLightGiftMessage",
            "repeatCount": "2",
            "giftInfo": {
                "giftId": "1001",
                "diamondCount": "1",
            },
            "giftStruct": {
                "name": "小爱心",
            },
        },
        room_id="516466932480",
    )

    assert event is not None
    assert event["event_type"] == "gift"
    assert event["payload"]["gift_id"] == 1001
    assert event["payload"]["gift_name"] == "小爱心"
    assert event["payload"]["gift_num"] == 2
    assert event["payload"]["price"] == 1
    assert event["payload"]["r_price"] == 2


def test_map_douyin_like_message_to_like_event() -> None:
    event = map_douyin_message(
        {
            "method": "WebcastLikeMessage",
            "count": 1,
            "total": 120,
            "user": {
                "nickname": "点赞用户",
            },
        },
        room_id="516466932480",
    )

    assert event is not None
    assert event["event_type"] == "like"
    assert event["payload"]["like_count"] == 120
    assert event["payload"]["like_delta"] == 1


def test_map_douyin_member_message_to_interact_event() -> None:
    event = map_douyin_message(
        {
            "method": "WebcastMemberMessage",
            "user": {
                "id": 456,
                "nickname": "进房用户",
            },
        },
        room_id="516466932480",
    )

    assert event is not None
    assert event["event_type"] == "interact"
    assert event["payload"]["interact_type"] == "enter"
