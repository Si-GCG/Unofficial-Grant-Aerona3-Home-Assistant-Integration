"""Improved data update coordinator for Grant Aerona3 Heat Pump."""
import logging
from datetime import timedelta
from typing import Any, Dict, Optional # Added Optional for type hints

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
    CONF_SYSTEM_ELEMENTS, # Import new constant
    CONF_FLOW_TEMP_SENSOR, CONF_RETURN_TEMP_SENSOR, CONF_OUTSIDE_TEMP_SENSOR,
    CONF_CYLINDER_TEMP_SENSOR, CONF_BUFFER_TEMP_SENSOR, CONF_MIX_WATER_TEMP_SENSOR,
    CONF_ROOM_TEMP_SENSOR, CONF_HUMIDITY_SENSOR, CONF_ZONE1_HEATING_TYPE,
    CONF_ZONE2_HEATING_TYPE, CONF_BACKUP_HEATER_EXTERNAL_SWITCH, CONF_EHS_EXTERNAL_SWITCH,
    CONF_HEATING_COOLING_CHANGE_OVER_CONTACT, CONF_ON_OFF_REMOTE_CONTACT,
    CONF_DHW_REMOTE_CONTACT, CONF_DUAL_SET_POINT_CONTROL, CONF_THREE_WAY_MIXING_VALVE_ENTITY,
    CONF_DHW_THREE_WAY_VALVE_ENTITY, CONF_EXTERNAL_FLOW_SWITCH_ENTITY # Import all new config constants
)

_LOGGER = logging.getLogger(__name__)


