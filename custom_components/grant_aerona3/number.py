"""Improved number platform for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, MANUFACTURER, MODEL, HOLDING_REGISTER_MAP
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 number entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # CRITICAL FIX: Create number entities for ALL writable holding registers
    for register_id, config in HOLDING_REGISTER_MAP.items():
        if config.get("writable", False):
            entities.append(
                GrantAerona3HoldingNumber(coordinator, config_entry, register_id)
            )

    # Add flow rate configuration entity
    entities.append(
        GrantAerona3FlowRateNumber(coordinator, config_entry)
    )

    _LOGGER.info("Creating %d number entities", len(entities))
    async_add_entities(entities)


class GrantAerona3HoldingNumber(CoordinatorEntity, NumberEntity):
    """Grant Aerona3 holding register number entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._register_id = register_id
        self._register_config = HOLDING_REGISTER_MAP[register_id]

        self._attr_unique_id = f"{config_entry.entry_id}_number_holding_{register_id}"
        self._attr_name = f"{self._register_config['name']}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Set number properties
        self._attr_native_unit_of_measurement = self._register_config["unit"]
        self._attr_mode = NumberMode.BOX  # Use box mode for precise control

        # Set min/max values based on register type and unit
        if self._register_config["unit"] == UnitOfTemperature.CELSIUS:
            # Temperature ranges
            if "dhw" in self._register_config["name"].lower():
                self._attr_native_min_value = 10.0
                self._attr_native_max_value = 70.0
                self._attr_native_step = 0.5
            elif "outdoor" in self._register_config["name"].lower():
                self._attr_native_min_value = -30.0
                self._attr_native_max_value = 50.0
                self._attr_native_step = 0.5
            else:
                self._attr_native_min_value = 0.0
                self._attr_native_max_value = 80.0
                self._attr_native_step = 0.5
        elif self._register_config["unit"] is None:
            # Non-unit values (modes, settings, etc.)
            name_lower = self._register_config["name"].lower()
            if "mode" in name_lower or "type" in name_lower or "function" in name_lower:
                self._attr_native_min_value = 0
                self._attr_native_max_value = 10  # Most modes are 0-3, give some room
                self._attr_native_step = 1
            elif "time" in name_lower or "delay" in name_lower:
                self._attr_native_min_value = 0
                self._attr_native_max_value = 300  # Up to 5 minutes for timing settings
                self._attr_native_step = 1
            else:
                self._attr_native_min_value = 0
                self._attr_native_max_value = 100
                self._attr_native_step = 1
        else:
            # Other units - set reasonable defaults
            self._attr_native_min_value = 0
            self._attr_native_max_value = 100
            self._attr_native_step = 1

        # Set icon based on function
        name_lower = self._register_config["name"].lower()
        if "temp" in name_lower:
            self._attr_icon = "mdi:thermometer"
        elif "dhw" in name_lower:
            self._attr_icon = "mdi:water-thermometer"
        elif "time" in name_lower or "delay" in name_lower:
            self._attr_icon = "mdi:clock"
        elif "hysteresis" in name_lower:
            self._attr_icon = "mdi:thermometer-lines"
        elif "flow" in name_lower:
            self._attr_icon = "mdi:pipe"
        else:
            self._attr_icon = "mdi:tune"

        # Set entity category
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value."""
        register_key = f"holding_{self._register_id}"
        if register_key not in self.coordinator.data:
            return None

        register_data = self.coordinator.data[register_key]
        
        # Check if register is available
        if not register_data.get("available", True):
            return None
            
        return register_data["value"]

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        # Convert value back to raw register value using the scale factor from const.py
        raw_value = int(value / self._register_config["scale"])

        success = await self.coordinator.async_write_holding_register(self._register_id, raw_value)
        if success:
            # Request immediate refresh to update state
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set value %s for %s", value, self._attr_name)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        register_key = f"holding_{self._register_id}"
        if register_key not in self.coordinator.data:
            return {"register_address": self._register_id, "status": "not_configured"}

        data = self.coordinator.data[register_key]

        attributes = {
            "register_address": self._register_id,
            "description": data.get("description", ""),
            "scale_factor": self._register_config["scale"],
            "raw_value": data.get("raw_value"),
            "available": data.get("available", True),
        }

        # Add error information if register is not available
        if not data.get("available", True):
            attributes["error"] = data.get("error", "Register not available")
            attributes["status"] = "unavailable"
        else:
            attributes["status"] = "available"

        # Add helpful information for specific setting types
        name_lower = self._register_config["name"].lower()
        if "dhw" in name_lower:
            attributes["tooltip"] = "DHW (Domestic Hot Water) temperature setting"
        elif "weather compensation" in name_lower:
            attributes["tooltip"] = "Weather compensation automatically adjusts heating based on outdoor temperature"
        elif "hysteresis" in name_lower:
            attributes["tooltip"] = "Hysteresis prevents frequent switching by creating a temperature band"
        elif "frost protection" in name_lower:
            attributes["tooltip"] = "Frost protection prevents system damage in cold weather"

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        register_key = f"holding_{self._register_id}"
        if register_key not in self.coordinator.data:
            return False
            
        # Entity is available even if register is not readable (shows unavailable state)
        return self.coordinator.last_update_success


class GrantAerona3FlowRateNumber(CoordinatorEntity, NumberEntity):
    """Grant Aerona3 flow rate configuration number entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the flow rate number entity."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{config_entry.entry_id}_flow_rate_config"
        self._attr_name = "Flow Rate"
        self._attr_native_unit_of_measurement = "L/min"
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value = 10.0
        self._attr_native_max_value = 50.0
        self._attr_native_step = 0.5
        self._attr_icon = "mdi:water-pump"
        self._attr_entity_category = EntityCategory.CONFIG

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.1.0",
        }

        # Default flow rate - typical for residential Grant Aerona3
        self._flow_rate = 30.0

    @property
    def native_value(self) -> float:
        """Return the current flow rate."""
        return self._flow_rate

    async def async_set_native_value(self, value: float) -> None:
        """Set the flow rate value."""
        self._flow_rate = value
        _LOGGER.info("Flow rate set to %.1f L/min", value)

        # Store in coordinator for COP calculations
        self.coordinator.flow_rate = value

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        return {
            "description": "Manually measured flow rate for COP calculations",
            "how_to_measure": "Use a flow meter or calculate from pump curves",
            "typical_range": "15-25 L/min for residential systems",
            "tooltip": "Set this to your actual measured flow rate for accurate COP calculations"
        }