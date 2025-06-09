"""Simplified Grant Aerona3 Heat Pump integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_SLAVE_ID, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL # Import new constants
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)

# All platforms that this integration will set up
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT, # Added Platform.SELECT for new dropdown entities
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grant Aerona3 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    try:
        # Extract configuration data from the entry.
        # Connection details are in entry.data, and user-selected options are in entry.options.
        host = entry.data.get(CONF_HOST)
        port = entry.data.get(CONF_PORT)
        slave_id = entry.data.get(CONF_SLAVE_ID) # Ensure this is captured in config_flow if needed
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL) # Ensure this is captured if needed

        # Initialize the coordinator, passing both data and options
        coordinator = GrantAerona3Coordinator(
            hass,
            host=host,
            port=port,
            slave_id=slave_id,
            scan_interval=scan_interval,
            config_options=entry.options # Pass the config_entry.options to the coordinator
        )
        
        # Perform initial data refresh to ensure data is available before setting up entities
        await coordinator.async_config_entry_first_refresh()
        
        # Store coordinator in hass data, using the entry_id for unique access
        hass.data[DOMAIN][entry.entry_id] = coordinator
        
        # Set up all defined platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        _LOGGER.info(
            "Grant Aerona3 integration setup completed for %s:%s (Entry ID: %s)",
            host, port, entry.entry_id
        )
        
        return True
        
    except Exception as err:
        _LOGGER.error("Failed to setup Grant Aerona3 integration for %s:%s: %s",
                      entry.data.get(CONF_HOST), entry.data.get(CONF_PORT), err)
        raise ConfigEntryNotReady(f"Failed to setup integration: {err}") from err


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload all platforms associated with this config entry
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Remove coordinator from hass data
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Grant Aerona3 integration unloaded successfully for entry ID: %s", entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    # This function handles reloading an integration instance.
    # It first unloads all platforms, then re-sets them up, effectively reloading.
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
