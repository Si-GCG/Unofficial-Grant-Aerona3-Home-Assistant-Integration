"""Improved data update coordinator for Grant Aerona3 Heat Pump."""
import logging
from datetime import timedelta
from typing import Any, Dict # Removed List and Tuple imports

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import pymodbus

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    INPUT_REGISTER_MAP,
    HOLDING_REGISTER_MAP,
    COIL_REGISTER_MAP,
    CONF_SYSTEM_ELEMENTS,
    CONF_FLOW_TEMP_SENSOR, CONF_RETURN_TEMP_SENSOR, CONF_OUTSIDE_TEMP_SENSOR,
    CONF_CYLINDER_TEMP_SENSOR, CONF_BUFFER_TEMP_SENSOR, CONF_MIX_WATER_TEMP_SENSOR,
    CONF_ROOM_TEMP_SENSOR, CONF_HUMIDITY_SENSOR,
    CONF_ZONE1_HEATING_TYPE, CONF_ZONE2_HEATING_TYPE,
    CONF_BACKUP_HEATER_EXTERNAL_SWITCH, CONF_EHS_EXTERNAL_SWITCH,
    CONF_HEATING_COOLING_CHANGE_OVER_CONTACT, CONF_ON_OFF_REMOTE_CONTACT,
    CONF_DHW_REMOTE_CONTACT, CONF_DUAL_SET_POINT_CONTROL,
    CONF_THREE_WAY_MIXING_VALVE_ENTITY, CONF_DHW_THREE_WAY_VALVE_ENTITY,
    CONF_EXTERNAL_FLOW_SWITCH_ENTITY
)

_LOGGER = logging.getLogger(__name__)


