"""Grant Aerona3 Heat Pump integration for Home Assistant with ASHP prefixes."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)

# All platforms supported by the integration
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grant Aerona3 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    try:
        # Initialize coordinator
        coordinator = GrantAerona3Coordinator(hass, entry)
        
        # Perform initial data refresh
        await coordinator.async_config_entry_first_refresh()
        
        # Store coordinator in hass data
        hass.data[DOMAIN][entry.entry_id] = coordinator
        
        # Set up all platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        _LOGGER.info(
            "Grant Aerona3 ASHP integration setup completed for %s (v1.1.0 with ashp_ prefixes)",
            entry.data["host"]
        )
        
        # Log entity count for debugging
        entity_count = (
            len(coordinator.data.get("input_registers", {}) or {}) +
            len(coordinator.data.get("holding_registers", {}) or {}) +
            7
        )
        _LOGGER.info("Created %d ASHP entities with ashp_ prefixes", entity_count)
        
        return True
        
    except Exception as err:
        _LOGGER.error("Failed to setup Grant Aerona3 ASHP integration: %s", err)
        raise ConfigEntryNotReady(f"Failed to setup integration: {err}") from err


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload all platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Remove coordinator from hass data
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("Grant Aerona3 ASHP integration unloaded successfully")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)