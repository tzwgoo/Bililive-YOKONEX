from __future__ import annotations

from pathlib import Path


def test_frontend_workspace_contains_vite_entrypoints() -> None:
    base_dir = Path(__file__).resolve().parent.parent

    assert (base_dir / "frontend" / "package.json").exists()
    assert (base_dir / "frontend" / "vite.config.ts").exists()
    assert (base_dir / "frontend" / "src" / "main.ts").exists()


def test_command_form_uses_local_storage_keys() -> None:
    app_js = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "biliLive.commandWsUrl" in app_js
    assert "biliLive.commandUid" in app_js
    assert "biliLive.commandToken" in app_js
    assert "biliLive.sessionMode" in app_js
    assert "biliLive.sessionValue" in app_js
    assert "biliLive.triggerMode" in app_js


def test_frontend_contains_dual_mode_controls() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    app_js = (base_dir / "app" / "static" / "app.js").read_text(encoding="utf-8")
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")

    assert "session-mode" in index_html
    assert "connection-mode" in index_html
    assert "output-mode" not in index_html
    assert "trigger-mode" in index_html
    assert "open_live" in index_html
    assert "third_party" in index_html
    assert "mode: sessionModeSelect.value" in app_js
    assert "value: sessionValueInput.value" in app_js
    assert "output_mode: connectionModeSelect.value" in app_js
    assert "trigger_mode: triggerModeSelect.value" in app_js


def test_frontend_contains_dashboard_tabs() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    app_js = (base_dir / "app" / "static" / "app.js").read_text(encoding="utf-8")
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")

    assert 'class="tab-shell dashboard-tabs"' in index_html
    assert 'id="dashboard-tab-nav"' in index_html
    assert 'data-tab-target="session-panel"' in index_html
    assert 'data-tab-target="connection-panel"' in index_html
    assert 'data-tab-target="events-panel"' in index_html
    assert 'data-tab-panel="session-panel"' in index_html
    assert 'data-tab-panel="connection-panel"' in index_html
    assert 'data-tab-panel="events-panel"' in index_html
    assert "const dashboardTabStorageKey = \"biliLive.dashboardTab\";" in app_js
    assert "function activateDashboardTab(tabId)" in app_js
    assert "dashboardTabButtons.forEach" in app_js


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
    assert "data.danmaku_command_id" in app_js
    assert "updateStatusDraftLabels(" in app_js
    assert "biliLive.danmakuUserLimitWindowSeconds" in app_js
    assert "biliLive.danmakuUserLimitMaxTriggers" in app_js
    assert "biliLive.danmakuMinGuardLevel" in app_js


def test_frontend_does_not_restore_idle_form_on_each_poll() -> None:
    app_js = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "restoreSessionDraft();" in app_js
    assert "} else {\n    restoreSessionDraft();\n  }" not in app_js


def test_frontend_persists_form_draft_while_user_is_typing() -> None:
    app_js = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'sessionValueInput.addEventListener("input", persistSessionDraft);' in app_js
    assert 'likeMultipleInput.addEventListener("input"' in app_js
    assert 'danmakuKeywordsInput.addEventListener("input"' in app_js
    assert 'danmakuCooldownSecondsInput.addEventListener("input"' in app_js
    assert 'danmakuUserLimitWindowSecondsInput.addEventListener("input"' in app_js
    assert 'danmakuUserLimitMaxTriggersInput.addEventListener("input"' in app_js
    assert 'danmakuMinGuardLevelSelect.addEventListener("change"' in app_js
    assert 'commandWsUrlInput.addEventListener("input", persistCommandForm);' in app_js
    assert 'commandUidInput.addEventListener("input", persistCommandForm);' in app_js
    assert 'commandTokenInput.addEventListener("input", persistCommandForm);' in app_js


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


