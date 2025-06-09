"""Improved binary sensor platform for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List # Added List for type hints

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN, MANUFACTURER, MODEL, COIL_REGISTER_MAP, INPUT_REGISTER_MAP, # Added INPUT_REGISTER_MAP
    # Import new config constants relevant for binary sensors
    CONF_SYSTEM_ELEMENTS, CONF_BACKUP_HEATER_EXTERNAL_SWITCH, CONF_EHS_EXTERNAL_SWITCH,
    CONF_HEATING_COOLING_CHANGE_OVER_CONTACT, CONF_ON_OFF_REMOTE_CONTACT,
    CONF_DHW_REMOTE_CONTACT, CONF_DUAL_SET_POINT_CONTROL,
    CONF_EXTERNAL_FLOW_SWITCH_ENTITY
)
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 binary sensor entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    selected_elements = config_entry.options.get(CONF_SYSTEM_ELEMENTS, [])

    entities = []

    # Create binary sensors for ALL coil registers, representing internal statuses
    # We will let the coordinator's _get_relevant_registers filter which ones are actually read.
    # The 'available' property of the entity will reflect if it's relevant and readable.
    for register_id in COIL_REGISTER_MAP.keys():
        entities.append(
            GrantAerona3CoilBinarySensor(coordinator, config_entry, register_id)
        )

    # Add specific system status binary sensors derived from input registers or logical states
    entities.extend([
        GrantAerona3SystemStatusSensor(coordinator, config_entry),
        GrantAerona3DefrostModeSensor(coordinator, config_entry),
        GrantAerona3ErrorStatusSensor(coordinator, config_entry), # Consolidated error sensor
    ])

    # Create binary sensors for linked external Home Assistant binary_sensor entities
    # These entities will reflect the state of the *chosen* external binary_sensor
    if config_entry.options.get(CONF_EXTERNAL_FLOW_SWITCH_ENTITY) and "external_flow_switch" in selected_elements:
        entities.append(GrantAerona3ExternalBinarySensor(coordinator, config_entry, CONF_EXTERNAL_FLOW_SWITCH_ENTITY, "External Flow Switch"))

    # The following external contacts are typically switches/relays that *control* the ASHP,
    # but their *state* can also be monitored if they are connected as binary sensors.
    # They are generally exposed as 'switch' entities if writable by HA.
    # We'll add them here as binary sensors if they are selected as 'binary_sensor' domain in config flow,
    # otherwise they'll be covered by 'switch' entities.
    if config_entry.options.get(CONF_HEATING_COOLING_CHANGE_OVER_CONTACT) and \
       "cooling_mode_enabled" in selected_elements and \
       hass.states.get(config_entry.options.get(CONF_HEATING_COOLING_CHANGE_OVER_CONTACT)).domain == "binary_sensor": # Check domain
        entities.append(GrantAerona3ExternalBinarySensor(coordinator, config_entry, CONF_HEATING_COOLING_CHANGE_OVER_CONTACT, "Heating/Cooling Changeover Contact"))

    if config_entry.options.get(CONF_ON_OFF_REMOTE_CONTACT) and \
       hass.states.get(config_entry.options.get(CONF_ON_OFF_REMOTE_CONTACT)).domain == "binary_sensor": # Check domain
        entities.append(GrantAerona3ExternalBinarySensor(coordinator, config_entry, CONF_ON_OFF_REMOTE_CONTACT, "ON/OFF Remote Contact"))

    if config_entry.options.get(CONF_DHW_REMOTE_CONTACT) and "hot_water_cylinder" in selected_elements and \
       hass.states.get(config_entry.options.get(CONF_DHW_REMOTE_CONTACT)).domain == "binary_sensor": # Check domain
        entities.append(GrantAerona3ExternalBinarySensor(coordinator, config_entry, CONF_DHW_REMOTE_CONTACT, "DHW Production Remote Contact"))

    if config_entry.options.get(CONF_DUAL_SET_POINT_CONTROL) and \
       ("multiple_heating_zones" in selected_elements or "dual_set_point_control_workaround" in selected_elements) and \
       hass.states.get(config_entry.options.get(CONF_DUAL_SET_POINT_CONTROL)).domain == "binary_sensor": # Check domain
        entities.append(GrantAerona3ExternalBinarySensor(coordinator, config_entry, CONF_DUAL_SET_POINT_CONTROL, "Dual Set Point Control"))


    _LOGGER.info("Creating %d binary sensor entities", len(entities))
    async_add_entities(entities)


class GrantAerona3CoilBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Grant Aerona3 coil register binary sensor entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        register_id: int,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._register_id = register_id
        self._register_config = COIL_REGISTER_MAP[register_id]
        self._config_entry = config_entry

        self._attr_unique_id = f"{config_entry.entry_id}_coil_{register_id}"
        self._attr_name = f"Grant Aerona3 {self._register_config['name']}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        self._attr_device_class = self._register_config.get("device_class")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC # Coils are usually diagnostic or config

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the binary sensor is on."""
        register_key = f"coil_{self._register_id}"
        if register_key not in self.coordinator.data:
            return None

        register_data = self.coordinator.data[register_key]
        if not register_data.get("available", True):
            return None
        return register_data["value"]

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


