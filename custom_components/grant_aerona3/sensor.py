# custom_components/grant_aerona3/sensor.py

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    INPUT_REGISTER_MAP,
    HOLDING_REGISTER_MAP,
    INPUT_REGISTER_FEATURES,
    HOLDING_REGISTER_FEATURES,
)
from .coordinator import GrantAerona3Coordinator
from .features import register_enabled

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 sensor entities with ashp_ prefixes."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    features = coordinator.features

    # Create sensors for input registers matching the configured hardware
    for register_id in INPUT_REGISTER_MAP.keys():
        if register_enabled(features, INPUT_REGISTER_FEATURES, register_id):
            entities.append(
                GrantAerona3InputSensor(coordinator, config_entry, register_id)
            )

    # Create sensors for holding registers matching the configured hardware
    for register_id in HOLDING_REGISTER_MAP.keys():
        if register_enabled(features, HOLDING_REGISTER_FEATURES, register_id):
            entities.append(
                GrantAerona3HoldingSensor(coordinator, config_entry, register_id)
            )

    # Add calculated sensors with ashp_ prefix
    entities.extend([
    GrantAerona3PowerSensor(coordinator, config_entry),
    GrantAerona3COPSensor(coordinator, config_entry),
    GrantAerona3DeltaTSensor(coordinator, config_entry),
    GrantAerona3EfficiencySensor(coordinator, config_entry),
    GrantAerona3WeatherCompSensor(coordinator, config_entry),
    ])

    _LOGGER.info("Creating %d ASHP sensor entities with ashp_ prefix", len(entities))
    async_add_entities(entities)

class GrantAerona3BaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Grant Aerona3 sensors with common properties."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the base sensor."""
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

class GrantAerona3InputSensor(GrantAerona3BaseSensor):
    """Grant Aerona3 input register sensor entity with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the sensor with ashp_ prefix."""
        super().__init__(coordinator, config_entry)
        self._register_id = register_id
        self._register_config = INPUT_REGISTER_MAP.get(register_id, {})
        
        # Create entity_id and names with ashp_ prefix
        register_name = self._register_config.get("name", f"Input Register {register_id}")
        clean_name = register_name.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace('/', '_')
        
        self._attr_name = f"ASHP {register_name}"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_input_{register_id}"
        self.entity_id = f"sensor.ashp_{clean_name}"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        raw_value = self.coordinator.data.get("input_registers", {}).get(self._register_id)
        if raw_value is None or raw_value == 65535:
            return None

        is_signed = self._register_config.get("signed", False)
        if is_signed and raw_value > 32767:
            raw_value -= 65536

        scale = self._register_config.get("scale", 1)
        offset = self._register_config.get("offset", 0)
        
        return round((raw_value * scale) + offset, 2)

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        return self._register_config.get("unit")

    @property
    def device_class(self) -> Optional[SensorDeviceClass]:
        """Return the device class."""
        return self._register_config.get("device_class")

    @property
    def state_class(self) -> Optional[SensorStateClass]:
        """Return the state class."""
        return self._register_config.get("state_class")

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        device_class = self._register_config.get("device_class")
        if device_class == SensorDeviceClass.TEMPERATURE:
            return "mdi:thermometer"
        elif device_class == SensorDeviceClass.POWER:
            return "mdi:flash"
        elif "frequency" in self._register_config.get("name", "").lower():
            return "mdi:gauge"
        elif "pressure" in self._register_config.get("name", "").lower():
            return "mdi:gauge-low"
        else:
            return "mdi:heat-pump"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "register_id": self._register_id,
            "register_type": "input",
            "description": self._register_config.get("description", ""),
            "raw_value": self.coordinator.data.get("input_registers", {}).get(self._register_id) if self.coordinator.data else None,
            "scale_factor": self._register_config.get("scale", 1),
            "offset": self._register_config.get("offset", 0),
        }

