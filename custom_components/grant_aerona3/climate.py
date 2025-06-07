"""Simplified climate platform for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 climate entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Create climate entity for Zone 1 (main zone)
    entities.append(GrantAerona3Climate(coordinator, config_entry, zone=1))
    
    # Create climate entity for Zone 2 if configured
    # Check if Zone 2 registers are available in the data
    if "input_12" in coordinator.data:  # Room Air Set Temperature Of Zone 2
        entities.append(GrantAerona3Climate(coordinator, config_entry, zone=2))
    
    async_add_entities(entities)


class GrantAerona3Climate(CoordinatorEntity, ClimateEntity):
    """Grant Aerona3 climate entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        zone: int,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._zone = zone
        
        self._attr_unique_id = f"{config_entry.entry_id}_climate_zone_{zone}"
        self._attr_name = f"Grant Aerona3 Zone {zone}"
        
        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }
        
        # Climate properties
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.TURN_ON |
            ClimateEntityFeature.TURN_OFF
        )
        
        # HVAC modes
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.AUTO,
        ]
        
        # Temperature limits
        self._attr_min_temp = 5.0
        self._attr_max_temp = 30.0
        self._attr_target_temperature_step = 0.5

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        # Use return water temperature as current temperature
        if "input_0" in self.coordinator.data:
            return self.coordinator.data["input_0"]["value"]
        return None

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the target temperature."""
        # Use room air set temperature for the zone
        if self._zone == 1 and "input_11" in self.coordinator.data:
            return self.coordinator.data["input_11"]["value"]
        elif self._zone == 2 and "input_12" in self.coordinator.data:
            return self.coordinator.data["input_12"]["value"]
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        # Get operating mode from register 10
        if "input_10" in self.coordinator.data:
            mode_value = self.coordinator.data["input_10"]["value"]
            mode_map = {
                0: HVACMode.OFF,
                1: HVACMode.HEAT,
                2: HVACMode.COOL,
            }
            return mode_map.get(mode_value, HVACMode.OFF)
        return HVACMode.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        # Get the scale factor from HOLDING_REGISTER_MAP for proper conversion
        from .const import HOLDING_REGISTER_MAP
        
        # Write to appropriate zone register
        if self._zone == 1:
            # Zone 1 uses holding register 2 (Fixed Flow Temp Zone 1)
            register_config = HOLDING_REGISTER_MAP.get(2)
            if register_config:
                raw_value = int(temperature / register_config["scale"])
                success = await self.coordinator.async_write_holding_register(2, raw_value)
            else:
                success = False
        elif self._zone == 2:
            # Zone 2 uses holding register 7 (Fixed Flow Temp Zone 2)
            register_config = HOLDING_REGISTER_MAP.get(7)
            if register_config:
                raw_value = int(temperature / register_config["scale"])
                success = await self.coordinator.async_write_holding_register(7, raw_value)
            else:
                success = False
        else:
            success = False
        
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set temperature for zone %d", self._zone)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        # Map HVAC mode to register value
        mode_map = {
            HVACMode.OFF: 0,
            HVACMode.HEAT: 1,
            HVACMode.COOL: 2,
            HVACMode.AUTO: 1,  # Default to heating for auto
        }
        
        mode_value = mode_map.get(hvac_mode)
        if mode_value is None:
            _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
            return
        
        # Note: The operating mode register (input_10) might be read-only
        # This is a simplified implementation - in practice, mode setting
        # might require writing to different registers or coils
        _LOGGER.warning("HVAC mode setting not fully implemented - register may be read-only")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = {
            "zone": self._zone,
        }
        
        # Add flow temperatures
        if "input_9" in self.coordinator.data:
            attributes["flow_temperature"] = self.coordinator.data["input_9"]["value"]
        
        if "input_0" in self.coordinator.data:
            attributes["return_temperature"] = self.coordinator.data["input_0"]["value"]
        
        # Add outdoor temperature
        if "input_6" in self.coordinator.data:
            attributes["outdoor_temperature"] = self.coordinator.data["input_6"]["value"]
        
        # Add compressor frequency
        if "input_1" in self.coordinator.data:
            attributes["compressor_frequency"] = self.coordinator.data["input_1"]["value"]
        
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Check if required registers are available
        required_registers = ["input_10"]  # Operating mode
        if self._zone == 1:
            required_registers.append("input_11")  # Zone 1 set temp
        elif self._zone == 2:
            required_registers.append("input_12")  # Zone 2 set temp
        
        return (
            self.coordinator.last_update_success and
            all(reg in self.coordinator.data for reg in required_registers)
        )