def test_frontend_contains_extended_danmaku_controls() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    app_js = (base_dir / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'id="danmaku-user-limit-window-seconds"' in index_html
    assert 'id="danmaku-user-limit-max-triggers"' in index_html
    assert 'id="danmaku-min-guard-level"' in index_html
    assert "danmaku_user_limit_window_seconds" in app_js
    assert "danmaku_user_limit_max_triggers" in app_js
    assert "danmaku_min_guard_level" in app_js
    assert 'id="danmaku-user-limit-window-seconds-label"' in index_html
    assert 'id="danmaku-user-limit-max-triggers-label"' in index_html
    assert 'id="danmaku-min-guard-level-label"' in index_html


def test_frontend_contains_bluetooth_panel_skeleton() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    app_js = (base_dir / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "Connection Mode" in index_html
    assert "连接方式" in index_html
    assert 'id="connection-mode-panel"' in index_html
    assert 'id="bluetooth-status-pill"' in index_html
    assert 'id="bluetooth-scan-btn"' in index_html
    assert 'id="bluetooth-devices"' in index_html
    assert 'id="bluetooth-rules"' in index_html
    assert 'id="bluetooth-rules-details"' in index_html
    assert "查看事件规则预览" in index_html
    assert 'href="/bluetooth/overlay"' in index_html
    assert 'id="command-connection-section"' in index_html
    assert 'id="bluetooth-connection-section"' in index_html
    assert 'id="bluetooth-waveforms"' not in index_html
    assert ">波形库<" not in index_html
    assert 'fetch("/api/bluetooth/status")' in app_js
    assert 'fetch("/api/bluetooth/scan"' in app_js
    assert 'window.open("/bluetooth/overlay"' in app_js
    assert "rule.rule_label || rule.event_label || rule.event_type || \"unknown\"" in app_js
    assert "rule.waveform_name || rule.waveform_id || \"-\"" in app_js


def test_frontend_uses_connection_mode_local_draft_keys() -> None:
    app_js = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "biliLive.connectionMode" in app_js
    assert "biliLive.outputMode" not in app_js
    assert "const connectionModeSelect =" in app_js
    assert "const connectionModeLabel =" in app_js


def test_frontend_contains_bluetooth_studio_entry_and_template() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    studio_html = (base_dir / "app" / "templates" / "bluetooth_studio.html").read_text(encoding="utf-8")
    studio_js = (base_dir / "app" / "static" / "bluetooth_studio.js").read_text(encoding="utf-8")

    assert 'href="/bluetooth/studio"' in index_html
    assert 'id="studio-waveform-library"' in studio_html
    assert 'id="studio-waveform-editor"' in studio_html
    assert 'id="studio-new-waveform-btn"' in studio_html
    assert 'id="studio-rule-groups"' in studio_html
    assert 'id="studio-save-btn"' in studio_html
    assert 'id="studio-waveform-name-input"' in studio_html
    assert 'id="studio-waveform-canvas"' in studio_html
    assert 'id="studio-waveform-steps"' in studio_html
    assert 'fetch("/api/bluetooth/studio")' in studio_js
    assert 'fetch("/api/bluetooth/rules"' in studio_js
    assert 'fetch("/api/bluetooth/waveforms"' in studio_js
    assert "function buildWaveformPreviewSvg(" in studio_js
    assert "function resolveWaveformMaxStrength(" in studio_js
    assert "function renderWaveformEditorCanvas(" in studio_js
    assert "pointerdown" in studio_js
    assert "draftDirty" in studio_js
    assert "activeDragHandle" in studio_js
    assert "最大强度 ${maxStrength}" in studio_js
    assert "rule.rule_label || rule.event_type" in studio_js
    assert "data-role=\"min-price\"" in studio_js
    assert "data-role=\"max-price\"" in studio_js
    assert 'const priceFilterGroupIds = new Set(["gift", "super_chat", "guard_buy", "guard_renew"]);' in studio_js
    assert "按价格升序整理" in studio_html
    assert "舰长弹幕" in studio_js
    assert "提督弹幕" in studio_js
    assert "总督弹幕" in studio_js
    assert "醒目留言" in studio_js
    assert "互动事件" in studio_js
    assert 'class="tab-shell studio-tabs"' in studio_html
    assert 'id="bluetooth-studio-tab-nav"' in studio_html
    assert 'data-tab-target="waveform-library-panel"' in studio_html
    assert 'data-tab-target="waveform-editor-panel"' in studio_html
    assert 'data-tab-target="rule-groups-panel"' in studio_html
    assert 'data-tab-panel="waveform-library-panel"' in studio_html
    assert 'data-tab-panel="waveform-editor-panel"' in studio_html
    assert 'data-tab-panel="rule-groups-panel"' in studio_html
    assert "const bluetoothStudioTabStorageKey = \"biliLive.bluetoothStudioTab\";" in studio_js
    assert "function activateBluetoothStudioTab(tabId)" in studio_js


def test_frontend_contains_command_studio_entry_and_template() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    studio_html = (base_dir / "app" / "templates" / "command_studio.html").read_text(encoding="utf-8")
    studio_js = (base_dir / "app" / "static" / "command_studio.js").read_text(encoding="utf-8")

    assert 'href="/command/studio"' in index_html
    assert 'class="studio-layout studio-layout-single"' in studio_html
    assert 'id="command-studio-gift-rules"' in studio_html
    assert 'id="command-studio-like-fixed-id"' in studio_html
    assert 'id="command-studio-danmaku-fixed-ids"' in studio_html
    assert 'id="command-studio-save-btn"' in studio_html
    assert "固定点赞指令 ID" in studio_html
    assert "固定弹幕指令 ID" in studio_html
    assert "点赞倍数阈值请在监听控制台设置" in studio_html
    assert "按价格升序整理" in studio_html
    assert 'fetch("/api/command/studio")' in studio_js
    assert 'fetch("/api/command/studio", {' in studio_js
    assert "function sortGiftRulesByPrice(" in studio_js
    assert 'data-action="sort-gift-rules"' in studio_js
    assert 'const fixedLikeIdContainer =' in studio_js
    assert "payload.like_command_id" in studio_js
    assert "like_trigger" in studio_js
    assert "点赞指令固定，不支持在页面修改。" in studio_js
    assert 'const fixedDanmakuIdsContainer =' in studio_js
    assert "payload.danmaku_command_ids" in studio_js
    assert "danmaku_captain_trigger" in studio_js
    assert "弹幕指令固定，不支持在页面修改。" in studio_js
    assert 'class="tab-shell studio-tabs"' in studio_html
    assert 'id="command-studio-tab-nav"' in studio_html
    assert 'data-tab-target="gift-rules-panel"' in studio_html
    assert 'data-tab-target="like-command-panel"' in studio_html
    assert 'data-tab-target="danmaku-command-panel"' in studio_html
    assert 'data-tab-panel="gift-rules-panel"' in studio_html
    assert 'data-tab-panel="like-command-panel"' in studio_html
    assert 'data-tab-panel="danmaku-command-panel"' in studio_html
    assert "const commandStudioTabStorageKey = \"biliLive.commandStudioTab\";" in studio_js
    assert "function activateCommandStudioTab(tabId)" in studio_js


def test_frontend_contains_single_column_command_studio_layout() -> None:
    style_css = (Path(__file__).resolve().parent.parent / "app" / "static" / "style.css").read_text(encoding="utf-8")

    assert ".studio-layout-single" in style_css
    assert "grid-template-columns: minmax(0, 1fr);" in style_css


def test_frontend_contains_bluetooth_studio_editor_styles() -> None:
    style_css = (Path(__file__).resolve().parent.parent / "app" / "static" / "style.css").read_text(encoding="utf-8")

    assert ".studio-waveform-card.is-selected" in style_css
    assert ".studio-waveform-actions" in style_css
    assert ".studio-waveform-editor" in style_css
    assert ".studio-editor-canvas" in style_css
    assert ".studio-editor-handle" in style_css
    assert ".studio-editor-grid" in style_css
    assert ".studio-waveform-steps" in style_css
    assert "overflow-x: auto" in style_css
    assert "min-width: 0" in style_css


def test_frontend_contains_bluetooth_overlay_template_and_script() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    overlay_html = (base_dir / "app" / "templates" / "bluetooth_overlay.html").read_text(encoding="utf-8")
    overlay_js = (base_dir / "app" / "static" / "bluetooth_overlay.js").read_text(encoding="utf-8")

    assert 'id="overlay-root"' in overlay_html
    assert 'data-style="{{ overlay_style }}"' in overlay_html
    assert 'id="overlay-waveform-name"' in overlay_html
    assert 'id="overlay-battery-value"' in overlay_html
    assert 'id="overlay-channel-a-bar"' in overlay_html
    assert 'id="overlay-channel-b-bar"' in overlay_html
    assert 'id="overlay-waveform-canvas"' in overlay_html
    assert 'id="overlay-danmaku-list"' in overlay_html
    assert 'id="overlay-highlight-label"' in overlay_html
    assert 'id="overlay-highlight-device-name"' in overlay_html
    assert 'id="overlay-highlight-message"' in overlay_html
    assert 'id="overlay-event-side"' in overlay_html
    assert 'id="overlay-event-waveform-name"' in overlay_html
    assert 'fetch("/api/bluetooth/overlay/status")' in overlay_js
    assert 'new EventSource("/api/bluetooth/overlay/stream")' in overlay_js
    assert 'overlayState.battery_level' in overlay_js
    assert "recent_events" in overlay_js
    assert "function renderOverlayDanmaku" in overlay_js
    assert "function renderOverlayHighlight" in overlay_js
    assert 'item.waveform_name || item.waveform_id || ""' in overlay_js
    assert 'latestEvent.waveform_name || latestEvent.waveform_id || overlayState.waveform_name || "待机中"' in overlay_js


def test_frontend_contains_control_log_panel_and_stream() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    app_js = (base_dir / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'id="control-events"' in index_html
    assert 'id="control-count"' in index_html
    assert 'new EventSource("/api/events/stream")' in app_js
    assert 'new EventSource("/api/control/stream")' in app_js
    assert "function renderControlEvent(event)" in app_js


def test_frontend_renders_interact_events() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    index_html = (base_dir / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    app_js = (base_dir / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'id="interact-events"' in index_html
    assert 'id="interact-count"' in index_html
    assert 'event.event_type === "interact"' in app_js
    assert "interact_label" in app_js


def test_bluetooth_panel_uses_vertical_stack_layout() -> None:
    style_css = (Path(__file__).resolve().parent.parent / "app" / "static" / "style.css").read_text(encoding="utf-8")

    assert ".bluetooth-grid" in style_css
    assert "grid-template-columns: minmax(0, 1fr);" in style_css
    assert ".bluetooth-preview-collapse" in style_css
    assert ".bluetooth-preview-summary" in style_css


def test_frontend_uses_compact_dashboard_layout() -> None:
    style_css = (Path(__file__).resolve().parent.parent / "app" / "static" / "style.css").read_text(encoding="utf-8")

    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in style_css
    assert ".config-card-chat {" in style_css
    assert "grid-column: 1 / -1;" in style_css
    assert "justify-content: flex-start;" in style_css


def test_frontend_renders_danmaku_guard_identity() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    app_js = (base_dir / "app" / "static" / "app.js").read_text(encoding="utf-8")
    style_css = (base_dir / "app" / "static" / "style.css").read_text(encoding="utf-8")

    assert "const danmakuGuardDisplayOptions =" in app_js
    assert "const danmakuEventTypes = new Set" in app_js
    assert "function resolveDanmakuGuardLabel(payload)" in app_js
    assert "function isDanmakuEventType(eventType)" in app_js
    assert "guard_label" in app_js
    assert "const guardLabel = resolveDanmakuGuardLabel(event.payload || {});" in app_js
    assert "identity-chip" in app_js
    assert ".event-meta-line" in style_css
    assert ".identity-chip" in style_css


def test_frontend_uses_minimalist_visual_system() -> None:
    style_css = (Path(__file__).resolve().parent.parent / "app" / "static" / "style.css").read_text(encoding="utf-8")

    assert "--bg: #f3f3ef;" in style_css
    assert "--panel: #ffffff;" in style_css
    assert "--line: #d7d6cf;" in style_css
    assert "--shadow: 0 10px 30px rgba(15, 23, 42, 0.04);" in style_css
    assert 'font-family: "Aptos", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;' in style_css
    assert "background: var(--bg);" in style_css


def test_frontend_contains_shared_tab_styles() -> None:
    style_css = (Path(__file__).resolve().parent.parent / "app" / "static" / "style.css").read_text(encoding="utf-8")

    assert ".tab-shell" in style_css
    assert ".tab-nav" in style_css
    assert ".tab-button" in style_css
    assert ".tab-button.is-active" in style_css
    assert ".tab-panel" in style_css
    assert ".tab-panel[hidden]" in style_css
    assert "position: sticky;" in style_css
    assert "top: 12px;" in style_css
    assert "z-index: 30;" in style_css
    assert "button:not(.secondary):not(.tab-button)" in style_css
    assert ".tab-button:hover" in style_css
    assert "color: var(--ink);" in style_css
