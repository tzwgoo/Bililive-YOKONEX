from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv
from app.runtime import resolve_runtime_path


@dataclass(frozen=True)
class Settings:
    app_id: int
    access_key_id: str
    access_key_secret: str
    command_ws_url: str | None = None
    command_ws_uid: str | None = None
    command_ws_token: str | None = None
    command_ws_user_id: str | None = None
    gift_mapping_path: str = "config/gift_command_mappings.json"


def load_settings() -> Settings:
    load_dotenv(dotenv_path=resolve_runtime_path(".env"))
    missing = [
        name
        for name in ("APP_ID", "BILI_ACCESS_KEY_ID", "BILI_ACCESS_KEY_SECRET")
        if not os.getenv(name)
    ]
    if missing:
        raise ValueError(f"Missing required settings: {', '.join(missing)}")

    return Settings(
        app_id=int(os.environ["APP_ID"]),
        access_key_id=os.environ["BILI_ACCESS_KEY_ID"],
        access_key_secret=os.environ["BILI_ACCESS_KEY_SECRET"],
        command_ws_url=os.getenv("COMMAND_WS_URL"),
        command_ws_uid=os.getenv("COMMAND_WS_UID"),
        command_ws_token=os.getenv("COMMAND_WS_TOKEN"),
        command_ws_user_id=os.getenv("COMMAND_WS_USER_ID"),
        gift_mapping_path=os.getenv("GIFT_MAPPING_PATH", "config/gift_command_mappings.json"),
    )
