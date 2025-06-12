"""DataUpdateCoordinator for Grant Aerona3 Heat Pump."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    INPUT_REGISTER_MAP,
    HOLDING_REGISTER_MAP,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class GrantAerona3Coordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Grant Aerona3 Heat Pump."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.slave_id = entry.data[CONF_SLAVE_ID]
        
        # Get scan interval, with fallback
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        
        self._client = ModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=10,
            retry_on_empty=True,
            retries=3,
        )
        
        _LOGGER.info(
            "Initialized ASHP coordinator for %s:%s (scan interval: %s seconds)",
            self.host,
            self.port,
            scan_interval
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from heat pump."""
        try:
            return await asyncio.wait_for(self._fetch_data(), timeout=30.0)
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to ASHP at {self.host}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with ASHP: {err}") from err

    async def _fetch_data(self) -> Dict[str, Any]:
        """Fetch all data from the heat pump."""
        data = {
            "input_registers": {},
            "holding_registers": {},
            "coil_registers": {},
            "last_update": self.hass.loop.time(),
        }

        try:
            # Connect to the heat pump
            connected = await self.hass.async_add_executor_job(self._client.connect)
            if not connected:
                raise UpdateFailed(f"Failed to connect to ASHP at {self.host}:{self.port}")

            # Read input registers (sensor data)
            input_data = await self._read_input_registers()
            data["input_registers"] = input_data

            # Read holding registers (configuration)
            holding_data = await self._read_holding_registers()
            data["holding_registers"] = holding_data

            # Add some calculated values
            data["calculated"] = self._calculate_derived_values(input_data, holding_data)

            _LOGGER.debug(
                "Successfully read %d input registers and %d holding registers from ASHP",
                len(input_data),
                len(holding_data)
            )

        except ModbusException as err:
            _LOGGER.error("Modbus error reading from ASHP: %s", err)
            raise UpdateFailed(f"Modbus communication error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error reading from ASHP: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err
        finally:
            # Always close the connection
            try:
                await self.hass.async_add_executor_job(self._client.close)
            except Exception:
                pass  # Ignore close errors

        return data

    async def _read_input_registers(self) -> Dict[int, float]:
        """Read all input registers."""
        input_data = {}
        
        # Read registers in chunks to avoid timeouts
        chunk_size = 20
        register_ids = list(INPUT_REGISTER_MAP.keys())
        
        for i in range(0, len(register_ids), chunk_size):
            chunk = register_ids[i:i + chunk_size]
            if not chunk:
                continue
                
            start_reg = min(chunk)
            end_reg = max(chunk)
            count = end_reg - start_reg + 1
            
            try:
                result = await self.hass.async_add_executor_job(
                    self._client.read_input_registers,
                    start_reg,
                    count,
                    self.slave_id
                )
                
                if not result.isError():
                    for j, reg_id in enumerate(range(start_reg, end_reg + 1)):
                        if reg_id in INPUT_REGISTER_MAP and j < len(result.registers):
                            input_data[reg_id] = result.registers[j]
                else:
                    _LOGGER.warning("Error reading input registers %d-%d: %s", start_reg, end_reg, result)
                    
            except Exception as err:
                _LOGGER.warning("Failed to read input registers %d-%d: %s", start_reg, end_reg, err)
                
        return input_data

    async def _read_holding_registers(self) -> Dict[int, float]:
        """Read all holding registers."""
        holding_data = {}
        
        # Read registers in chunks
        chunk_size = 20
        register_ids = list(HOLDING_REGISTER_MAP.keys())
        
        for i in range(0, len(register_ids), chunk_size):
            chunk = register_ids[i:i + chunk_size]
            if not chunk:
                continue
                
            start_reg = min(chunk)
            end_reg = max(chunk)
            count = end_reg - start_reg + 1
            
            try:
                result = await self.hass.async_add_executor_job(
                    self._client.read_holding_registers,
                    start_reg,
                    count,
                    self.slave_id
                )
                
                if not result.isError():
                    for j, reg_id in enumerate(range(start_reg, end_reg + 1)):
                        if reg_id in HOLDING_REGISTER_MAP and j < len(result.registers):
                            holding_data[reg_id] = result.registers[j]
                else:
                    _LOGGER.warning("Error reading holding registers %d-%d: %s", start_reg, end_reg, result)
                    
            except Exception as err:
                _LOGGER.warning("Failed to read holding registers %d-%d: %s", start_reg, end_reg, err)
                
        return holding_data

    def _calculate_derived_values(self, input_data: Dict[int, float], holding_data: Dict[int, float]) -> Dict[str, Any]:
        """Calculate derived values from raw register data."""
        calculated = {}
        try:
            flow_temp = input_data.get(1)
            return_temp = input_data.get(0)
            outdoor_temp = input_data.get(2)
            if flow_temp is not None:
                flow_temp = flow_temp * 0.1
            if return_temp is not None:
                return_temp = return_temp * 0.1
            if outdoor_temp is not None:
                outdoor_temp = outdoor_temp * 0.1

            if (
                flow_temp is not None
                and return_temp is not None
                and outdoor_temp is not None
            ):
                temp_lift = flow_temp - outdoor_temp
                if temp_lift > 0:
                    cop = max(6.8 - (temp_lift * 0.1), 1.0)
                    calculated["cop"] = round(cop, 2)
            # Calculate estimated power if frequency is available
            frequency = input_data.get(1, 0)
            if frequency > 0:
                estimated_power = (frequency / 100) * 3000  # Basic estimation
                calculated["estimated_power"] = min(estimated_power, 8000)
            
            # Calculate daily energy estimate (very basic)
            if "estimated_power" in calculated:
                daily_energy = (calculated["estimated_power"] / 1000) * 24
                calculated["daily_energy"] = round(daily_energy, 2)
                
                # Calculate daily cost estimate
                uk_rate = 0.30  # £0.30 per kWh
                calculated["daily_cost"] = round(daily_energy * uk_rate, 2)
            
            # Add weather compensation calculation
            if outdoor_temp is not None:
                indoor_target = 21.0
                base_flow_temp = 35.0
                compensation_curve = 1.5
                
                if outdoor_temp < indoor_target:
                    temp_diff = indoor_target - outdoor_temp
                    target_flow = base_flow_temp + (temp_diff * compensation_curve)
                    calculated["weather_comp_target"] = min(target_flow, 55.0)
                else:
                    calculated["weather_comp_target"] = base_flow_temp
            
        except Exception as err:
            _LOGGER.warning("Error calculating derived values: %s", err)
        
        return calculated

    async def async_write_register(self, register: int, value: int) -> bool:
        """Write a value to a holding register."""
        try:
            connected = await self.hass.async_add_executor_job(self._client.connect)
            if not connected:
                _LOGGER.error("Failed to connect for writing register %d", register)
                return False

            result = await self.hass.async_add_executor_job(
                self._client.write_register,
                register,
                value,
                self.slave_id
            )
            
            if result.isError():
                _LOGGER.error("Error writing register %d: %s", register, result)
                return False
            
            _LOGGER.info("Successfully wrote value %d to register %d", value, register)
            
            # Trigger a data refresh
            await self.async_request_refresh()
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to write register %d: %s", register, err)
            return False
        finally:
            try:
                await self.hass.async_add_executor_job(self._client.close)
            except Exception:
                pass