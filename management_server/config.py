from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class ManagementSettings:
    database_path: Path = Path("data/management.db")
    admin_username: str = ""
    admin_password: str = ""
    registration_token: str = ""
    cookie_secure: bool = False
    session_hours: int = 12

    def validate(self) -> None:
        missing: list[str] = []
        if not self.admin_username:
            missing.append("MANAGEMENT_ADMIN_USERNAME")
        if not self.admin_password:
            missing.append("MANAGEMENT_ADMIN_PASSWORD")
        if not self.registration_token:
            missing.append("MANAGEMENT_REGISTRATION_TOKEN")
        if missing:
            raise RuntimeError(f"缺少管理服务器配置: {', '.join(missing)}")


def load_management_settings() -> ManagementSettings:
    load_dotenv(".env.management")
    return ManagementSettings(
        database_path=Path(os.getenv("MANAGEMENT_DATABASE_PATH", "data/management.db")),
        admin_username=str(os.getenv("MANAGEMENT_ADMIN_USERNAME", "") or "").strip(),
        admin_password=str(os.getenv("MANAGEMENT_ADMIN_PASSWORD", "") or ""),
        registration_token=str(os.getenv("MANAGEMENT_REGISTRATION_TOKEN", "") or "").strip(),
        cookie_secure=_read_bool("MANAGEMENT_COOKIE_SECURE", False),
        session_hours=max(1, _read_int("MANAGEMENT_SESSION_HOURS", 12)),
    )


def _read_bool(name: str, default: bool) -> bool:
    value = str(os.getenv(name, "") or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _read_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, default) or default))
    except (TypeError, ValueError):
        return default
