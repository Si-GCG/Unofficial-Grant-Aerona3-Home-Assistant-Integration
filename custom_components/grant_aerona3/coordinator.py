from __future__ import annotations
# custom_components/grant_aerona3/coordinator.py
import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Dict

from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ModbusException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_UNIT_ID,
    CONF_SCAN_INTERVAL,
    INPUT_REGISTER_MAP,
    HOLDING_REGISTER_MAP,
    COIL_REGISTER_MAP,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

class GrantAerona3Coordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Coordinator for Grant Aerona3 Heat Pump."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.connection_type = entry.data.get("connection_type", "tcp")
        self.host = entry.data.get(CONF_HOST)
        self.port = entry.data.get(CONF_PORT)
        self.serial_port = entry.data.get("serial_port")
        self.baudrate = entry.data.get("baudrate")
        self.bytesize = entry.data.get("bytesize")
        self.method = entry.data.get("method")
        self.parity = entry.data.get("parity")
        self.stopbits = entry.data.get("stopbits")
        self.unit_id = entry.data[CONF_UNIT_ID]
        # Use options if present, else data, else default
        scan_interval = (
            entry.options.get(CONF_SCAN_INTERVAL)
            if hasattr(entry, "options") and entry.options.get(CONF_SCAN_INTERVAL) is not None
            else entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        flow_rate_lpm = (
            entry.options.get("flow_rate_lpm")
            if hasattr(entry, "options") and entry.options.get("flow_rate_lpm") is not None
            else entry.data.get("flow_rate_lpm", 34.0)
        )
        self.flow_rate_lpm = flow_rate_lpm

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        # Create a persistent client reference (not always used; per-fetch clients created)
        if self.connection_type == "tcp":
            self._client = ModbusTcpClient(host=self.host, port=self.port, timeout=10)
        else:
            self._client = ModbusSerialClient(
                method=self.method,
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=10,
            )

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await asyncio.wait_for(self._fetch_data(), timeout=180.0)
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to ASHP at {self.host}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with ASHP: {err}") from err

    async def _fetch_data(self) -> Dict[str, Any]:
        data = {
            "input_registers": {},
            "holding_registers": {},
            "coil_registers": {},
            "last_update": time.monotonic(),
        }
        
        # Create a fresh client for each fetch to avoid connection issues
        if self.connection_type == "tcp":
            client = ModbusTcpClient(host=self.host, port=self.port, timeout=5)
        else:
            client = ModbusSerialClient(
                method=self.method,
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=5,
            )
        
        try:
            # Connect with timeout
            connected = await asyncio.wait_for(
                self.hass.async_add_executor_job(client.connect), 
                timeout=30.0
            )
            if not connected:
                raise UpdateFailed(f"Failed to connect to ASHP at {self.host}:{self.port}")
            
            # Read data with individual timeouts
            data["input_registers"] = await self._read_input_registers(client)
            data["holding_registers"] = await self._read_holding_registers(client)
            data["coil_registers"] = await self._read_coil_registers(client)
            data["calculated"] = self._calculate_derived_values(
                data["input_registers"], data["holding_registers"]
            )
            
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout during Modbus operation: %s", err)
            raise UpdateFailed(f"Timeout during Modbus operation: {err}") from err
        except ModbusException as err:
            _LOGGER.error("Modbus error: %s", err)
            raise UpdateFailed(f"Modbus communication error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err
        finally:
            try:
                await self.hass.async_add_executor_job(client.close)
            except Exception:
                pass
        return data

    async def _read_input_registers(self, client: object) -> Dict[int, float]:
        input_data = {}
        
        # Read only the most critical registers first to test connectivity
        critical_registers = [0, 1, 3, 6, 9]  # Return temp, frequency, power, outdoor temp, flow temp
        
        for reg_id in critical_registers:
            if reg_id in INPUT_REGISTER_MAP:
                try:
                    result = await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            lambda reg=reg_id: client.read_input_registers(reg, count=1, device_id=self.unit_id)
                        ),
                        timeout=3.0
                    )
                    if not result.isError():
                        raw_value = result.registers[0]
                        # Handle signed 16-bit values
                        if raw_value > 32767:
                            raw_value = raw_value - 65536
                        input_data[reg_id] = raw_value
                    else:
                        _LOGGER.debug("Error reading input register %d: %s", reg_id, result)
                except Exception as err:
                    _LOGGER.debug("Failed to read input register %d: %s", reg_id, err)
        
        # If critical registers work, try reading the rest
        if input_data:
            remaining_registers = [reg for reg in INPUT_REGISTER_MAP.keys() if reg not in critical_registers]
            for reg_id in remaining_registers:
                try:
                    result = await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            lambda reg=reg_id: client.read_input_registers(reg, count=1, device_id=self.unit_id)
                        ),
                        timeout=2.0
                    )
                    if not result.isError():
                        raw_value = result.registers[0]
                        if raw_value > 32767:
                            raw_value = raw_value - 65536
                        input_data[reg_id] = raw_value
                except Exception as err:
                    _LOGGER.debug("Failed to read input register %d: %s", reg_id, err)
                    continue  # Continue with other registers
        
        return input_data

    async def _read_holding_registers(self, client: object) -> Dict[int, float]:
        holding_data = {}
        
        # Get all writable registers from the map - these are the ones we need for number entities
        writable_registers = [reg_id for reg_id, config in HOLDING_REGISTER_MAP.items() if config.get("writable", False)]
        
        _LOGGER.debug("Reading %d writable holding registers: %s", len(writable_registers), writable_registers)
        
        # Read registers in smaller batches to avoid overwhelming the device
        batch_size = 5
        for i in range(0, len(writable_registers), batch_size):
            batch = writable_registers[i:i + batch_size]
            
            for reg_id in batch:
                try:
                    result = await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            lambda reg=reg_id: client.read_holding_registers(reg, count=1, device_id=self.unit_id)
                        ),
                        timeout=2.0
                    )
                    if not result.isError():
                        raw_value = result.registers[0]
                        if raw_value > 32767:
                            raw_value = raw_value - 65536
                        holding_data[reg_id] = raw_value
                        _LOGGER.debug("Successfully read register %d: %d", reg_id, raw_value)
                    else:
                        _LOGGER.debug("Error reading holding register %d: %s", reg_id, result)
                except Exception as err:
                    _LOGGER.debug("Failed to read holding register %d: %s", reg_id, err)
            
            # Small delay between batches to avoid overwhelming the device
            if i + batch_size < len(writable_registers):
                await asyncio.sleep(0.1)
        
        _LOGGER.info("Successfully read %d/%d holding registers", len(holding_data), len(writable_registers))
        return holding_data

    async def _read_coil_registers(self, client: object) -> Dict[int, bool]:
        coil_data = {}
        
        # Read only a few critical coils to avoid timeouts
        critical_coils = [2, 3, 6, 7, 18]  # Weather compensation zone1/zone2 and key settings
        
        for reg_id in critical_coils:
            if reg_id in COIL_REGISTER_MAP:
                try:
                    result = await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            lambda reg=reg_id: client.read_coils(reg, count=1, device_id=self.unit_id)
                        ),
                        timeout=2.0
                    )
                    if not result.isError():
                        coil_data[reg_id] = result.bits[0]
                    else:
                        _LOGGER.debug("Error reading coil register %d: %s", reg_id, result)
                except Exception as err:
                    _LOGGER.debug("Failed to read coil register %d: %s", reg_id, err)
        
        return coil_data

    def _calculate_derived_values(self, input_data: Dict[int, float], holding_data: Dict[int, float]) -> Dict[str, Any]:
        calculated = {}
        try:
            flow_temp = input_data.get(9)  # Outgoing Water Temperature (°C)
            return_temp = input_data.get(0)  # Return Water Temperature (°C)
            power_w = input_data.get(3, 0) * 100  # Power in W (register 3, scale 100)
            flow_rate_lph = self.flow_rate_lpm * 60

            if (
                flow_temp is not None
                and return_temp is not None
                and power_w > 0
                and flow_rate_lph > 0
            ):
                delta_t = flow_temp - return_temp
                heat_output_w = flow_rate_lph * 1.16 * delta_t
                cop = heat_output_w / power_w if power_w > 0 else 0
                calculated["cop"] = round(cop, 2)
                calculated["heat_output_w"] = round(heat_output_w, 1)
                calculated["delta_t"] = round(delta_t, 2)
        except Exception as err:
            _LOGGER.warning("Error calculating derived values: %s", err)
        return calculated

    async def async_write_register(self, register: int, value: int) -> bool:
        """Write to a holding register."""
        if self.connection_type == "tcp":
            client = ModbusTcpClient(host=self.host, port=self.port, timeout=5)
        else:
            client = ModbusSerialClient(
                method=self.method,
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=5,
            )
        
        try:
            connected = await asyncio.wait_for(
                self.hass.async_add_executor_job(client.connect),
                timeout=10.0
            )
            if not connected:
                _LOGGER.error("Failed to connect for writing register %d", register)
                return False
            
            result = await asyncio.wait_for(
                self.hass.async_add_executor_job(
                    lambda: client.write_register(register, value, device_id=self.unit_id)
                ),
                timeout=5.0
            )
            
            if result.isError():
                _LOGGER.error("Error writing register %d: %s", register, result)
                return False
            
            _LOGGER.info("Successfully wrote value %d to register %d", value, register)
            await self.async_request_refresh()
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to write register %d: %s", register, err)
            return False
        finally:
            try:
                await self.hass.async_add_executor_job(client.close)
            except Exception:
                pass

    async def async_write_coil(self, address: int, value: bool) -> bool:
        """Write to a coil register."""
        # Create a fresh client like async_write_register does
        if self.connection_type == "tcp":
            client = ModbusTcpClient(host=self.host, port=self.port, timeout=5)
        else:
            client = ModbusSerialClient(
                method=self.method,
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=5,
            )
        
        try:
            connected = await asyncio.wait_for(
                self.hass.async_add_executor_job(client.connect),
                timeout=10.0
            )
            if not connected:
                _LOGGER.error("Failed to connect for writing coil %d", address)
                return False
            
            result = await asyncio.wait_for(
                self.hass.async_add_executor_job(
                    lambda: client.write_coil(address, value, device_id=self.unit_id)
                ),
                timeout=5.0
            )
            
            if result.isError():
                _LOGGER.error("Error writing coil %d: %s", address, result)
                return False
            
            _LOGGER.info("Successfully wrote value %s to coil %d", value, address)
            await self.async_request_refresh()
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to write coil %d: %s", address, err)
            return False
        finally:
            try:
                await self.hass.async_add_executor_job(client.close)
            except Exception:
                pass
