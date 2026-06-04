from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.command_gateway.mapping import ALLOWED_COMMAND_SLOTS
from app.command_gateway.mapping import GiftCommandMapper
from app.models import is_danmaku_event_type, resolve_danmaku_event_type
from app.services.danmaku_settings import FIXED_DANMAKU_COMMAND_IDS
from app.services.danmaku_settings import FIXED_LIKE_COMMAND_ID


EVENT_TYPE_LABELS = {
    "gift": "礼物",
    "super_chat": "醒目留言",
    "guard_buy": "上舰",
    "guard_renew": "续费",
}
EVENT_TYPE_ORDER = {
    "gift": 0,
    "super_chat": 1,
    "guard_buy": 2,
    "guard_renew": 3,
}

DANMAKU_EVENT_RULE_DEFINITIONS = [
    {"id": "danmaku-normal", "event_type": "danmaku", "guard_level": 0, "label": "普通弹幕"},
    {"id": "danmaku-captain", "event_type": "danmaku_captain", "guard_level": 3, "label": "舰长弹幕"},
    {"id": "danmaku-commander", "event_type": "danmaku_commander", "guard_level": 2, "label": "提督弹幕"},
    {"id": "danmaku-governor", "event_type": "danmaku_governor", "guard_level": 1, "label": "总督弹幕"},
]
DEFAULT_DANMAKU_SLOT_RULES = [
    {
        "id": item["id"],
        "enabled": False,
        "event_type": item["event_type"],
        "guard_level": item["guard_level"],
        "command_slot": "",
    }
    for item in DANMAKU_EVENT_RULE_DEFINITIONS
]
DANMAKU_EVENT_TYPE_TO_GUARD_LEVEL = {
    str(item["event_type"]): int(item["guard_level"])
    for item in DANMAKU_EVENT_RULE_DEFINITIONS
}


