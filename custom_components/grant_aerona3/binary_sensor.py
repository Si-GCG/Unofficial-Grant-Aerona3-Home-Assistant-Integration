from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, INPUT_REGISTER_MAP
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)

def get_scaled_input(coordinator: GrantAerona3Coordinator, reg_id: int) -> Optional[float]:
    """Get scaled input register value."""
    reg_info = INPUT_REGISTER_MAP.get(reg_id, {})
    scale = reg_info.get("scale", 1)
    value = coordinator.data.get("input_registers", {}).get(reg_id)
    return value * scale if value is not None else None

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 binary sensor entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [
        GrantAerona3CompressorSensor(coordinator, config_entry),
        GrantAerona3DefrostSensor(coordinator, config_entry),
        GrantAerona3AlarmSensor(coordinator, config_entry),
        GrantAerona3HeatingActiveSensor(coordinator, config_entry),
        GrantAerona3DHWActiveSensor(coordinator, config_entry),
        GrantAerona3BackupHeaterSensor(coordinator, config_entry),
        GrantAerona3FrostProtectionSensor(coordinator, config_entry),
        GrantAerona3WeatherCompActiveSensorZone1(coordinator, config_entry),
        GrantAerona3WeatherCompActiveSensorZone2(coordinator, config_entry),
        GrantAerona3CommunicationSensor(coordinator, config_entry),
    ]
    _LOGGER.info("Creating %d ASHP binary sensor entities", len(entities))
    async_add_entities(entities)

class GrantAerona3BaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base class for Grant Aerona3 binary sensors."""
    
    def __init__(self, coordinator: GrantAerona3Coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "ASHP Grant Aerona3",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "2.0.0",
            "configuration_url": f"http://{self._config_entry.data.get('host', '')}",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

class GrantAerona3CompressorSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for compressor running status."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the compressor sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Compressor Running"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_compressor_running"
        self.entity_id = "binary_sensor.ashp_compressor_running"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:engine"

    @property
    def is_on(self) -> bool:
        """Return true if compressor is running."""
        if not self.coordinator.data:
            return False
        frequency = get_scaled_input(self.coordinator, 1)
        power = get_scaled_input(self.coordinator, 3)
        return (frequency or 0) > 0 or (power or 0) > 200

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "compressor_frequency": get_scaled_input(self.coordinator, 1),
            "power_consumption": get_scaled_input(self.coordinator, 3),
        }

class GrantAerona3DefrostSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for defrost active status."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the defrost sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Defrost Active"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_defrost_active"
        self.entity_id = "binary_sensor.ashp_defrost_active"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:snowflake-melt"

    @property
    def is_on(self) -> bool:
        """Return true if defrost is active."""
        if not self.coordinator.data:
            return False
        outdoor_temp = get_scaled_input(self.coordinator, 6)
        frequency = get_scaled_input(self.coordinator, 1)
        return (outdoor_temp is not None and outdoor_temp <= 5) and (frequency == 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "outdoor_temperature": get_scaled_input(self.coordinator, 6),
            "compressor_frequency": get_scaled_input(self.coordinator, 1),
        }

class GrantAerona3AlarmSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for alarm status."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the alarm sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Alarm Status"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_alarm_status"
        self.entity_id = "binary_sensor.ashp_alarm_status"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alert-circle"

    @property
    def is_on(self) -> bool:
        """Return true if alarm is active."""
        if not self.coordinator.data:
            return False
        alarm_register = get_scaled_input(self.coordinator, 21)
        return (alarm_register or 0) > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        code = get_scaled_input(self.coordinator, 21)
        return {
            "alarm_code": code,
            "alarm_description": self._get_alarm_description(code),
        }

    def _get_alarm_description(self, code: Optional[int]) -> str:
        """Get alarm description from code."""
        if code is None:
            return "No Data"
        alarm_codes = {
            0: "No Alarm",
            1: "High Pressure",
            2: "Low Pressure",
            3: "Compressor Overload",
            4: "Fan Motor Error",
            5: "Water Flow Error",
            6: "Temperature Sensor Error",
            7: "Communication Error",
        }
        return alarm_codes.get(code, f"Unknown Alarm ({code})")

class GrantAerona3HeatingActiveSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for heating active status."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the heating active sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Heating Active"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_heating_active"
        self.entity_id = "binary_sensor.ashp_heating_active"
        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_icon = "mdi:radiator"

    @property
    def is_on(self) -> bool:
        """Return true if heating is active."""
        if not self.coordinator.data:
            return False
        operation_mode = get_scaled_input(self.coordinator, 10)
        flow_temp = get_scaled_input(self.coordinator, 9)
        return_temp = get_scaled_input(self.coordinator, 0)
        return operation_mode == 1 and (flow_temp or 0) > (return_temp or 0) + 1

class GrantAerona3DHWActiveSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for DHW active status."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the DHW active sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Active"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_active"
        self.entity_id = "binary_sensor.ashp_dhw_active"
        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_icon = "mdi:water-boiler"

    @property
    def is_on(self) -> bool:
        """Return true if DHW is active."""
        if not self.coordinator.data:
            return False
        dhw_mode = get_scaled_input(self.coordinator, 13)
        return (dhw_mode or 0) > 0

class GrantAerona3BackupHeaterSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for backup heater active status."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the backup heater sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Backup Heater Active"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_backup_heater_active"
        self.entity_id = "binary_sensor.ashp_backup_heater_active"
        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_icon = "mdi:heating-coil"

    @property
    def is_on(self) -> bool:
        """Return true if backup heater is active."""
        if not self.coordinator.data:
            return False
        outdoor_temp = get_scaled_input(self.coordinator, 6)
        power = get_scaled_input(self.coordinator, 3)
        return (outdoor_temp is not None and outdoor_temp < -5) and (power or 0) > 5000

class GrantAerona3FrostProtectionSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for frost protection active status."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the frost protection sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Frost Protection Active"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_frost_protection_active"
        self.entity_id = "binary_sensor.ashp_frost_protection_active"
        self._attr_device_class = BinarySensorDeviceClass.SAFETY
        self._attr_icon = "mdi:snowflake-alert"

    @property
    def is_on(self) -> bool:
        """Return true if frost protection is active."""
        if not self.coordinator.data:
            return False
        outdoor_temp = get_scaled_input(self.coordinator, 6)
        flow_temp = get_scaled_input(self.coordinator, 9)
        return (outdoor_temp is not None and outdoor_temp < 0) or (flow_temp is not None and flow_temp < 5)

class GrantAerona3WeatherCompActiveSensorZone1(GrantAerona3BaseBinarySensor):
    """Binary sensor for weather compensation active status zone 1."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the weather compensation sensor zone 1."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Weather Compensation Active Zone 1"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_weather_compensation_active"
        self.entity_id = "binary_sensor.ashp_weather_compensation_active"
        self._attr_icon = "mdi:weather-partly-cloudy"

    @property
    def is_on(self) -> bool:
        """Return true if weather compensation is active."""
        if not self.coordinator.data:
            return False
        coil_regs = self.coordinator.data.get("coil_registers", {})
        weather_comp_enabled = coil_regs.get(2, 0)
        return weather_comp_enabled > 0

