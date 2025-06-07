"""Simplified data update coordinator for Grant Aerona3 Heat Pump."""
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

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
    """Grant Aerona3 data update coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.slave_id = entry.data[CONF_SLAVE_ID]
        
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

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the heat pump."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_data)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with heat pump: {err}") from err

    def _fetch_data(self) -> Dict[str, Any]:
        """Fetch data from the heat pump (runs in executor)."""
        data = {}
        
        try:
            if not self._client.connect():
                raise ModbusException("Failed to connect to Modbus device")

            # Read all input registers
            input_data = self._read_input_registers()
            data.update(input_data)

            # Read all holding registers
            holding_data = self._read_holding_registers()
            data.update(holding_data)

            # Read all coil registers
            coil_data = self._read_coil_registers()
            data.update(coil_data)

        finally:
            self._client.close()

        return data

    def _read_input_registers(self) -> Dict[str, Any]:
        """Read all input registers."""
        data = {}
        
        # Read input registers 0-32 in blocks
        try:
            # Read registers 0-18 (first block)
            result = self._client.read_input_registers(
                address=0,
                count=19,
                slave=self.slave_id
            )
            
            if not result.isError():
                for addr, config in INPUT_REGISTER_MAP.items():
                    if addr < len(result.registers):
                        raw_value = result.registers[addr]
                        
                        # Handle signed values (temperature can be negative)
                        if raw_value > 32767:
                            raw_value = raw_value - 65536
                        
                        # Apply scaling from const.py
                        scaled_value = raw_value * config["scale"]
                        
                        data[f"input_{addr}"] = {
                            "value": scaled_value,
                            "raw_value": result.registers[addr],
                            "name": config["name"],
                            "unit": config["unit"],
                            "device_class": config["device_class"],
                            "state_class": config.get("state_class"),
                            "description": config.get("description", "")
                        }
            
            # Read register 32 (Plate Heat Exchanger Temperature)
            if 32 in INPUT_REGISTER_MAP:
                result = self._client.read_input_registers(
                    address=32,
                    count=1,
                    slave=self.slave_id
                )
                
                if not result.isError():
                    config = INPUT_REGISTER_MAP[32]
                    raw_value = result.registers[0]
                    
                    if raw_value > 32767:
                        raw_value = raw_value - 65536
                    
                    scaled_value = raw_value * config["scale"]
                    
                    data["input_32"] = {
                        "value": scaled_value,
                        "raw_value": result.registers[0],
                        "name": config["name"],
                        "unit": config["unit"],
                        "device_class": config["device_class"],
                        "state_class": config.get("state_class"),
                        "description": config.get("description", "")
                    }
                    
        except Exception as err:
            _LOGGER.error("Error reading input registers: %s", err)
            
        return data

    def _read_holding_registers(self) -> Dict[str, Any]:
        """Read all holding registers."""
        data = {}
        
        # Read each holding register individually
        for addr, config in HOLDING_REGISTER_MAP.items():
            try:
                result = self._client.read_holding_registers(
                    address=addr,
                    count=1,
                    slave=self.slave_id
                )
                
                if not result.isError():
                    raw_value = result.registers[0]
                    
                    # Handle signed values
                    if raw_value > 32767:
                        raw_value = raw_value - 65536
                    
                    # Apply scaling from const.py
                    scaled_value = raw_value * config["scale"]
                    
                    data[f"holding_{addr}"] = {
                        "value": scaled_value,
                        "raw_value": result.registers[0],
                        "name": config["name"],
                        "unit": config["unit"],
                        "device_class": config.get("device_class"),
                        "description": config.get("description", ""),
                        "writable": config.get("writable", False)
                    }
                    
            except Exception as err:
                _LOGGER.error("Error reading holding register %s: %s", addr, err)
                
        return data

    def _read_coil_registers(self) -> Dict[str, Any]:
        """Read all coil registers."""
        data = {}
        
        # Read each coil register individually
        for addr, config in COIL_REGISTER_MAP.items():
            try:
                result = self._client.read_coils(
                    address=addr,
                    count=1,
                    slave=self.slave_id
                )
                
                if not result.isError():
                    data[f"coil_{addr}"] = {
                        "value": result.bits[0],
                        "name": config["name"],
                        "description": config["description"]
                    }
                    
            except Exception as err:
                _LOGGER.error("Error reading coil register %s: %s", addr, err)
                
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
        try:
            if not self._client.connect():
                return False
                
            result = self._client.write_register(
                address=address,
                value=value,
                slave=self.slave_id
            )
            
            return not result.isError()
            
        finally:
            self._client.close()

    async def async_write_coil(self, address: int, value: bool) -> bool:
        """Write to a coil register."""
        try:
            return await self.hass.async_add_executor_job(
                self._write_coil, address, value
            )
        except Exception as err:
            _LOGGER.error("Error writing coil register %s: %s", address, err)
            return False

    def _write_coil(self, address: int, value: bool) -> bool:
        """Write to a coil register (runs in executor)."""
        try:
            if not self._client.connect():
                return False
                
            result = self._client.write_coil(
                address=address,
                value=value,
                slave=self.slave_id
            )
            
            return not result.isError()
            
        finally:
            self._client.close()