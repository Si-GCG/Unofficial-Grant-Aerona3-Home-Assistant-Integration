"""Feature-selection helpers for the Grant Aerona3 integration."""
from __future__ import annotations

from typing import Any, Dict, Tuple

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_HAS_BUFFER,
    CONF_HAS_COOLING,
    CONF_HAS_DHW_TANK,
    CONF_HAS_EHS,
    CONF_ZONES,
    DEFAULT_FEATURES,
    FEATURE_ZONE2,
    ZONES_DUAL,
)


def get_feature(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Return a config value, options (Configure) taking precedence over data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


def enabled_features(entry: ConfigEntry) -> frozenset[str]:
    """Return the set of enabled feature keys for this entry."""
    enabled = set()
    for key in (CONF_HAS_DHW_TANK, CONF_HAS_BUFFER, CONF_HAS_EHS, CONF_HAS_COOLING):
        if get_feature(entry, key, DEFAULT_FEATURES[key]):
            enabled.add(key)
    if get_feature(entry, CONF_ZONES, DEFAULT_FEATURES[CONF_ZONES]) == ZONES_DUAL:
        enabled.add(FEATURE_ZONE2)
    return frozenset(enabled)


def register_enabled(
    features: frozenset[str],
    feature_map: Dict[int, Tuple[str, ...]],
    register_id: int,
) -> bool:
    """Return True if a register should be polled/exposed with these features.

    Registers absent from the feature map are core and always enabled.
    """
    return all(req in features for req in feature_map.get(register_id, ()))
