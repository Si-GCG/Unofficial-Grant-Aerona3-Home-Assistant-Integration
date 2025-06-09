"""Improved switch platform for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN, MANUFACTURER, MODEL, COIL_REGISTER_MAP,
    CONF_SYSTEM_ELEMENTS, # Import new config constants
    CONF_BACKUP_HEATER_EXTERNAL_SWITCH, CONF_EHS_EXTERNAL_SWITCH,
    CONF_HEATING_COOLING_CHANGE_OVER_CONTACT, CONF_ON_OFF_REMOTE_CONTACT,
    CONF_DHW_REMOTE_CONTACT, CONF_DUAL_SET_POINT_CONTROL,
    CONF_THREE_WAY_MIXING_VALVE_ENTITY, CONF_DHW_THREE_WAY_VALVE_ENTITY # Valves might also be switches
)
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 switch entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    selected_elements = config_entry.options.get(CONF_SYSTEM_ELEMENTS, [])

    entities = []

    # Create switches for specific writable coil registers that represent ON/OFF functions
    # These are Modbus coils directly controlled by the ASHP.
    for register_id, config in COIL_REGISTER_MAP.items():
        # Only create switches for coils explicitly marked as writable (if not already handled by another platform)
        # and that logically represent a user-controllable ON/OFF feature.
        name_lower = config["name"].lower()

        # Heuristic to determine if a coil should be a switch entity
        if config.get("writable", False) and any(word in name_lower for word in [
            "heating weather compensation", "cooling weather compensation", "anti-legionella",
            "frost protection based on room", "frost protection based on outdoor",
            "frost protection based on flow", "dhw storage frost protection",
            "secondary system circuit frost protection", "compensation for room humidity",
            "dehumidifier", "terminal 19-18 : dhw remote contact", # This is usually an input but if writable...
            "terminal 22-23 : dual set point control", # This is usually an input but if writable...
            "terminal 28-29 : night mode", # This is usually an input but if writable...
            "terminal 30-31 : low tariff", # This is usually an input but if writable...
            "operation at the time of reboot after blackout",
        ]):
            # Avoid creating a switch if it's already handled by climate entity's mode or other specific logic
            # For example, "Terminal 19-18 : DHW Remote Contact" might be exposed as a switch for DHW call.
            # "Terminal 22-23 : Dual Set Point Control" also might be a switch.
            entities.append(
                GrantAerona3CoilSwitch(coordinator, config_entry, register_id)
            )
        else:
            _LOGGER.debug("Skipping coil %d (%s) for switch entity creation (not marked writable or not a common switch type).", register_id, config.get("name"))


    # Create switches for linked external Home Assistant switch entities
    # These represent devices *outside* the ASHP controlled by HA, but whose state
    # or control might be relevant to the ASHP's operation or displayed on the ASHP UI.
    linked_external_switches = {
        CONF_BACKUP_HEATER_EXTERNAL_SWITCH: "Backup Heater",
        CONF_EHS_EXTERNAL_SWITCH: "External Heat Source (EHS)",
        # For contacts like DHW Remote, ON/OFF Remote, H/C Changeover, Dual Set Point:
        # If the user linked a *switch* entity in config_flow, we create an external switch.
        # If they linked a *binary_sensor*, it's handled by binary_sensor.py.
        CONF_ON_OFF_REMOTE_CONTACT: "Main ON/OFF Remote Contact",
        CONF_DHW_REMOTE_CONTACT: "DHW Production Remote Contact",
        CONF_DUAL_SET_POINT_CONTROL: "Dual Set Point Control Trigger",
        CONF_HEATING_COOLING_CHANGE_OVER_CONTACT: "Heating/Cooling Changeover Actuator",
        CONF_THREE_WAY_MIXING_VALVE_ENTITY: "Heating 3-Way Mixing Valve", # If a valve is treated as simple on/off switch
        CONF_DHW_THREE_WAY_VALVE_ENTITY: "DHW 3-Way Valve (External)", # If a valve is treated as simple on/off switch
    }

    for config_key, name_suffix in linked_external_switches.items():
        entity_id = config_entry.options.get(config_key)
        if entity_id:
            # Important: Verify that the linked entity is indeed a 'switch' domain
            # We need to get the state from hass to check its domain.
            state = hass.states.get(entity_id)
            if state and state.domain == "switch":
                entities.append(
                    GrantAerona3ExternalSwitch(coordinator, config_entry, config_key, name_suffix)
                )
            else:
                _LOGGER.warning("Configured entity '%s' for '%s' is not a switch. Skipping external switch creation.", entity_id, config_key)


    _LOGGER.info("Creating %d switch entities", len(entities))
    async_add_entities(entities)


class GrantAerona3CoilSwitch(CoordinatorEntity, SwitchEntity):
    """Grant Aerona3 writable coil register switch entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._register_id = register_id
        self._register_config = COIL_REGISTER_MAP[register_id]
        self._config_entry = config_entry

        self._attr_unique_id = f"{config_entry.entry_id}_coil_switch_{register_id}"
        self._attr_name = f"Grant Aerona3 {self._register_config['name']}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Set entity category for configuration items
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:toggle-switch" # Generic switch icon

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the switch is on."""
        register_key = f"coil_{self._register_id}"
        if register_key not in self.coordinator.data:
            return None

        register_data = self.coordinator.data[register_key]
        if not register_data.get("available", True):
            return None
        return register_data["value"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        success = await self.coordinator.async_write_coil(self._register_id, True)
        if success:
            _LOGGER.debug("Successfully turned ON coil switch %d (%s)", self._register_id, self._attr_name)
            await self.coordinator.async_request_refresh() # Request immediate refresh to update state
        else:
            _LOGGER.error("Failed to turn on switch %s at address %d", self._attr_name, self._register_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        success = await self.coordinator.async_write_coil(self._register_id, False)
        if success:
            _LOGGER.debug("Successfully turned OFF coil switch %d (%s)", self._register_id, self._attr_name)
            await self.coordinator.async_request_refresh() # Request immediate refresh to update state
        else:
            _LOGGER.error("Failed to turn off switch %s at address %d", self._attr_name, self._register_id)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        register_key = f"coil_{self._register_id}"
        data = self.coordinator.data.get(register_key, {})

        attributes = {
            "register_address": self._register_id,
            "description": data.get("description", ""),
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
        register_key = f"coil_{self._register_id}"
        register_data = self.coordinator.data.get(register_key)
        return self.coordinator.last_update_success and register_data and register_data.get("available", False)


class GrantAerona3ExternalSwitch(CoordinatorEntity, SwitchEntity):
    """Switch entity for external Home Assistant switches linked in config flow."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        config_key: str, # The key from config_flow (e.g., CONF_BACKUP_HEATER_EXTERNAL_SWITCH)
        name_suffix: str, # A user-friendly name for this external switch
    ) -> None:
        """Initialize the external switch entity."""
        super().__init__(coordinator)
        self._config_key = config_key
        self._entity_id_linked = config_entry.options.get(config_key) # The actual HA entity ID
        self._name_suffix = name_suffix
        self._hass = coordinator.hass # Get hass instance for service calls

        self._attr_unique_id = f"{config_entry.entry_id}_external_switch_{config_key}"
        self._attr_name = f"Grant Aerona3 {self._name_suffix}"

        # Device info - Link this to the main ASHP device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        self._attr_entity_category = EntityCategory.CONFIG # These are configuration/control switches
        self._attr_icon = "mdi:toggle-switch"

    @property
    def is_on(self) -> Optional[bool]:
        """Return the state of the external switch."""
        if not self._entity_id_linked:
            return None # No external entity configured

        # Get the state directly from Home Assistant
        state = self._hass.states.get(self._entity_id_linked)
        if state:
            return state.state == "on"
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the external switch on."""
        if self._entity_id_linked:
            try:
                await self._hass.services.async_call(
                    "switch", "turn_on", {"entity_id": self._entity_id_linked}, blocking=True
                )
                _LOGGER.debug("Successfully called turn_on service for external switch: %s", self._entity_id_linked)
            except Exception as e:
                _LOGGER.error("Failed to turn on external switch %s: %s", self._entity_id_linked, e)
        else:
            _LOGGER.warning("Attempted to turn on external switch, but no entity is linked for %s.", self._config_key)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the external switch off."""
        if self._entity_id_linked:
            try:
                await self._hass.services.async_call(
                    "switch", "turn_off", {"entity_id": self._entity_id_linked}, blocking=True
                )
                _LOGGER.debug("Successfully called turn_off service for external switch: %s", self._entity_id_linked)
            except Exception as e:
                _LOGGER.error("Failed to turn off external switch %s: %s", self._entity_id_linked, e)
        else:
            _LOGGER.warning("Attempted to turn off external switch, but no entity is linked for %s.", self._config_key)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        attributes = {
            "linked_entity_id": self._entity_id_linked,
            "description": f"Controls external switch linked for {self._name_suffix}",
        }
        # Add current state of the linked entity for debugging/info
        state = self._hass.states.get(self._entity_id_linked)
        if state:
            attributes["current_linked_state"] = state.state
        else:
            attributes["current_linked_state"] = "unavailable_in_ha"

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self._entity_id_linked:
            return False # Not configured

        # An external switch is available if the coordinator is updating AND
        # the linked entity itself is available in Home Assistant.
        linked_state = self._hass.states.get(self._entity_id_linked)
        return self.coordinator.last_update_success and linked_state and linked_state.state != "unavailable"