class CommandRuleService:
    def __init__(
        self,
        *,
        config_path: Path,
        mapper: GiftCommandMapper,
        danmaku_dispatcher: Any | None = None,
    ) -> None:
        self.config_path = config_path
        self.mapper = mapper
        self.danmaku_dispatcher = danmaku_dispatcher
        self._payload = self._load_payload()
        self._apply_payload(self._payload)

    def get_studio_payload(self) -> dict[str, Any]:
        return {
            "rules": [dict(item) for item in self._payload["rules"]],
            "like_rules": [],
            "like_command_id": FIXED_LIKE_COMMAND_ID,
            "danmaku_slot_rules": [],
            "danmaku_command_ids": dict(FIXED_DANMAKU_COMMAND_IDS),
            "command_slots": sorted(ALLOWED_COMMAND_SLOTS),
            "event_types": [
                {"value": event_type, "label": label}
                for event_type, label in EVENT_TYPE_LABELS.items()
            ],
            "danmaku_event_types": [
                {
                    "value": str(item["event_type"]),
                    "label": str(item["label"]),
                    "guard_level": int(item["guard_level"]),
                }
                for item in DANMAKU_EVENT_RULE_DEFINITIONS
            ],
        }

    def save_rules(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized_payload = self._normalize_payload(payload)
        self._payload = normalized_payload
        self.config_path.write_text(
            json.dumps(normalized_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._apply_payload(normalized_payload)
        return {
            "success": True,
            **self.get_studio_payload(),
        }

    def _load_payload(self) -> dict[str, list[dict[str, Any]]]:
        if not self.config_path.exists():
            return self._normalize_payload({})

        raw_payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        return self._normalize_payload(raw_payload)

    def _apply_payload(self, payload: dict[str, list[dict[str, Any]]]) -> None:
        self.mapper.replace_rules(list(payload["rules"]))
        if self.danmaku_dispatcher is not None and hasattr(self.danmaku_dispatcher, "set_command_slot_rules"):
            self.danmaku_dispatcher.set_command_slot_rules([])

    def _normalize_payload(self, raw_payload: Any) -> dict[str, list[dict[str, Any]]]:
        if isinstance(raw_payload, list):
            raw_payload = {
                "rules": raw_payload,
                "like_rules": [],
                "danmaku_slot_rules": [],
            }
        if not isinstance(raw_payload, dict):
            raw_payload = {}

        rules = raw_payload.get("rules", [])
        like_rules = raw_payload.get("like_rules", [])
        danmaku_slot_rules = raw_payload.get("danmaku_slot_rules", [])

        normalized_rules = [
            self._normalize_price_rule(item, index)
            for index, item in enumerate(rules)
            if isinstance(item, dict)
        ]
        normalized_rules = self._sort_price_rules(normalized_rules)
        self._validate_price_rule_overlaps(normalized_rules)
        normalized_like_rules = []
        normalized_danmaku_rules = self._normalize_danmaku_slot_rules(danmaku_slot_rules)
        return {
            "rules": normalized_rules,
            "like_rules": normalized_like_rules,
            "danmaku_slot_rules": normalized_danmaku_rules,
        }

    def _sort_price_rules(self, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            rules,
            key=lambda item: (
                EVENT_TYPE_ORDER.get(str(item.get("event_type", "gift")), 999),
                int(item.get("min_price", 0) or 0),
                float("inf") if item.get("max_price") is None else int(item.get("max_price", 0) or 0),
                str(item.get("id", "")),
            ),
        )

    def _validate_price_rule_overlaps(self, rules: list[dict[str, Any]]) -> None:
        rules_by_event_type: dict[str, list[dict[str, Any]]] = {}
        for item in rules:
            if not bool(item.get("enabled", True)):
                continue
            event_type = str(item.get("event_type", "gift") or "gift")
            rules_by_event_type.setdefault(event_type, []).append(item)

        for event_type, items in rules_by_event_type.items():
            previous_max_price: int | None = None
            previous_rule_id = ""
            for item in items:
                min_price = int(item.get("min_price", 0) or 0)
                max_price = item.get("max_price")
                normalized_max_price = None if max_price is None else int(max_price)
                if previous_max_price is not None and min_price <= previous_max_price:
                    event_label = EVENT_TYPE_LABELS.get(event_type, event_type)
                    raise ValueError(
                        f"{event_label} 的价格区间重叠: {previous_rule_id} 与 {item['id']}"
                    )
                previous_max_price = normalized_max_price
                previous_rule_id = str(item.get("id", ""))
                if previous_max_price is None:
                    break

    def _normalize_price_rule(self, item: dict[str, Any], index: int) -> dict[str, Any]:
        event_type = str(item.get("event_type", "gift") or "gift").strip()
        if event_type not in EVENT_TYPE_LABELS:
            event_type = "gift"
        command_slot = self._normalize_command_slot(item.get("command_slot"))
        min_price = self._normalize_non_negative_int(item.get("min_price"))
        max_price = self._normalize_optional_non_negative_int(item.get("max_price"))
        if max_price is not None and max_price < min_price:
            max_price = min_price
        return {
            "id": str(item.get("id", "") or f"{event_type}-rule-{index + 1}"),
            "enabled": bool(item.get("enabled", True)),
            "event_type": event_type,
            "min_price": min_price,
            "max_price": max_price,
            "command_slot": command_slot,
        }

    def _normalize_like_rule(self, item: dict[str, Any], index: int) -> dict[str, Any]:
        return {
            "id": str(item.get("id", "") or f"like-rule-{index + 1}"),
            "enabled": bool(item.get("enabled", True)),
            "like_multiple": max(1, self._normalize_non_negative_int(item.get("like_multiple"), fallback=100)),
            "command_slot": self._normalize_command_slot(item.get("command_slot"), fallback="command_three"),
        }

    def _normalize_danmaku_slot_rules(self, rules: Any) -> list[dict[str, Any]]:
        return []

    def _normalize_danmaku_event_type(self, item: dict[str, Any]) -> str | None:
        event_type = str(item.get("event_type", "") or "").strip()
        if is_danmaku_event_type(event_type):
            return event_type
        guard_level = self._normalize_non_negative_int(item.get("guard_level"))
        if guard_level not in (0, 1, 2, 3):
            return None
        return resolve_danmaku_event_type(guard_level).value

    def _normalize_command_slot(
        self,
        value: Any,
        *,
        fallback: str = "",
        allow_blank: bool = False,
    ) -> str:
        normalized = str(value or "").strip()
        if allow_blank and not normalized:
            return ""
        if normalized in ALLOWED_COMMAND_SLOTS:
            return normalized
        return fallback

    def _normalize_non_negative_int(self, value: Any, *, fallback: int = 0) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = fallback
        return max(0, normalized)

    def _normalize_optional_non_negative_int(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return self._normalize_non_negative_int(value)
