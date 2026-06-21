from __future__ import annotations

import json
from dataclasses import dataclass

from app.runtime import resolve_runtime_path

VALID_LOG_LEVELS = {
    "critical",
    "error",
    "warning",
    "info",
    "debug",
    "trace",
}

DEFAULT_PORT = 8000
DEFAULT_LOG_LEVEL = "info"

@dataclass(frozen=True)
class ServerSettings:
    port: int = DEFAULT_PORT
    log_level: str = DEFAULT_LOG_LEVEL

def load_server_settings() -> ServerSettings:
    """
    从运行目录的 config/server.json 加载服务器配置（端口号和 uvicorn 日志级别）。
    如果文件不存在或内容无效，则使用默认配置。
    该设置属于较少使用的可选本地部署配置，因此不会被持久化到 %APPDATA%，仅从运行目录读取。
    """
    config_path = resolve_runtime_path("config/server.json")

    if not config_path.exists():
        return ServerSettings()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ServerSettings()

    port = data.get("port", DEFAULT_PORT)
    log_level = data.get("log_level", DEFAULT_LOG_LEVEL)

    if not isinstance(port, int) or not (0 <= port <= 65535):
        port = DEFAULT_PORT

    if log_level not in VALID_LOG_LEVELS:
        log_level = DEFAULT_LOG_LEVEL

    return ServerSettings(
        port=port,
        log_level=log_level,
    )