"""Improved binary sensor platform for Grant Aerona3 Heat Pump."""
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
from homeassistant.helpers.entity import EntityCategory

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

    # CRITICAL FIX: Create binary sensors for ALL coil registers, not just available ones
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

    _LOGGER.info("Creating %d binary sensor entities", len(entities))
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
        self._attr_name = f"{self._register_config['name']}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
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
            self._attr_entity_category = EntityCategory.CONFIG
        elif any(word in name_lower for word in ["alarm", "error", "frost"]):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the binary sensor is on."""
        register_key = f"coil_{self._register_id}"
        if register_key not in self.coordinator.data:
            return None

        register_data = self.coordinator.data[register_key]
        
        # Check if register is available
        if not register_data.get("available", True):
            return None
            
        return register_data["value"]

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
        self._attr_name = "System Status"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the system is running."""
        # Check if compressor is running (frequency > 0)
        if "input_1" in self.coordinator.data:
            register_data = self.coordinator.data["input_1"]
            if register_data.get("available", True):
                frequency = register_data["value"]
                return frequency > 0
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        attributes = {}

        # Add operating mode if available
        if "input_10" in self.coordinator.data:
            register_data = self.coordinator.data["input_10"]
            if register_data.get("available", True):
                mode_value = register_data["value"]
                mode_map = {0: "Off", 1: "Heating", 2: "Cooling"}
                attributes["operating_mode"] = mode_map.get(mode_value, f"Unknown ({mode_value})")

        # Add compressor frequency
        if "input_1" in self.coordinator.data:
            register_data = self.coordinator.data["input_1"]
            if register_data.get("available", True):
                attributes["compressor_frequency"] = register_data["value"]

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
        self._attr_name = "Defrost Mode"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:snowflake-melt"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if defrost mode is active."""
        # Check defrost temperature vs outdoor temperature
        defrost_data = self.coordinator.data.get("input_5")
        outdoor_data = self.coordinator.data.get("input_6")
        
        if defrost_data and outdoor_data:
            if defrost_data.get("available", True) and outdoor_data.get("available", True):
                defrost_temp = defrost_data["value"]
                outdoor_temp = outdoor_data["value"]

                # Simple defrost detection - when defrost temp is significantly higher than outdoor temp
                # and outdoor temp is below freezing
                if outdoor_temp < 2 and defrost_temp > outdoor_temp + 10:
                    return True

        return False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        attributes = {}

        defrost_data = self.coordinator.data.get("input_5")
        if defrost_data and defrost_data.get("available", True):
            attributes["defrost_temperature"] = defrost_data["value"]

        outdoor_data = self.coordinator.data.get("input_6")
        if outdoor_data and outdoor_data.get("available", True):
            attributes["outdoor_temperature"] = outdoor_data["value"]

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
        self._attr_name = Error Status"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
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
                register_data = self.coordinator.data[register_key]
                if register_data.get("available", True):
                    name_lower = config["name"].lower()
                    if "alarm" in name_lower or "error" in name_lower:
                        if register_data["value"]:
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
                register_data = self.coordinator.data[register_key]
                if register_data.get("available", True):
                    name_lower = config["name"].lower()
                    if "alarm" in name_lower or "error" in name_lower:
                        if register_data["value"]:
                            active_errors.append(config["name"])

        attributes["active_errors"] = active_errors
        attributes["error_count"] = len(active_errors)

        return attributes