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

from .const import (
    DOMAIN, MANUFACTURER, MODEL, INPUT_REGISTER_MAP, HOLDING_REGISTER_MAP,
    # Import all new config constants relevant for sensors
    CONF_SYSTEM_ELEMENTS, CONF_FLOW_TEMP_SENSOR, CONF_RETURN_TEMP_SENSOR,
    CONF_OUTSIDE_TEMP_SENSOR, CONF_CYLINDER_TEMP_SENSOR, CONF_BUFFER_TEMP_SENSOR,
    CONF_MIX_WATER_TEMP_SENSOR, CONF_ROOM_TEMP_SENSOR, CONF_HUMIDITY_SENSOR,
    HEATING_TYPES # For zone heating type display if needed
)
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 sensor entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    selected_elements = config_entry.options.get(CONF_SYSTEM_ELEMENTS, [])
    
    entities = []

    # Create sensors for ALL input registers from Modbus
    for register_id in INPUT_REGISTER_MAP.keys():
        entities.append(
            GrantAerona3InputSensor(coordinator, config_entry, register_id)
        )

    # Create sensors for ALL holding registers from Modbus
    for register_id in HOLDING_REGISTER_MAP.keys():
        entities.append(
            GrantAerona3HoldingSensor(coordinator, config_entry, register_id)
        )

    # Create sensors for linked external Home Assistant sensors
    # These entities will display the state of the *chosen* external sensor
    if config_entry.options.get(CONF_FLOW_TEMP_SENSOR):
        entities.append(GrantAerona3ExternalSensor(coordinator, config_entry, CONF_FLOW_TEMP_SENSOR, "Flow Temperature (External)"))
    if config_entry.options.get(CONF_RETURN_TEMP_SENSOR):
        entities.append(GrantAerona3ExternalSensor(coordinator, config_entry, CONF_RETURN_TEMP_SENSOR, "Return Temperature (External)"))
    if config_entry.options.get(CONF_OUTSIDE_TEMP_SENSOR):
        entities.append(GrantAerona3ExternalSensor(coordinator, config_entry, CONF_OUTSIDE_TEMP_SENSOR, "Outdoor Temperature (External)"))
    if config_entry.options.get(CONF_CYLINDER_TEMP_SENSOR) and "hot_water_cylinder" in selected_elements:
        entities.append(GrantAerona3ExternalSensor(coordinator, config_entry, CONF_CYLINDER_TEMP_SENSOR, "DHW Tank Temperature (External)"))
    if config_entry.options.get(CONF_BUFFER_TEMP_SENSOR) and "buffer_tank" in selected_elements:
        entities.append(GrantAerona3ExternalSensor(coordinator, config_entry, CONF_BUFFER_TEMP_SENSOR, "Buffer Tank Temperature (External)"))
    if config_entry.options.get(CONF_MIX_WATER_TEMP_SENSOR) and "3way_mixing_valve_heating" in selected_elements:
        entities.append(GrantAerona3ExternalSensor(coordinator, config_entry, CONF_MIX_WATER_TEMP_SENSOR, "Mix Water Temperature (External)"))
    if config_entry.options.get(CONF_ROOM_TEMP_SENSOR): # Room temp can be relevant for zone 1 or 2
        entities.append(GrantAerona3ExternalSensor(coordinator, config_entry, CONF_ROOM_TEMP_SENSOR, "Room Temperature (External)"))
    if config_entry.options.get(CONF_HUMIDITY_SENSOR) and "humidity_sensor_present" in selected_elements:
        entities.append(GrantAerona3ExternalSensor(coordinator, config_entry, CONF_HUMIDITY_SENSOR, "Room Humidity (External)"))


    # Add calculated sensors (Power, Energy, COP, Efficiency)
    # These need to intelligently use Modbus or external sensor data based on availability
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
        self._config_entry = config_entry # Store for options access

        self._attr_unique_id = f"{config_entry.entry_id}_input_{register_id}"
        self._attr_name = f"Grant Aerona3 {self._register_config['name']}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
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
        elif "temperature" in self._register_config["name"].lower() and "set" not in self._register_config["name"].lower():
            self._attr_entity_category = EntityCategory.DIAGNOSTIC # Diagnostic for measured temps
        else:
            self._attr_entity_category = EntityCategory.MEASUREMENT # Default for general measurements


    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        register_key = f"input_{self._register_id}"
        if register_key not in self.coordinator.data:
            return None

        register_data = self.coordinator.data[register_key]
        
        # Check if register is available (was successfully read or is relevant)
        if not register_data.get("available", True):
            return None
            
        return register_data["value"]

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        register_key = f"input_{self._register_id}"
        data = self.coordinator.data.get(register_key, {}) # Use .get for safety

        attributes = {
            "register_address": self._register_id,
            "raw_value": data.get("raw_value"),
            "description": data.get("description", ""),
            "available": data.get("available", False), # Default to False if key not in data
        }

        # Add error information if register is not available
        if not data.get("available", True):
            attributes["error"] = data.get("error", "Register not available or not relevant to configured system.")
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
        register_data = self.coordinator.data.get(register_key)
        
        # Entity is available if coordinator is successfully updating AND the specific register was available/relevant
        return self.coordinator.last_update_success and register_data and register_data.get("available", False)


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
        self._config_entry = config_entry # Store for options access

        self._attr_unique_id = f"{config_entry.entry_id}_holding_{register_id}"
        self._attr_name = f"Grant Aerona3 {self._register_config['name']} (Current)"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Set sensor properties
        self._attr_native_unit_of_measurement = self._register_config["unit"]
        self._attr_device_class = self._register_config.get("device_class")

        # Mark as diagnostic since these are configuration values that might not change often
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
        data = self.coordinator.data.get(register_key, {}) # Use .get for safety

        attributes = {
            "register_address": self._register_id,
            "raw_value": data.get("raw_value"),
            "description": data.get("description", ""),
            "writable": data.get("writable", False),
            "scale_factor": self._register_config["scale"],
            "available": data.get("available", False), # Default to False
        }

        # Add error information if register is not available
        if not data.get("available", True):
            attributes["error"] = data.get("error", "Register not available or not relevant to configured system.")
            attributes["status"] = "unavailable"
        else:
            attributes["status"] = "available"

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        register_key = f"holding_{self._register_id}"
        register_data = self.coordinator.data.get(register_key)
        
        return self.coordinator.last_update_success and register_data and register_data.get("available", False)


