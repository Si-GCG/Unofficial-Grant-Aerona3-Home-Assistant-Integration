# weather_compensation_entities.py

from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, SW_VERSION
from .weather_compensation import WeatherCompensationController

_LOGGER = logging.getLogger(__name__)

async def async_setup_weather_compensation_entities(
    hass,
    config_entry: ConfigEntry,
    coordinator,
    weather_compensation: WeatherCompensationController,
    async_add_entities: AddEntitiesCallback,
) -> None:
    if not weather_compensation.is_enabled():
        _LOGGER.debug("Weather compensation not enabled, skipping entities")
        return

    entities = [
        WeatherCompensationStatusSensor(coordinator, config_entry, weather_compensation),
        WeatherCompensationTargetTempSensor(coordinator, config_entry, weather_compensation),
    ]
    # Add boost switch if dual curve is enabled
    if weather_compensation.secondary_curve:
        entities.append(WeatherCompensationBoostSwitch(coordinator, config_entry, weather_compensation))
    async_add_entities(entities)

class WeatherCompensationStatusSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, weather_compensation: WeatherCompensationController):
        super().__init__(coordinator)
        self.weather_compensation = weather_compensation
        self._attr_unique_id = f"{config_entry.entry_id}_weather_compensation_status"
        self._attr_name = "ASHP Weather Compensation Status"
        self._attr_icon = "mdi:thermometer-auto"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP Grant Aerona3",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": SW_VERSION,
        }

    @property
    def native_value(self) -> str:
        status = self.weather_compensation.get_status()
        if not status.get("enabled", False):
            return "Disabled"
        if status.get("boost_active", False):
            return "Boost Active"
        return "Active"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.weather_compensation.get_status()

class WeatherCompensationTargetTempSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, weather_compensation: WeatherCompensationController):
        super().__init__(coordinator)
        self.weather_compensation = weather_compensation
        self._attr_unique_id = f"{config_entry.entry_id}_weather_compensation_target_temp"
        self._attr_name = "ASHP WC Target Flow Temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:thermometer-water"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP Grant Aerona3",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": SW_VERSION,
        }

    @property
    def native_value(self) -> Optional[float]:
        status = self.weather_compensation.get_status()
        return status.get("last_flow_temp")

class WeatherCompensationBoostSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, config_entry, weather_compensation: WeatherCompensationController):
        super().__init__(coordinator)
        self.weather_compensation = weather_compensation
        self._attr_unique_id = f"{config_entry.entry_id}_weather_compensation_boost"
        self._attr_name = "ASHP WC Boost Mode"
        self._attr_icon = "mdi:fire"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP Grant Aerona3",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": SW_VERSION,
        }

    @property
    def is_on(self) -> bool:
        return self.weather_compensation.get_status().get("boost_active", False)

    async def async_turn_on(self, **kwargs):
        await self.weather_compensation.activate_boost_mode(duration_minutes=120, reason="switch")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.weather_compensation.deactivate_boost_mode(reason="switch")
        await self.coordinator.async_request_refresh()
