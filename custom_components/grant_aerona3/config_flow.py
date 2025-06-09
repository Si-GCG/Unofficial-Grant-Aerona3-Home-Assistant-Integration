# custom_components/grant_aerona3/config_flow.py

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.const import CONF_HOST, CONF_PORT

_LOGGER = logging.getLogger(__name__)

# Define major system components that a user can select as present in their installation.
# These selections will influence which other configuration options or entities become relevant.
SYSTEM_ELEMENTS = {
    "hot_water_cylinder": "Hot Water Cylinder (DHW)",
    "buffer_tank": "Buffer Tank",
    "cooling_mode_enabled": "ASHP unit supports Cooling Mode (e.g., AEYC-1242XU)",
    "backup_electric_heater": "Backup Electric Heater (Immersion/External)",
    "external_heat_source_ehs": "External Heat Source (e.g., Boiler via EHS input)",
    "additional_water_pump": "Additional Water Pump (e.g., secondary heating circuit pump)",
    "3way_mixing_valve_heating": "3-Way Mixing Valve (for Heating Zones)",
    "dhw_3way_valve": "DHW 3-Way Valve (for hot water production)",
    "external_flow_switch": "External Flow Switch (connected to ASHP terminal)",
    "humidity_sensor_present": "External Humidity Sensor (connected to ASHP terminal)",
    "multiple_heating_zones": "Multiple Heating Zones (e.g., Zone 1 & Zone 2 enabled)",
    "low_tariff_mode_support": "ASHP supports Low Tariff Mode",
    "night_mode_support": "ASHP supports Night Mode",
    "dehumidifier_support": "ASHP supports Dehumidifier control",
    "dual_set_point_control_workaround": "Dual Set Point Control (as alternative heating profile / cold snap mode)",
}

# Define specific heating types for zones
HEATING_TYPES = {
    "underfloor_heating": "Underfloor Heating",
    "radiators": "Radiators",
}

# Define keys for configuration data stored in options.
# These are primarily for linking *existing* Home Assistant entities.
CONF_SYSTEM_ELEMENTS = "system_elements"

# External sensor entity IDs to be linked by the user
CONF_FLOW_TEMP_SENSOR = "flow_temperature_sensor_entity_id"
CONF_RETURN_TEMP_SENSOR = "return_temperature_sensor_entity_id"
CONF_OUTSIDE_TEMP_SENSOR = "outside_temperature_sensor_entity_id"
CONF_CYLINDER_TEMP_SENSOR = "cylinder_temperature_sensor_entity_id"
CONF_BUFFER_TEMP_SENSOR = "buffer_temperature_sensor_entity_id"
CONF_MIX_WATER_TEMP_SENSOR = "mix_water_temperature_sensor_entity_id"
CONF_ROOM_TEMP_SENSOR = "room_temperature_sensor_entity_id"
CONF_HUMIDITY_SENSOR = "humidity_sensor_entity_id"

# Specific zone heating types
CONF_ZONE1_HEATING_TYPE = "zone1_heating_type"
CONF_ZONE2_HEATING_TYPE = "zone2_heating_type"

# External control entity IDs to be linked by the user (e.g., existing HA switches/binary_sensors)
CONF_BACKUP_HEATER_EXTERNAL_SWITCH = "backup_heater_external_switch_entity_id"
CONF_EHS_EXTERNAL_SWITCH = "ehs_external_switch_entity_id"
CONF_HEATING_COOLING_CHANGE_OVER_CONTACT = "heating_cooling_change_over_contact_entity_id"
CONF_ON_OFF_REMOTE_CONTACT = "on_off_remote_contact_entity_id"
CONF_DHW_REMOTE_CONTACT = "dhw_remote_contact_entity_id"
CONF_DUAL_SET_POINT_CONTROL = "dual_set_point_control_entity_id"
CONF_THREE_WAY_MIXING_VALVE_ENTITY = "three_way_mixing_valve_entity_id"
CONF_DHW_THREE_WAY_VALVE_ENTITY = "dhw_three_way_valve_entity_id"
CONF_EXTERNAL_FLOW_SWITCH_ENTITY = "external_flow_switch_entity_id"


