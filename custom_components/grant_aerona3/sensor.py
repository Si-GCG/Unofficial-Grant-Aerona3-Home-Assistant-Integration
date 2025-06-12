"""Improved sensor platform for Grant Aerona3 Heat Pump with ashp_ prefixes."""
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

from .const import DOMAIN, MANUFACTURER, MODEL, INPUT_REGISTER_MAP, HOLDING_REGISTER_MAP
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 sensor entities with ashp_ prefixes."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Create sensors for ALL input registers with ashp_ prefix
    for register_id in INPUT_REGISTER_MAP.keys():
        entities.append(
            GrantAerona3InputSensor(coordinator, config_entry, register_id)
        )

    # Create sensors for ALL holding registers with ashp_ prefix
    for register_id in HOLDING_REGISTER_MAP.keys():
        entities.append(
            GrantAerona3HoldingSensor(coordinator, config_entry, register_id)
        )

    # Add calculated sensors with ashp_ prefix
    entities.extend([
        GrantAerona3PowerSensor(coordinator, config_entry),
        GrantAerona3EnergySensor(coordinator, config_entry),
        GrantAerona3COPSensor(coordinator, config_entry),
        GrantAerona3EfficiencySensor(coordinator, config_entry),
        GrantAerona3WeatherCompSensor(coordinator, config_entry),
        GrantAerona3DailyCostSensor(coordinator, config_entry),
        GrantAerona3MonthlyCostSensor(coordinator, config_entry),
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
        if raw_value is None:
            return None
        
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
        if raw_value is None:
            return None
        
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
    def entity_category(self) -> Optional[EntityCategory]:
        """Return the entity category for configuration parameters."""
        if self._register_config.get("writable", False):
            return EntityCategory.CONFIG
        return None

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


class GrantAerona3EnergySensor(GrantAerona3BaseSensor):
    """Grant Aerona3 energy consumption sensor with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the energy sensor with ashp_ prefix."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Daily Energy"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_daily_energy"
        self.entity_id = "sensor.ashp_daily_energy"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> Optional[float]:
        """Return daily energy consumption."""
        if not self.coordinator.data:
            return None
        
        # Look for energy register or calculate from power
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Try to get direct energy reading (adjust register as needed)
        energy = input_regs.get(10)  # Adjust this register number
        if energy is not None:
            return round(energy / 1000, 2) if energy > 0 else 0
        
        # Note: For actual energy tracking, users should set up utility_meter
        # This is just a placeholder
        return 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "calculation_method": "direct_register",
            "note": "Use utility_meter integration with power sensor for accurate daily tracking"
        }


class GrantAerona3COPSensor(GrantAerona3BaseSensor):
    """Grant Aerona3 Coefficient of Performance sensor with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the COP sensor with ashp_ prefix."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Coefficient of Performance"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_coefficient_of_performance"
        self.entity_id = "sensor.ashp_coefficient_of_performance"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = None
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> Optional[float]:
        """Calculate COP from available data."""
        if not self.coordinator.data:
            return None
        
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Get temperatures for COP calculation
        flow_temp = input_regs.get(1)
        flow_temp = flow_temp * 0.1 if flow_temp is not None else None
        return_temp = input_regs.get(0, 0) * 0.1 if input_regs.get(0) else None  # Adjust register/scale
        value = input_regs.get(2)
        value = value * 0.1 if value is not None else None
        
        if flow_temp and return_temp and value:
            # Simplified COP calculation based on temperatures
            temp_lift = flow_temp - value
            if temp_lift > 0:
                # Basic COP estimation - adjust formula as needed
                cop = 6.8 - (temp_lift * 0.1)
                return round(max(cop, 1.0), 2)
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        input_regs = self.coordinator.data.get("input_registers", {}) if self.coordinator.data else {}
        return {
            "calculation_method": "temperature_based_estimation",
            "flow_temperature": input_regs.get(1, 0) * 0.1 if input_regs.get(1) else None,
            "return_temperature": input_regs.get(0, 0) * 0.1 if input_regs.get(0) else None,
            "outdoor_temperature": input_regs.get(2, 0) * 0.1 if input_regs.get(2) else None,
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


class GrantAerona3DailyCostSensor(GrantAerona3BaseSensor):
    """Grant Aerona3 daily cost sensor with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the daily cost sensor with ashp_ prefix."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Daily Cost Estimate"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_daily_cost_estimate"
        self.entity_id = "sensor.ashp_daily_cost_estimate"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "GBP"
        self._attr_icon = "mdi:currency-gbp"

    @property
    def native_value(self) -> Optional[float]:
        """Calculate estimated daily cost."""
        if not self.coordinator.data:
            return None
        
        # Basic cost calculation - this would be enhanced with actual energy tracking
        input_regs = self.coordinator.data.get("input_registers", {})
        
        # Estimate from current power consumption
        power = input_regs.get(5, 0)  # Adjust register
        if power > 0:
            # Estimate daily consumption and cost
            daily_kwh = (power / 1000) * 24  # Very rough estimate
            uk_rate = 0.30  # £0.30 per kWh typical rate
            return round(daily_kwh * uk_rate, 2)
        
        return 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "electricity_rate": "0.30 GBP/kWh",
            "note": "Estimated cost - set up utility_meter for accurate tracking"
        }


class GrantAerona3MonthlyCostSensor(GrantAerona3BaseSensor):
    """Grant Aerona3 monthly cost sensor with ashp_ prefix."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the monthly cost sensor with ashp_ prefix."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Monthly Cost Projection"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_monthly_cost_projection"
        self.entity_id = "sensor.ashp_monthly_cost_projection"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "GBP"
        self._attr_icon = "mdi:calendar-month"

    @property
    def native_value(self) -> Optional[float]:
        """Calculate projected monthly cost."""
        if not self.coordinator.data:
            return None
        
        # Basic monthly projection
        input_regs = self.coordinator.data.get("input_registers", {})
        
        power = input_regs.get(5, 0)  # Adjust register
        if power > 0:
            # Estimate monthly consumption and cost
            monthly_kwh = (power / 1000) * 24 * 30  # Very rough estimate
            uk_rate = 0.30  # £0.30 per kWh typical rate
            return round(monthly_kwh * uk_rate, 2)
        
        return 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "electricity_rate": "0.30 GBP/kWh",
            "projection_method": "current_power_x30_days",
            "note": "Projection based on current consumption - actual costs may vary"
        }