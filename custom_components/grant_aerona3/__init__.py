"""Grant Aerona3 Heat Pump integration for Home Assistant."""
from __future__ import annotations
import logging
import time
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    CONF_EXPERIMENTAL_FLOW_OFFSET,
    CONF_HAS_ADVANCED_CONFIG,
    CONF_HAS_BACKUP_HEATER,
    CONF_HAS_BUFFER,
    CONF_HAS_DHW_TANK,
    CONF_HAS_EHS,
    CONF_HAS_HUMIDITY_SENSOR,
    CONF_HAS_MIXING_VALVE,
    CONF_HAS_REMOTE_OUTDOOR_SENSOR,
    CONF_HAS_TARIFF_CONTROL,
    CONF_MAX_FLOW_TEMP,
    DEFAULT_MAX_FLOW_TEMP,
    FEATURE_ZONE2,
    INPUT_REGISTER_MAP,
    HOLDING_REGISTER_MAP,
    INPUT_REGISTER_FEATURES,
    HOLDING_REGISTER_FEATURES,
)
from .coordinator import GrantAerona3Coordinator
from .features import get_feature, register_enabled
from .flow_offset import WriteLimiter
from .flow_offset_manager import STORE_VERSION, FlowOffsetManager

_LOGGER = logging.getLogger(__name__)

# All platforms supported by the integration
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
]

# unique_id suffixes of the hand-written entities gated on each feature
# (register-based sensors/numbers are derived from the register maps instead)
FEATURE_UNIQUE_ID_SUFFIXES = {
    CONF_HAS_DHW_TANK: (
        "dhw_active", "dhw_priority", "dhw_hp_only_mode", "dhw_3way_valve",
        "anti_legionella", "dhw_tank_probe", "dhw_remote_contact",
    ),
    CONF_HAS_BUFFER: ("buffer_tank_probe",),
    CONF_HAS_EHS: ("ehs_function", "ehs_terminal"),
    CONF_EXPERIMENTAL_FLOW_OFFSET: ("flow_offset", "flow_offset_zone2"),
    FEATURE_ZONE2: ("weather_compensation_active_zone2", "flow_offset_zone2"),
    CONF_HAS_BACKUP_HEATER: ("backup_heater_enable", "backup_heater_active"),
    CONF_HAS_HUMIDITY_SENSOR: ("humidity_comp", "humidity_sensor"),
    CONF_HAS_MIXING_VALVE: ("mixing_valve", "mix_water_probe"),
    CONF_HAS_REMOTE_OUTDOOR_SENSOR: ("outdoor_probe",),
    CONF_HAS_TARIFF_CONTROL: ("night_mode", "low_tariff"),
    CONF_HAS_ADVANCED_CONFIG: (
        "freeze_protection", "terminal_20_21", "terminal_24_25",
        "terminal_47_alarm", "terminal_48_pump1", "terminal_49_pump2",
        "frost_outdoor", "frost_water", "dual_set_point", "flow_switch",
    ),
}


def _remove_disabled_entities(hass: HomeAssistant, entry: ConfigEntry, features: frozenset) -> None:
    """Drop registry entries for hardware the user has unticked.

    Without this, entities for disabled features linger as 'unavailable'
    after a reload instead of disappearing.
    """
    stale_ids = set()
    for reg_id in INPUT_REGISTER_MAP:
        if not register_enabled(features, INPUT_REGISTER_FEATURES, reg_id):
            stale_ids.add(f"ashp_{entry.entry_id}_input_{reg_id}")
    for reg_id, config in HOLDING_REGISTER_MAP.items():
        if not register_enabled(features, HOLDING_REGISTER_FEATURES, reg_id):
            stale_ids.add(f"ashp_{entry.entry_id}_holding_{reg_id}")
            stale_ids.add(f"{entry.entry_id}_number_holding_{reg_id}")
        elif config.get("writable", False):
            # sensor.py no longer creates a sensor for writable registers -
            # the number entity already exposes the same value.
            stale_ids.add(f"ashp_{entry.entry_id}_holding_{reg_id}")
    for feature, suffixes in FEATURE_UNIQUE_ID_SUFFIXES.items():
        if feature not in features:
            for suffix in suffixes:
                stale_ids.add(f"ashp_{entry.entry_id}_{suffix}")

    registry = er.async_get(hass)
    removed = 0
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.unique_id in stale_ids:
            registry.async_remove(reg_entry.entity_id)
            removed += 1
    if removed:
        _LOGGER.info("Removed %d entities for hardware not present in this installation", removed)


