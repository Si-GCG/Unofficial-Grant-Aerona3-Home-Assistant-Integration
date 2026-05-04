# number.py

"""Improved number platform for Grant Aerona3 Heat Pump with enhanced debugging."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, MANUFACTURER, MODEL, SW_VERSION, HOLDING_REGISTER_MAP
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 number entities."""
    _LOGGER.info("Setting up Grant Aerona3 number entities")

    # Check if coordinator exists
    if DOMAIN not in hass.data:
        _LOGGER.error("Domain %s not found in hass.data", DOMAIN)
        return

    if config_entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("Config entry %s not found in hass.data[%s]", config_entry.entry_id, DOMAIN)
        return

    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.info("Coordinator found: %s", type(coordinator).__name__)

    entities = []
    # Debug: Check what's in HOLDING_REGISTER_MAP
    _LOGGER.info("Total holding registers defined: %d", len(HOLDING_REGISTER_MAP))
    writable_registers = [reg for reg, config in HOLDING_REGISTER_MAP.items() if config.get("writable", False)]
    _LOGGER.info("Writable registers: %s", writable_registers)

    # Create number entities for ALL writable holding registers
    for register_id, config in HOLDING_REGISTER_MAP.items():
        if config.get("writable", False):
            _LOGGER.info("Creating number entity for register %d: %s", register_id, config["name"])
            try:
                entity = GrantAerona3HoldingNumber(coordinator, config_entry, register_id)
                entities.append(entity)
                _LOGGER.debug("Successfully created entity for register %d", register_id)
            except Exception as e:
                _LOGGER.error("Failed to create entity for register %d: %s", register_id, e)

    # Add flow rate configuration entity
    try:
        _LOGGER.info("Creating flow rate number entity")
        entities.append(GrantAerona3FlowRateNumber(coordinator, config_entry))
        _LOGGER.debug("Successfully created flow rate entity")
    except Exception as e:
        _LOGGER.error("Failed to create flow rate entity: %s", e)

    _LOGGER.info("Created %d number entities total", len(entities))

    if entities:
        async_add_entities(entities, True)  # Force update_before_add
        _LOGGER.info("Successfully added %d number entities", len(entities))
    else:
        _LOGGER.warning("No number entities were created!")

