from __future__ import annotations

from pathlib import Path


def test_command_form_uses_local_storage_keys() -> None:
    app_js = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "biliLive.commandWsUrl" in app_js
    assert "biliLive.commandUid" in app_js


def test_frontend_contains_dual_mode_controls() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    app_js = (base_dir / "app" / "static" / "app.js").read_text(encoding="utf-8")
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")

    assert "session-mode" in index_html
    assert "trigger-mode" in index_html
    assert "open_live" in index_html
    assert "third_party" in index_html
    assert "mode: sessionModeSelect.value" in app_js
    assert "value: sessionValueInput.value" in app_js
    assert "trigger_mode: triggerModeSelect.value" in app_js


def test_event_panels_use_fixed_height_scroll_layout() -> None:
    style_css = (Path(__file__).resolve().parent.parent / "app" / "static" / "style.css").read_text(encoding="utf-8")

    assert "height: clamp(" in style_css
    assert "overflow-y: auto" in style_css


def test_status_panel_uses_horizontal_layout() -> None:
    style_css = (Path(__file__).resolve().parent.parent / "app" / "static" / "style.css").read_text(encoding="utf-8")

    assert "grid-column: 1 / -1" in style_css
    assert "grid-template-columns: repeat(auto-fit, minmax(140px, 1fr))" in style_css
