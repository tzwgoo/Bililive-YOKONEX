from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv
from app.runtime import resolve_persistent_path


@dataclass(frozen=True)
class Settings:
    command_ws_url: str | None = None
    command_ws_uid: str | None = None
    command_ws_token: str | None = None
    command_ws_user_id: str | None = None
    gift_mapping_path: str = "config/gift_command_mappings.json"
    management_ws_url: str = ""
    management_registration_token: str = ""
    management_client_name: str = ""
    management_heartbeat_seconds: int = 15


def load_settings() -> Settings:
    # .env 也放入用户数据目录，避免安装包更新时把本地连接配置覆盖掉。
    load_dotenv(dotenv_path=resolve_persistent_path(".env"))
    heartbeat_seconds = _read_positive_int("MANAGEMENT_HEARTBEAT_SECONDS", 15)
    return Settings(
        # 当前运行态只依赖第三方消息流配置，不再读取开放平台凭据。
        command_ws_url=os.getenv("COMMAND_WS_URL"),
        command_ws_uid=os.getenv("COMMAND_WS_UID"),
        command_ws_token=os.getenv("COMMAND_WS_TOKEN"),
        command_ws_user_id=os.getenv("COMMAND_WS_USER_ID"),
        gift_mapping_path=os.getenv("GIFT_MAPPING_PATH", "config/gift_command_mappings.json"),
        # 远程管理代理没有客户端界面，仅在配置了服务器地址和注册密钥后静默启用。
        management_ws_url=str(os.getenv("MANAGEMENT_WS_URL", "") or "").strip(),
        management_registration_token=str(os.getenv("MANAGEMENT_REGISTRATION_TOKEN", "") or "").strip(),
        management_client_name=str(os.getenv("MANAGEMENT_CLIENT_NAME", "") or "").strip(),
        management_heartbeat_seconds=heartbeat_seconds,
    )


def _read_positive_int(name: str, default: int) -> int:
    try:
        value = int(str(os.getenv(name, default) or default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default
