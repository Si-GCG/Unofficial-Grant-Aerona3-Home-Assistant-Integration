"""Feature-selection helpers for the Grant Aerona3 integration."""
from __future__ import annotations

from typing import Any, Dict, Tuple

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_HAS_ADVANCED_CONFIG,
    CONF_HAS_BACKUP_HEATER,
    CONF_HAS_BUFFER,
    CONF_HAS_COOLING,
    CONF_HAS_DEHUMIDIFIER,
    CONF_EXPERIMENTAL_FLOW_OFFSET,
    CONF_EXPERIMENTAL_FLOW_CONTROLLER,
    CONF_FC_COLD_FLOW,
    CONF_FC_COLD_OUTDOOR,
    CONF_FC_MILD_FLOW,
    CONF_FC_MILD_OUTDOOR,
    CONF_FC_MIN_FLOW,
    CONF_MAX_FLOW_TEMP,
    DEFAULT_MAX_FLOW_TEMP,
    CONF_HAS_DHW_TANK,
    CONF_HAS_EHS,
    CONF_HAS_HUMIDITY_SENSOR,
    CONF_HAS_MIXING_VALVE,
    CONF_HAS_REMOTE_OUTDOOR_SENSOR,
    CONF_HAS_TARIFF_CONTROL,
    CONF_ZONES,
    DEFAULT_FEATURES,
    FEATURE_ZONE2,
    ZONES_DUAL,
)
from .flow_controller import Settings

BOOLEAN_FEATURE_KEYS = (
    CONF_HAS_DHW_TANK,
    CONF_HAS_BUFFER,
    CONF_HAS_EHS,
    CONF_HAS_COOLING,
    CONF_HAS_BACKUP_HEATER,
    CONF_HAS_HUMIDITY_SENSOR,
    CONF_HAS_MIXING_VALVE,
    CONF_HAS_REMOTE_OUTDOOR_SENSOR,
    CONF_HAS_TARIFF_CONTROL,
    CONF_HAS_DEHUMIDIFIER,
    CONF_HAS_ADVANCED_CONFIG,
    CONF_EXPERIMENTAL_FLOW_OFFSET,
    CONF_EXPERIMENTAL_FLOW_CONTROLLER,
)


def get_feature(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Return a config value, options (Configure) taking precedence over data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


def enabled_features(entry: ConfigEntry) -> frozenset[str]:
    """Return the set of enabled feature keys for this entry."""
    enabled = set()
    for key in BOOLEAN_FEATURE_KEYS:
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


def flow_controller_settings(entry: ConfigEntry) -> Settings:
    """The controller's curve points and limits, defaults where unset."""
    defaults = Settings()

    def value(key: str, default: float) -> float:
        return float(get_feature(entry, key, default))

    return Settings(
        cold_outdoor=value(CONF_FC_COLD_OUTDOOR, defaults.cold_outdoor),
        cold_flow=value(CONF_FC_COLD_FLOW, defaults.cold_flow),
        mild_outdoor=value(CONF_FC_MILD_OUTDOOR, defaults.mild_outdoor),
        mild_flow=value(CONF_FC_MILD_FLOW, defaults.mild_flow),
        min_flow=value(CONF_FC_MIN_FLOW, defaults.min_flow),
        max_flow=value(CONF_MAX_FLOW_TEMP, DEFAULT_MAX_FLOW_TEMP),
    )
