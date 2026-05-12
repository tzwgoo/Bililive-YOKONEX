from __future__ import annotations

import sys
from pathlib import Path


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


def resolve_bundle_path(relative_path: str) -> Path:
    return bundle_root() / relative_path


def resolve_runtime_path(relative_path: str) -> Path:
    return runtime_root() / relative_path