class GrantAerona3Coordinator(DataUpdateCoordinator):
    """Grant Aerona3 data update coordinator with improved entity creation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.hass = hass # Store hass for external entity state access
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.slave_id = entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)

        # Retrieve system elements and linked entities from options
        self.selected_elements = entry.options.get(CONF_SYSTEM_ELEMENTS, [])
        self.linked_sensors = {
            CONF_FLOW_TEMP_SENSOR: entry.options.get(CONF_FLOW_TEMP_SENSOR),
            CONF_RETURN_TEMP_SENSOR: entry.options.get(CONF_RETURN_TEMP_SENSOR),
            CONF_OUTSIDE_TEMP_SENSOR: entry.options.get(CONF_OUTSIDE_TEMP_SENSOR),
            CONF_CYLINDER_TEMP_SENSOR: entry.options.get(CONF_CYLINDER_TEMP_SENSOR),
            CONF_BUFFER_TEMP_SENSOR: entry.options.get(CONF_BUFFER_TEMP_SENSOR),
            CONF_MIX_WATER_TEMP_SENSOR: entry.options.get(CONF_MIX_WATER_TEMP_SENSOR),
            CONF_ROOM_TEMP_SENSOR: entry.options.get(CONF_ROOM_TEMP_SENSOR),
            CONF_HUMIDITY_SENSOR: entry.options.get(CONF_HUMIDITY_SENSOR),
        }
        self.linked_controls = {
            CONF_BACKUP_HEATER_EXTERNAL_SWITCH: entry.options.get(CONF_BACKUP_HEATER_EXTERNAL_SWITCH),
            CONF_EHS_EXTERNAL_SWITCH: entry.options.get(CONF_EHS_EXTERNAL_SWITCH),
            CONF_HEATING_COOLING_CHANGE_OVER_CONTACT: entry.options.get(CONF_HEATING_COOLING_CHANGE_OVER_CONTACT),
            CONF_ON_OFF_REMOTE_CONTACT: entry.options.get(CONF_ON_OFF_REMOTE_CONTACT),
            CONF_DHW_REMOTE_CONTACT: entry.options.get(CONF_DHW_REMOTE_CONTACT),
            CONF_DUAL_SET_POINT_CONTROL: entry.options.get(CONF_DUAL_SET_POINT_CONTROL),
            CONF_THREE_WAY_MIXING_VALVE_ENTITY: entry.options.get(CONF_THREE_WAY_MIXING_VALVE_ENTITY),
            CONF_DHW_THREE_WAY_VALVE_ENTITY: entry.options.get(CONF_DHW_THREE_WAY_VALVE_ENTITY),
            CONF_EXTERNAL_FLOW_SWITCH_ENTITY: entry.options.get(CONF_EXTERNAL_FLOW_SWITCH_ENTITY),
        }

        self.zone1_heating_type = entry.options.get(CONF_ZONE1_HEATING_TYPE)
        self.zone2_heating_type = entry.options.get(CONF_ZONE2_HEATING_TYPE)

        # Detect pymodbus version for parameter compatibility
        pymodbus_version = tuple(map(int, pymodbus.__version__.split('.')[:2]))
        self._use_slave_param = pymodbus_version >= (3, 0)

        self._client = ModbusTcpClient(self.host, self.port)
        self._client.strict = False # Allow non-strict Modbus adherence

        # Store flow rate for COP calculation, default if not set
        self.flow_rate = entry.options.get("flow_rate", 28.0) # Default to 28 L/min

        _LOGGER.info("Using pymodbus %s, slave parameter: %s",
                    pymodbus.__version__, self._use_slave_param)

        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the heat pump via Modbus."""
        data = {}
        client_connected = False
        slave_kwargs = self._get_slave_kwargs()

        try:
            client_connected = await self.hass.async_add_executor(self._client.connect)
            if not client_connected:
                raise UpdateFailed(f"Failed to connect to Modbus device at {self.host}:{self.port}")

            # Read Input Registers
            input_registers_to_read = self._get_relevant_registers(INPUT_REGISTER_MAP, self.selected_elements)
            for address, config in input_registers_to_read:
                try:
                    result = await self.hass.async_add_executor(
                        self._client.read_input_registers, address=address, count=1, **slave_kwargs
                    )
                    if result.isError():
                        _LOGGER.debug("Error reading input register %d: %s", address, result)
                        data[f"input_{address}"] = {"available": False, "error": str(result)}
                    else:
                        raw_value = result.registers[0]
                        scaled_value = (raw_value * config.get("scale", 1)) + config.get("offset", 0)
                        data[f"input_{address}"] = {
                            "value": scaled_value,
                            "raw_value": raw_value,
                            "available": True,
                            "description": config["description"]
                        }
                except ModbusException as e:
                    _LOGGER.debug("Modbus exception reading input register %d: %s", address, e)
                    data[f"input_{address}"] = {"available": False, "error": str(e)}
                except Exception as e:
                    _LOGGER.warning("Unexpected error reading input register %d: %s", address, e)
                    data[f"input_{address}"] = {"available": False, "error": str(e)}

            # Read Holding Registers
            holding_registers_to_read = self._get_relevant_registers(HOLDING_REGISTER_MAP, self.selected_elements)
            for address, config in holding_registers_to_read:
                try:
                    result = await self.hass.async_add_executor(
                        self._client.read_holding_registers, address=address, count=1, **slave_kwargs
                    )
                    if result.isError():
                        _LOGGER.debug("Error reading holding register %d: %s", address, result)
                        data[f"holding_{address}"] = {"available": False, "error": str(result)}
                    else:
                        raw_value = result.registers[0]
                        scaled_value = (raw_value * config.get("scale", 1)) + config.get("offset", 0)
                        data[f"holding_{address}"] = {
                            "value": scaled_value,
                            "raw_value": raw_value,
                            "available": True,
                            "description": config["description"],
                            "writable": config.get("writable", False)
                        }
                except ModbusException as e:
                    _LOGGER.debug("Modbus exception reading holding register %d: %s", address, e)
                    data[f"holding_{address}"] = {"available": False, "error": str(e)}
                except Exception as e:
                    _LOGGER.warning("Unexpected error reading holding register %d: %s", address, e)
                    data[f"holding_{address}"] = {"available": False, "error": str(e)}

            # Read Coil Registers (for status/control)
            coil_registers_to_read = self._get_relevant_registers(COIL_REGISTER_MAP, self.selected_elements)
            for address, config in coil_registers_to_read:
                try:
                    result = await self.hass.async_add_executor(
                        self._client.read_coils, address=address, count=1, **slave_kwargs
                    )
                    if result.isError():
                        _LOGGER.debug("Error reading coil register %d: %s", address, result)
                        data[f"coil_{address}"] = {"available": False, "error": str(result)}
                    else:
                        # PyModbus returns bits as a list of booleans
                        value = result.bits[0]
                        data[f"coil_{address}"] = {
                            "value": value,
                            "available": True,
                            "description": config["description"],
                            "writable": config.get("writable", False)
                        }
                except ModbusException as e:
                    _LOGGER.debug("Modbus exception reading coil register %d: %s", address, e)
                    data[f"coil_{address}"] = {"available": False, "error": str(e)}
                except Exception as e:
                    _LOGGER.warning("Unexpected error reading coil register %d: %s", address, e)
                    data[f"coil_{address}"] = {"available": False, "error": str(e)}

        except UpdateFailed:
            raise # Re-raise if connection failed
        except Exception as e:
            _LOGGER.error("Error fetching Modbus data: %s", e)
            raise UpdateFailed(f"Error fetching Modbus data: {e}") from e
        finally:
            if client_connected:
                await self.hass.async_add_executor(self._client.close)

        # Include states of linked external Home Assistant entities
        for config_key, entity_id in self.linked_sensors.items():
            if entity_id:
                state = self.hass.states.get(entity_id)
                data[f"external_sensor_{config_key}"] = {
                    "value": state.state if state else None,
                    "available": state is not None and state.state != "unavailable",
                    "unit": getattr(state, "unit_of_measurement", None) if state else None,
                    "entity_id": entity_id
                }
                if not data[f"external_sensor_{config_key}"]["available"]:
                    _LOGGER.debug("External sensor %s (%s) is unavailable.", config_key, entity_id)

        for config_key, entity_id in self.linked_controls.items():
            if entity_id:
                state = self.hass.states.get(entity_id)
                data[f"external_control_{config_key}"] = {
                    "value": state.state if state else None,
                    "available": state is not None and state.state != "unavailable",
                    "entity_id": entity_id
                }
                if not data[f"external_control_{config_key}"]["available"]:
                    _LOGGER.debug("External control %s (%s) is unavailable.", config_key, entity_id)

        return data

    def _get_slave_kwargs(self) -> Dict[str, Any]:
        """Return slave_id argument based on pymodbus version."""
        if self._use_slave_param:
            return {"slave": self.slave_id}
        return {"unit": self.slave_id}

    async def async_write_holding_register(self, address: int, value: int) -> bool:
        """Write to a holding register."""
        return await self.hass.async_add_executor(self._write_holding_register, address, value)

    def _write_holding_register(self, address: int, value: int) -> bool:
        """Write to a holding register (runs in executor)."""
        client_connected = False
        slave_kwargs = self._get_slave_kwargs()
        try:
            client_connected = self._client.connect()
            if not client_connected:
                _LOGGER.error("Failed to connect for writing holding register %d", address)
                return False

            result = self._client.write_register(
                address=address,
                value=value,
                **slave_kwargs
            )
            if result is not None:
                success = not result.isError()
                if not success:
                    _LOGGER.error("Failed to write holding register %d: %s", address, str(result))
                return success
            else:
                _LOGGER.error("Write to holding register %d returned None", address)
                return False
        except Exception as err:
            _LOGGER.error("Exception writing holding register %d: %s", address, str(err))
            return False
        finally:
            if client_connected:
                try:
                    self._client.close()
                except Exception as close_err:
                    _LOGGER.warning("Error closing client after write: %s", str(close_err))

    async def async_write_coil(self, address: int, value: bool) -> bool:
        """Write to a coil register."""
        return await self.hass.async_add_executor(self._write_coil, address, value)

    def _write_coil(self, address: int, value: bool) -> bool:
        """Write to a coil register (runs in executor)."""
        client_connected = False
        slave_kwargs = self._get_slave_kwargs()

        try:
            client_connected = self._client.connect()
            if not client_connected:
                _LOGGER.error("Failed to connect for writing coil register %d", address)
                return False

            result = self._client.write_coil(
                address=address,
                value=value,
                **slave_kwargs
            )

            if result is not None:
                success = not result.isError()
                if not success:
                    _LOGGER.error("Failed to write coil register %d: %s", address, str(result))
                return success
            else:
                _LOGGER.error("Write to coil register %d returned None", address)
                return False

        except Exception as err:
            _LOGGER.error("Exception writing coil register %d: %s", address, str(err))
            return False
        finally:
            if client_connected:
                try:
                    self._client.close()
                except Exception as close_err:
                    _LOGGER.warning("Error closing client after write: %s", str(close_err))

    def _get_relevant_registers(self, register_map: Dict[int, Dict[str, Any]], selected_elements: list[str]) -> list[tuple[int, Dict[str, Any]]]: # Changed List to list, Tuple to tuple
        """
        Filter registers based on selected system elements in the configuration.
        This function should be updated to include more specific filtering logic
        as more system elements are added and linked to specific registers.
        """
        relevant_registers = []
        for address, config in register_map.items():
            is_relevant = True
            name_lower = config["name"].lower()

            # Example filtering logic:
            if "dhw" in name_lower and "hot_water_cylinder" not in selected_elements and \
               "anti-legionella" not in name_lower: # Anti-legionella might be relevant even if no tank
                is_relevant = False
            elif "buffer tank" in name_lower and "buffer_tank" not in selected_elements:
                is_relevant = False
            elif "cooling" in name_lower and "cooling_mode_enabled" not in selected_elements:
                is_relevant = False
            elif "backup heater" in name_lower and "backup_electric_heater" not in selected_elements:
                is_relevant = False
            elif "ehs" in name_lower and "external_heat_source_ehs" not in selected_elements:
                is_relevant = False
            elif "additional water pump" in name_lower and "additional_water_pump" not in selected_elements:
                is_relevant = False
            elif "mixing valve" in name_lower and "3way_mixing_valve_heating" not in selected_elements:
                is_relevant = False
            elif "flow switch" in name_lower and "external_flow_switch" not in selected_elements:
                 is_relevant = False
            elif "humidity" in name_lower and "humidity_sensor_present" not in selected_elements:
                 is_relevant = False
            elif "zone 2" in name_lower and "multiple_heating_zones" not in selected_elements:
                is_relevant = False
            elif "low tariff" in name_lower and "low_tariff_mode_support" not in selected_elements:
                is_relevant = False
            elif "night mode" in name_lower and "night_mode_support" not in selected_elements:
                is_relevant = False
            elif "dehumidifier" in name_lower and "dehumidifier_support" not in selected_elements:
                is_relevant = False
            # Special case for "Dual Set Point Control" which might be a workaround
            elif "dual set point" in name_lower and \
                 not ("multiple_heating_zones" in selected_elements or "dual_set_point_control_workaround" in selected_elements):
                 is_relevant = False

            # Add more specific conditions based on manual and system elements for other registers if needed.

            if is_relevant:
                relevant_registers.append((address, config))
        return relevant_registers
