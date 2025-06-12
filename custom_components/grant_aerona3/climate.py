"""Climate platform for Grant Aerona3 Heat Pump with corrected register mappings."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    OPERATING_MODES,
    CLIMATE_MODES,
)
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 climate entities with ashp_ prefixes."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Add climate entities
    entities.extend([
        GrantAerona3MainZoneClimate(coordinator, config_entry),
        GrantAerona3Zone2Climate(coordinator, config_entry),
        GrantAerona3DHWClimate(coordinator, config_entry),
    ])

    _LOGGER.info("Creating %d ASHP climate entities", len(entities))
    async_add_entities(entities)


class GrantAerona3BaseClimate(CoordinatorEntity, ClimateEntity):
    """Base class for Grant Aerona3 climate entities."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_precision = 0.5

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


class GrantAerona3MainZoneClimate(GrantAerona3BaseClimate):
    """Climate entity for main heating zone (Zone 1)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the main zone climate entity."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Zone 1"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_zone_1"
        self.entity_id = "climate.ashp_zone_1"
        
        # Climate entity features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        
        # Supported HVAC modes
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.AUTO,
        ]
        
        # FIXED: Temperature limits based on holding register doc - correct scaling
        self._attr_min_temp = 23
        self._attr_max_temp = 60.0  
        self._attr_target_temperature_step = 0.5

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        if not self.coordinator.data:
            return None
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # FIXED: Use Zone1 room temperature from register 11 (Master remote controller)
        # Reference: Register 11: "Room air set temperature of Zone1(Master)" - Unit: 0.1°C
        room_temp = input_regs.get(11, 0) * 0.1 if input_regs.get(11) else None
        
        if room_temp and room_temp > 0:
            return round(room_temp, 1)
        
        # FIXED: Fallback to return water temperature (register 0) - Unit: 1°C (no scaling)
        # Reference: Register 0: "Return water temperature" - Unit: 1°C
        return_temp = input_regs.get(0, 0) if input_regs.get(0) else None
        if return_temp and return_temp > 0:
            return round(float(return_temp), 1)
        
        return 21.0  # Default room temperature

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the target temperature for Zone 1."""
        if not self.coordinator.data:
            return None
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        
        # Check if we're in heating or cooling mode to determine which setpoint to use
        current_mode = self._get_current_mode()
        
        if current_mode == "heating":
            # FIXED: Register 2: Zone1 Fixed Outgoing water set point in Heating (/10 scaling)
            target = holding_regs.get(2, 450) / 10 if holding_regs.get(2) else None  # Default 45°C
        elif current_mode == "cooling":
            # FIXED: Register 12: Zone1 Fixed Outgoing water set point in Cooling (/10 scaling)
            target = holding_regs.get(12, 70) / 10 if holding_regs.get(12) else None  # Default 7°C
        else:
            # Default to heating setpoint
            target = holding_regs.get(2, 450) / 10 if holding_regs.get(2) else None
        
        if target and target > 0:
            return round(target, 1)
        
        return 45

    def _get_current_mode(self) -> str:
        """Determine current operating mode."""
        if not self.coordinator.data:
            return "heating"
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # FIXED: Check operation mode from input register 10 (Selected operating mode)
        # Reference: Register 10: "Selected operating mode (0=Heating/Cooling OFF, 1=Heating, 2=Cooling)"
        mode = input_regs.get(10, 1)  # Default to heating
        
        if mode == 1:
            return "heating"
        elif mode == 2:
            return "cooling"
        else:
            return "heating"  # Default

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if not self.coordinator.data:
            return HVACMode.OFF
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # FIXED: Get operation mode from input register 10
        mode = input_regs.get(10, 0)
        # FIXED: Current consumption from register 3 with 100W scale
        # Reference: Register 3: "Current consumption value" - Unit: 100W
        power = input_regs.get(3, 0) * 100  # Current consumption (100W scale)
        # FIXED: Compressor frequency from register 1
        # Reference: Register 1: "Compressor operating frequency" - Unit: 1Hz
        frequency = input_regs.get(1, 0)  # Compressor frequency
        
        # Check if system is actually running
        if mode == 0 or (power < 100 and frequency == 0):
            return HVACMode.OFF
        elif mode == 1:
            return HVACMode.HEAT
        elif mode == 2:
            return HVACMode.COOL
        else:
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        if not self.coordinator.data:
            return HVACAction.OFF
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # FIXED: Check if compressor is running
        frequency = input_regs.get(1, 0)  # Compressor frequency (1Hz scale)
        power = input_regs.get(3, 0) * 100  # Current power (100W scale)
        
        if frequency > 0 or power > 200:
            # Determine if heating or cooling based on mode
            mode = input_regs.get(10, 1)
            if mode == 2:  # Cooling mode
                return HVACAction.COOLING
            else:  # Heating mode or auto
                return HVACAction.HEATING
        else:
            return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature for Zone 1."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        # Convert to register value (/10 scaling, so multiply by 10)
        register_value = int(temperature * 10)
        
        # Determine which register to write based on current mode
        current_mode = self._get_current_mode()
        
        if current_mode == "heating":
            # Write to register 2: Zone1 Heating setpoint
            register_id = 2
        elif current_mode == "cooling":
            # Write to register 12: Zone1 Cooling setpoint
            register_id = 12
        else:
            # Default to heating
            register_id = 2
        
        success = await self.coordinator.async_write_register(register_id, register_value)
        
        if success:
            _LOGGER.info("Set Zone 1 target temperature to %s°C (register %d)", temperature, register_id)
        else:
            _LOGGER.error("Failed to set Zone 1 target temperature to %s°C", temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode for Zone 1."""
        # Note: The actual operation mode might be controlled by a different register
        # This would need to be determined from the input register mappings
        _LOGGER.info("HVAC mode change requested for Zone 1: %s", hvac_mode)
        # Implementation would depend on finding the correct control register

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        input_regs = self.coordinator.data.get("input_registers", {})
        holding_regs = self.coordinator.data.get("holding_registers", {})
        
        return {
            "zone": "Zone 1",
            # FIXED: Flow temperature from register 9 (Outgoing water temperature) - 1°C scale
            "flow_temperature": input_regs.get(9, 0) if input_regs.get(9) else None,
            # FIXED: Return temperature from register 0 - 1°C scale
            "return_temperature": input_regs.get(0, 0) if input_regs.get(0) else None,
            # FIXED: Outdoor temperature from register 6 - 1°C scale
            "outdoor_temperature": input_regs.get(6, 0) if input_regs.get(6) else None,
            # FIXED: Compressor frequency from register 1 - 1Hz scale
            "compressor_frequency": input_regs.get(1, 0),
            # FIXED: Current power from register 3 - 100W scale
            "current_power": input_regs.get(3, 0) * 100,
            # FIXED: Operation mode from register 10
            "operation_mode": OPERATING_MODES.get(input_regs.get(10, 0), "Unknown"),
            # FIXED: Heating setpoint from register 2 - /10 scaling
            "heating_setpoint": holding_regs.get(2, 0) / 10 if holding_regs.get(2) else None,
            # FIXED: Cooling setpoint from register 12 - /10 scaling
            "cooling_setpoint": holding_regs.get(12, 0) / 10 if holding_regs.get(12) else None,
            # FIXED: Max heating temp from register 3 - /10 scaling
            "max_heating_temp": holding_regs.get(3, 0) / 10 if holding_regs.get(3) else None,
            # FIXED: Min heating temp from register 4 - /10 scaling
            "min_heating_temp": holding_regs.get(4, 0) / 10 if holding_regs.get(4) else None,
            # ADDED: Plate heat exchanger temperature from register 32 - 1°C scale
            "plate_heat_exchanger_temp": input_regs.get(32, 0) if input_regs.get(32) else None,
        }


class GrantAerona3Zone2Climate(GrantAerona3BaseClimate):
    """Climate entity for Zone 2."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Zone 2 climate entity."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Zone 2"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_zone_2"
        self.entity_id = "climate.ashp_zone_2"
        
        # Climate entity features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        
        # Supported HVAC modes
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.AUTO,
        ]
        
        # Temperature limits
        self._attr_min_temp = 23
        self._attr_max_temp = 60.0
        self._attr_target_temperature_step = 0.5

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the target temperature for Zone 2."""
        if not self.coordinator.data:
            return None
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        
        current_mode = self._get_current_mode()
        
        if current_mode == "heating":
            # FIXED: Register 7: Zone2 Fixed Outgoing water set point in Heating (/10 scaling)
            target = holding_regs.get(7, 450) / 10 if holding_regs.get(7) else None
        elif current_mode == "cooling":
            # FIXED: Register 17: Zone2 Fixed Outgoing water set point in Cooling (/10 scaling)
            target = holding_regs.get(17, 70) / 10 if holding_regs.get(17) else None
        else:
            target = holding_regs.get(7, 450) / 10 if holding_regs.get(7) else None
        
        if target and target > 0:
            return round(target, 1)
        
        return 45

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature for Zone 2."""
        if not self.coordinator.data:
            return None
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # FIXED: Use Zone2 room temperature from register 12 (Slave remote controller)
        # Reference: Register 12: "Room air set temperature of Zone2(Slave)" - Unit: 0.1°C
        room_temp = input_regs.get(12, 0) * 0.1 if input_regs.get(12) else None
        
        if room_temp and room_temp > 0:
            return round(room_temp, 1)
        
        # FIXED: Fallback to return water temperature (register 0) - 1°C scale
        return_temp = input_regs.get(0, 0) if input_regs.get(0) else None
        if return_temp and return_temp > 0:
            return round(float(return_temp), 1)
        
        return 21.0  # Default room temperature

    def _get_current_mode(self) -> str:
        """Determine current operating mode for Zone 2."""
        # Same logic as Zone 1
        if not self.coordinator.data:
            return "heating"
        
        input_regs = self.coordinator.data.get("input_registers", {})
        mode = input_regs.get(10, 1)  # Register 10: Selected operating mode
        
        if mode == 1:
            return "heating"
        elif mode == 2:
            return "cooling"
        else:
            return "heating"

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode for Zone 2."""
        # Zone 2 follows the same system mode as Zone 1
        if not self.coordinator.data:
            return HVACMode.OFF
        
        input_regs = self.coordinator.data.get("input_registers", {})
        mode = input_regs.get(10, 0)  # Register 10: Selected operating mode
        power = input_regs.get(3, 0) * 100  # Current consumption (100W scale)
        frequency = input_regs.get(1, 0)
        
        if mode == 0 or (power < 100 and frequency == 0):
            return HVACMode.OFF
        elif mode == 1:
            return HVACMode.HEAT
        elif mode == 2:
            return HVACMode.COOL
        else:
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action for Zone 2."""
        # Similar to Zone 1
        if not self.coordinator.data:
            return HVACAction.OFF
        
        input_regs = self.coordinator.data.get("input_registers", {})
        frequency = input_regs.get(1, 0)
        power = input_regs.get(3, 0) * 100  # Current consumption (100W scale)
        
        if frequency > 0 or power > 200:
            mode = input_regs.get(10, 1)  # Register 10: Selected operating mode
            if mode == 2:
                return HVACAction.COOLING
            else:
                return HVACAction.HEATING
        else:
            return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature for Zone 2."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        register_value = int(temperature * 10)
        current_mode = self._get_current_mode()
        
        if current_mode == "heating":
            register_id = 7  # Zone2 Heating setpoint
        elif current_mode == "cooling":
            register_id = 17  # Zone2 Cooling setpoint
        else:
            register_id = 7
        
        success = await self.coordinator.async_write_register(register_id, register_value)
        
        if success:
            _LOGGER.info("Set Zone 2 target temperature to %s°C (register %d)", temperature, register_id)
        else:
            _LOGGER.error("Failed to set Zone 2 target temperature to %s°C", temperature)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes for Zone 2."""
        if not self.coordinator.data:
            return {}
        
        input_regs = self.coordinator.data.get("input_registers", {})
        holding_regs = self.coordinator.data.get("holding_registers", {})
        
        return {
            "zone": "Zone 2",
            # FIXED: Flow temperature from register 9 - 1°C scale
            "flow_temperature": input_regs.get(9, 0) if input_regs.get(9) else None,
            # FIXED: Return temperature from register 0 - 1°C scale
            "return_temperature": input_regs.get(0, 0) if input_regs.get(0) else None,
            # FIXED: Outdoor temperature from register 6 - 1°C scale
            "outdoor_temperature": input_regs.get(6, 0) if input_regs.get(6) else None,
            # FIXED: Heating setpoint from register 7 - /10 scaling
            "heating_setpoint": holding_regs.get(7, 0) / 10 if holding_regs.get(7) else None,
            # FIXED: Cooling setpoint from register 17 - /10 scaling
            "cooling_setpoint": holding_regs.get(17, 0) / 10 if holding_regs.get(17) else None,
            # FIXED: Max heating temp from register 8 - /10 scaling
            "max_heating_temp": holding_regs.get(8, 0) / 10 if holding_regs.get(8) else None,
            # FIXED: Min heating temp from register 9 - /10 scaling
            "min_heating_temp": holding_regs.get(9, 0) / 10 if holding_regs.get(9) else None,
        }


class GrantAerona3DHWClimate(GrantAerona3BaseClimate):
    """Climate entity for DHW (Domestic Hot Water) control."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the DHW climate entity."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Tank"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_tank"
        self.entity_id = "climate.ashp_dhw_tank"
        
        # DHW specific features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        
        # DHW only supports heat and off modes
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
        ]
        
        self._attr_min_temp = 40.0 
        self._attr_max_temp = 60.0  
        self._attr_target_temperature_step = 0.5

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current DHW tank temperature."""
        if not self.coordinator.data:
            return None
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # FIXED: Get DHW tank temperature from input register 16 (Terminal 7-8)
        # Reference: Register 16: "DHW tank temperature (Terminal 7-8)" - Unit: 0.1°C
        temp = input_regs.get(16, 0) * 0.1 if input_regs.get(16) else None
        
        if temp and temp > 0:
            return round(temp, 1)
        
        return 50.0  # Default DHW temperature

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the target DHW temperature."""
        if not self.coordinator.data:
            return None
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        
        # FIXED: Check DHW mode from input register 13 to determine which setpoint to use
        # Reference: Register 13: "Selected DHW operating mode (0=disable, 1=Comfort, 2=Economy, 3=Force)"
        input_regs = self.coordinator.data.get("input_registers", {})
        dhw_mode = input_regs.get(13, 1) if input_regs else 1
        
        if dhw_mode == 1:  # Comfort mode
            # Register 28: DHW Comfort set temperature (/10 scaling)
            target = holding_regs.get(28, 500) / 10 if holding_regs.get(28) else None  # Default 50°C
        elif dhw_mode == 2:  # Economy mode
            # Register 29: DHW Economy set temperature (/10 scaling)
            target = holding_regs.get(29, 430) / 10 if holding_regs.get(29) else None  # Default 43°C
        elif dhw_mode == 3:  # Force/Boost mode
            # Register 31: DHW Over boost mode set point (/10 scaling)
            target = holding_regs.get(31, 600) / 10 if holding_regs.get(31) else None  # Default 60°C
        else:
            # Default to comfort mode
            target = holding_regs.get(28, 500) / 10 if holding_regs.get(28) else None
        
        if target and target > 0:
            return round(target, 1)
        
        return 50.0  

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current DHW HVAC mode."""
        if not self.coordinator.data:
            return HVACMode.OFF
        
        input_regs = self.coordinator.data.get("input_registers", {})
        holding_regs = self.coordinator.data.get("holding_registers", {})
        
        # Check DHW priority setting from register 26
        dhw_priority = holding_regs.get(26, 0)
        
        # FIXED: Check DHW mode from input register 13
        dhw_mode = input_regs.get(13, 0)
        
        if dhw_priority > 0 and dhw_mode > 0:
            return HVACMode.HEAT
        else:
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return current DHW HVAC action."""
        if not self.coordinator.data:
            return HVACAction.OFF
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Check if DHW heating is active
        current_temp = self.current_temperature or 0
        target_temp = self.target_temperature or 0
        power = input_regs.get(3, 0) * 100  # Current consumption (100W scale)
        
        # DHW is heating if below target and system is consuming power
        if current_temp < target_temp - 1 and power > 200:
            return HVACAction.HEATING
        elif current_temp >= target_temp:
            return HVACAction.IDLE
        else:
            return HVACAction.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new DHW target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        # Validate temperature range
        if not (self._attr_min_temp <= temperature <= self._attr_max_temp):
            _LOGGER.error(
                "DHW temperature %s°C outside allowed range %s-%s°C",
                temperature, self._attr_min_temp, self._attr_max_temp
            )
            return
        
        # Convert to register value (/10 scaling, so multiply by 10)
        register_value = int(temperature * 10)
        
        # Determine which register to write based on current DHW mode
        input_regs = self.coordinator.data.get("input_registers", {}) if self.coordinator.data else {}
        dhw_mode = input_regs.get(13, 1)  # Default to comfort mode
        
        if dhw_mode == 1:  # Comfort mode
            register_id = 28
        elif dhw_mode == 2:  # Economy mode
            register_id = 29
        elif dhw_mode == 3:  # Force/Boost mode
            register_id = 31
        else:
            register_id = 28  # Default to comfort
        
        success = await self.coordinator.async_write_register(register_id, register_value)
        
        if success:
            _LOGGER.info("Set DHW target temperature to %s°C (register %d, mode %d)", temperature, register_id, dhw_mode)
        else:
            _LOGGER.error("Failed to set DHW target temperature to %s°C", temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new DHW HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            # Set DHW priority to 0 (register 26)
            mode_value = 0
            register_id = 26
        elif hvac_mode == HVACMode.HEAT:
            # Set DHW priority to 1 (DHW available and priority over space heating)
            mode_value = 1
            register_id = 26
        else:
            _LOGGER.error("Unsupported DHW HVAC mode: %s", hvac_mode)
            return
        
        success = await self.coordinator.async_write_register(register_id, mode_value)
        
        if success:
            _LOGGER.info("Set DHW HVAC mode to %s (register %d = %d)", hvac_mode, register_id, mode_value)
        else:
            _LOGGER.error("Failed to set DHW HVAC mode to %s", hvac_mode)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        input_regs = self.coordinator.data.get("input_registers", {})
        holding_regs = self.coordinator.data.get("holding_registers", {})
        
        # FIXED: DHW modes mapping - use correct register 13
        dhw_modes = {
            0: "Off",
            1: "Comfort",
            2: "Economy", 
            3: "Boost"
        }
        
        return {
            # FIXED: DHW mode from input register 13, not holding register 42
            "dhw_mode": dhw_modes.get(input_regs.get(13, 0), "Unknown"),
            "tank_temperature": self.current_temperature,
            "heating_active": self.hvac_action == HVACAction.HEATING,
            # FIXED: Power consumption from input register 3 with 100W scale
            "power_consumption": input_regs.get(3, 0) * 100,
            # ADDED: Additional useful DHW attributes
            "dhw_priority": holding_regs.get(26, 0),  # DHW production priority setting
            "comfort_setpoint": holding_regs.get(28) / 10 if holding_regs.get(28) is not None else None,
            "economy_setpoint": holding_regs.get(29, 0) / 10 if holding_regs.get(29) else None,
            "boost_setpoint": holding_regs.get(31, 0) / 10 if holding_regs.get(31) else None,
            "dhw_hysteresis": holding_regs.get(30, 0) / 10 if holding_regs.get(30) else None,
        }