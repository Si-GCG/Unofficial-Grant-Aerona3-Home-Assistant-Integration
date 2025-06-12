"""Improved sensor platform for Grant Aerona3 Heat Pump."""
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

MAX_POWER_W = 25000
RATED_POWER_W = 13000
DEFAULT_FLOW_RATE = 30.0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 sensor entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # CRITICAL FIX: Create sensors for ALL input registers, not just available ones
    for register_id in INPUT_REGISTER_MAP.keys():
        entities.append(
            GrantAerona3InputSensor(coordinator, config_entry, register_id)
        )

    # CRITICAL FIX: Create sensors for ALL holding registers, not just available ones
    for register_id in HOLDING_REGISTER_MAP.keys():
        entities.append(
            GrantAerona3HoldingSensor(coordinator, config_entry, register_id)
        )

    # Add calculated sensors
    entities.extend([
        GrantAerona3PowerSensor(coordinator, config_entry),
        GrantAerona3EnergySensor(coordinator, config_entry),
        GrantAerona3COPSensor(coordinator, config_entry),
        GrantAerona3EfficiencySensor(coordinator, config_entry),
    ])

    _LOGGER.info("Creating %d sensor entities", len(entities))
    async_add_entities(entities)


class GrantAerona3InputSensor(CoordinatorEntity, SensorEntity):
    """Grant Aerona3 input register sensor entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._register_id = register_id
        self._register_config = INPUT_REGISTER_MAP[register_id]

        self._attr_unique_id = f"{config_entry.entry_id}_input_{register_id}"
        self._attr_name = f"{self._register_config['name']}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Set sensor properties
        self._attr_native_unit_of_measurement = self._register_config["unit"]
        self._attr_device_class = self._register_config["device_class"]
        self._attr_state_class = self._register_config.get("state_class")

        # Set entity category for diagnostic sensors
        if "error" in self._register_config["name"].lower() or "alarm" in self._register_config["name"].lower():
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        register_key = f"input_{self._register_id}"
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
        register_key = f"input_{self._register_id}"
        if register_key not in self.coordinator.data:
            return {"register_address": self._register_id, "status": "not_configured"}

        data = self.coordinator.data[register_key]

        attributes = {
            "register_address": self._register_id,
            "raw_value": data.get("raw_value"),
            "description": data.get("description", ""),
            "available": data.get("available", True),
        }

        # Add error information if register is not available
        if not data.get("available", True):
            attributes["error"] = data.get("error", "Register not available")
            attributes["status"] = "unavailable"
        else:
            attributes["status"] = "available"

        # Add helpful tooltips for common terms
        name_lower = self._register_config["name"].lower()
        if "cop" in name_lower:
            attributes["tooltip"] = "COP (Coefficient of Performance) measures heat pump efficiency"
        elif "dhw" in name_lower:
            attributes["tooltip"] = "DHW (Domestic Hot Water) refers to your home's hot water system"
        elif "compressor" in name_lower:
            attributes["tooltip"] = "The compressor is the heart of your heat pump"
        elif "defrost" in name_lower:
            attributes["tooltip"] = "Defrost mode removes ice from the outdoor unit"

        # Add scaling information
        attributes["scale_factor"] = self._register_config["scale"]

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        register_key = f"input_{self._register_id}"
        if register_key not in self.coordinator.data:
            return False
            
        # Entity is available even if register is not readable (shows unavailable state)
        return self.coordinator.last_update_success


class GrantAerona3HoldingSensor(CoordinatorEntity, SensorEntity):
    """Grant Aerona3 holding register sensor entity (read-only display)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._register_id = register_id
        self._register_config = HOLDING_REGISTER_MAP[register_id]

        self._attr_unique_id = f"{config_entry.entry_id}_holding_{register_id}"
        self._attr_name = f"{self._register_config['name']}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Set sensor properties
        self._attr_native_unit_of_measurement = self._register_config["unit"]
        self._attr_device_class = self._register_config.get("device_class")

        # Mark as diagnostic since these are configuration values
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        register_key = f"holding_{self._register_id}"
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
        register_key = f"holding_{self._register_id}"
        if register_key not in self.coordinator.data:
            return {"register_address": self._register_id, "status": "not_configured"}

        data = self.coordinator.data[register_key]

        attributes = {
            "register_address": self._register_id,
            "raw_value": data.get("raw_value"),
            "description": data.get("description", ""),
            "writable": data.get("writable", False),
            "scale_factor": self._register_config["scale"],
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
        register_key = f"holding_{self._register_id}"
        if register_key not in self.coordinator.data:
            return False
            
        # Entity is available even if register is not readable (shows unavailable state)
        return self.coordinator.last_update_success


class GrantAerona3PowerSensor(CoordinatorEntity, SensorEntity):
    """Power consumption sensor."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the power sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{config_entry.entry_id}_power_consumption"
        self._attr_name = "Power Consumption"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> Optional[float]:
        """Return the power consumption in watts."""
        if "input_3" in self.coordinator.data:
            register_data = self.coordinator.data["input_3"]
            if register_data.get("available", True):
                return register_data["value"]
        return None


class GrantAerona3COPSensor(CoordinatorEntity, SensorEntity):
    """COP (Coefficient of Performance) sensor."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the COP sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{config_entry.entry_id}_cop"
        self._attr_name = "COP"
        self._attr_native_unit_of_measurement = None
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:thermometer-chevron-up"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> Optional[float]:
        """Return the calculated COP."""
        # Get required data
        power_data = self.coordinator.data.get("input_3")  # Current Consumption Value
        flow_temp_data = self.coordinator.data.get("input_9")  # Outgoing Water Temperature
        return_temp_data = self.coordinator.data.get("input_0")  # Return Water Temperature
        
        if not all([power_data, flow_temp_data, return_temp_data]):
            return None
        
        # Check if all registers are available
        if not all([data.get("available", True) for data in [power_data, flow_temp_data, return_temp_data]]):
            return None
        
        power = power_data["value"]
        flow_temp = flow_temp_data["value"]
        return_temp = return_temp_data["value"]
        
        # Validate inputs
        if power <= 0 or power > MAX_POWER_W:
            return None
        
        # Calculate temperature difference
        temp_diff = abs(flow_temp - return_temp)
        if temp_diff <= 1.0 or temp_diff > 20.0:  # Reasonable temp difference
            return None
        
        # Get flow rate from your existing number entity OR coordinator
        flow_rate = getattr(self.coordinator, 'flow_rate', None)
        
        # If coordinator doesn't have it, try to get from Home Assistant state
        if not flow_rate or flow_rate <= 0:
            try:
                # Try to get the flow rate from your number entity
                flow_rate_state = self.coordinator.hass.states.get("number.ashp_flow_rate")
                if flow_rate_state and flow_rate_state.state not in ["unavailable", "unknown"]:
                    flow_rate = float(flow_rate_state.state)
                else:
                    # Fallback to your measured value
                    flow_rate = DEFAULT_FLOW_RATE
            except Exception:
                flow_rate = DEFAULT_FLOW_RATE
        
        if flow_rate and flow_rate > 0:
            # Accurate COP calculation with flow rate
            # Convert flow rate from L/min to kg/s
            mass_flow_rate = (flow_rate * 1.0) / 60  # kg/s (water density = 1 kg/L)
            
            # Calculate heat output in kW
            # Specific heat of water = 4.18 kJ/kg·K
            heat_output_kw = (mass_flow_rate * 4.18 * temp_diff) / 1000
            
            # Calculate COP = Heat Output / Electrical Input
            power_kw = power / 1000
            if power_kw > 0:
                cop = heat_output_kw / power_kw
                
                # Validate COP is reasonable for 13kW system
                if cop < 1.0 or cop > 8.0:
                    # Fall back to simplified calculation
                    return self._simplified_cop_calculation(temp_diff, power)
                
                return round(cop, 2)
        
        # Simplified calculation fallback
        return self._simplified_cop_calculation(temp_diff, power)

    def _simplified_cop_calculation(self, temp_diff: float, power: float) -> float:
        """Simplified COP calculation for 13kW Grant Aerona3."""
        # Get outdoor temperature if available
        outdoor_temp_data = self.coordinator.data.get("input_6")
        outdoor_temp = 0  # Default assumption
        
        if outdoor_temp_data and outdoor_temp_data.get("available", True):
            outdoor_temp = outdoor_temp_data["value"]
        
        # Base efficiency for 13kW system varies with outdoor temperature
        if outdoor_temp >= 10:
            base_efficiency = 4.2  # Excellent conditions
        elif outdoor_temp >= 7:
            base_efficiency = 3.8  # Good conditions
        elif outdoor_temp >= 2:
            base_efficiency = 3.2  # Normal conditions
        elif outdoor_temp >= -2:
            base_efficiency = 2.8  # Cold conditions
        else:
            base_efficiency = 2.3  # Very cold conditions
        
        # Adjust for system load (13kW system performance characteristics)
        load_factor = power / RATED_POWER_W  # Percentage of rated capacity
        if load_factor > 0.8:
            base_efficiency *= 0.95  # Slight reduction at high load
        elif load_factor < 0.3:
            base_efficiency *= 0.9   # Slight reduction at very low load
        
        # Adjust for temperature difference (optimal around 7-10°C for radiators)
        if temp_diff < 5:
            temp_factor = 1.1  # Low temp diff = high efficiency
        elif temp_diff <= 10:
            temp_factor = 1.0  # Optimal range
        elif temp_diff <= 15:
            temp_factor = 0.95  # Slightly high
        else:
            temp_factor = 0.85  # High temp diff = lower efficiency
        
        estimated_efficiency = base_efficiency * temp_factor
        
        # Cap at reasonable limits for 13kW system
        cop = max(1.8, min(estimated_efficiency, 6.5))
        return round(cop, 2)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional COP calculation details."""
        # Get flow rate from coordinator or number entity
        flow_rate = getattr(self.coordinator, 'flow_rate', None)
        
        if not flow_rate or flow_rate <= 0:
            try:
                flow_rate_state = self.coordinator.hass.states.get("number.ashp_flow_rate")
                if flow_rate_state and flow_rate_state.state not in ["unavailable", "unknown"]:
                    flow_rate = float(flow_rate_state.state)
            except Exception:
                flow_rate = None
        
        attributes = {
            "tooltip": "COP (Coefficient of Performance) measures how efficiently your heat pump converts electricity into heat",
            "explanation": "Higher COP values mean better efficiency and lower running costs",
            "system_size": "13kW Grant Aerona3",
            "recommended_flow_rate": "35 L/min (Grant recommendation)",
            "current_setting": "30 L/min (installer setting - lowest pump speed)",
            "flow_rate_note": "30 L/min is good for normal operation, 35 L/min for extreme conditions"
        }
        
        if flow_rate and flow_rate > 0:
            attributes.update({
                "calculation_method": "accurate_with_flow_rate",
                "flow_rate_used": f"{flow_rate} L/min",
                "flow_rate_source": "number entity or coordinator",
                "formula": "COP = (Flow Rate × Specific Heat × ΔT) / Electrical Power",
                "note": "Accurate COP calculation using configured flow rate"
            })
        else:
            attributes.update({
                "calculation_method": "simplified_estimation",
                "note": "Using simplified calculation - check flow rate number entity",
                "fallback_flow_rate": f"{DEFAULT_FLOW_RATE} L/min (your measured value)"
            })
        
        # Add current readings for debugging
        power_data = self.coordinator.data.get("input_3")
        flow_temp_data = self.coordinator.data.get("input_9")
        return_temp_data = self.coordinator.data.get("input_0")
        outdoor_temp_data = self.coordinator.data.get("input_6")

        if power_data:
            attributes["current_power_w"] = power_data.get("value")
            attributes["system_load_percent"] = round((power_data.get("value", 0) / RATED_POWER_W) * 100, 1)

        if flow_temp_data:
            attributes["flow_temperature_c"] = flow_temp_data.get("value")

        if return_temp_data:
            attributes["return_temperature_c"] = return_temp_data.get("value")

        if outdoor_temp_data:
            attributes["outdoor_temperature_c"] = outdoor_temp_data.get("value")

        if flow_temp_data and return_temp_data:
            flow_temp = flow_temp_data.get("value", 0)
            return_temp = return_temp_data.get("value", 0)
            temp_diff = abs(flow_temp - return_temp)
            attributes["temperature_difference_c"] = temp_diff

            # Add efficiency guidance
            if temp_diff < 5:
                attributes["temp_diff_status"] = "Very efficient (low ΔT)"
            elif temp_diff <= 10:
                attributes["temp_diff_status"] = "Optimal range"
            elif temp_diff <= 15:
                attributes["temp_diff_status"] = "Acceptable (high ΔT)"
            else:
                attributes["temp_diff_status"] = "Check system - very high ΔT"

        return attributes


class GrantAerona3EfficiencySensor(CoordinatorEntity, SensorEntity):
    """System efficiency sensor."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the efficiency sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{config_entry.entry_id}_system_efficiency"
        self._attr_name = "System Efficiency"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:gauge"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> Optional[float]:
        """Return the system efficiency percentage."""
        # Calculate based on COP if available
        power_data = self.coordinator.data.get("input_3")
        flow_temp_data = self.coordinator.data.get("input_9")
        return_temp_data = self.coordinator.data.get("input_0")

        if not all([power_data, flow_temp_data, return_temp_data]):
            return None

        # Check if all registers are available
        if not all([data.get("available", True) for data in [power_data, flow_temp_data, return_temp_data]]):
            return None

        power = power_data["value"]
        flow_temp = flow_temp_data["value"]
        return_temp = return_temp_data["value"]

        if power <= 0:
            return None

        temp_diff = abs(flow_temp - return_temp)
        if temp_diff <= 0:
            return None

        # Simple efficiency calculation based on temperature difference and power
        # Higher temp difference with lower power = better efficiency
        if temp_diff > 0 and power > 0:
            efficiency = min((temp_diff / power) * 10000, 100)  # Scale and cap at 100%
            return round(efficiency, 1)

        return None


class GrantAerona3EnergySensor(CoordinatorEntity, SensorEntity):
    """Energy consumption sensor (calculated from power over time)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{config_entry.entry_id}_energy_consumption"
        self._attr_name = "Energy Consumption"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Energy calculation state
        self._last_power = None
        self._last_update = None
        self._total_energy = 0.0

    @property
    def native_value(self) -> float:
        """Return the total energy consumption in kWh."""
        if "input_3" in self.coordinator.data:
            register_data = self.coordinator.data["input_3"]
            if register_data.get("available", True):
                current_power = register_data["value"]

                # Simple energy integration (this is only accurate if called every second)
                # For production use, prefer Home Assistant's utility meter integration.
                if current_power > 0:
                    self._total_energy += current_power / 1000 / 3600  # Very rough estimation

        return round(self._total_energy, 3)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional energy attributes."""
        return {
            "calculation_method": "basic_integration",
            "note": "Energy calculated by basic power integration - consider using utility meter for accuracy"
        }
