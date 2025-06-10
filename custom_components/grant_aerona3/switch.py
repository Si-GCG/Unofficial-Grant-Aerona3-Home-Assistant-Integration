"""Improved switch platform for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, MANUFACTURER, MODEL, COIL_REGISTER_MAP
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 switch entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # CRITICAL FIX: Create switches for ALL configuration coil registers
    # Only create switches for configuration items, not status/alarm items
    for register_id, config in COIL_REGISTER_MAP.items():
        name_lower = config["name"].lower()

        # Only create switches for configuration items, not status/alarm items
        if any(word in name_lower for word in [
            "weather compensation", "anti-legionella", "frost protection",
            "enable", "terminal", "remote", "function", "compensation",
            "backup", "heater", "pump", "valve", "modbus"
        ]) and not any(word in name_lower for word in ["alarm", "error"]):
            entities.append(
                GrantAerona3CoilSwitch(coordinator, config_entry, register_id)
            )

    _LOGGER.info("Creating %d switch entities", len(entities))
    async_add_entities(entities)


class GrantAerona3CoilSwitch(CoordinatorEntity, SwitchEntity):
    """Grant Aerona3 coil register switch entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._register_id = register_id
        self._register_config = COIL_REGISTER_MAP[register_id]

        self._attr_unique_id = f"{config_entry.entry_id}_switch_coil_{register_id}"
        self._attr_name = f"{self._register_config['name']}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Set icon based on function
        name_lower = self._register_config["name"].lower()
        if "weather" in name_lower or "compensation" in name_lower:
            self._attr_icon = "mdi:weather-partly-cloudy"
        elif "frost" in name_lower or "protection" in name_lower:
            self._attr_icon = "mdi:snowflake"
        elif "pump" in name_lower:
            self._attr_icon = "mdi:pump"
        elif "heater" in name_lower:
            self._attr_icon = "mdi:radiator"
        elif "valve" in name_lower:
            self._attr_icon = "mdi:valve"
        elif "terminal" in name_lower or "modbus" in name_lower:
            self._attr_icon = "mdi:connection"
        else:
            self._attr_icon = "mdi:toggle-switch"

        # Set entity category
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the switch is on."""
        register_key = f"coil_{self._register_id}"
        if register_key not in self.coordinator.data:
            return None

        register_data = self.coordinator.data[register_key]
        
        # Check if register is available
        if not register_data.get("available", True):
            return None
            
        return register_data["value"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        success = await self.coordinator.async_write_coil(self._register_id, True)
        if success:
            # Request immediate refresh to update state
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn on switch %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        success = await self.coordinator.async_write_coil(self._register_id, False)
        if success:
            # Request immediate refresh to update state
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn off switch %s", self._attr_name)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        register_key = f"coil_{self._register_id}"
        if register_key not in self.coordinator.data:
            return {"register_address": self._register_id, "status": "not_configured"}

        data = self.coordinator.data[register_key]

        attributes = {
            "register_address": self._register_id,
            "description": data.get("description", ""),
            "available": data.get("available", True),
        }

        # Add error information if register is not available
        if not data.get("available", True):
            attributes["error"] = data.get("error", "Register not available")
            attributes["status"] = "unavailable"
        else:
            attributes["status"] = "available"

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        register_key = f"coil_{self._register_id}"
        if register_key not in self.coordinator.data:
            return False
            
        # Entity is available even if register is not readable (shows unavailable state)
        return self.coordinator.last_update_success