class GrantAerona3ConfigFlow(config_entries.ConfigFlow):
    """Grant Aerona3 config flow for initial setup."""

    VERSION = 1
    # IMPORTANT: This DOMAIN attribute is crucial for Home Assistant to correctly
    # identify and load your configuration flow. Make sure it matches your integration's domain.
    DOMAIN = "grant_aerona3"
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial user setup step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            # Set a unique ID for the configuration entry to prevent duplicates.
            await self.async_set_unique_id(f"grant_aerona3_{host}_{port}")
            self._abort_if_unique_id_configured()

            _LOGGER.debug("Configuring ASHP at %s:%s with initial selected elements: %s", host, port, user_input.get(CONF_SYSTEM_ELEMENTS))

            # Create the initial configuration entry. Connection details go in 'data',
            # and selected system elements/sensor links go into 'options' for later modification.
            return self.async_create_entry(
                title=f"Grant Aerona3 ({host})",
                data={CONF_HOST: host, CONF_PORT: port},
                options=self._create_initial_options_from_user_input(user_input)
            )

        # Schema for the initial setup form. This collects basic connection details
        # and allows initial selection of major system elements and critical sensors.
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="192.168.1.100"): str, # Default IP for example
                vol.Required(CONF_PORT, default=8888): vol.All(int, vol.Range(min=1, max=65535)),
                # Multi-select dropdown for major system elements present in the installation
                vol.Optional(CONF_SYSTEM_ELEMENTS, default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[{"value": k, "label": v} for k, v in SYSTEM_ELEMENTS.items()],
                        multiple=True,
                        mode="dropdown",
                    )
                ),
                # Initial selectors for core temperature sensors, as these are almost always present.
                vol.Optional(CONF_OUTSIDE_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
                ),
                vol.Optional(CONF_ROOM_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
                ),
                vol.Optional(CONF_FLOW_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
                ),
                vol.Optional(CONF_RETURN_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    def _create_initial_options_from_user_input(self, user_input):
        """Helper function to compile initial options from user input, including defaults."""
        options = {
            CONF_SYSTEM_ELEMENTS: user_input.get(CONF_SYSTEM_ELEMENTS, []),
            CONF_FLOW_TEMP_SENSOR: user_input.get(CONF_FLOW_TEMP_SENSOR, ""),
            CONF_RETURN_TEMP_SENSOR: user_input.get(CONF_RETURN_TEMP_SENSOR, ""),
            CONF_OUTSIDE_TEMP_SENSOR: user_input.get(CONF_OUTSIDE_TEMP_SENSOR, ""),
            CONF_CYLINDER_TEMP_SENSOR: user_input.get(CONF_CYLINDER_TEMP_SENSOR, ""),
            CONF_BUFFER_TEMP_SENSOR: user_input.get(CONF_BUFFER_TEMP_SENSOR, ""),
            CONF_MIX_WATER_TEMP_SENSOR: user_input.get(CONF_MIX_WATER_TEMP_SENSOR, ""),
            CONF_ROOM_TEMP_SENSOR: user_input.get(CONF_ROOM_TEMP_SENSOR, ""),
            CONF_HUMIDITY_SENSOR: user_input.get(CONF_HUMIDITY_SENSOR, ""),
            CONF_ZONE1_HEATING_TYPE: user_input.get(CONF_ZONE1_HEATING_TYPE, ""),
            CONF_ZONE2_HEATING_TYPE: user_input.get(CONF_ZONE2_HEATING_TYPE, ""),
            CONF_BACKUP_HEATER_EXTERNAL_SWITCH: user_input.get(CONF_BACKUP_HEATER_EXTERNAL_SWITCH, ""),
            CONF_EHS_EXTERNAL_SWITCH: user_input.get(CONF_EHS_EXTERNAL_SWITCH, ""),
            CONF_HEATING_COOLING_CHANGE_OVER_CONTACT: user_input.get(CONF_HEATING_COOLING_CHANGE_OVER_CONTACT, ""),
            CONF_ON_OFF_REMOTE_CONTACT: user_input.get(CONF_ON_OFF_REMOTE_CONTACT, ""),
            CONF_DHW_REMOTE_CONTACT: user_input.get(CONF_DHW_REMOTE_CONTACT, ""),
            CONF_DUAL_SET_POINT_CONTROL: user_input.get(CONF_DUAL_SET_POINT_CONTROL, ""),
            CONF_THREE_WAY_MIXING_VALVE_ENTITY: user_input.get(CONF_THREE_WAY_MIXING_VALVE_ENTITY, ""),
            CONF_DHW_THREE_WAY_VALVE_ENTITY: user_input.get(CONF_DHW_THREE_WAY_VALVE_ENTITY, ""),
            CONF_EXTERNAL_FLOW_SWITCH_ENTITY: user_input.get(CONF_EXTERNAL_FLOW_SWITCH_ENTITY, ""),
        }
        return options

    @callback
    def async_get_options_flow(self, config_entry):
        """Get the options flow for this handler, allowing users to modify settings after initial setup."""
        return GrantAerona3OptionsFlow(config_entry)


class GrantAerona3OptionsFlow(config_entries.OptionsFlow):
    """Grant Aerona3 options flow for post-installation configuration."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options form."""
        errors = {}

        if user_input is not None:
            # Update the configuration entry's options with the new user input.
            return self.async_create_entry(title="", data=user_input)

        current_options = self.config_entry.options

        # Define the base schema for the options form.
        # Defaults are pre-filled from the current configuration entry's options.
        options_schema_dict = {
            vol.Optional(
                CONF_SYSTEM_ELEMENTS,
                default=current_options.get(CONF_SYSTEM_ELEMENTS, [])
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[{"value": k, "label": v} for k, v in SYSTEM_ELEMENTS.items()],
                    multiple=True,
                    mode="dropdown",
                )
            ),
            # Always show core temperature sensors, regardless of initial system elements,
            # as they are fundamental for ASHP monitoring.
            vol.Optional(
                CONF_FLOW_TEMP_SENSOR,
                default=current_options.get(CONF_FLOW_TEMP_SENSOR, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
            ),
            vol.Optional(
                CONF_RETURN_TEMP_SENSOR,
                default=current_options.get(CONF_RETURN_TEMP_SENSOR, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
            ),
            vol.Optional(
                CONF_OUTSIDE_TEMP_SENSOR,
                default=current_options.get(CONF_OUTSIDE_TEMP_SENSOR, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
            ),
            vol.Optional(
                CONF_ROOM_TEMP_SENSOR,
                default=current_options.get(CONF_ROOM_TEMP_SENSOR, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
            ),
        }

        # Dynamically add more selectors based on the currently selected system elements.
        selected_elements = current_options.get(CONF_SYSTEM_ELEMENTS, [])

        # Always show Zone 1 heating type selector
        options_schema_dict[vol.Required(
            CONF_ZONE1_HEATING_TYPE,
            default=current_options.get(CONF_ZONE1_HEATING_TYPE, "")
        )] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[{"value": k, "label": v} for k, v in HEATING_TYPES.items()],
                multiple=False,
                mode="dropdown",
                translation_key="zone1_heating_type"
            )
        )

        # Only show Zone 2 heating type if multiple zones are enabled
        if "multiple_heating_zones" in selected_elements:
            options_schema_dict[vol.Optional(
                CONF_ZONE2_HEATING_TYPE,
                default=current_options.get(CONF_ZONE2_HEATING_TYPE, "")
            )] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[{"value": k, "label": v} for k, v in HEATING_TYPES.items()],
                    multiple=False,
                    mode="dropdown",
                    translation_key="zone2_heating_type"
                )
            )

        # Always show Dual Set Point Control selector
        options_schema_dict[vol.Optional(
            CONF_DUAL_SET_POINT_CONTROL,
            default=current_options.get(CONF_DUAL_SET_POINT_CONTROL, "")
        )] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="switch", multiple=False)
        )

        if "hot_water_cylinder" in selected_elements:
            options_schema_dict[vol.Optional(
                CONF_CYLINDER_TEMP_SENSOR,
                default=current_options.get(CONF_CYLINDER_TEMP_SENSOR, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
            )
            options_schema_dict[vol.Optional(
                CONF_DHW_THREE_WAY_VALVE_ENTITY,
                default=current_options.get(CONF_DHW_THREE_WAY_VALVE_ENTITY, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="valve", multiple=False)
            )
            options_schema_dict[vol.Optional(
                CONF_DHW_REMOTE_CONTACT,
                default=current_options.get(CONF_DHW_REMOTE_CONTACT, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch", multiple=False)
            )

        if "buffer_tank" in selected_elements:
            options_schema_dict[vol.Optional(
                CONF_BUFFER_TEMP_SENSOR,
                default=current_options.get(CONF_BUFFER_TEMP_SENSOR, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
            )

        if "3way_mixing_valve_heating" in selected_elements:
             options_schema_dict[vol.Optional(
                CONF_MIX_WATER_TEMP_SENSOR,
                default=current_options.get(CONF_MIX_WATER_TEMP_SENSOR, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=False)
            )
             options_schema_dict[vol.Optional(
                CONF_THREE_WAY_MIXING_VALVE_ENTITY,
                default=current_options.get(CONF_THREE_WAY_MIXING_VALVE_ENTITY, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="valve", multiple=False)
            )

        if "backup_electric_heater" in selected_elements:
            options_schema_dict[vol.Optional(
                CONF_BACKUP_HEATER_EXTERNAL_SWITCH,
                default=current_options.get(CONF_BACKUP_HEATER_EXTERNAL_SWITCH, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch", multiple=False)
            )

        if "external_heat_source_ehs" in selected_elements:
            options_schema_dict[vol.Optional(
                CONF_EHS_EXTERNAL_SWITCH,
                default=current_options.get(CONF_EHS_EXTERNAL_SWITCH, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch", multiple=False)
            )

        if "external_flow_switch" in selected_elements:
            options_schema_dict[vol.Optional(
                CONF_EXTERNAL_FLOW_SWITCH_ENTITY,
                default=current_options.get(CONF_EXTERNAL_FLOW_SWITCH_ENTITY, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", device_class="motion", multiple=False)
            )

        if "humidity_sensor_present" in selected_elements:
            options_schema_dict[vol.Optional(
                CONF_HUMIDITY_SENSOR,
                default=current_options.get(CONF_HUMIDITY_SENSOR, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="humidity", multiple=False)
            )

        if "cooling_mode_enabled" in selected_elements:
            options_schema_dict[vol.Optional(
                CONF_HEATING_COOLING_CHANGE_OVER_CONTACT,
                default=current_options.get(CONF_HEATING_COOLING_CHANGE_OVER_CONTACT, "")
            )] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["binary_sensor", "switch"], multiple=False)
            )

        # General remote ON/OFF contact (e.g., from a wired thermostat)
        options_schema_dict[vol.Optional(
            CONF_ON_OFF_REMOTE_CONTACT,
            default=current_options.get(CONF_ON_OFF_REMOTE_CONTACT, "")
        )] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "switch"], multiple=False)
        )

        options_schema = vol.Schema(options_schema_dict)
        return self.async_show_form(step_id="init", data_schema=options_schema, errors=errors)