async def _async_setup_flow_offsets(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: GrantAerona3Coordinator
) -> dict[int, FlowOffsetManager]:
    """Create the per-zone flow offset managers (experimental, opt-in) and hook them up."""
    if CONF_EXPERIMENTAL_FLOW_OFFSET not in coordinator.features:
        return {}
    limiter = WriteLimiter()
    zones = [1] + ([2] if FEATURE_ZONE2 in coordinator.features else [])
    managers: dict[int, FlowOffsetManager] = {}
    for zone in zones:
        store = Store(hass, STORE_VERSION, f"{DOMAIN}_flow_offset_{entry.entry_id}_zone{zone}")
        manager = FlowOffsetManager(
            zone,
            coordinator,
            store,
            lambda: float(get_feature(entry, CONF_MAX_FLOW_TEMP, DEFAULT_MAX_FLOW_TEMP)),
            limiter,
            time.monotonic,
            hass.async_create_task,
        )
        await manager.async_load()
        manager.on_coordinator_update()  # capture the baseline from the first poll
        entry.async_on_unload(coordinator.async_add_listener(manager.on_coordinator_update))
        managers[zone] = manager
    return managers


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grant Aerona3 from a config entry."""
    # Ensure domain data structure exists
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    # Extract configuration data early for logging
    host = entry.data.get("host")
    unit_id = entry.data.get("unit_id", entry.data.get("slave_id"))  # fallback for old configs
    
    # Validate required configuration (serial connections have no host)
    if entry.data.get("connection_type", "tcp") == "tcp" and not host:
        _LOGGER.error("Host configuration is missing")
        return False
    
    setup_started = time.monotonic()
    try:
        # Initialize coordinator
        coordinator = GrantAerona3Coordinator(hass, entry)
        _LOGGER.info("Enabled hardware features: %s", sorted(coordinator.features) or "core only")

        # Perform initial data refresh
        await coordinator.async_config_entry_first_refresh()
        first_poll_seconds = time.monotonic() - setup_started

        # Store coordinator in hass data - simple overwrite approach
        # This avoids the recursive loop risk mentioned in the review
        if entry.entry_id in hass.data[DOMAIN]:
            _LOGGER.warning("Replacing existing coordinator for entry %s", entry.entry_id)

        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Flow offset managers (one per zone), listening to every poll
        coordinator.flow_offsets = await _async_setup_flow_offsets(hass, entry, coordinator)

        # Clean up entities left over from previously enabled features
        _remove_disabled_entities(hass, entry, coordinator.features)

        # Set up all platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Set up options update listener
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
        
        entity_count = len(
            er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        )
        _LOGGER.info(
            "Grant Aerona3 set up in %.1fs (first poll %.1fs, %d entities, unit_id %s)",
            time.monotonic() - setup_started,
            first_poll_seconds,
            entity_count,
            unit_id,
        )

        return True
        
    except Exception as err:
        _LOGGER.error("Failed to setup Grant Aerona3 ASHP integration: %s", err, exc_info=True)
        raise ConfigEntryNotReady(f"Failed to setup integration: {err}") from err

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        # Unload all platforms
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        
        if unload_ok:
            # Remove coordinator from hass data
            if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
                hass.data[DOMAIN].pop(entry.entry_id, None)
                _LOGGER.info("Grant Aerona3 ASHP integration unloaded successfully")
            else:
                _LOGGER.warning("Coordinator not found in hass data during unload")
        
        return unload_ok
    except Exception as e:
        _LOGGER.error("Error during unload: %s", e, exc_info=True)
        return False

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    try:
        unloaded = await async_unload_entry(hass, entry)
        if unloaded:
            await async_setup_entry(hass, entry)
        else:
            _LOGGER.error("Reload aborted: unload failed for entry %s", entry.entry_id)
    except Exception as e:
        _LOGGER.error("Error during reload: %s", e, exc_info=True)
        raise