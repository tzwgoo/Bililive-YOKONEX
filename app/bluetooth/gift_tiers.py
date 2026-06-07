from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GiftTierDefinition:
    rule_id: str
    label: str
    min_price: int
    max_price: int | None
    default_waveform_id: str
    default_toy_waveform_id: str = "toy-preset-01"


GIFT_TIER_DEFINITIONS: tuple[GiftTierDefinition, ...] = (
    GiftTierDefinition("gift-tier-01", "礼物档位 01", 0, 99, "ems-preset-01", "toy-preset-01"),
    GiftTierDefinition("gift-tier-02", "礼物档位 02", 100, 999, "ems-preset-02", "toy-preset-02"),
    GiftTierDefinition("gift-tier-03", "礼物档位 03", 1000, 4999, "ems-preset-03", "toy-preset-03"),
    GiftTierDefinition("gift-tier-04", "礼物档位 04", 5000, 9999, "ems-preset-04", "toy-preset-04"),
    GiftTierDefinition("gift-tier-05", "礼物档位 05", 10000, 19999, "ems-preset-05", "toy-preset-05"),
    GiftTierDefinition("gift-tier-06", "礼物档位 06", 20000, 49999, "ems-preset-06", "toy-preset-06"),
    GiftTierDefinition("gift-tier-07", "礼物档位 07", 50000, 99999, "ems-preset-07", "toy-preset-07"),
    GiftTierDefinition("gift-tier-08", "礼物档位 08", 100000, 199999, "ems-preset-08", "toy-preset-08"),
    GiftTierDefinition("gift-tier-09", "礼物档位 09", 200000, 999999, "ems-preset-09", "toy-preset-09"),
    GiftTierDefinition("gift-tier-10", "礼物档位 10", 1000000, None, "ems-preset-10", "toy-preset-10"),
)

GIFT_TIER_BY_RULE_ID = {
    item.rule_id: item
    for item in GIFT_TIER_DEFINITIONS
}


def build_default_gift_rules(*, enabled: bool = True) -> list[dict[str, Any]]:
    return [
        {
            "id": tier.rule_id,
            "enabled": enabled,
            "event_type": "gift",
            "waveform_id": tier.default_waveform_id,
            "toy_waveform_id": tier.default_toy_waveform_id,
            "cooldown_seconds": 0,
            "filters": {
                "min_price": tier.min_price,
                "max_price": tier.max_price,
            },
        }
        for tier in GIFT_TIER_DEFINITIONS
    ]


def match_gift_tier_rule(price: int) -> GiftTierDefinition | None:
    for tier in GIFT_TIER_DEFINITIONS:
        if price < tier.min_price:
            continue
        if tier.max_price is not None and price > tier.max_price:
            continue
        return tier
    return None
