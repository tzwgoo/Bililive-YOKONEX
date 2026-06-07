from __future__ import annotations

from dataclasses import dataclass
import json
import struct
from typing import Any
import zlib

from app.models import EventType, LiveEvent, resolve_danmaku_event_type


HEADER_LENGTH = 16
PROTOCOL_VERSION_PLAIN = 1
PROTOCOL_VERSION_RAW_JSON = 0
PROTOCOL_VERSION_ZLIB = 2
SEQUENCE_ID = 1

OP_HEARTBEAT = 2
OP_HEARTBEAT_REPLY = 3
OP_SEND_SMS_REPLY = 5
OP_AUTH = 7
OP_AUTH_REPLY = 8


@dataclass(slots=True)
class DecodedPacket:
    packet_length: int
    header_length: int
    version: int
    operation: int
    sequence_id: int
    body: bytes


def encode_packet(*, operation: int, body: bytes = b"", version: int = PROTOCOL_VERSION_PLAIN) -> bytes:
    packet_length = HEADER_LENGTH + len(body)
    header = struct.pack(
        ">IHHII",
        packet_length,
        HEADER_LENGTH,
        version,
        operation,
        SEQUENCE_ID,
    )
    return header + body


def decode_packets(data: bytes) -> list[DecodedPacket]:
    packets: list[DecodedPacket] = []
    offset = 0
    while offset + HEADER_LENGTH <= len(data):
        packet_length, header_length, version, operation, sequence_id = struct.unpack(
            ">IHHII",
            data[offset : offset + HEADER_LENGTH],
        )
        body_start = offset + header_length
        body_end = offset + packet_length
        body = data[body_start:body_end]
        offset = body_end

        if version == PROTOCOL_VERSION_ZLIB:
            packets.extend(decode_packets(zlib.decompress(body)))
            continue

        packets.append(
            DecodedPacket(
                packet_length=packet_length,
                header_length=header_length,
                version=version,
                operation=operation,
                sequence_id=sequence_id,
                body=body,
            )
        )
    return packets


def parse_event_message(message: dict[str, Any]) -> LiveEvent | None:
    cmd = message.get("cmd")
    data = message.get("data", {})
    if not isinstance(data, dict):
        return None

    event_type: EventType | None = None
    payload: dict[str, Any]
    if cmd == "LIVE_OPEN_PLATFORM_SEND_GIFT":
        event_type = EventType.GIFT
        guard_level = int(data.get("guard_level", 0) or 0)
        payload = {
            "gift_id": data.get("gift_id", 0),
            "gift_name": data.get("gift_name", ""),
            "gift_num": data.get("gift_num", 0),
            "price": data.get("price", 0),
            "r_price": data.get("r_price", 0),
            "paid": data.get("paid", False),
            "gift_icon": data.get("gift_icon", ""),
            "combo_gift": data.get("combo_gift", False),
            "guard_level": guard_level,
            "guard_label": {
                1: "总督",
                2: "提督",
                3: "舰长",
            }.get(guard_level, ""),
        }
    elif cmd == "LIVE_OPEN_PLATFORM_DM":
        event_type = resolve_danmaku_event_type(int(data.get("guard_level", 0) or 0))
        payload = {
            "msg": data.get("msg", ""),
            "msg_id": data.get("msg_id", ""),
            "fans_medal_level": data.get("fans_medal_level", 0),
            "guard_level": data.get("guard_level", 0),
            "guard_label": {
                1: "总督",
                2: "提督",
                3: "舰长",
            }.get(int(data.get("guard_level", 0) or 0), ""),
        }
    elif cmd == "LIVE_OPEN_PLATFORM_LIKE":
        event_type = EventType.LIKE
        payload = {
            "like_text": data.get("like_text", ""),
            "like_count": data.get("like_count", 0),
        }
    elif cmd == "LIVE_OPEN_PLATFORM_INTERACTION_END":
        event_type = EventType.SYSTEM
        payload = {
            "game_id": data.get("game_id", ""),
            "message": "互动场次已结束，请重新启动监听",
        }
    else:
        return None

    return LiveEvent(
        source="open_live",
        event_type=event_type,
        cmd=cmd,
        room_id=int(data.get("room_id", 0) or 0),
        open_id=str(data.get("open_id", "")),
        uname=str(data.get("uname", "")),
        timestamp=int(data.get("timestamp", 0) or 0),
        payload=payload,
    )


def parse_json_body(body: bytes) -> dict[str, Any]:
    return json.loads(body.decode("utf-8"))
