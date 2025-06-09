"""Improved number platform for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime, PERCENTAGE # Added UnitOfTime, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN, MANUFACTURER, MODEL, HOLDING_REGISTER_MAP,
    CONF_SYSTEM_ELEMENTS # Import new config constant
)
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 number entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    selected_elements = config_entry.options.get(CONF_SYSTEM_ELEMENTS, [])

    entities = []

    # Create number entities for ALL writable holding registers
    # The availability of these entities will be determined by the coordinator.
    for register_id, config in HOLDING_REGISTER_MAP.items():
        if config.get("writable", False):
            # Check if this register is relevant based on selected elements.
            # This logic should mirror _get_relevant_registers in coordinator.py for consistency.
            name_lower = config["name"].lower()
            is_relevant_to_elements = True

            # Example: Only create DHW related number entities if hot_water_cylinder is selected
            if "dhw" in name_lower and "hot_water_cylinder" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Only create buffer tank related number entities if buffer_tank is selected
            elif "buffer tank" in name_lower and "buffer_tank" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Only create mixing valve related number entities if 3way_mixing_valve_heating is selected
            elif "mixing valve" in name_lower and "3way_mixing_valve_heating" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Only create backup heater related number entities if backup_electric_heater is selected
            elif "backup heater" in name_lower and "backup_electric_heater" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Only create EHS related number entities if external_heat_source_ehs is selected
            elif "ehs" in name_lower and "external_heat_source_ehs" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Only create humidity related number entities if humidity_sensor_present is selected
            elif "humidity" in name_lower and "humidity_sensor_present" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Zone 2 specific parameters
            elif "zone 2" in name_lower and "multiple_heating_zones" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Dual set point parameters should be shown if either relevant option is chosen
            elif "dual set point" in name_lower and \
                 not ("multiple_heating_zones" in selected_elements or "dual_set_point_control_workaround" in selected_elements):
                is_relevant_to_elements = False

            # Add more conditions as needed for other system elements

            if is_relevant_to_elements:
                entities.append(
                    GrantAerona3HoldingNumber(coordinator, config_entry, register_id)
                )
            else:
                _LOGGER.debug("Skipping holding register %d (%s) for number entity creation (not relevant to configured system).", register_id, config.get("name"))


    # Add flow rate configuration entity (always available as it's a manual input for calculations)
    entities.append(
        GrantAerona3FlowRateNumber(coordinator, config_entry)
    )

    _LOGGER.info("Creating %d number entities", len(entities))
    async_add_entities(entities)


class GrantAerona3HoldingNumber(CoordinatorEntity, NumberEntity):
    """Grant Aerona3 writable holding register number entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._register_id = register_id
        self._register_config = HOLDING_REGISTER_MAP[register_id]
        self._config_entry = config_entry

        self._attr_unique_id = f"{config_entry.entry_id}_holding_number_{register_id}"
        self._attr_name = f"Grant Aerona3 {self._register_config['name']}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Set number properties
        self._attr_native_unit_of_measurement = self._register_config["unit"]
        self._attr_device_class = self._register_config.get("device_class")
        self._attr_mode = NumberMode.SLIDER # Or NumberMode.BOX if precise input is preferred

        # Determine min/max values and step based on register type or manual.
        # This requires careful review of each register in the manual.
        # Placeholder values for now, should be specific to each register.
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 0.1 # Default step, override for specific registers

        # Example: For temperature setpoints (like registers 2, 7, 28, 29, etc.)
        if self._attr_device_class == UnitOfTemperature.CELSIUS:
            self._attr_native_min_value = 5.0
            self._attr_native_max_value = 60.0
            self._attr_native_step = 0.5
        elif self._attr_device_class == UnitOfTime.MINUTES or self._attr_device_class == UnitOfTime.SECONDS:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 3600 # Max seconds, adjust per register
            self._attr_native_step = 1
        elif self._attr_native_unit_of_measurement == PERCENTAGE:
             self._attr_native_min_value = 0
             self._attr_native_max_value = 100
             self._attr_native_step = 1

        # Set entity category for configuration settings
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value of the holding register."""
        register_key = f"holding_{self._register_id}"
        if register_key not in self.coordinator.data:
            return None

        register_data = self.coordinator.data[register_key]
        if not register_data.get("available", True):
            return None
        return register_data["value"]

    async def async_set_native_value(self, value: float) -> None:
        """Set the native value of the number entity (write to Modbus holding register)."""
        register_config = HOLDING_REGISTER_MAP.get(self._register_id)
        if not register_config or not register_config.get("writable", False):
            _LOGGER.error("Attempted to write to non-writable or non-existent register %d", self._register_id)
            return

        # Apply scaling from const.py to convert user value to raw Modbus value
        scale = register_config.get("scale", 1)
        raw_value = int(value / scale) # Convert float to int for Modbus, after scaling

        success = await self.coordinator.async_write_holding_register(self._register_id, raw_value)
        if success:
            _LOGGER.debug("Successfully set holding register %d (%s) to %f (raw: %d)", self._register_id, self._attr_name, value, raw_value)
            await self.coordinator.async_request_refresh() # Request immediate refresh to update state
        else:
            _LOGGER.error("Failed to set value for number entity %s at address %d", self._attr_name, self._register_id)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        register_key = f"holding_{self._register_id}"
        data = self.coordinator.data.get(register_key, {})

        attributes = {
            "register_address": self._register_id,
            "raw_value": data.get("raw_value"),
            "description": data.get("description", ""),
            "writable": data.get("writable", False),
            "scale_factor": self._register_config.get("scale"),
            "available": data.get("available", False),
        }
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
        # Entity is available if coordinator is successfully updating AND the specific register was available/relevant
        return self.coordinator.last_update_success and register_data and register_data.get("available", False)


class GrantAerona3FlowRateNumber(CoordinatorEntity, NumberEntity):
    """Manually configured flow rate for COP calculations."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the flow rate number entity."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{config_entry.entry_id}_flow_rate_manual"
        self._attr_name = "Grant Aerona3 Flow Rate (Manual)"
        self._attr_native_unit_of_measurement = "L/min" # Liters per minute
        self._attr_native_min_value = 10.0
        self._attr_native_max_value = 50.0
        self._attr_native_step = 0.5
        self._attr_icon = "mdi:water-pump"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_mode = NumberMode.SLIDER

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Initialize with the value stored in the coordinator (which might be default or previously set)
        self._flow_rate = coordinator.flow_rate

    @property
    def native_value(self) -> float:
        """Return the current flow rate."""
        # This value comes directly from the coordinator's stored state
        return self.coordinator.flow_rate

    async def async_set_native_value(self, value: float) -> None:
        """Set the flow rate value."""
        # Update the flow rate in the coordinator, which will then be used by COP sensor
        self.coordinator.flow_rate = value
        _LOGGER.info("Flow rate set to %.1f L/min via manual number entity.", value)
        self.async_write_ha_state() # Update Home Assistant state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        return {
            "description": "Manually entered flow rate for COP calculations (Liters/minute).",
            "how_to_measure": "Use a flow meter or calculate from pump curves/system design.",
            "typical_range": "15-25 L/min for residential systems.",
            "note": "This value does NOT control the pump. It is used only for heat output/COP calculations."
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # This entity is always available as its value is local to the integration.
        return True