class GrantAerona3WeatherCompActiveSensorZone2(GrantAerona3BaseBinarySensor):
    """Binary sensor for weather compensation active status zone 2."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the weather compensation sensor zone 2."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Weather Compensation Active Zone 2"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_weather_compensation_active_zone2"
        self.entity_id = "binary_sensor.ashp_weather_compensation_active_zone2"
        self._attr_icon = "mdi:weather-partly-cloudy"

    @property
    def is_on(self) -> bool:
        """Return true if weather compensation is active."""
        if not self.coordinator.data:
            return False
        coil_regs = self.coordinator.data.get("coil_registers", {})
        weather_comp_enabled = coil_regs.get(3, 0)
        return weather_comp_enabled > 0

class GrantAerona3CommunicationSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for communication status."""
    
    def __init__(self, coordinator, config_entry):
        """Initialize the communication sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Communication Status"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_communication_status"
        self.entity_id = "binary_sensor.ashp_communication_status"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:connection"

    @property
    def is_on(self) -> bool:
        """Return true if communication is active."""
        if not self.coordinator.data:
            return False
        last_update = self.coordinator.data.get("last_update", 0)
        current_time = asyncio.get_running_loop().time()
        return (current_time - last_update) < 120

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        last_update = self.coordinator.data.get("last_update", 0)
        current_time = asyncio.get_running_loop().time()
        return {
            "last_update_seconds_ago": round(current_time - last_update),
            "coordinator_available": self.coordinator.last_update_success,
        }