from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWED_COMMAND_SLOTS = {
    "command_one",
    "command_two",
    "command_three",
    "command_four",
    "command_five",
    "command_six",
    "command_seven",
    "command_eight",
    "command_nine",
    "command_ten",
}


class GiftCommandMapper:
    def __init__(self, rules: list[dict[str, Any]] | None = None) -> None:
        self.rules: list[dict[str, Any]] = []
        self._price_rules: list[tuple[int, int | None, str]] = []
        self._like_rules: list[tuple[int, str]] = []
        self.replace_rules(rules or [])

    def replace_rules(self, rules: list[dict[str, Any]] | None) -> None:
        self.rules = rules or []
        self._price_rules = []
        self._like_rules = []

        for rule in self.rules:
            if not bool(rule.get("enabled", True)):
                continue
            event_type = str(rule.get("event_type", "gift")).strip() or "gift"
            command_slot = str(rule.get("command_slot", "")).strip()
            if command_slot not in ALLOWED_COMMAND_SLOTS:
                continue

            if event_type == "like":
                like_multiple = self._coerce_price(rule.get("like_multiple"))
                if like_multiple is None or like_multiple <= 0:
                    continue
                self._like_rules.append((like_multiple, command_slot))
                continue

            min_price = self._coerce_price(rule.get("min_price"))
            if min_price is None:
                continue
            max_price = self._coerce_price(rule.get("max_price"), allow_none=True)
            if max_price is not None and max_price < min_price:
                continue
            self._price_rules.append((event_type, min_price, max_price, command_slot))

    @classmethod
    def from_file(cls, path: str | Path) -> "GiftCommandMapper":
        mapping_path = Path(path)
        if not mapping_path.exists():
            return cls([])

        payload = json.loads(mapping_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            merged_rules: list[dict[str, Any]] = []
            if isinstance(payload.get("rules"), list):
                merged_rules.extend(rule for rule in payload["rules"] if isinstance(rule, dict))
            if isinstance(payload.get("like_rules"), list):
                merged_rules.extend(
                    {
                        **rule,
                        "event_type": rule.get("event_type", "like"),
                    }
                    for rule in payload["like_rules"]
                    if isinstance(rule, dict)
                )
            payload = merged_rules
        if not isinstance(payload, list):
            raise ValueError("礼物映射文件格式错误，必须是 JSON 数组或包含 rules 的对象")
        return cls(payload)

    def resolve_command_id(self, gift_payload: dict[str, Any], *, event_type: str = "gift") -> str | None:
        price = self._coerce_price(
            gift_payload.get("price", gift_payload.get("r_price")),
        )
        if price is None:
            return None
        normalized_event_type = str(event_type or "gift").strip() or "gift"
        command_id = self._resolve_price_rule(price=price, event_type=normalized_event_type)
        if command_id is not None:
            return command_id
        if normalized_event_type != "gift":
            return self._resolve_price_rule(price=price, event_type="gift")
        return None

    def _resolve_price_rule(self, *, price: int, event_type: str) -> str | None:
        for rule_event_type, min_price, max_price, command_slot in self._price_rules:
            if rule_event_type != event_type:
                continue
            if price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            return command_slot
        return None

    def resolve_like_command(self, like_payload: dict[str, Any]) -> tuple[str | None, int | None]:
        like_count = self._coerce_price(like_payload.get("like_count"))
        if like_count is None or like_count <= 0:
            return None, None
        for like_multiple, command_slot in self._like_rules:
            return command_slot, like_multiple
        return None, None

    def _coerce_price(self, value: Any, *, allow_none: bool = False) -> int | None:
        if value in (None, ""):
            return None if allow_none else None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
