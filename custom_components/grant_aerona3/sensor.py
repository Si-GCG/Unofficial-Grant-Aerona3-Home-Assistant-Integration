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

        if power <= 0:
            return None

        # Calculate temperature difference
        temp_diff = abs(flow_temp - return_temp)
        if temp_diff <= 0:
            return None

        # Check if flow rate is configured
        flow_rate = getattr(self.coordinator, 'flow_rate', None)

        if flow_rate and flow_rate > 0:
            # Accurate COP calculation with flow rate
            # Q = flow_rate (L/min) × density (kg/L) × specific_heat (kJ/kg·K) × temp_diff (K)
            # Convert flow rate from L/min to kg/s
            mass_flow_rate = (flow_rate * 1.0) / 60  # kg/s (assuming water density = 1 kg/L)

            # Calculate heat output in kW
            # Specific heat of water = 4.18 kJ/kg·K
            heat_output_kw = (mass_flow_rate * 4.18 * temp_diff) / 1000

            # Calculate COP = Heat Output / Electrical Input
            power_kw = power / 1000
            cop = heat_output_kw / power_kw

            return round(cop, 2)
        else:
            # Simplified COP calculation without flow rate
            estimated_efficiency = 2.5 + (temp_diff / 15)  # Base efficiency + temp factor
            cop = min(estimated_efficiency, 6.0)  # Cap at 6.0

            return round(cop, 2)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional COP calculation details."""
        flow_rate = getattr(self.coordinator, 'flow_rate', None)

        attributes = {
            "tooltip": "COP (Coefficient of Performance) measures how efficiently your heat pump converts electricity into heat",
            "explanation": "Higher COP values mean better efficiency and lower running costs",
        }

        if flow_rate and flow_rate > 0:
            attributes.update({
                "calculation_method": "accurate_with_flow_rate",
                "flow_rate_used": f"{flow_rate} L/min",
                "formula": "COP = (Flow Rate × Specific Heat × ΔT) / Electrical Power",
                "note": "Accurate COP calculation using configured flow rate"
            })
        else:
            attributes.update({
                "calculation_method": "simplified_estimation",
                "note": "Simplified COP calculation - configure flow rate for accuracy",
                "how_to_improve": "Set the 'Flow Rate' number entity to your measured flow rate"
            })

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

                # Simple energy integration (this would be better with a utility meter)
                # This is a basic implementation - consider using Home Assistant's utility meter instead
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
