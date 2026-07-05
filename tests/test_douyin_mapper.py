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
