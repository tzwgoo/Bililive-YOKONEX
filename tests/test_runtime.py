from __future__ import annotations

from pathlib import Path

from app.runtime import resolve_bundle_path, resolve_runtime_path


def test_resolve_bundle_path_points_to_repo_resource() -> None:
    path = resolve_bundle_path("app/templates/index.html")

    assert path == Path(__file__).resolve().parent.parent / "app" / "templates" / "index.html"


def test_resolve_runtime_path_points_to_repo_runtime_file() -> None:
    path = resolve_runtime_path("config/gift_command_mappings.json")

    assert path == Path(__file__).resolve().parent.parent / "config" / "gift_command_mappings.json"
