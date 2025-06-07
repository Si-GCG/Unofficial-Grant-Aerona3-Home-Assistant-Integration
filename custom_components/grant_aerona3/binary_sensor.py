"""Simplified binary sensor platform for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, COIL_REGISTER_MAP
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 binary sensor entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Create binary sensors for all coil registers
    for register_id in COIL_REGISTER_MAP.keys():
        entities.append(
            GrantAerona3CoilBinarySensor(coordinator, config_entry, register_id)
        )
    
    # Add system status binary sensors
    entities.extend([
        GrantAerona3SystemStatusSensor(coordinator, config_entry),
        GrantAerona3DefrostModeSensor(coordinator, config_entry),
        GrantAerona3ErrorStatusSensor(coordinator, config_entry),
    ])
    
    async_add_entities(entities)


class GrantAerona3CoilBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Grant Aerona3 coil register binary sensor entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._register_id = register_id
        self._register_config = COIL_REGISTER_MAP[register_id]
        
        self._attr_unique_id = f"{config_entry.entry_id}_coil_{register_id}"
        self._attr_name = f"Grant Aerona3 {self._register_config['name']}"
        
        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }
        
        # Set device class based on register function
        name_lower = self._register_config["name"].lower()
        if "alarm" in name_lower or "error" in name_lower:
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        elif "frost" in name_lower or "protection" in name_lower:
            self._attr_device_class = BinarySensorDeviceClass.SAFETY
        elif "pump" in name_lower or "valve" in name_lower or "heater" in name_lower:
            self._attr_device_class = BinarySensorDeviceClass.RUNNING
        else:
            self._attr_device_class = None
        
        # Set entity category for configuration items
        if any(word in name_lower for word in ["terminal", "enable", "config"]):
            self._attr_entity_category = "config"
        elif any(word in name_lower for word in ["alarm", "error", "frost"]):
            self._attr_entity_category = "diagnostic"

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the binary sensor is on."""
        register_key = f"coil_{self._register_id}"
        if register_key not in self.coordinator.data:
            return None
            
        return self.coordinator.data[register_key]["value"]

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        register_key = f"coil_{self._register_id}"
        if register_key not in self.coordinator.data:
            return {}
            
        data = self.coordinator.data[register_key]
        
        return {
            "register_address": self._register_id,
            "description": data.get("description", ""),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        register_key = f"coil_{self._register_id}"
        return (
            self.coordinator.last_update_success and
            register_key in self.coordinator.data
        )


class GrantAerona3SystemStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """System status binary sensor."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the system status sensor."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{config_entry.entry_id}_system_status"
        self._attr_name = "Grant Aerona3 System Status"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the system is running."""
        # Check if compressor is running (frequency > 0)
        if "input_1" in self.coordinator.data:
            frequency = self.coordinator.data["input_1"]["value"]
            return frequency > 0
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        attributes = {}
        
        # Add operating mode if available
        if "input_10" in self.coordinator.data:
            mode_value = self.coordinator.data["input_10"]["value"]
            mode_map = {0: "Off", 1: "Heating", 2: "Cooling"}
            attributes["operating_mode"] = mode_map.get(mode_value, f"Unknown ({mode_value})")
        
        # Add compressor frequency
        if "input_1" in self.coordinator.data:
            attributes["compressor_frequency"] = self.coordinator.data["input_1"]["value"]
        
        return attributes


class GrantAerona3DefrostModeSensor(CoordinatorEntity, BinarySensorEntity):
    """Defrost mode binary sensor."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the defrost mode sensor."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{config_entry.entry_id}_defrost_mode"
        self._attr_name = "Grant Aerona3 Defrost Mode"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:snowflake-melt"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if defrost mode is active."""
        # Check defrost temperature vs outdoor temperature
        if "input_5" in self.coordinator.data and "input_6" in self.coordinator.data:
            defrost_temp = self.coordinator.data["input_5"]["value"]
            outdoor_temp = self.coordinator.data["input_6"]["value"]
            
            # Simple defrost detection - when defrost temp is significantly higher than outdoor temp
            # and outdoor temp is below freezing
            if outdoor_temp < 2 and defrost_temp > outdoor_temp + 10:
                return True
                
        return False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        attributes = {}
        
        if "input_5" in self.coordinator.data:
            attributes["defrost_temperature"] = self.coordinator.data["input_5"]["value"]
        
        if "input_6" in self.coordinator.data:
            attributes["outdoor_temperature"] = self.coordinator.data["input_6"]["value"]
            
        return attributes


class GrantAerona3ErrorStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """Error status binary sensor."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the error status sensor."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{config_entry.entry_id}_error_status"
        self._attr_name = "Grant Aerona3 Error Status"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = "diagnostic"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if there are any errors."""
        # Check for any alarm or error coils being active
        error_coils = []
        
        for register_id, config in COIL_REGISTER_MAP.items():
            register_key = f"coil_{register_id}"
            if register_key in self.coordinator.data:
                name_lower = config["name"].lower()
                if "alarm" in name_lower or "error" in name_lower:
                    if self.coordinator.data[register_key]["value"]:
                        error_coils.append(config["name"])
        
        return len(error_coils) > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        attributes = {}
        
        # List all active errors
        active_errors = []
        for register_id, config in COIL_REGISTER_MAP.items():
            register_key = f"coil_{register_id}"
            if register_key in self.coordinator.data:
                name_lower = config["name"].lower()
                if "alarm" in name_lower or "error" in name_lower:
                    if self.coordinator.data[register_key]["value"]:
                        active_errors.append(config["name"])
        
        attributes["active_errors"] = active_errors
        attributes["error_count"] = len(active_errors)
        
        return attributes