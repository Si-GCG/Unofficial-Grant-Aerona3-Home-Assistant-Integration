"""Improved climate platform for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import logging
from typing import Any, List, Optional, Dict

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH # Example fan modes, if applicable
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.event import async_track_state_change_event # Import for external sensor listening

from .const import (
    DOMAIN, MANUFACTURER, MODEL, HOLDING_REGISTER_MAP, INPUT_REGISTER_MAP,
    # Import all constants related to config options
    CONF_SYSTEM_ELEMENTS, CONF_FLOW_TEMP_SENSOR, CONF_RETURN_TEMP_SENSOR,
    CONF_OUTSIDE_TEMP_SENSOR, CONF_CYLINDER_TEMP_SENSOR, CONF_BUFFER_TEMP_SENSOR,
    CONF_MIX_WATER_TEMP_SENSOR, CONF_ROOM_TEMP_SENSOR, CONF_HUMIDITY_SENSOR,
    CONF_ZONE1_HEATING_TYPE, CONF_ZONE2_HEATING_TYPE, CONF_BACKUP_HEATER_EXTERNAL_SWITCH,
    CONF_EHS_EXTERNAL_SWITCH, CONF_HEATING_COOLING_CHANGE_OVER_CONTACT,
    CONF_ON_OFF_REMOTE_CONTACT, CONF_DHW_REMOTE_CONTACT, CONF_DUAL_SET_POINT_CONTROL,
    CONF_THREE_WAY_MIXING_VALVE_ENTITY, CONF_DHW_THREE_WAY_VALVE_ENTITY,
    CONF_EXTERNAL_FLOW_SWITCH_ENTITY,
    OPERATING_MODES # Assuming this maps to input_10
)
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 climate entities."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    selected_elements = config_entry.options.get(CONF_SYSTEM_ELEMENTS, [])

    # Always create climate entity for Zone 1 (main zone)
    entities.append(GrantAerona3Climate(coordinator, config_entry, zone=1))

    # Create climate entity for Zone 2 ONLY if multiple heating zones are selected
    if "multiple_heating_zones" in selected_elements:
        entities.append(GrantAerona3Climate(coordinator, config_entry, zone=2))

    _LOGGER.info("Creating %d climate entities", len(entities))
    async_add_entities(entities)


class GrantAerona3Climate(CoordinatorEntity, ClimateEntity):
    """Grant Aerona3 climate entity."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        zone: int,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._zone = zone
        self._config_entry = config_entry
        self._hass = coordinator.hass # Get hass instance from coordinator

        self._attr_unique_id = f"{config_entry.entry_id}_climate_zone_{zone}"
        self._attr_name = f"Grant Aerona3 Zone {zone}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Grant Aerona3 Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0", # Consider dynamically fetching SW version from ASHP if available
        }

        # Climate properties
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 0.5 # Granularity of temperature setting

        # Determine supported HVAC modes based on config_options
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        if "cooling_mode_enabled" in self._config_entry.options.get(CONF_SYSTEM_ELEMENTS, []):
            self._attr_hvac_modes.append(HVACMode.COOL)
        # Assuming Auto is not directly controllable from this register, but rather internal logic
        # self._attr_hvac_modes.append(HVACMode.AUTO)

        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.TURN_ON |
            ClimateEntityFeature.TURN_OFF
        )
        # Add support for presets if relevant, e.g. 'comfort', 'economy' for DHW or heating
        # self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE
        # self._attr_preset_modes = ["comfort", "economy"] # Example

        # Temperature limits (based on common ASHP ranges, can be refined per specific model/manual)
        self._attr_min_temp = 5.0 # Min flow temp for heating
        self._attr_max_temp = 60.0 # Max flow temp for heating

        # If cooling is enabled, define cooling specific temp ranges
        if "cooling_mode_enabled" in self._config_entry.options.get(CONF_SYSTEM_ELEMENTS, []):
            self._attr_min_temp_cooling = 7.0 # Min flow temp for cooling
            self._attr_max_temp_cooling = 30.0 # Max flow temp for cooling


        # Internal storage for external sensor states, updated by coordinator
        self._external_sensor_data: Dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to Home Assistant."""
        await super().async_added_to_hass()
        # No need to register listeners here for external sensors;
        # the coordinator already fetches them and makes them available in self.coordinator.data["external_sensors"]
        # We just need to ensure self.coordinator.async_request_refresh() is called regularly.

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature for the zone."""
        # Prioritize external room temp sensor if configured for this zone
        if self._zone == 1:
            external_room_temp_data = self.coordinator.data.get("external_sensors", {}).get(CONF_ROOM_TEMP_SENSOR)
            if external_room_temp_data and external_room_temp_data.get("available") and external_room_temp_data.get("value") is not None:
                return external_room_temp_data["value"]
        elif self._zone == 2:
            # Assuming a different external room sensor for Zone 2 if configured,
            # or a specific Modbus register for Zone 2 room temp.
            # For simplicity, for now, we'll assume Zone 2 also uses CONF_ROOM_TEMP_SENSOR if it's the only one
            # or relies on its internal Modbus register (input_12).
            pass

        # Fallback to internal Modbus room air set temperature (input_11 for Zone 1, input_12 for Zone 2)
        if self._zone == 1 and "input_11" in self.coordinator.data:
            register_data = self.coordinator.data["input_11"]
            if register_data.get("available", True):
                return register_data["value"]
        elif self._zone == 2 and "input_12" in self.coordinator.data:
            register_data = self.coordinator.data["input_12"]
            if register_data.get("available", True):
                return register_data["value"]
        return None

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the target temperature for the zone."""
        # This will be the "Fixed Flow Temp" from holding registers (2 for Zone 1, 7 for Zone 2)
        if self._zone == 1 and "holding_2" in self.coordinator.data:
            register_data = self.coordinator.data["holding_2"]
            if register_data.get("available", True):
                return register_data["value"]
        elif self._zone == 2 and "holding_7" in self.coordinator.data:
            register_data = self.coordinator.data["holding_7"]
            if register_data.get("available", True):
                return register_data["value"]
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        # Get operating mode from register 10
        if "input_10" in self.coordinator.data:
            register_data = self.coordinator.data["input_10"]
            if register_data.get("available", True):
                mode_value = register_data["value"]
                # Map Modbus values to Home Assistant HVAC modes
                mode_map = {
                    0: HVACMode.OFF,
                    1: HVACMode.HEAT,
                    2: HVACMode.COOL,
                    # 3: DHW (handled by a separate switch/sensor, not a climate mode for this entity)
                    # 4: AUTO (if the ASHP has a true auto mode that switches between H/C)
                }
                return mode_map.get(mode_value, HVACMode.OFF)
        return HVACMode.OFF # Default to OFF if data is unavailable

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature (fixed flow temp)."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.warning("Attempted to set temperature without a value.")
            return

        # Determine the target Modbus holding register based on zone
        if self._zone == 1:
            register_address = 2  # Fixed Flow Temp Zone 1
            max_flow_temp_reg = 3 # Max Flow Temp Zone1
            min_flow_temp_reg = 4 # Min Flow Temp Zone1
            weather_comp_coil = 2 # Heating Weather Compensation Zone 1 Coil
        elif self._zone == 2:
            register_address = 7  # Fixed Flow Temp Zone 2
            max_flow_temp_reg = 8 # Max Flow Temp Zone2
            min_flow_temp_reg = 9 # Min Flow Temp Zone2
            weather_comp_coil = 3 # Heating Weather Compensation Zone 2 Coil
        else:
            _LOGGER.error("Invalid zone for temperature setting: %s", self._zone)
            return

        register_config = HOLDING_REGISTER_MAP.get(register_address)
        if not register_config:
            _LOGGER.error("Holding register config not found for address %d", register_address)
            return

        # Apply scaling from const.py to convert Celsius to raw Modbus value
        scale = register_config.get("scale", 1)
        raw_value = int(temperature / scale)

        # Basic validation against min/max temps if defined in coordinator's data
        # (These come from registers 3/4 for Zone 1, 8/9 for Zone 2)
        # You would typically also apply weather compensation logic here before writing
        # or have separate entities for fixed setpoint vs. weather compensation.
        
        # Check if weather compensation is enabled for this zone
        weather_comp_enabled = self.coordinator.data.get(f"coil_{weather_comp_coil}", {}).get("value", False)
        if weather_comp_enabled:
             _LOGGER.info("Weather compensation is enabled for Zone %d. Setting fixed temperature may not be effective.", self._zone)
             # If weather compensation is on, setting a fixed temp might be overridden by the ASHP's internal logic.
             # You might want to automatically switch off weather compensation if the user sets a fixed temp.
             # success_comp_off = await self.coordinator.async_write_coil(weather_comp_coil, False)

        success = await self.coordinator.async_write_holding_register(register_address, raw_value)
        if success:
            _LOGGER.debug("Successfully set target temperature for Zone %d to %f°C (raw: %d)", self._zone, temperature, raw_value)
            await self.coordinator.async_request_refresh() # Request update to reflect changes
        else:
            _LOGGER.error("Failed to set temperature for zone %d at address %d", self._zone, register_address)


    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        # The 'Selected Operating Mode' (input_10) is typically a read-only register
        # that reflects the ASHP's current operating state.
        # To change the mode, you usually need to interact with a specific control coil
        # or a higher-level command that triggers the ASHP's internal mode change.

        # For Grant/Chofu, mode changes are often done via remote contacts/terminals or internal parameters.
        # Based on the manual, Terminal 20-21 (ON/OFF remote contact) and Terminal 24-25 (Heating/Cooling mode remote contact)
        # are relevant.

        selected_elements = self._config_entry.options.get(CONF_SYSTEM_ELEMENTS, [])

        if hvac_mode == HVACMode.OFF:
            # Attempt to turn off via ON/OFF remote contact if configured
            on_off_contact_entity_id = self._config_entry.options.get(CONF_ON_OFF_REMOTE_CONTACT)
            if on_off_contact_entity_id:
                await self._hass.services.async_call("switch", "turn_off",
                                                   {"entity_id": on_off_contact_entity_id}, blocking=True)
                _LOGGER.info("Turned off ASHP via ON/OFF remote contact: %s", on_off_contact_entity_id)
            else:
                _LOGGER.warning("ON/OFF remote contact not configured. Cannot turn off ASHP via external contact.")
                # Fallback: If no external contact, you might try to set an internal Modbus coil to OFF
                # (e.g., if the ASHP has a 'main power' coil that is writable).
                # This depends heavily on your specific ASHP's Modbus map.
                # For example, if COIL_REGISTER_MAP has an "Overall System ON/OFF" at address X:
                # success = await self.coordinator.async_write_coil(X, False)
                # if not success: _LOGGER.error("Failed to turn off ASHP via Modbus coil.")

        elif hvac_mode == HVACMode.HEAT:
            # Ensure ASHP is ON (if off)
            on_off_contact_entity_id = self._config_entry.options.get(CONF_ON_OFF_REMOTE_CONTACT)
            if on_off_contact_entity_id:
                await self._hass.services.async_call("switch", "turn_on",
                                                   {"entity_id": on_off_contact_entity_id}, blocking=True)
                _LOGGER.info("Ensured ASHP is ON via ON/OFF remote contact: %s", on_off_contact_entity_id)

            # Set heating mode via Heating/Cooling changeover contact if configured
            hc_changeover_contact_entity_id = self._config_entry.options.get(CONF_HEATING_COOLING_CHANGE_OVER_CONTACT)
            if hc_changeover_contact_entity_id and "cooling_mode_enabled" in selected_elements:
                # Manual states from manual: 1=Cooling is CLOSE, Heating is OPEN; 2=Cooling is OPEN, Heating is CLOSE
                # Assuming 'OPEN' means 'turn_off' and 'CLOSE' means 'turn_on' for a switch entity
                # This depends on how the external contact is wired and exposed in HA.
                # If 'Heating is OPEN contact', then turn off the switch entity linked to that contact.
                # If 'Heating is CLOSE contact', then turn on the switch entity linked to that contact.
                # This mapping is complex and needs to be verified against the physical wiring and terminal 92/92 configuration.

                # For simplicity, assuming a simple "heating/cooling" switch for the H/C changeover:
                # If we want HEAT, we'd ensure the H/C changeover contact is in the 'heating' state.
                # This might mean turning it OFF or ON, depending on its configuration (Terminal 92 in HOLDING_REGISTER_MAP).
                # Example: If Terminal 92 config (Heating/Cooling mode remote contact) is 1 (Cooling=CLOSE, Heating=OPEN):
                # For Heating: ensure the switch is OFF (OPEN)
                # For Cooling: ensure the switch is ON (CLOSE)
                _LOGGER.warning("Heating/Cooling changeover logic needs to be carefully implemented based on Terminal 92 settings.")
                # Placeholder for actual service call based on Terminal 92 config
                # await self._hass.services.async_call("switch", "turn_off", {"entity_id": hc_changeover_contact_entity_id}, blocking=True)

            # You might also need to write to a specific Modbus holding register if your ASHP allows setting
            # operating mode directly via Modbus, rather than just reading input_10.
            # E.g., self.coordinator.async_write_holding_register(MODE_SETTING_REGISTER_ADDR, 1) # 1 for Heating

        elif hvac_mode == HVACMode.COOL:
            if "cooling_mode_enabled" not in selected_elements:
                _LOGGER.warning("Cooling mode is not enabled in integration configuration.")
                return

            # Ensure ASHP is ON (if off)
            on_off_contact_entity_id = self._config_entry.options.get(CONF_ON_OFF_REMOTE_CONTACT)
            if on_off_contact_entity_id:
                await self._hass.services.async_call("switch", "turn_on",
                                                   {"entity_id": on_off_contact_entity_id}, blocking=True)
                _LOGGER.info("Ensured ASHP is ON via ON/OFF remote contact: %s", on_off_contact_entity_id)

            # Set cooling mode via Heating/Cooling changeover contact if configured
            hc_changeover_contact_entity_id = self._config_entry.options.get(CONF_HEATING_COOLING_CHANGE_OVER_CONTACT)
            if hc_changeover_contact_entity_id:
                # Similar logic as above, but for Cooling.
                _LOGGER.warning("Heating/Cooling changeover logic needs to be carefully implemented based on Terminal 92 settings.")
                # await self._hass.services.async_call("switch", "turn_on", {"entity_id": hc_changeover_contact_entity_id}, blocking=True)

            # You might also need to write to a specific Modbus holding register if your ASHP allows setting
            # operating mode directly via Modbus.
            # E.g., self.coordinator.async_write_holding_register(MODE_SETTING_REGISTER_ADDR, 2) # 2 for Cooling

        elif hvac_mode == HVACMode.AUTO:
            _LOGGER.warning("Auto HVAC mode not directly controllable for Grant Aerona3 via Modbus. "
                            "It typically reflects the ASHP's internal decision.")
            # For auto, you might enable weather compensation and let the ASHP decide.
            pass
        else:
            _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
            return

        await self.coordinator.async_request_refresh() # Refresh after setting mode

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        attributes: Dict[str, Any] = {
            "zone": self._zone,
            "configured_system_elements": self._config_entry.options.get(CONF_SYSTEM_ELEMENTS, []),
        }

        # Add zone-specific heating type if configured
        if self._zone == 1:
            heating_type = self._config_entry.options.get(CONF_ZONE1_HEATING_TYPE)
            if heating_type:
                attributes["zone1_heating_type"] = heating_type
        elif self._zone == 2:
            heating_type = self._config_entry.options.get(CONF_ZONE2_HEATING_TYPE)
            if heating_type:
                attributes["zone2_heating_type"] = heating_type

        # Add Modbus register values (ensure 'available' is checked)
        # Current Modbus state (from coordinator.data)
        for reg_map, reg_type_prefix in [(INPUT_REGISTER_MAP, "input"), (HOLDING_REGISTER_MAP, "holding")]:
            for addr, config in reg_map.items():
                register_key = f"{reg_type_prefix}_{addr}"
                if register_key in self.coordinator.data and self.coordinator.data[register_key].get("available", False):
                    # Only add if the register is available and conceptually relevant for THIS entity.
                    # Avoid adding all Modbus registers if they are not directly related to climate control.
                    # This requires careful selection based on what attributes are meaningful here.
                    if "temperature" in config.get("name", "").lower() or \
                       "flow temp" in config.get("name", "").lower() or \
                       "outdoor" in config.get("name", "").lower() or \
                       "room air set" in config.get("name", "").lower() and \
                       f"zone {self._zone}" in config.get("name", "").lower(): # Limit to current zone relevant temps
                        attributes[config["name"].lower().replace(' ', '_')] = self.coordinator.data[register_key]["value"]


        # Add external sensor data (from coordinator.external_sensor_states)
        external_sensors = self.coordinator.data.get("external_sensors", {})
        for config_key in [
            CONF_FLOW_TEMP_SENSOR, CONF_RETURN_TEMP_SENSOR, CONF_OUTSIDE_TEMP_SENSOR,
            CONF_CYLINDER_TEMP_SENSOR, CONF_BUFFER_TEMP_SENSOR, CONF_MIX_WATER_TEMP_SENSOR,
            CONF_ROOM_TEMP_SENSOR, CONF_HUMIDITY_SENSOR
        ]:
            if external_sensors.get(config_key, {}).get("available"):
                attributes[config_key] = external_sensors[config_key]["value"]
            elif external_sensors.get(config_key, {}).get("entity_id"): # If entity ID exists but not available
                attributes[config_key] = "unavailable"


        # Add external control entity IDs and their states if linked
        linked_controls = {
            CONF_BACKUP_HEATER_EXTERNAL_SWITCH: "backup_heater_control",
            CONF_EHS_EXTERNAL_SWITCH: "ehs_control",
            CONF_HEATING_COOLING_CHANGE_OVER_CONTACT: "heating_cooling_changeover_control",
            CONF_ON_OFF_REMOTE_CONTACT: "on_off_remote_control",
            CONF_DHW_REMOTE_CONTACT: "dhw_remote_control",
            CONF_DUAL_SET_POINT_CONTROL: "dual_set_point_control",
            CONF_THREE_WAY_MIXING_VALVE_ENTITY: "3way_mixing_valve_control",
            CONF_DHW_THREE_WAY_VALVE_ENTITY: "dhw_3way_valve_control",
            CONF_EXTERNAL_FLOW_SWITCH_ENTITY: "external_flow_switch_status",
        }
        for config_key, attribute_name in linked_controls.items():
            if external_sensors.get(config_key, {}).get("entity_id"):
                attributes[attribute_name] = external_sensors[config_key]["entity_id"]
                attributes[f"{attribute_name}_state"] = external_sensors[config_key]["value"]
            elif self._config_entry.options.get(config_key): # If linked but not found by coordinator
                 attributes[attribute_name] = self._config_entry.options.get(config_key)
                 attributes[f"{attribute_name}_state"] = "not_available"


        # Add other relevant attributes from coordinator.data as needed
        # Example: compressor frequency, defrost mode
        if "input_1" in self.coordinator.data and self.coordinator.data["input_1"].get("available", False):
            attributes["compressor_frequency"] = self.coordinator.data["input_1"]["value"]
        if "input_5" in self.coordinator.data and self.coordinator.data["input_5"].get("available", False):
            attributes["defrost_temperature"] = self.coordinator.data["input_5"]["value"]

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Climate entity is available if the coordinator is successfully updating data
        return self.coordinator.last_update_success
