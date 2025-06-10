"""Improved climate platform for Grant Aerona3 Heat Pump."""
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

from .const import DOMAIN, MANUFACTURER, MODEL, HOLDING_REGISTER_MAP
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

    # CRITICAL FIX: Always create climate entity for Zone 1 (main zone)
    entities.append(GrantAerona3Climate(coordinator, config_entry, zone=1))

    # CRITICAL FIX: Always create climate entity for Zone 2 
    # Don't check if data is available during setup - entity will handle unavailable state
    entities.append(GrantAerona3Climate(coordinator, config_entry, zone=2))

    _LOGGER.info("Creating %d climate entities", len(entities))
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
        self._attr_name = f"Zone {zone}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASAHP",
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
            register_data = self.coordinator.data["input_0"]
            if register_data.get("available", True):
                return register_data["value"]
        return None

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the target temperature."""
        # Use room air set temperature for the zone
        if self._zone == 1:
            register_key = "input_11"
        elif self._zone == 2:
            register_key = "input_12"
        else:
            return None

        if register_key in self.coordinator.data:
            register_data = self.coordinator.data[register_key]
            if register_data.get("available", True):
                return register_data["value"]
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        # Get operating mode from register 10
        if "input_10" in self.coordinator.data:
            register_data = self.coordinator.data["input_10"]
            if register_data.get("available", True):
                mode_value = register_data["value"]
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
        flow_temp_data = self.coordinator.data.get("input_9")
        if flow_temp_data and flow_temp_data.get("available", True):
            attributes["flow_temperature"] = flow_temp_data["value"]

        return_temp_data = self.coordinator.data.get("input_0")
        if return_temp_data and return_temp_data.get("available", True):
            attributes["return_temperature"] = return_temp_data["value"]

        # Add outdoor temperature
        outdoor_temp_data = self.coordinator.data.get("input_6")
        if outdoor_temp_data and outdoor_temp_data.get("available", True):
            attributes["outdoor_temperature"] = outdoor_temp_data["value"]

        # Add compressor frequency
        compressor_data = self.coordinator.data.get("input_1")
        if compressor_data and compressor_data.get("available", True):
            attributes["compressor_frequency"] = compressor_data["value"]

        # Add zone-specific information
        if self._zone == 1:
            zone_temp_data = self.coordinator.data.get("input_11")
        else:
            zone_temp_data = self.coordinator.data.get("input_12")

        if zone_temp_data:
            if zone_temp_data.get("available", True):
                attributes["zone_available"] = True
            else:
                attributes["zone_available"] = False
                attributes["zone_error"] = zone_temp_data.get("error", "Zone not available")

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Climate entity is available if coordinator is working
        # Individual zone availability is shown in attributes
        return self.coordinator.last_update_success