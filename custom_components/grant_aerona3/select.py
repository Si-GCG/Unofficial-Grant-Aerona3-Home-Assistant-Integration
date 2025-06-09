"""Select platform for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up Grant Aerona3 select entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    selected_elements = config_entry.options.get(CONF_SYSTEM_ELEMENTS, [])

    entities = []

    # Create select entities for writable holding registers that have an options_map
    for register_id, config in HOLDING_REGISTER_MAP.items():
        if config.get("writable", False) and "options_map" in config:
            # Check if this register is relevant based on selected elements.
            # This logic should mirror _get_relevant_registers in coordinator.py for consistency.
            name_lower = config["name"].lower()
            is_relevant_to_elements = True

            # Example: Only create DHW related select entities if hot_water_cylinder is selected
            if "dhw" in name_lower and "hot_water_cylinder" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Only create "Main water pump" related select entities if additional_water_pump is NOT selected (assuming it's mutually exclusive with main pump config)
            # or if it's always relevant. This needs careful consideration based on the specific register meaning.
            # For "Type Of Configuration Of Main Water Pump" (reg 41)
            # For "Type Of Operation Of Additional Water Pump" (reg 49)
            elif "main water pump" in name_lower and "additional_water_pump" in selected_elements:
                # If an additional pump is selected, the main pump config might still be relevant, but check context.
                pass # This is complex, will need careful review of manual and specific register.
            elif "additional water pump" in name_lower and "additional_water_pump" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Backup heater function type
            elif "backup heater type of function" in name_lower and "backup_electric_heater" not in selected_elements:
                is_relevant_to_elements = False
            # Example: EHS function type
            elif "ehs type of function" in name_lower and "external_heat_source_ehs" not in selected_elements:
                is_relevant_to_elements = False
            # Example: Freeze protection functions
            elif "freeze protection functions" in name_lower and not (
                "frost_protection_based_on_room_temperature" in selected_elements or # Assuming these are selected in config flow's system elements for frost protection
                "frost_protection_based_on_outdoor_temperature" in selected_elements or
                "frost_protection_based_on_flow_temp" in selected_elements or
                "dhw_storage_frost_protection" in selected_elements or
                "secondary_system_circuit_frost_protection" in selected_elements
            ):
                # If no specific frost protection type is enabled, this setting might not be relevant
                pass # This needs to match the system elements related to frost protection in config_flow.py


            # Add more conditions as needed for other system elements and their associated select entities

            if is_relevant_to_elements:
                entities.append(
                    GrantAerona3HoldingSelect(coordinator, config_entry, register_id)
                )
            else:
                _LOGGER.debug("Skipping holding register %d (%s) for select entity creation (not relevant to configured system).", register_id, config.get("name"))

    _LOGGER.info("Creating %d select entities", len(entities))
    async_add_entities(entities)


class GrantAerona3HoldingSelect(CoordinatorEntity, SelectEntity):
    """Grant Aerona3 writable holding register select entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._register_id = register_id
        self._register_config = HOLDING_REGISTER_MAP[register_id]
        self._config_entry = config_entry

        self._attr_unique_id = f"{config_entry.entry_id}_holding_select_{register_id}"
        self._attr_name = f"Grant Aerona3 {self._register_config['name']}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # The options for the select entity come from the 'options_map' in const.py
        self._options_map = self._register_config["options_map"]
        self._attr_options = list(self._options_map.values()) # List of display names

        # Set entity category for configuration settings
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:form-select" # Generic select icon

    @property
    def current_option(self) -> Optional[str]:
        """Return the current selected option."""
        register_key = f"holding_{self._register_id}"
        if register_key not in self.coordinator.data:
            return None

        register_data = self.coordinator.data[register_key]
        if not register_data.get("available", True):
            return None
        
        # Get the raw Modbus value and map it to the display string
        current_value = int(register_data["value"]) # Assuming the value is integer representing the key
        
        # Find the display string in the options_map by value (key)
        for key, display_name in self._options_map.items():
            if key == current_value:
                return display_name
        
        _LOGGER.warning("Modbus value %s for register %d (%s) not found in options map.",
                        current_value, self._register_id, self._attr_name)
        return None # Value not found in map

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the Modbus value (key) corresponding to the selected display name
        selected_value = None
        for key, display_name in self._options_map.items():
            if display_name == option:
                selected_value = key
                break

        if selected_value is None:
            _LOGGER.error("Selected option '%s' not found in options map for register %d.", option, self._register_id)
            return

        # Write the selected Modbus value to the holding register
        success = await self.coordinator.async_write_holding_register(self._register_id, selected_value)
        if success:
            _LOGGER.debug("Successfully set holding register %d (%s) to value %d (option: %s)", self._register_id, self._attr_name, selected_value, option)
            await self.coordinator.async_request_refresh() # Request immediate refresh
        else:
            _LOGGER.error("Failed to set option '%s' for select entity %s at address %d", option, self._attr_name, self._register_id)

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
            "options_map": self._options_map, # Include the full options map for debugging/info
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