class GrantAerona3Coordinator(DataUpdateCoordinator):
    """Grant Aerona3 data update coordinator with improved entity creation."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        slave_id: int,
        scan_interval: int,
        config_options: Dict[str, Any] # Added to receive the options from config_flow
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass # Store hass for later use, especially for external sensor states
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.config_options = config_options # Store the configuration options

        # Detect pymodbus version for parameter compatibility
        pymodbus_version = tuple(map(int, pymodbus.__version__.split('.')[:2]))
        self._use_slave_param = pymodbus_version >= (3, 0)

        _LOGGER.info("Using pymodbus %s, slave parameter: %s",
                    pymodbus.__version__, self._use_slave_param)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

        self._client = ModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=10
        )

        # Track which registers are available vs unavailable (already present, keep)
        self._available_registers = {
            'input': set(),
            'holding': set(),
            'coil': set()
        }

        # Flow rate for COP calculations (already present, keep)
        self.flow_rate = 20.0  # Default flow rate

        # Dictionary to hold states of linked external HA sensors
        self.external_sensor_states: Dict[str, Any] = {}

    def _get_slave_kwargs(self) -> Dict[str, int]:
        """Get the correct slave/unit parameter for the pymodbus version."""
        if self._use_slave_param:
            return {"slave": self.slave_id}
        else:
            return {"unit": self.slave_id}

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the heat pump and external sensors."""
        data = {}
        try:
            # Fetch data from the Modbus device
            modbus_data = await self.hass.async_add_executor_job(self._fetch_modbus_data)
            data.update(modbus_data)

            # Fetch data from linked external Home Assistant sensors
            self._fetch_external_sensor_states()
            data["external_sensors"] = self.external_sensor_states # Store external sensor states in data

            return data
        except Exception as err:
            _LOGGER.error("Error communicating with heat pump or fetching external sensor data: %s", err)
            # Even on error, ensure placeholder entries are created for entities
            # and external sensor states are reset to indicate unavailability.
            self._create_placeholder_entries(data) # Ensure placeholders are created even if Modbus failed
            self.external_sensor_states = {} # Clear external sensor states on update failure
            raise UpdateFailed(f"Error communicating with heat pump: {err}") from err

    def _fetch_modbus_data(self) -> Dict[str, Any]:
        """Fetch data from the heat pump Modbus (runs in executor)."""
        data = {}
        client_connected = False
        try:
            client_connected = self._client.connect()
            if not client_connected:
                raise ModbusException("Failed to connect to Modbus device")

            # Get selected system elements for conditional reading
            selected_elements = self.config_options.get(CONF_SYSTEM_ELEMENTS, [])

            # Determine which registers to read based on selected system elements
            input_registers_to_read = self._get_relevant_registers(INPUT_REGISTER_MAP, selected_elements)
            holding_registers_to_read = self._get_relevant_registers(HOLDING_REGISTER_MAP, selected_elements)
            coil_registers_to_read = self._get_relevant_registers(COIL_REGISTER_MAP, selected_elements)

            _LOGGER.debug("Input registers to read: %s", [addr for addr, _ in input_registers_to_read])
            _LOGGER.debug("Holding registers to read: %s", [addr for addr, _ in holding_registers_to_read])
            _LOGGER.debug("Coil registers to read: %s", [addr for addr, _ in coil_registers_to_read])


            # Read only relevant input registers
            input_data = self._read_input_registers(input_registers_to_read)
            data.update(input_data)

            # Read only relevant holding registers
            holding_data = self._read_holding_registers(holding_registers_to_read)
            data.update(holding_data)

            # Read only relevant coil registers
            coil_data = self._read_coil_registers(coil_registers_to_read)
            data.update(coil_data)

            # Create placeholder entries for *all* registers defined in const.py,
            # regardless of whether they were read or not. This ensures entities are created for all
            # and their 'available' state is correctly reflected.
            self._create_placeholder_entries(data)

        except Exception as err:
            _LOGGER.error("Error during Modbus data fetch: %s", str(err))
            # Critical: Ensure placeholders are created even on connection/read error
            self._create_placeholder_entries(data)
            raise # Re-raise to trigger UpdateFailed in async_update_data
        finally:
            if client_connected:
                try:
                    self._client.close()
                except Exception as close_err:
                    _LOGGER.warning("Error closing Modbus client: %s", str(close_err))

        _LOGGER.info("Successfully read %d Modbus registers out of %d total possible",
                     len(data), len(INPUT_REGISTER_MAP) + len(HOLDING_REGISTER_MAP) + len(COIL_REGISTER_MAP))
        return data

    def _get_relevant_registers(self, register_map: Dict[int, Dict[str, Any]], selected_elements: List[str]) -> List[Tuple[int, Dict[str, Any]]]:
        """Determine which registers from a map are relevant based on selected system elements."""
        relevant_registers = []
        for addr, config in register_map.items():
            # Always include core registers (e.g., general temperatures, operating mode)
            # You'll need to define what's "core" or always relevant.
            # For now, if no explicit condition, include it.
            is_relevant = True

            # Example conditional logic based on register name/description and selected elements
            name_lower = config["name"].lower()
            if "dhw" in name_lower and "hot_water_cylinder" not in selected_elements:
                is_relevant = False
            elif "buffer" in name_lower and "buffer_tank" not in selected_elements:
                is_relevant = False
            elif "mix water" in name_lower and "3way_mixing_valve_heating" not in selected_elements:
                is_relevant = False
            elif "cooling" in name_lower and "cooling_mode_enabled" not in selected_elements:
                # Include general cooling registers even if cooling mode isn't explicitly enabled,
                # if they provide diagnostic info. Adjust as needed.
                if "fixed flow temp" in name_lower or "max flow temp" in name_lower or "min flow temp" in name_lower:
                    is_relevant = False # Don't try to set cooling setpoints if not enabled
                pass
            elif "backup heater" in name_lower and "backup_electric_heater" not in selected_elements:
                is_relevant = False
            elif "ehs" in name_lower and "external_heat_source_ehs" not in selected_elements:
                is_relevant = False
            elif "additional water pump" in name_lower and "additional_water_pump" not in selected_elements:
                is_relevant = False
            elif "humidity sensor" in name_lower and "humidity_sensor_present" not in selected_elements:
                is_relevant = False
            elif "flow switch" in name_lower and "external_flow_switch" not in selected_elements:
                is_relevant = False
            elif "zone 2" in name_lower and "multiple_heating_zones" not in selected_elements:
                is_relevant = False
            # Add more conditions based on SYSTEM_ELEMENTS as needed

            if is_relevant:
                relevant_registers.append((addr, config))
        return relevant_registers

    def _create_placeholder_entries(self, data: Dict[str, Any]) -> None:
        """Create placeholder entries for registers that couldn't be read or are not relevant.
        
        This ensures all entities are created and their 'available' state is correctly reflected.
        """
        selected_elements = self.config_options.get(CONF_SYSTEM_ELEMENTS, [])
        
        # Helper to check if a register would be relevant based on selected elements
        def _is_register_conceptually_relevant(addr, config_map, elements):
            config = config_map[addr]
            name_lower = config["name"].lower()

            if "dhw" in name_lower and "hot_water_cylinder" not in elements: return False
            if "buffer" in name_lower and "buffer_tank" not in elements: return False
            if "mix water" in name_lower and "3way_mixing_valve_heating" not in elements: return False
            if "cooling" in name_lower and "cooling_mode_enabled" not in elements:
                # Still include cooling if it's a general sensor, but not if it's a setpoint for a disabled mode
                if "fixed flow temp" in name_lower or "max flow temp" in name_lower or "min flow temp" in name_lower:
                    return False
            if "backup heater" in name_lower and "backup_electric_heater" not in elements: return False
            if "ehs" in name_lower and "external_heat_source_ehs" not in elements: return False
            if "additional water pump" in name_lower and "additional_water_pump" not in elements: return False
            if "humidity sensor" in name_lower and "humidity_sensor_present" not in elements: return False
            if "flow switch" in name_lower and "external_flow_switch" not in elements: return False
            if "zone 2" in name_lower and "multiple_heating_zones" not in elements: return False
            # Add more conditions matching _get_relevant_registers here for consistency
            return True

        # Create placeholders for all possible input registers (even if not read this cycle)
        for addr, config in INPUT_REGISTER_MAP.items():
            register_key = f"input_{addr}"
            if register_key not in data: # Only add if not already successfully read
                data[register_key] = {
                    "value": None,
                    "raw_value": None,
                    "name": config.get("name", f"Input Register {addr}"),
                    "unit": config.get("unit"),
                    "device_class": config.get("device_class"),
                    "state_class": config.get("state_class"),
                    "description": config.get("description", ""),
                    "available": False, # Mark as unavailable as it wasn't read or is irrelevant
                    "error": "Register not available or not relevant to configured system."
                }
                # If a register is *conceptually* not relevant, mark it as such
                if not _is_register_conceptually_relevant(addr, INPUT_REGISTER_MAP, selected_elements):
                    data[register_key]["error"] = "Register not relevant to configured system elements."


        # Create placeholders for all possible holding registers
        for addr, config in HOLDING_REGISTER_MAP.items():
            register_key = f"holding_{addr}"
            if register_key not in data: # Only add if not already successfully read
                data[register_key] = {
                    "value": None,
                    "raw_value": None,
                    "name": config.get("name", f"Holding Register {addr}"),
                    "unit": config.get("unit"),
                    "device_class": config.get("device_class"),
                    "description": config.get("description", ""),
                    "writable": config.get("writable", False),
                    "available": False,
                    "error": "Register not available or not relevant to configured system."
                }
                if not _is_register_conceptually_relevant(addr, HOLDING_REGISTER_MAP, selected_elements):
                    data[register_key]["error"] = "Register not relevant to configured system elements."

        # Create placeholders for all possible coil registers
        for addr, config in COIL_REGISTER_MAP.items():
            register_key = f"coil_{addr}"
            if register_key not in data: # Only add if not already successfully read
                data[register_key] = {
                    "value": False,  # Default to False for coils that aren't read
                    "name": config.get("name", f"Coil Register {addr}"),
                    "description": config.get("description", ""),
                    "available": False,
                    "error": "Register not available or not relevant to configured system."
                }
                if not _is_register_conceptually_relevant(addr, COIL_REGISTER_MAP, selected_elements):
                    data[register_key]["error"] = "Register not relevant to configured system elements."

    def _read_input_registers(self, registers_to_read: List[Tuple[int, Dict[str, Any]]]) -> Dict[str, Any]:
        """Read a subset of input registers."""
        data = {}
        slave_kwargs = self._get_slave_kwargs()

        for addr, config in registers_to_read:
            try:
                result = self._client.read_input_registers(
                    address=addr,
                    count=1,
                    **slave_kwargs
                )

                if result is not None and not result.isError():
                    raw_value = result.registers[0]

                    # Handle signed values
                    if raw_value > 32767: # Max value for 16-bit unsigned int
                        raw_value = raw_value - 65536 # Convert to signed 16-bit

                    scale = config.get("scale", 1)
                    scaled_value = raw_value * scale

                    data[f"input_{addr}"] = {
                        "value": scaled_value,
                        "raw_value": result.registers[0],
                        "name": config.get("name", f"Input Register {addr}"),
                        "unit": config.get("unit"),
                        "device_class": config.get("device_class"),
                        "state_class": config.get("state_class"),
                        "description": config.get("description", ""),
                        "available": True
                    }
                    self._available_registers['input'].add(addr)
                elif result is not None:
                    _LOGGER.debug("Input register %d (%s) not available: %s",
                                addr, config.get("name", f"Register {addr}"), str(result))
                else:
                    _LOGGER.debug("Input register %d (%s) read returned None",
                                addr, config.get("name", f"Register {addr}"))

            except Exception as err:
                _LOGGER.debug("Error reading input register %d (%s): %s",
                            addr, config.get("name", f"Register {addr}"), str(err))
                # Continue even if one register fails
                continue

        _LOGGER.info("Attempted to read %d input registers, %d successful.",
                     len(registers_to_read), len(data))
        return data

    def _read_holding_registers(self, registers_to_read: List[Tuple[int, Dict[str, Any]]]) -> Dict[str, Any]:
        """Read a subset of holding registers."""
        data = {}
        slave_kwargs = self._get_slave_kwargs()

        for addr, config in registers_to_read:
            try:
                result = self._client.read_holding_registers(
                    address=addr,
                    count=1,
                    **slave_kwargs
                )

                if result is not None and not result.isError():
                    raw_value = result.registers[0]

                    # Handle signed values
                    if raw_value > 32767:
                        raw_value = raw_value - 65536

                    scale = config.get("scale", 1)
                    scaled_value = raw_value * scale

                    data[f"holding_{addr}"] = {
                        "value": scaled_value,
                        "raw_value": result.registers[0],
                        "name": config.get("name", f"Holding Register {addr}"),
                        "unit": config.get("unit"),
                        "device_class": config.get("device_class"),
                        "description": config.get("description", ""),
                        "writable": config.get("writable", False),
                        "available": True
                    }
                    self._available_registers['holding'].add(addr)
                elif result is not None:
                    _LOGGER.debug("Holding register %d (%s) not available: %s",
                                addr, config.get("name", f"Register {addr}"), str(result))
                else:
                    _LOGGER.debug("Holding register %d (%s) read returned None",
                                addr, config.get("name", f"Register {addr}"))

            except Exception as err:
                _LOGGER.debug("Error reading holding register %d (%s): %s",
                            addr, config.get("name", f"Register {addr}"), str(err))
                continue

        _LOGGER.info("Attempted to read %d holding registers, %d successful.",
                     len(registers_to_read), len(data))
        return data

    def _read_coil_registers(self, registers_to_read: List[Tuple[int, Dict[str, Any]]]) -> Dict[str, Any]:
        """Read a subset of coil registers."""
        data = {}
        slave_kwargs = self._get_slave_kwargs()

        for addr, config in registers_to_read:
            try:
                result = self._client.read_coils(
                    address=addr,
                    count=1,
                    **slave_kwargs
                )

                if result is not None and not result.isError():
                    data[f"coil_{addr}"] = {
                        "value": result.bits[0],
                        "name": config.get("name", f"Coil Register {addr}"),
                        "description": config.get("description", ""),
                        "available": True
                    }
                    self._available_registers['coil'].add(addr)
                elif result is not None:
                    _LOGGER.debug("Coil register %d (%s) not available: %s",
                                addr, config.get("name", f"Register {addr}"), str(result))
                else:
                    _LOGGER.debug("Coil register %d (%s) read returned None",
                                addr, config.get("name", f"Register {addr}"))

            except Exception as err:
                _LOGGER.debug("Error reading coil register %d (%s): %s",
                            addr, config.get("name", f"Register {addr}"), str(err))
                continue

        _LOGGER.info("Attempted to read %d coil registers, %d successful.",
                     len(registers_to_read), len(data))
        return data

    def _fetch_external_sensor_states(self) -> None:
        """Fetch states of external Home Assistant sensors linked in configuration."""
        self.external_sensor_states = {} # Clear previous states
        # Loop through all sensor entity IDs defined in config_options
        linked_sensors = {
            CONF_FLOW_TEMP_SENSOR: self.config_options.get(CONF_FLOW_TEMP_SENSOR),
            CONF_RETURN_TEMP_SENSOR: self.config_options.get(CONF_RETURN_TEMP_SENSOR),
            CONF_OUTSIDE_TEMP_SENSOR: self.config_options.get(CONF_OUTSIDE_TEMP_SENSOR),
            CONF_CYLINDER_TEMP_SENSOR: self.config_options.get(CONF_CYLINDER_TEMP_SENSOR),
            CONF_BUFFER_TEMP_SENSOR: self.config_options.get(CONF_BUFFER_TEMP_SENSOR),
            CONF_MIX_WATER_TEMP_SENSOR: self.config_options.get(CONF_MIX_WATER_TEMP_SENSOR),
            CONF_ROOM_TEMP_SENSOR: self.config_options.get(CONF_ROOM_TEMP_SENSOR),
            CONF_HUMIDITY_SENSOR: self.config_options.get(CONF_HUMIDITY_SENSOR),
            # Add other external control entities if their state needs to be known by coordinator
            CONF_BACKUP_HEATER_EXTERNAL_SWITCH: self.config_options.get(CONF_BACKUP_HEATER_EXTERNAL_SWITCH),
            CONF_EHS_EXTERNAL_SWITCH: self.config_options.get(CONF_EHS_EXTERNAL_SWITCH),
            CONF_HEATING_COOLING_CHANGE_OVER_CONTACT: self.config_options.get(CONF_HEATING_COOLING_CHANGE_OVER_CONTACT),
            CONF_ON_OFF_REMOTE_CONTACT: self.config_options.get(CONF_ON_OFF_REMOTE_CONTACT),
            CONF_DHW_REMOTE_CONTACT: self.config_options.get(CONF_DHW_REMOTE_CONTACT),
            CONF_DUAL_SET_POINT_CONTROL: self.config_options.get(CONF_DUAL_SET_POINT_CONTROL),
            CONF_THREE_WAY_MIXING_VALVE_ENTITY: self.config_options.get(CONF_THREE_WAY_MIXING_VALVE_ENTITY),
            CONF_DHW_THREE_WAY_VALVE_ENTITY: self.config_options.get(CONF_DHW_THREE_WAY_VALVE_ENTITY),
            CONF_EXTERNAL_FLOW_SWITCH_ENTITY: self.config_options.get(CONF_EXTERNAL_FLOW_SWITCH_ENTITY),
        }

        for config_key, entity_id in linked_sensors.items():
            if entity_id: # If an entity ID is configured for this sensor
                state = self.hass.states.get(entity_id)
                if state:
                    try:
                        # Attempt to convert to float if it's a numeric sensor, otherwise store as is
                        value = float(state.state) if state.state.replace('.', '', 1).isdigit() else state.state
                        self.external_sensor_states[config_key] = {
                            "value": value,
                            "last_updated": state.last_updated,
                            "available": True,
                            "entity_id": entity_id
                        }
                    except ValueError:
                        self.external_sensor_states[config_key] = {
                            "value": state.state,
                            "last_updated": state.last_updated,
                            "available": True,
                            "entity_id": entity_id
                        }
                        _LOGGER.warning("Could not convert state '%s' for external sensor %s to float.", state.state, entity_id)
                else:
                    self.external_sensor_states[config_key] = {
                        "value": None,
                        "last_updated": None,
                        "available": False,
                        "entity_id": entity_id,
                        "error": "Entity state not found in Home Assistant."
                    }
                    _LOGGER.debug("External sensor entity %s not found in Home Assistant states.", entity_id)
            else:
                self.external_sensor_states[config_key] = {
                    "value": None,
                    "available": False,
                    "entity_id": None,
                    "error": "No entity configured for this sensor."
                }


    async def async_write_holding_register(self, address: int, value: int) -> bool:
        """Write to a holding register."""
        try:
            return await self.hass.async_add_executor_job(
                self._write_holding_register, address, value
            )
        except Exception as err:
            _LOGGER.error("Error writing holding register %s: %s", address, err)
            return False

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
        try:
            return await self.hass.async_add_executor_job(
                self._write_coil, address, value
            )
        except Exception as err:
            _LOGGER.error("Error writing coil register %d: %s", address, str(err))
            return False

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
