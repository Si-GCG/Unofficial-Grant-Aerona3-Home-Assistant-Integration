"""Grant Aerona3 Heat Pump integration for Home Assistant."""
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
    Platform.SWITCH,
    Platform.NUMBER,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grant Aerona3 from a config entry."""
    # Ensure domain data structure exists
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    # Extract configuration data early for logging
    host = entry.data.get("host")
    unit_id = entry.data.get("unit_id", entry.data.get("slave_id"))  # fallback for old configs
    
    # Validate required configuration
    if not host:
        _LOGGER.error("Host configuration is missing")
        return False
    
    try:
        # Initialize coordinator
        coordinator = GrantAerona3Coordinator(hass, entry)
        
        # Perform initial data refresh
        await coordinator.async_config_entry_first_refresh()
        
        # Store coordinator in hass data - simple overwrite approach
        # This avoids the recursive loop risk mentioned in the review
        if entry.entry_id in hass.data[DOMAIN]:
            _LOGGER.warning("Replacing existing coordinator for entry %s", entry.entry_id)
        
        hass.data[DOMAIN][entry.entry_id] = coordinator
        
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