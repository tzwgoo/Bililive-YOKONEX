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
        self.rules = rules or []
        self._price_rules: list[tuple[int, int | None, str]] = []

        for rule in self.rules:
            command_slot = str(rule.get("command_slot", "")).strip()
            if command_slot not in ALLOWED_COMMAND_SLOTS:
                continue

            min_price = self._coerce_price(rule.get("min_price"))
            if min_price is None:
                continue
            max_price = self._coerce_price(rule.get("max_price"), allow_none=True)
            if max_price is not None and max_price < min_price:
                continue
            self._price_rules.append((min_price, max_price, command_slot))

    @classmethod
    def from_file(cls, path: str | Path) -> "GiftCommandMapper":
        mapping_path = Path(path)
        if not mapping_path.exists():
            return cls([])

        payload = json.loads(mapping_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("rules", [])
        if not isinstance(payload, list):
            raise ValueError("礼物映射文件格式错误，必须是 JSON 数组或包含 rules 的对象")
        return cls(payload)

    def resolve_command_id(self, gift_payload: dict[str, Any]) -> str | None:
        price = self._coerce_price(
            gift_payload.get("r_price", gift_payload.get("price")),
        )
        if price is None:
            return None
        for min_price, max_price, command_slot in self._price_rules:
            if price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            return command_slot
        return None

    def _coerce_price(self, value: Any, *, allow_none: bool = False) -> int | None:
        if value in (None, ""):
            return None if allow_none else None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
