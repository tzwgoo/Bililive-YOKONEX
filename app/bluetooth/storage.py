from __future__ import annotations

import json
from pathlib import Path

from app.bluetooth.ems_builtin_waveforms import is_preset_waveform_id
from app.bluetooth.gift_tiers import GIFT_TIER_BY_RULE_ID
from app.bluetooth.gift_tiers import build_default_gift_rules
from app.bluetooth.models import BLUETOOTH_DANMAKU_RULE_DEFINITIONS
from app.bluetooth.models import BluetoothConfigPayload
from app.bluetooth.models import BluetoothEventRule
from app.bluetooth.models import BluetoothSettings
from app.bluetooth.models import EmsWaveform
from app.bluetooth.models import EmsWaveformStep
from app.bluetooth.models import build_default_special_event_rules
from app.bluetooth.models import build_default_payload
from app.bluetooth.models import build_default_danmaku_rules
from app.bluetooth.models import payload_to_dict


class BluetoothSettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> BluetoothConfigPayload:
        if not self.path.exists():
            return build_default_payload()

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        defaults = build_default_payload()

        settings_data = payload.get("bluetooth_settings", {})
        settings = BluetoothSettings(
            enabled=bool(settings_data.get("enabled", defaults.bluetooth_settings.enabled)),
            scan_timeout_seconds=max(1, int(settings_data.get("scan_timeout_seconds", defaults.bluetooth_settings.scan_timeout_seconds))),
            connect_timeout_seconds=max(1, int(settings_data.get("connect_timeout_seconds", defaults.bluetooth_settings.connect_timeout_seconds))),
            auto_reconnect=bool(settings_data.get("auto_reconnect", defaults.bluetooth_settings.auto_reconnect)),
            last_connected_device_id=str(settings_data.get("last_connected_device_id", "")),
            last_connected_device_name=str(settings_data.get("last_connected_device_name", "")),
            default_target_device_id=str(settings_data.get("default_target_device_id", "")),
        )

        normalized_input_waveforms = [
            _normalize_waveform(item)
            for item in payload.get("ems_waveforms", [])
            if isinstance(item, dict)
        ]
        if normalized_input_waveforms:
            custom_waveforms = [
                waveform for waveform in normalized_input_waveforms
                if waveform.id.lower() != "ems-default-pulse" and not is_preset_waveform_id(waveform.id)
            ]
            waveforms = [*custom_waveforms, *defaults.ems_waveforms]
        else:
            waveforms = defaults.ems_waveforms

        rules = [
            _normalize_rule(item)
            for item in payload.get("bluetooth_event_rules", [])
            if isinstance(item, dict)
        ]
        if not rules:
            rules = defaults.bluetooth_event_rules
        else:
            rules = _migrate_legacy_default_rules(rules)

        return BluetoothConfigPayload(
            bluetooth_settings=settings,
            ems_waveforms=waveforms,
            bluetooth_event_rules=rules,
        )

    def save(self, payload: BluetoothConfigPayload) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload_to_dict(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _normalize_waveform(item: dict) -> EmsWaveform:
    steps = item.get("steps", [])
    normalized_steps = [
        EmsWaveformStep(
            duration_ms=max(1, int(step.get("duration_ms", 200))),
            channel_a=_normalize_channel_strength(step.get("channel_a", 40)),
            channel_a_mode=max(1, int(step.get("channel_a_mode", step.get("a_mode", 1)))),
            channel_a_frequency=max(1, int(step.get("channel_a_frequency", step.get("a_frequency", 10)))),
            channel_a_pulse_width=max(1, int(step.get("channel_a_pulse_width", step.get("a_pulse_width", 5)))),
            channel_b=_normalize_channel_strength(step.get("channel_b", 40)),
            channel_b_mode=max(1, int(step.get("channel_b_mode", step.get("b_mode", 1)))),
            channel_b_frequency=max(1, int(step.get("channel_b_frequency", step.get("b_frequency", 10)))),
            channel_b_pulse_width=max(1, int(step.get("channel_b_pulse_width", step.get("b_pulse_width", 5)))),
        )
        for step in steps
        if isinstance(step, dict)
    ]
    if not normalized_steps:
        normalized_steps = [EmsWaveformStep()]
    return EmsWaveform(
        id=str(item.get("id", "custom-wave")),
        name=str(item.get("name", "自定义波形")),
        builtin=bool(item.get("builtin", False)),
        editable=bool(item.get("editable", True)),
        execution_mode=str(item.get("execution_mode", "fixed") or "fixed").lower(),
        loop_count=max(1, int(item.get("loop_count", 1))),
        steps=normalized_steps,
    )


def _normalize_rule(item: dict) -> BluetoothEventRule:
    filters = item.get("filters", {})
    return BluetoothEventRule(
        id=str(item.get("id", "rule-default")),
        enabled=bool(item.get("enabled", False)),
        event_type=str(item.get("event_type", "gift")),
        waveform_id=str(item.get("waveform_id", "")),
        cooldown_seconds=max(0, int(item.get("cooldown_seconds", 0))),
        filters=filters if isinstance(filters, dict) else {},
    )


def _normalize_channel_strength(value) -> int:
    return max(0, min(int(value), 180))


def _migrate_legacy_default_rules(rules: list[BluetoothEventRule]) -> list[BluetoothEventRule]:
    rules = _migrate_legacy_gift_default_rule(rules)
    rules = _migrate_legacy_danmaku_default_rules(rules)
    rules = _migrate_legacy_special_event_rules(rules)
    rules = _append_missing_special_event_rules(rules)
    rule_map = {rule.id: rule for rule in rules}
    for rule_id in ("like-default",):
        rule = rule_map.get(rule_id)
        if rule is None:
            continue
        if rule_id == "like-default" and rule.event_type == "like" and rule.waveform_id == "ems-preset-01" and rule.enabled is False:
            rule.enabled = True
    return rules


def _migrate_legacy_special_event_rules(rules: list[BluetoothEventRule]) -> list[BluetoothEventRule]:
    legacy_rule_ids = {
        "super-chat-default",
        "guard-buy-default",
        "guard-renew-default",
    }
    has_legacy_special_rule = any(rule.id in legacy_rule_ids for rule in rules)
    has_new_special_rule = any(
        rule.id.startswith("super-chat-tier-")
        or rule.id.startswith("guard-buy-tier-")
        or rule.id.startswith("guard-renew-tier-")
        for rule in rules
    )
    if not has_legacy_special_rule or has_new_special_rule:
        return rules

    legacy_rules_by_event_type = {
        rule.event_type: rule
        for rule in rules
        if rule.id in legacy_rule_ids
    }
    migrated_rules: list[BluetoothEventRule] = []
    for default_rule in build_default_special_event_rules(enabled=True):
        if default_rule.event_type == "interact":
            continue
        legacy_rule = legacy_rules_by_event_type.get(default_rule.event_type)
        if legacy_rule is None:
            migrated_rules.append(default_rule)
            continue
        migrated_rules.append(
            BluetoothEventRule(
                id=default_rule.id,
                enabled=legacy_rule.enabled,
                event_type=default_rule.event_type,
                waveform_id=default_rule.waveform_id,
                cooldown_seconds=legacy_rule.cooldown_seconds,
                filters=dict(default_rule.filters),
            )
        )
    remaining_rules = [rule for rule in rules if rule.id not in legacy_rule_ids]
    return [*remaining_rules, *migrated_rules]


def _append_missing_special_event_rules(rules: list[BluetoothEventRule]) -> list[BluetoothEventRule]:
    """为旧配置补齐新增的 SC、舰队和互动事件规则。"""
    existing_rule_ids = {rule.id for rule in rules}
    missing_rules = [
        rule
        for rule in build_default_special_event_rules(enabled=True)
        if rule.id not in existing_rule_ids
    ]
    return [*rules, *missing_rules]


def _migrate_legacy_gift_default_rule(rules: list[BluetoothEventRule]) -> list[BluetoothEventRule]:
    if any(rule.id in GIFT_TIER_BY_RULE_ID for rule in rules):
        return rules

    gift_default = next((rule for rule in rules if rule.id == "gift-default" and rule.event_type == "gift"), None)
    if gift_default is None:
        return rules

    is_default_waveform = gift_default.waveform_id == "ems-preset-06"
    is_default_filters = not gift_default.filters
    default_rules = build_default_gift_rules(enabled=True)
    if not is_default_waveform or not is_default_filters:
        default_rules = [
            {
                **item,
                "enabled": gift_default.enabled,
                "waveform_id": gift_default.waveform_id,
            }
            for item in build_default_gift_rules(enabled=gift_default.enabled)
        ]

    migrated_rules = [
        BluetoothEventRule(
            id=str(item["id"]),
            enabled=bool(item["enabled"]),
            event_type=str(item["event_type"]),
            waveform_id=str(item["waveform_id"]),
            cooldown_seconds=int(item["cooldown_seconds"]),
            filters=dict(item["filters"]),
        )
        for item in default_rules
    ]
    remaining_rules = [rule for rule in rules if rule.id != "gift-default"]
    return [*migrated_rules, *remaining_rules]


def _migrate_legacy_danmaku_default_rules(rules: list[BluetoothEventRule]) -> list[BluetoothEventRule]:
    if any(rule.id in {item["id"] for item in BLUETOOTH_DANMAKU_RULE_DEFINITIONS} for rule in rules):
        return rules

    legacy_rule = next(
        (
            rule
            for rule in rules
            if rule.id == "danmaku-default" and rule.event_type == "danmaku"
        ),
        None,
    )
    if legacy_rule is None:
        return rules

    migrated_rules = []
    for default_rule in build_default_danmaku_rules(enabled=legacy_rule.enabled):
        default_rule.waveform_id = legacy_rule.waveform_id or default_rule.waveform_id
        default_rule.filters = dict(legacy_rule.filters)
        default_rule.cooldown_seconds = legacy_rule.cooldown_seconds
        migrated_rules.append(default_rule)

    remaining_rules = [rule for rule in rules if rule.id != "danmaku-default"]
    return [*remaining_rules, *migrated_rules]
