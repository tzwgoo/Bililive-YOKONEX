from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_USER_DATA_DIRNAME = "Bililive-YOKONEX"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def bundle_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return _repo_root()


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _repo_root()


def user_data_root() -> Path:
    override_root = str(os.getenv("BILILIVE_USER_DATA_DIR", "") or "").strip()
    if override_root:
        return Path(override_root).expanduser()

    if getattr(sys, "frozen", False):
        appdata_root = str(os.getenv("APPDATA", "") or "").strip()
        if appdata_root:
            return Path(appdata_root) / APP_USER_DATA_DIRNAME
    return runtime_root()


def resolve_bundle_path(relative_path: str) -> Path:
    return bundle_root() / relative_path


def resolve_runtime_path(relative_path: str) -> Path:
    return runtime_root() / relative_path


def resolve_persistent_path(relative_path: str) -> Path:
    """解析用户可写配置路径。

    打包运行时优先落到 %AppData%，避免应用覆盖更新时丢失用户波形和配置；
    首次切换目录时会自动从旧运行目录迁移已有文件。
    """

    target_path = user_data_root() / relative_path
    legacy_path = runtime_root() / relative_path
    if target_path == legacy_path:
        return target_path

    if not target_path.exists() and legacy_path.exists() and legacy_path.is_file():
        # 只迁移用户可写配置文件，不复制静态资源目录，避免污染安装包内容。
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_path, target_path)
    return target_path


def ensure_persistent_file(
    relative_path: str,
    *,
    default_source_path: Path | None = None,
    default_text: str | None = None,
) -> Path:
    """确保用户配置文件存在。

    会先走持久化路径解析和旧文件迁移；如果目标文件仍不存在，
    则优先复制 default_source_path，其次写入 default_text。
    """

    target_path = resolve_persistent_path(relative_path)
    if target_path.exists():
        return target_path

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if default_source_path is not None and default_source_path.exists() and default_source_path.is_file():
        shutil.copy2(default_source_path, target_path)
        return target_path

    if default_text is not None:
        target_path.write_text(default_text, encoding="utf-8")
    return target_path
