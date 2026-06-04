from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PriceTierDefinition:
    rule_id: str
    event_type: str
    label: str
    min_price: int
    max_price: int | None
    default_waveform_id: str


SPECIAL_PRICE_TIER_DEFINITIONS: tuple[PriceTierDefinition, ...] = (
    PriceTierDefinition("super-chat-tier-01", "super_chat", "醒目留言档位 01", 30, 49, "ems-preset-07"),
    PriceTierDefinition("super-chat-tier-02", "super_chat", "醒目留言档位 02", 50, 99, "ems-preset-07"),
    PriceTierDefinition("super-chat-tier-03", "super_chat", "醒目留言档位 03", 100, 499, "ems-preset-07"),
    PriceTierDefinition("super-chat-tier-04", "super_chat", "醒目留言档位 04", 500, 999, "ems-preset-07"),
    PriceTierDefinition("super-chat-tier-05", "super_chat", "醒目留言档位 05", 1000, 1999, "ems-preset-07"),
    PriceTierDefinition("super-chat-tier-06", "super_chat", "醒目留言档位 06", 2000, None, "ems-preset-07"),
    PriceTierDefinition("guard-buy-tier-01", "guard_buy", "上舰档位 01", 100000, 999999, "ems-preset-08"),
    PriceTierDefinition("guard-buy-tier-02", "guard_buy", "上舰档位 02", 1000000, 9999999, "ems-preset-08"),
    PriceTierDefinition("guard-buy-tier-03", "guard_buy", "上舰档位 03", 10000000, None, "ems-preset-08"),
    PriceTierDefinition("guard-renew-tier-01", "guard_renew", "续费档位 01", 50000, 999999, "ems-preset-08"),
    PriceTierDefinition("guard-renew-tier-02", "guard_renew", "续费档位 02", 1000000, 9999999, "ems-preset-08"),
    PriceTierDefinition("guard-renew-tier-03", "guard_renew", "续费档位 03", 10000000, None, "ems-preset-08"),
)

SPECIAL_PRICE_TIER_BY_RULE_ID = {
    item.rule_id: item
    for item in SPECIAL_PRICE_TIER_DEFINITIONS
}

SPECIAL_PRICE_TIER_RULE_IDS_BY_EVENT_TYPE = {
    event_type: tuple(
        item.rule_id
        for item in SPECIAL_PRICE_TIER_DEFINITIONS
        if item.event_type == event_type
    )
    for event_type in {"super_chat", "guard_buy", "guard_renew"}
}

PRICE_FILTER_EVENT_TYPES = {"gift", "super_chat", "guard_buy", "guard_renew"}


def build_default_special_price_rules(*, enabled: bool = True) -> list[dict[str, Any]]:
    return [
        {
            "id": tier.rule_id,
            "enabled": enabled,
            "event_type": tier.event_type,
            "waveform_id": tier.default_waveform_id,
            "cooldown_seconds": 0,
            "filters": {
                "min_price": tier.min_price,
                "max_price": tier.max_price,
            },
        }
        for tier in SPECIAL_PRICE_TIER_DEFINITIONS
    ]
