from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GiftCommandMapper:
    def __init__(self, rules: list[dict[str, Any]] | None = None) -> None:
        self.rules = rules or []
        self._commands_by_gift_id: dict[int, str] = {}
        self._commands_by_gift_name: dict[str, str] = {}

        for rule in self.rules:
            command_id = str(rule.get("command_id", "")).strip()
            if not command_id:
                continue

            gift_id = rule.get("gift_id")
            if gift_id not in (None, ""):
                try:
                    self._commands_by_gift_id[int(gift_id)] = command_id
                except (TypeError, ValueError):
                    pass

            gift_name = str(rule.get("gift_name", "")).strip()
            if gift_name:
                self._commands_by_gift_name[gift_name] = command_id

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
        gift_id = gift_payload.get("gift_id")
        if gift_id not in (None, ""):
            try:
                command_id = self._commands_by_gift_id.get(int(gift_id))
            except (TypeError, ValueError):
                command_id = None
            if command_id:
                return command_id

        gift_name = str(gift_payload.get("gift_name", "")).strip()
        if gift_name:
            return self._commands_by_gift_name.get(gift_name)
        return None
