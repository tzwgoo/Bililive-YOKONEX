from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv
from app.runtime import resolve_runtime_path


@dataclass(frozen=True)
class Settings:
    command_ws_url: str | None = None
    command_ws_uid: str | None = None
    command_ws_token: str | None = None
    command_ws_user_id: str | None = None
    gift_mapping_path: str = "config/gift_command_mappings.json"


def load_settings() -> Settings:
    load_dotenv(dotenv_path=resolve_runtime_path(".env"))
    return Settings(
        # 当前运行态只依赖第三方消息流配置，不再读取开放平台凭据。
        command_ws_url=os.getenv("COMMAND_WS_URL"),
        command_ws_uid=os.getenv("COMMAND_WS_UID"),
        command_ws_token=os.getenv("COMMAND_WS_TOKEN"),
        command_ws_user_id=os.getenv("COMMAND_WS_USER_ID"),
        gift_mapping_path=os.getenv("GIFT_MAPPING_PATH", "config/gift_command_mappings.json"),
    )
