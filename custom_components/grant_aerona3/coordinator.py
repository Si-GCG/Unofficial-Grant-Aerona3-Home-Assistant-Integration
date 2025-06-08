"""Improved data update coordinator for Grant Aerona3 Heat Pump."""
import logging
from datetime import timedelta
from typing import Any, Dict

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
)

_LOGGER = logging.getLogger(__name__)


class GrantAerona3Coordinator(DataUpdateCoordinator):
    """Grant Aerona3 data update coordinator with improved entity creation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.slave_id = entry.data[CONF_SLAVE_ID]

        # Detect pymodbus version for parameter compatibility
        pymodbus_version = tuple(map(int, pymodbus.__version__.split('.')[:2]))
        self._use_slave_param = pymodbus_version >= (3, 0)

        _LOGGER.info("Using pymodbus %s, slave parameter: %s",
                    pymodbus.__version__, self._use_slave_param)

        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

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

        # Track which registers are available vs unavailable
        self._available_registers = {
            'input': set(),
            'holding': set(),
            'coil': set()
        }
        
        # Flow rate for COP calculations
        self.flow_rate = 20.0  # Default flow rate

    def _get_slave_kwargs(self) -> Dict[str, int]:
        """Get the correct slave/unit parameter for the pymodbus version."""
        if self._use_slave_param:
            return {"slave": self.slave_id}
        else:
            return {"unit": self.slave_id}

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the heat pump."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_data)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with heat pump: {err}") from err

    def _fetch_data(self) -> Dict[str, Any]:
        """Fetch data from the heat pump (runs in executor)."""
        data = {}

        # Use context manager for automatic client cleanup
        client_connected = False
        try:
            client_connected = self._client.connect()
            if not client_connected:
                raise ModbusException("Failed to connect to Modbus device")

            # Read all input registers
            input_data = self._read_input_registers()
            data.update(input_data)

            # Read all holding registers with improved error handling
            holding_data = self._read_holding_registers_bulk()
            data.update(holding_data)

            # Read all coil registers
            coil_data = self._read_coil_registers_bulk()
            data.update(coil_data)

            # CRITICAL FIX: Create placeholder entries for unavailable registers
            # This ensures entities are still created even if registers can't be read
            self._create_placeholder_entries(data)

        except Exception as err:
            _LOGGER.error("Error during data fetch: %s", str(err))
            # Even on error, create placeholder entries so entities can be created
            self._create_placeholder_entries(data)
            raise
        finally:
            # Ensure client is always closed, even if connect() failed
            if client_connected:
                try:
                    self._client.close()
                except Exception as close_err:
                    _LOGGER.warning("Error closing Modbus client: %s", str(close_err))

        _LOGGER.info("Successfully read %d total registers", len(data))
        return data

    def _create_placeholder_entries(self, data: Dict[str, Any]) -> None:
        """Create placeholder entries for registers that couldn't be read.
        
        This ensures all entities are created even if some registers are unavailable.
        """
        # Create placeholders for missing input registers
        for addr, config in INPUT_REGISTER_MAP.items():
            register_key = f"input_{addr}"
            if register_key not in data:
                data[register_key] = {
                    "value": None,
                    "raw_value": None,
                    "name": config.get("name", f"Input Register {addr}"),
                    "unit": config.get("unit"),
                    "device_class": config.get("device_class"),
                    "state_class": config.get("state_class"),
                    "description": config.get("description", ""),
                    "available": False,
                    "error": "Register not available"
                }

        # Create placeholders for missing holding registers
        for addr, config in HOLDING_REGISTER_MAP.items():
            register_key = f"holding_{addr}"
            if register_key not in data:
                data[register_key] = {
                    "value": None,
                    "raw_value": None,
                    "name": config.get("name", f"Holding Register {addr}"),
                    "unit": config.get("unit"),
                    "device_class": config.get("device_class"),
                    "description": config.get("description", ""),
                    "writable": config.get("writable", False),
                    "available": False,
                    "error": "Register not available"
                }

        # Create placeholders for missing coil registers
        for addr, config in COIL_REGISTER_MAP.items():
            register_key = f"coil_{addr}"
            if register_key not in data:
                data[register_key] = {
                    "value": False,  # Default to False for coils
                    "name": config.get("name", f"Coil Register {addr}"),
                    "description": config.get("description", ""),
                    "available": False,
                    "error": "Register not available"
                }

    def _read_input_registers(self) -> Dict[str, Any]:
        """Read all input registers."""
        data = {}
        slave_kwargs = self._get_slave_kwargs()

        # Read input registers individually to avoid index mapping issues
        for addr, config in INPUT_REGISTER_MAP.items():
            try:
                result = self._client.read_input_registers(
                    address=addr,
                    count=1,
                    **slave_kwargs
                )

                if result is not None and not result.isError():
                    raw_value = result.registers[0]  # Always use index 0 for single register reads

                    # Handle signed values (temperature can be negative)
                    if raw_value > 32767:
                        raw_value = raw_value - 65536

                    # Apply scaling from const.py with safe config access
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
                continue

        _LOGGER.info("Successfully read %d input registers", len(data))
        return data

    def _read_holding_registers_bulk(self) -> Dict[str, Any]:
        """Read holding registers individually with robust error handling."""
        data = {}
        successful_reads = 0
        failed_reads = 0
        slave_kwargs = self._get_slave_kwargs()

        # Read each holding register individually to avoid bulk read failures
        for addr, config in HOLDING_REGISTER_MAP.items():
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

                    # Apply scaling from const.py with safe config access
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
                    successful_reads += 1
                elif result is not None:
                    _LOGGER.debug("Holding register %d (%s) not available: %s",
                                addr, config.get("name", f"Register {addr}"), str(result))
                    failed_reads += 1
                else:
                    _LOGGER.debug("Holding register %d (%s) read returned None",
                                addr, config.get("name", f"Register {addr}"))
                    failed_reads += 1

            except Exception as err:
                _LOGGER.debug("Error reading holding register %d (%s): %s",
                            addr, config.get("name", f"Register {addr}"), str(err))
                failed_reads += 1
                continue

        _LOGGER.info("Successfully read %d holding registers (%d failed/unavailable)",
                    successful_reads, failed_reads)
        return data

    def _read_coil_registers_bulk(self) -> Dict[str, Any]:
        """Read coil registers individually with robust error handling."""
        data = {}
        successful_reads = 0
        failed_reads = 0
        slave_kwargs = self._get_slave_kwargs()

        # Read each coil register individually to avoid bulk read failures
        for addr, config in COIL_REGISTER_MAP.items():
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
                    successful_reads += 1
                elif result is not None:
                    _LOGGER.debug("Coil register %d (%s) not available: %s",
                                addr, config.get("name", f"Register {addr}"), str(result))
                    failed_reads += 1
                else:
                    _LOGGER.debug("Coil register %d (%s) read returned None",
                                addr, config.get("name", f"Register {addr}"))
                    failed_reads += 1

            except Exception as err:
                _LOGGER.debug("Error reading coil register %d (%s): %s",
                            addr, config.get("name", f"Register {addr}"), str(err))
                failed_reads += 1
                continue

        _LOGGER.info("Successfully read %d coil registers (%d failed/unavailable)",
                    successful_reads, failed_reads)
        return data

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