class GrantAerona3HoldingSensor(GrantAerona3BaseSensor):
    """Grant Aerona3 holding register sensor entity with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the sensor with ashp_ prefix."""
        super().__init__(coordinator, config_entry)
        self._register_id = register_id
        self._register_config = HOLDING_REGISTER_MAP.get(register_id, {})
        
        # Create entity_id and names with ashp_ prefix
        register_name = self._register_config.get("name", f"Holding Register {register_id}")
        clean_name = register_name.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace('/', '_')
        
        self._attr_name = f"ASHP {register_name}"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_holding_{register_id}"
        self.entity_id = f"sensor.ashp_{clean_name}"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        raw_value = self.coordinator.data.get("holding_registers", {}).get(self._register_id)
        if raw_value is None or raw_value == 65535:
            return None

        is_signed = self._register_config.get("signed", False)
        if is_signed and raw_value > 32767:
            raw_value -= 65536

        scale = self._register_config.get("scale", 1)
        offset = self._register_config.get("offset", 0)
        
        return round((raw_value * scale) + offset, 2)

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        return self._register_config.get("unit")

    @property
    def device_class(self) -> Optional[SensorDeviceClass]:
        """Return the device class."""
        return self._register_config.get("device_class")

    @property
    def state_class(self) -> Optional[SensorStateClass]:
        """Return the state class."""
        return self._register_config.get("state_class")

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        if self._register_config.get("writable", False):
            return "mdi:cog"
        elif self._register_config.get("device_class") == SensorDeviceClass.TEMPERATURE:
            return "mdi:thermometer-lines"
        else:
            return "mdi:heat-pump-outline"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "register_id": self._register_id,
            "register_type": "holding",
            "writable": self._register_config.get("writable", False),
            "description": self._register_config.get("description", ""),
            "raw_value": self.coordinator.data.get("holding_registers", {}).get(self._register_id) if self.coordinator.data else None,
            "scale_factor": self._register_config.get("scale", 1),
            "offset": self._register_config.get("offset", 0),
        }

class GrantAerona3PowerSensor(GrantAerona3BaseSensor):
    """Grant Aerona3 calculated power sensor with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the power sensor with ashp_ prefix."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Current Power"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_current_power"
        self.entity_id = "sensor.ashp_current_power"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_icon = "mdi:flash"

    @property
    def native_value(self) -> Optional[float]:
        """Calculate power consumption from available registers."""
        if not self.coordinator.data:
            return None
        
        # Get power from register 3: Current consumption value (100W scale)
        input_regs = self.coordinator.data.get("input_registers", {})
        
        power = input_regs.get(3)  # Register 3: Current consumption value
        if power is not None and power >= 0:
            return round(power * 100, 1)  # Convert from 100W scale to watts
        
        return 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        input_regs = self.coordinator.data.get("input_registers", {})
        return {
            "register_source": "Register 3 - Current consumption value",
            "scale_factor": "100W",
            "compressor_frequency": input_regs.get(1, 0),
            "raw_power_value": input_regs.get(3, 0),
        }

class GrantAerona3DeltaTSensor(GrantAerona3BaseSensor):
    """Grant Aerona3 Delta T sensor with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Delta T"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_delta_t"
        self.entity_id = "sensor.ashp_delta_t"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer-lines"

    @property
    def native_value(self) -> Optional[float]:
        """Calculate Delta T (flow temp - return temp)."""
        if not self.coordinator.data:
            return None
    
        input_regs = self.coordinator.data.get("input_registers", {})
        flow_temp = input_regs.get(9)  # Register 9: Flow temperature
        return_temp = input_regs.get(0)  # Register 0: Return temperature
    
        if flow_temp is not None and return_temp is not None:
            flow_temp_c = flow_temp 
            return_temp_c = return_temp 
            return round(flow_temp_c - return_temp_c, 2)
        return None
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        input_regs = self.coordinator.data.get("input_registers", {}) if self.coordinator.data else {}
        return {
            "flow_temperature": input_regs.get(9, 0) if input_regs.get(9) else None,
            "return_temperature": input_regs.get(0, 0) if input_regs.get(0) else None,
            "raw_values": {
                "flow_reg": input_regs.get(9),
                "return_reg": input_regs.get(0),
            }
        }