class GrantAerona3SystemStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor to indicate if the heat pump system is running."""

    def __init__(
        self, coordinator: GrantAerona3Coordinator, config_entry: ConfigEntry
    ) -> None:
        """Initialize the system status sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_system_running"
        self._attr_name = "Grant Aerona3 System Running"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the system is considered running."""
        # Check 'Selected Operating Mode' (input_10)
        # 0: Off, 1: Heating, 2: Cooling, 3: DHW, 4: Auto
        mode_data = self.coordinator.data.get("input_10")
        if mode_data and mode_data.get("available", True):
            return mode_data["value"] in [1, 2, 3, 4] # Running if not 'Off'
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class GrantAerona3DefrostModeSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor to indicate if the heat pump is in defrost mode."""

    def __init__(
        self, coordinator: GrantAerona3Coordinator, config_entry: ConfigEntry
    ) -> None:
        """Initialize the defrost mode sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_defrost_mode"
        self._attr_name = "Grant Aerona3 Defrost Mode"
        self._attr_device_class = BinarySensorDeviceClass.COLD # Or other suitable device class
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the heat pump is in defrost mode."""
        # Assuming defrost mode is indicated by a specific coil or input register value.
        # This needs to be confirmed from the Modbus map for the specific defrost status.
        # Placeholder: Using a non-existent register for now, replace with actual.
        # e.g., if there's a coil 50 that is ON during defrost
        # if "coil_50" in self.coordinator.data:
        #    return self.coordinator.data["coil_50"]["value"]

        # If a specific input register like 'defrost temperature' (input_5) changing indicates defrost:
        defrost_temp_data = self.coordinator.data.get("input_5")
        if defrost_temp_data and defrost_temp_data.get("available", True):
            # Define a threshold or specific value that indicates defrost mode
            # For example, if Defrost Temperature goes above a certain threshold only during defrost.
            # This is an educated guess and needs validation against manual/observed behavior.
            return defrost_temp_data["value"] > 0 # Example: if defrost temp > 0 means defrost is active
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Available if the coordinator is updating and the specific defrost register is available
        return self.coordinator.last_update_success and self.coordinator.data.get("input_5", {}).get("available", False)


