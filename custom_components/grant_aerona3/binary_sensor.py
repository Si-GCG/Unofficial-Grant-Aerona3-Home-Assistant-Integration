"""Binary sensor platform for Grant Aerona3 Heat Pump with ashp_ prefixes."""
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

from .const import DOMAIN, MANUFACTURER, MODEL, INPUT_REGISTER_MAP, HOLDING_REGISTER_MAP
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 binary sensor entities with ashp_ prefixes."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Add status binary sensors
    entities.extend([
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
    ])

    _LOGGER.info("Creating %d ASHP binary sensor entities", len(entities))
    async_add_entities(entities)


class GrantAerona3BaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base class for Grant Aerona3 binary sensors."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
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


class GrantAerona3CompressorSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for compressor running status."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
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
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Check compressor frequency (register 1)
        frequency = input_regs.get(1, 0)
        
        # Check power consumption (register 3 with 100W scale)
        power = input_regs.get(3, 0) * 100
        
        # Compressor is running if frequency > 0 or power > threshold
        return frequency > 0 or power > 200

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        input_regs = self.coordinator.data.get("input_registers", {})
        return {
            "compressor_frequency": input_regs.get(1, 0),
            "power_consumption": input_regs.get(3, 0) * 100,  # Convert to watts
        }


class GrantAerona3DefrostSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for defrost cycle status."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the defrost sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Defrost Active"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_defrost_active"
        self.entity_id = "binary_sensor.ashp_defrost_active"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:snowflake-melt"

    @property
    def is_on(self) -> bool:
        """Return true if defrost cycle is active."""
        if not self.coordinator.data:
            return False
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Check outdoor temperature and compressor status for defrost detection
        outdoor_temp = input_regs.get(2)
        outdoor_temp = outdoor_temp * 0.1 if outdoor_temp is not None else 10  # Adjust register/scale
        frequency = input_regs.get(1, 0)
        
        # Simple defrost detection logic
        # Defrost typically occurs when outdoor temp is low and compressor stops briefly
        return outdoor_temp <= 5 and frequency == 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        input_regs = self.coordinator.data.get("input_registers", {})
        return {
            "outdoor_temperature": input_regs.get(2, 0) * 0.1 if input_regs.get(2) else None,
            "compressor_frequency": input_regs.get(1, 0),
        }


class GrantAerona3AlarmSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for alarm status."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
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
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Check for alarm conditions (adjust register as needed)
        alarm_register = input_regs.get(20, 0)  # Adjust register number
        
        return alarm_register > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        input_regs = self.coordinator.data.get("input_registers", {})
        return {
            "alarm_code": input_regs.get(20, 0),
            "alarm_description": self._get_alarm_description(input_regs.get(20, 0)),
        }

    def _get_alarm_description(self, code: int) -> str:
        """Get alarm description from code."""
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
    """Binary sensor for heating mode status."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
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
        
        input_regs = self.coordinator.data.get("input_registers", {})
        holding_regs = self.coordinator.data.get("holding_registers", {})
        
        # Check operation mode and temperatures
        operation_mode = input_regs.get(13, 0)  # Adjust register
        flow_temp = input_regs.get(1)
        flow_temp = flow_temp * 0.1 if flow_temp is not None else 0
        return_temp = input_regs.get(0, 0) * 0.1 if input_regs.get(0) else 0
        
        # Heating is active if in heating mode and flow temp > return temp
        return operation_mode == 0 and flow_temp > return_temp + 1


class GrantAerona3DHWActiveSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for DHW (Domestic Hot Water) mode status."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the DHW active sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Active"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_active"
        self.entity_id = "binary_sensor.ashp_dhw_active"
        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_icon = "mdi:water-boiler"

    @property
    def is_on(self) -> bool:
        """Return true if DHW heating is active."""
        if not self.coordinator.data:
            return False
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        dhw_mode = input_regs.get(13, 0)  
        
        return dhw_mode > 0


class GrantAerona3BackupHeaterSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for backup heater status."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
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
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Check backup heater status (adjust logic as needed)
        outdoor_temp = input_regs.get(2)
        outdoor_temp = outdoor_temp * 0.1 if outdoor_temp is not None else 10
        power = input_regs.get(5, 0)
        
        # Backup heater likely active when outdoor temp is very low and power is high
        return outdoor_temp < -5 and power > 5000


class GrantAerona3FrostProtectionSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for frost protection status."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
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
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Check for frost protection conditions
        outdoor_temp = input_regs.get(2)
        outdoor_temp = outdoor_temp * 0.1 if outdoor_temp is not None else 10
        flow_temp = input_regs.get(1)
        flow_temp = flow_temp * 0.1 if flow_temp is not None else 0
        
        # Frost protection active when outdoor temp very low or flow temp near freezing
        return outdoor_temp < 0 or flow_temp < 5


class GrantAerona3WeatherCompActiveSensorZone1(GrantAerona3BaseBinarySensor):
    """Binary sensor for weather compensation status(Zone 1)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the weather compensation sensor Zone 1."""
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
    """Binary sensor for weather compensation status (Zone 2)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the weather compensation sensor for Zone 2."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Weather Compensation Active Zone 2"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_weather_compensation_active_zone2"
        self.entity_id = "binary_sensor.ashp_weather_compensation_active_zone2"
        self._attr_icon = "mdi:weather-partly-cloudy"

    @property
    def is_on(self) -> bool:
        """Return true if weather compensation is active for Zone 2."""
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        weather_comp_enabled = coil_regs.get(3, 0)  # Changed from 2 to 3
        
        return weather_comp_enabled > 0


class GrantAerona3CommunicationSensor(GrantAerona3BaseBinarySensor):
    """Binary sensor for communication status."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the communication sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Communication Status"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_communication_status"
        self.entity_id = "binary_sensor.ashp_communication_status"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:connection"

    @property
    def is_on(self) -> bool:
        """Return true if communication is working."""
        if not self.coordinator.data:
            return False
        
        # Check if we have recent data
        last_update = self.coordinator.data.get("last_update", 0)
        current_time = self.coordinator.hass.loop.time()
        
        # Communication OK if last update was within 2 minutes
        return (current_time - last_update) < 120

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        last_update = self.coordinator.data.get("last_update", 0)
        current_time = self.coordinator.hass.loop.time()
        
        return {
            "last_update_seconds_ago": round(current_time - last_update),
            "coordinator_available": self.coordinator.last_update_success,
        }