from __future__ import annotations

from pathlib import Path


def test_command_form_uses_local_storage_keys() -> None:
    app_js = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "biliLive.commandWsUrl" in app_js
    assert "biliLive.commandUid" in app_js
    assert "biliLive.commandToken" in app_js
    assert "biliLive.sessionMode" in app_js
    assert "biliLive.triggerMode" in app_js


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


def test_gift_value_display_prefers_unit_price_with_total_hint() -> None:
    app_js = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "function formatGiftValue(payload)" in app_js
    assert "单价 ${unitPrice} · 总价值 ${totalPrice}" in app_js
    assert "价值 ${unitPrice}" in app_js


def test_frontend_restores_local_draft_before_session_start() -> None:
    app_js = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "function restoreSessionDraft()" in app_js
    assert "function persistSessionDraft()" in app_js
    assert "function updateStatusDraftLabels(" in app_js
    assert "const fixedDanmakuCommandId = \"danmaku_trigger\";" in app_js
    assert "persistSessionDraft();" in app_js
    assert "if (data.can_stop) {" in app_js
    assert "restoreSessionDraft();" in app_js
    assert "data.danmaku_command_id" in app_js
    assert "updateStatusDraftLabels(" in app_js


def test_frontend_hides_fixed_danmaku_command_slot_display() -> None:
    index_html = (Path(__file__).resolve().parent.parent / "app" / "templates" / "index.html").read_text(encoding="utf-8")

    assert "固定指令槽位" not in index_html
    assert "danmaku-command-id-label" not in index_html
    assert "danmaku-command-id-fixed" not in index_html


def test_frontend_hides_removed_runtime_snapshot_fields() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    app_js = (base_dir / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "当前模式" not in index_html
    assert "配置状态" not in index_html
    assert "最近指令结果" not in index_html
    assert "最近心跳时间" not in index_html
    assert 'id="mode-label"' not in index_html
    assert 'id="config-loaded"' not in index_html
    assert 'id="last-command-message"' not in index_html
    assert 'id="last-heartbeat-at"' not in index_html
    assert "const modeLabel =" not in app_js
    assert "const configLoaded =" not in app_js
    assert "const lastCommandMessage =" not in app_js
    assert "const lastHeartbeatAt =" not in app_js
