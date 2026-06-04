from __future__ import annotations

import zlib

from app.bilibili.ws_protocol import (
    OP_AUTH,
    OP_SEND_SMS_REPLY,
    decode_packets,
    encode_packet,
    parse_event_message,
)
from app.models import EventType


def test_encode_packet_sets_expected_operation() -> None:
    packet = encode_packet(operation=OP_AUTH, body=b'{"key":"value"}')
    assert len(packet) > 16


def test_decode_packets_handles_zlib_payload() -> None:
    inner = encode_packet(
        operation=OP_SEND_SMS_REPLY,
        body=b'{"cmd":"LIVE_OPEN_PLATFORM_LIKE","data":{}}',
    )
    outer = encode_packet(
        operation=OP_SEND_SMS_REPLY,
        body=zlib.compress(inner),
        version=2,
    )

    packets = decode_packets(outer)

    assert packets[0].body == b'{"cmd":"LIVE_OPEN_PLATFORM_LIKE","data":{}}'


def test_parse_event_message_builds_gift_event() -> None:
    event = parse_event_message(
        {
            "cmd": "LIVE_OPEN_PLATFORM_SEND_GIFT",
            "data": {
                "room_id": 1,
                "open_id": "user-open-id",
                "uname": "测试用户",
                "timestamp": 1714113037,
                "gift_id": 1001,
                "gift_name": "小心心",
                "gift_num": 2,
                "price": 1000,
                "r_price": 2000,
                "paid": True,
                "gift_icon": "https://example.com/icon.png",
                "combo_gift": False,
            },
        }
    )

    assert event is not None
    assert event.event_type == EventType.GIFT
    assert event.payload["gift_name"] == "小心心"


def test_parse_event_message_builds_interaction_end_event() -> None:
    event = parse_event_message(
        {
            "cmd": "LIVE_OPEN_PLATFORM_INTERACTION_END",
            "data": {
                "game_id": "game-123",
                "timestamp": 1714113037,
            },
        }
    )

    assert event is not None
    assert event.event_type == EventType.SYSTEM
    assert event.payload["game_id"] == "game-123"


def test_parse_event_message_builds_guard_specific_danmaku_event() -> None:
    event = parse_event_message(
        {
            "cmd": "LIVE_OPEN_PLATFORM_DM",
            "data": {
                "room_id": 1,
                "open_id": "user-open-id",
                "uname": "测试提督",
                "timestamp": 1714113037,
                "msg": "提督弹幕",
                "msg_id": "msg-1",
                "fans_medal_level": 25,
                "guard_level": 2,
            },
        }
    )

    assert event is not None
    assert event.event_type == EventType.DANMAKU_COMMANDER
    assert event.payload["guard_level"] == 2
    assert event.payload["guard_label"] == "提督"