class GrantAerona3ErrorStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor to indicate if any error/alarm is active."""

    def __init__(
        self, coordinator: GrantAerona3Coordinator, config_entry: ConfigEntry
    ) -> None:
        """Initialize the error status sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_error_status"
        self._attr_name = "Grant Aerona3 Error Status"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if any alarm or error coils being active."""
        # Iterate through relevant coil registers that indicate alarms/errors
        active_errors = []
        for register_id, config in COIL_REGISTER_MAP.items():
            name_lower = config["name"].lower()
            # Assuming "alarm" or "error" in the name indicates an error status coil
            if "alarm" in name_lower or "error" in name_lower:
                register_key = f"coil_{register_id}"
                register_data = self.coordinator.data.get(register_key)
                if register_data and register_data.get("available", True) and register_data["value"]:
                    active_errors.append(config["name"])

        # Also check for a dedicated error code input register (if available)
        # Based on constants.py, ERROR_CODES map to actual error values.
        # input_register_14: 'Alarm Code'
        alarm_code_data = self.coordinator.data.get("input_14")
        if alarm_code_data and alarm_code_data.get("available", True) and alarm_code_data["value"] != 0:
            active_errors.append(f"Alarm Code: {alarm_code_data['value']} ({INPUT_REGISTER_MAP[14].get('description', '')})")


        return len(active_errors) > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes (list of active errors)."""
        attributes = {}
        active_errors = []

        # List active errors from coil registers
        for register_id, config in COIL_REGISTER_MAP.items():
            name_lower = config["name"].lower()
            if "alarm" in name_lower or "error" in name_lower:
                register_key = f"coil_{register_id}"
                register_data = self.coordinator.data.get(register_key)
                if register_data and register_data.get("available", True) and register_data["value"]:
                    active_errors.append(config["name"])

        # Add specific alarm code from input register if present
        alarm_code_data = self.coordinator.data.get("input_14")
        if alarm_code_data and alarm_code_data.get("available", True) and alarm_code_data["value"] != 0:
            alarm_description = INPUT_REGISTER_MAP[14].get("description", f"Unknown Alarm Code {alarm_code_data['value']}")
            # Look up the actual error message if it's in ERROR_CODES map
            if alarm_code_data['value'] in ERROR_CODES:
                alarm_description = ERROR_CODES[alarm_code_data['value']]
            active_errors.append(f"Main Alarm: {alarm_description} (Code: {alarm_code_data['value']})")


        attributes["active_errors"] = active_errors
        attributes["error_count"] = len(active_errors)
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # This sensor is available if the coordinator is updating.
        # Its 'is_on' state will reflect whether errors are detected based on data.
        return self.coordinator.last_update_success


class GrantAerona3ExternalBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor entity for external Home Assistant binary_sensors linked in config flow."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        config_key: str, # The key from config_flow (e.g., CONF_EXTERNAL_FLOW_SWITCH_ENTITY)
        name_suffix: str, # A user-friendly name for this external binary sensor
    ) -> None:
        """Initialize the external binary sensor entity."""
        super().__init__(coordinator)
        self._config_key = config_key
        self._entity_id_linked = config_entry.options.get(config_key) # The actual HA entity ID
        self._name_suffix = name_suffix

        self._attr_unique_id = f"{config_entry.entry_id}_external_binary_{config_key}"
        self._attr_name = f"Grant Aerona3 {self._name_suffix}"

        # Device info - Link this to the main ASHP device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

        # Attempt to set device class based on what's expected for this config_key
        if "flow switch" in name_suffix.lower():
            self._attr_device_class = BinarySensorDeviceClass.MOTION # Best fit for flow detection
        elif "contact" in name_suffix.lower() or "switch" in name_suffix.lower():
            self._attr_device_class = BinarySensorDeviceClass.OPENING # Or other suitable contact device class
        # Add more mappings as needed for other types of external binary sensors

        self._attr_entity_category = EntityCategory.DIAGNOSTIC # Typically diagnostic for linked sensors

    @property
    def is_on(self) -> Optional[bool]:
        """Return the state of the external binary sensor."""
        if not self._entity_id_linked:
            return None # No external entity configured

        external_sensor_data = self.coordinator.data.get("external_sensors", {}).get(self._config_key)
        if external_sensor_data and external_sensor_data.get("available"):
            # For binary sensors, the value should be boolean (True/False)
            return bool(external_sensor_data["value"])
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        external_sensor_data = self.coordinator.data.get("external_sensors", {}).get(self._config_key, {})

        attributes = {
            "linked_entity_id": self._entity_id_linked,
            "description": f"External binary sensor linked for {self._name_suffix}",
            "available": external_sensor_data.get("available", False),
        }
        if not external_sensor_data.get("available", True):
            attributes["error"] = external_sensor_data.get("error", "External binary sensor entity unavailable or not configured.")
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
