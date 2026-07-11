"""Grant Aerona3 Heat Pump integration for Home Assistant."""
from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN,
    CONF_HAS_BUFFER,
    CONF_HAS_DHW_TANK,
    CONF_HAS_EHS,
    FEATURE_ZONE2,
    INPUT_REGISTER_MAP,
    HOLDING_REGISTER_MAP,
    INPUT_REGISTER_FEATURES,
    HOLDING_REGISTER_FEATURES,
)
from .coordinator import GrantAerona3Coordinator
from .features import register_enabled

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
    FEATURE_ZONE2: ("weather_compensation_active_zone2",),
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
    for reg_id in HOLDING_REGISTER_MAP:
        if not register_enabled(features, HOLDING_REGISTER_FEATURES, reg_id):
            stale_ids.add(f"ashp_{entry.entry_id}_holding_{reg_id}")
            stale_ids.add(f"{entry.entry_id}_number_holding_{reg_id}")
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
    
    try:
        # Initialize coordinator
        coordinator = GrantAerona3Coordinator(hass, entry)
        _LOGGER.info("Enabled hardware features: %s", sorted(coordinator.features) or "core only")

        # Perform initial data refresh
        await coordinator.async_config_entry_first_refresh()

        # Store coordinator in hass data - simple overwrite approach
        # This avoids the recursive loop risk mentioned in the review
        if entry.entry_id in hass.data[DOMAIN]:
            _LOGGER.warning("Replacing existing coordinator for entry %s", entry.entry_id)

        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Clean up entities left over from previously enabled features
        _remove_disabled_entities(hass, entry, coordinator.features)

        # Set up all platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Set up options update listener
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
        
        _LOGGER.info(
            "Grant Aerona3 ASHP integration setup completed for %s (v1.1.4 with ashp_ prefixes)",
            host
        )
        
        # Log entity count for debugging
        try:
            input_regs = coordinator.data.get("input_registers", {}) or {}
            holding_regs = coordinator.data.get("holding_registers", {}) or {}
            entity_count = len(input_regs) + len(holding_regs) + 7
            _LOGGER.info("Created %d ASHP entities with ashp_ prefixes (unit_id: %s)", entity_count, unit_id)
        except Exception as e:
            _LOGGER.warning("Could not calculate entity count: %s", e)
            _LOGGER.info("Grant Aerona3 integration setup completed for %s", host)
        
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