class GrantAerona3COPSensor(GrantAerona3BaseSensor):
    """Grant Aerona3 Coefficient of Performance sensor with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Coefficient of Performance"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_coefficient_of_performance"
        self.entity_id = "sensor.ashp_coefficient_of_performance"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = ""
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> Optional[float]:
        """Calculate COP from available data."""
        if not self.coordinator.data:
            return None
    
        input_regs = self.coordinator.data.get("input_registers", {})
        flow_temp = input_regs.get(9)  # Register 9: Flow temperature
        return_temp = input_regs.get(0)  # Register 0: Return temperature
        power_raw = input_regs.get(3)  # Register 3: Power consumption
    
        flow_rate = getattr(self.coordinator, 'flow_rate_lpm', 34.0)
    
        if (
            flow_temp is not None
            and return_temp is not None
            and power_raw is not None
            and flow_rate is not None
            and power_raw > 0
        ):
            # Apply correct scaling factors
            flow_temp_c = flow_temp  # Temperature scaling
            return_temp_c = return_temp  # Temperature scaling
            power_watts = power_raw * 100  # Power scaling (100W per unit)
            
            delta_t = flow_temp_c - return_temp_c
            
            if delta_t > 0:  # Only calculate if we have positive delta T
                # Calculate thermal output in kW
                # Formula: thermal_output = flow_rate(L/min) * specific_heat(4.186 kJ/kg°C) * delta_T(°C) / 60(s) / 1000(kW conversion)
                thermal_output_kw = (flow_rate * 4.186 * delta_t) / 60
                electrical_input_kw = power_watts / 1000
                
                if electrical_input_kw > 0:
                    cop = thermal_output_kw / electrical_input_kw
                    return round(cop, 2)
        return None
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        input_regs = self.coordinator.data.get("input_registers", {}) if self.coordinator.data else {}
        flow_rate = getattr(self.coordinator, 'flow_rate_lpm', 34.0)
        return {
            "calculation_method": "full_physics",
            "flow_temperature": input_regs.get(9, 0)  if input_regs.get(9) else None,
            "return_temperature": input_regs.get(0, 0) if input_regs.get(0) else None,
            "power": input_regs.get(3, 0) * 100,
            "flow_rate": flow_rate,
            "raw_values": {
                "flow_reg": input_regs.get(9),
                "return_reg": input_regs.get(0), 
                "power_reg": input_regs.get(3)
            }
        }

class GrantAerona3EfficiencySensor(GrantAerona3BaseSensor):
    """Grant Aerona3 efficiency sensor with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the efficiency sensor with ashp_ prefix."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP System Efficiency"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_system_efficiency"
        self.entity_id = "sensor.ashp_system_efficiency"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:percent"

    @property
    def native_value(self) -> Optional[float]:
        """Calculate system efficiency percentage."""
        if not self.coordinator.data:
            return None
        
        # Get COP and convert to efficiency percentage
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Simple efficiency based on compressor frequency
        frequency = input_regs.get(1, 0)
        if frequency > 0:
            # Basic efficiency calculation - adjust as needed
            efficiency = min((frequency / 100) * 85, 95)  # Scale to percentage
            return round(efficiency, 1)
        
        return None

class GrantAerona3WeatherCompSensor(GrantAerona3BaseSensor):
    """Grant Aerona3 weather compensation sensor with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the weather compensation sensor with ashp_ prefix."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Weather Compensation"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_weather_compensation"
        self.entity_id = "sensor.ashp_weather_compensation"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:weather-partly-cloudy"

    @property
    def native_value(self) -> Optional[float]:
        """Return weather compensation target temperature."""
        if not self.coordinator.data:
            return None
        
        # Get from holding register or calculate
        holding_regs = self.coordinator.data.get("holding_registers", {})
        
        # Try to get weather compensation setting (adjust register as needed)
        comp_temp = holding_regs.get(50)  # Adjust register number
        if comp_temp is not None:
            return round(comp_temp * 0.1, 1)  # Adjust scale factor
        
        return None