class GrantAerona3ExternalSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for external Home Assistant sensors linked in config flow."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        config_key: str, # The key from config_flow (e.g., CONF_ROOM_TEMP_SENSOR)
        name_suffix: str, # A user-friendly name for this external sensor
    ) -> None:
        """Initialize the external sensor entity."""
        super().__init__(coordinator)
        self._config_key = config_key
        self._entity_id_linked = config_entry.options.get(config_key) # The actual HA entity ID
        self._name_suffix = name_suffix

        self._attr_unique_id = f"{config_entry.entry_id}_external_{config_key}"
        self._attr_name = f"Grant Aerona3 {self._name_suffix}"

        # Device info - Link this to the main ASHP device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Attempt to set device class and unit based on what's expected for this config_key
        if "temperature" in name_suffix.lower():
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        elif "humidity" in name_suffix.lower():
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_native_unit_of_measurement = PERCENTAGE
        # Add more mappings as needed for other types of external sensors (e.g., pressure)

        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC # Typically diagnostic for linked sensors

    @property
    def native_value(self) -> Any:
        """Return the state of the external sensor."""
        if not self._entity_id_linked:
            return None # No external entity configured

        external_sensor_data = self.coordinator.data.get("external_sensors", {}).get(self._config_key)
        if external_sensor_data and external_sensor_data.get("available"):
            return external_sensor_data["value"]
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        external_sensor_data = self.coordinator.data.get("external_sensors", {}).get(self._config_key, {})

        attributes = {
            "linked_entity_id": self._entity_id_linked,
            "description": f"External sensor linked for {self._name_suffix}",
            "available": external_sensor_data.get("available", False),
        }
        if not external_sensor_data.get("available", True):
            attributes["error"] = external_sensor_data.get("error", "External sensor entity unavailable or not configured.")
            attributes["status"] = "unavailable"
        else:
            attributes["status"] = "available"
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self._entity_id_linked:
            return False # Not configured

        external_sensor_data = self.coordinator.data.get("external_sensors", {}).get(self._config_key)
        # Available if coordinator is running and the specific external sensor data is marked as available
        return self.coordinator.last_update_success and external_sensor_data and external_sensor_data.get("available", False)


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
        self._attr_name = "Grant Aerona3 Power Consumption"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
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
        self._attr_name = "Grant Aerona3 COP"
        self._attr_native_unit_of_measurement = None # COP is dimensionless
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:thermometer-chevron-up"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> Optional[float]:
        """Return the calculated COP."""
        # Prioritize external flow/return temps if configured and available
        flow_temp = None
        return_temp = None

        external_flow_data = self.coordinator.data.get("external_sensors", {}).get(CONF_FLOW_TEMP_SENSOR)
        if external_flow_data and external_flow_data.get("available"):
            flow_temp = external_flow_data["value"]
        elif "input_9" in self.coordinator.data and self.coordinator.data["input_9"].get("available", True):
            flow_temp = self.coordinator.data["input_9"]["value"] # Fallback to Modbus

        external_return_data = self.coordinator.data.get("external_sensors", {}).get(CONF_RETURN_TEMP_SENSOR)
        if external_return_data and external_return_data.get("available"):
            return_temp = external_return_data["value"]
        elif "input_0" in self.coordinator.data and self.coordinator.data["input_0"].get("available", True):
            return_temp = self.coordinator.data["input_0"]["value"] # Fallback to Modbus

        # Get power consumption
        power_data = self.coordinator.data.get("input_3") # Current Consumption Value from Modbus
        
        if not all([power_data, flow_temp is not None, return_temp is not None]):
            return None

        if not power_data.get("available", True): # Check if Modbus power data is available
            return None

        power = power_data["value"]

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
            # Specific heat of water = 4.18 kJ/kg·K (or 4.186 J/g·K)
            heat_output_kw = (mass_flow_rate * 4.18 * temp_diff) / 1000 # Convert kJ to kWh if power is in W, or just kW

            # Calculate COP = Heat Output / Electrical Input
            power_kw = power / 1000 # Convert W to kW
            cop = heat_output_kw / power_kw

            return round(cop, 2)
        else:
            # Simplified COP calculation without flow rate - more robust than previous fixed value
            # This is a generic estimation and might not be accurate for all conditions
            # A common rule of thumb for heat pumps is that COP drops significantly with increasing temp difference.
            # Example: COP ~ (Target Temp + 273.15) / (Target Temp - Source Temp)
            # For a very rough estimation, let's use some simplified curve or lookup
            # This part needs to be validated against real ASHP COP curves for accuracy.
            
            # Simple linear estimation based on temp difference (highly speculative)
            # Larger temp difference usually means lower COP.
            # Let's say, COP of 4 at 5C dT, COP of 2 at 25C dT
            # Slope = (2-4)/(25-5) = -2/20 = -0.1
            # COP = 4 - 0.1 * (temp_diff - 5)
            # This is still a very rough approximation without knowing the ASHP's actual curve.
            
            # A safer approach for simplified estimation if flow rate is unknown:
            # You might just return None if COP cannot be accurately calculated,
            # or provide a very generic estimation, stating its limitations in attributes.
            _LOGGER.warning("Flow rate not configured for COP calculation. COP estimation will be less accurate. "
                            "Please set 'Grant Aerona3 Flow Rate' for accurate COP.")
            return None # Better to return None than a potentially misleading value

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
                "formula": "COP = (Mass Flow Rate × Specific Heat Capacity × ΔT) / Electrical Power",
                "note": "Accurate COP calculation using configured flow rate and external/Modbus temperatures"
            })
        else:
            attributes.update({
                "calculation_method": "simplified_estimation_unavailable", # Changed from 'simplified_estimation'
                "note": "COP cannot be accurately calculated without a configured flow rate.",
                "how_to_improve": "Set the 'Grant Aerona3 Flow Rate' number entity to your measured flow rate for accurate COP."
            })

        # Indicate which temperature sensors are being used for COP calculation
        attributes["flow_temp_source"] = "External" if self.coordinator.data.get("external_sensors", {}).get(CONF_FLOW_TEMP_SENSOR, {}).get("available") else "Modbus (input_9)"
        attributes["return_temp_source"] = "External" if self.coordinator.data.get("external_sensors", {}).get(CONF_RETURN_TEMP_SENSOR, {}).get("available") else "Modbus (input_0)"
        attributes["power_source"] = "Modbus (input_3)" # Assuming power is always from Modbus

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
        self._attr_name = "Grant Aerona3 System Efficiency"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:gauge"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> Optional[float]:
        """Return the system efficiency percentage."""
        # Efficiency is often directly related to COP. A simple conversion is Efficiency = COP / Max_Possible_COP_Carnot
        # Or, just return COP * 100 as a percentage of input power converted to heat.
        # It's less common to have a separate "efficiency" percentage unless it's a specific metric.

        cop_value = self.coordinator.data.get(f"{DOMAIN}_cop", {}).get("value") # Access the calculated COP sensor's value
        if cop_value is not None:
            # A common definition for seasonal efficiency can be EER or SCOP.
            # If you want to show 'efficiency' based on COP, you might say efficiency = COP/5 (as 5 is a good target COP) * 100
            # Or just COP * 100 (which isn't strictly efficiency in the energy conversion sense, but a common display)
            # Let's define efficiency as (Heat Output / Electrical Input) * 100, which is just COP * 100
            return round(cop_value * 100, 1)

        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional efficiency attributes."""
        return {
            "tooltip": "Overall system efficiency derived from COP, representing heat output per unit of electricity input."
        }


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
        self._attr_name = "Grant Aerona3 Energy Consumption"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Energy calculation state - these are better managed by HA's `utility_meter`
        # for proper long-term statistics, but keeping a simple integrator for instant value.
        self._last_power_watt = None
        self._last_update_timestamp = None
        self._total_energy_kwh = 0.0

    @property
    def native_value(self) -> Optional[float]:
        """Return the total energy consumption in kWh."""
        current_power_data = self.coordinator.data.get("input_3")
        if not current_power_data or not current_power_data.get("available", True):
            # If power data is unavailable, can't calculate energy.
            return self._total_energy_kwh # Return last known total, don't increment

        current_power_watt = current_power_data["value"]
        current_timestamp = self.coordinator.last_update_success_time # Use coordinator's last update time

        if self._last_power_watt is not None and self._last_update_timestamp is not None and current_timestamp is not None:
            time_delta_seconds = (current_timestamp - self._last_update_timestamp).total_seconds()
            if time_delta_seconds > 0:
                # Simple trapezoidal integration (average power over time interval)
                average_power_watt = (self._last_power_watt + current_power_watt) / 2
                energy_joules = average_power_watt * time_delta_seconds
                energy_kwh = energy_joules / (3.6 * 10**6) # Convert Joules to kWh
                self._total_energy_kwh += energy_kwh
        
        self._last_power_watt = current_power_watt
        self._last_update_timestamp = current_timestamp

        return round(self._total_energy_kwh, 3)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional energy attributes."""
        return {
            "calculation_method": "trapezoidal_integration",
            "note": "Energy calculated by integrating power over time. For official long-term statistics, consider using Home Assistant's built-in Utility Meter helper which is more robust for energy monitoring."
        }