class GrantAerona3HoldingNumber(CoordinatorEntity, NumberEntity):
    """Grant Aerona3 holding register number entity."""

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

        self._attr_unique_id = f"{config_entry.entry_id}_number_holding_{register_id}"
        self._attr_name = self._register_config['name']  # Remove ASHP prefix
        self._attr_has_entity_name = True

        _LOGGER.debug(
            "Initializing number entity: %s (register %d)", 
            self._attr_name, 
            register_id
        )

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": SW_VERSION,
        }

        # Set number properties
        self._attr_native_unit_of_measurement = self._register_config.get("unit")
        self._attr_mode = NumberMode.BOX  # Use box mode for precise control

        # Use min/max/step from the register config, fallback to safe defaults
        self._attr_native_min_value = self._register_config.get("min", 0)
        self._attr_native_max_value = self._register_config.get("max", 100)
        self._attr_native_step = self._register_config.get("step", 1)

        # Set icon based on function
        name_lower = self._register_config["name"].lower()
        if "temp" in name_lower:
            self._attr_icon = "mdi:thermometer"
        elif "dhw" in name_lower:
            self._attr_icon = "mdi:water-thermometer"
        elif "time" in name_lower or "delay" in name_lower:
            self._attr_icon = "mdi:clock"
        elif "hysteresis" in name_lower:
            self._attr_icon = "mdi:thermometer-lines"
        elif "flow" in name_lower:
            self._attr_icon = "mdi:pipe"
        else:
            self._attr_icon = "mdi:tune"

        # Set entity category
        self._attr_entity_category = EntityCategory.CONFIG

        _LOGGER.debug(
            "Number entity configured: min=%s, max=%s, step=%s, unit=%s",
            self._attr_native_min_value,
            self._attr_native_max_value, 
            self._attr_native_step,
            self._attr_native_unit_of_measurement
        )

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value."""
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data available for register %d", self._register_id)
            return None
            
        holding_registers = self.coordinator.data.get("holding_registers", {})
        raw_value = holding_registers.get(self._register_id)
        
        if raw_value is None:
            _LOGGER.debug("No value found for register %d in coordinator data", self._register_id)
            return None
            
        scale = self._register_config.get("scale", 1)
        scaled_value = raw_value * scale
        
        _LOGGER.debug(
            "Register %d: raw=%s, scale=%s, scaled=%s", 
            self._register_id, raw_value, scale, scaled_value
        )
        
        return scaled_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.info("Setting value %s for register %d (%s)", value, self._register_id, self._attr_name)
        
        scale = self._register_config.get("scale", 1)
        raw_value = int(value / scale)
        
        _LOGGER.debug("Scaled value %s to raw value %d for register %d", value, raw_value, self._register_id)
        
        # Use the correct method name from coordinator
        success = await self.coordinator.async_write_register(self._register_id, raw_value)
        if not success:
            _LOGGER.error("Failed to set value %s for %s", value, self._attr_name)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        holding_registers = self.coordinator.data.get("holding_registers", {}) if self.coordinator.data else {}
        raw_value = holding_registers.get(self._register_id)
        
        attributes = {
            "register_address": self._register_id,
            "scale_factor": self._register_config.get("scale", 1),
            "raw_value": raw_value,
            "available": raw_value is not None,
        }

        # Add helpful information for specific setting types
        name_lower = self._register_config["name"].lower()
        if "dhw" in name_lower:
            attributes["tooltip"] = "DHW (Domestic Hot Water) temperature setting"
        elif "weather compensation" in name_lower:
            attributes["tooltip"] = "Weather compensation automatically adjusts heating based on outdoor temperature"
        elif "hysteresis" in name_lower:
            attributes["tooltip"] = "Hysteresis prevents frequent switching by creating a temperature band"
        elif "frost protection" in name_lower:
            attributes["tooltip"] = "Frost protection prevents system damage in cold weather"

        if raw_value is None:
            attributes["status"] = "not_configured"
        else:
            attributes["status"] = "available"

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Check if we have valid data from coordinator
        if not self.coordinator.last_update_success:
            _LOGGER.debug("Coordinator last update was not successful for register %d", self._register_id)
            return False
            
        # Check if we have holding register data
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data for register %d", self._register_id)
            return False
            
        holding_registers = self.coordinator.data.get("holding_registers", {})
        is_available = self._register_id in holding_registers
        
        if not is_available:
            _LOGGER.debug("Register %d not found in holding_registers data", self._register_id)
        
        return is_available

class GrantAerona3FlowRateNumber(CoordinatorEntity, NumberEntity):
    """Grant Aerona3 flow rate configuration number entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the flow rate number entity."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{config_entry.entry_id}_flow_rate_config"
        self._attr_name = "Flow Rate"  # Remove ASHP prefix
        self._attr_has_entity_name = True
        self._attr_native_unit_of_measurement = "L/min"
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value = 10.0
        self._attr_native_max_value = 50.0
        self._attr_native_step = 0.5
        self._attr_icon = "mdi:water-pump"
        self._attr_entity_category = EntityCategory.CONFIG

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": SW_VERSION,
        }

        self._config_entry = config_entry
        self._flow_rate = getattr(coordinator, 'flow_rate_lpm', 34.0)
        
        _LOGGER.debug("Flow rate entity initialized with value: %s L/min", self._flow_rate)

    @property
    def native_value(self) -> float:
        """Return the current flow rate."""
        current_value = getattr(self.coordinator, 'flow_rate_lpm', self._flow_rate)
        _LOGGER.debug("Flow rate current value: %s L/min", current_value)
        return current_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the flow rate value."""
        self._flow_rate = value
        self.coordinator.flow_rate_lpm = value
        new_options = {**self._config_entry.options, "flow_rate_lpm": value}
        self.hass.config_entries.async_update_entry(self._config_entry, options=new_options)

    @property
    def available(self) -> bool:
        """Flow rate entity is always available."""
        return True

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        return {
            "description": "Manually measured flow rate for COP calculations",
            "how_to_measure": "Use a flow meter or calculate from pump curves",
            "typical_range": "15-25 L/min for residential systems",
            "tooltip": "Set this to your actual measured flow rate for accurate COP calculations"
        }
