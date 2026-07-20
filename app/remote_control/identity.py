from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class DeviceIdentity:
    client_id: str = ""
    device_token: str = ""

    @property
    def is_enrolled(self) -> bool:
        return bool(self.client_id and self.device_token)


class DeviceIdentityStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> DeviceIdentity:
        if not self.path.exists():
            return DeviceIdentity()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return DeviceIdentity()
        return DeviceIdentity(
            client_id=str(payload.get("client_id", "") or "").strip(),
            device_token=str(payload.get("device_token", "") or "").strip(),
        )

    def save(self, identity: DeviceIdentity) -> None:
        """原子保存设备凭据，避免程序退出时留下半个 JSON 文件。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary_path.write_text(
            json.dumps(asdict(identity), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self.path)
