from __future__ import annotations
# custom_components/grant_aerona3/coordinator.py
import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Dict

from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.framer import FramerType

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
    INPUT_REGISTER_FEATURES,
    HOLDING_REGISTER_FEATURES,
    COIL_REGISTER_FEATURES,
    DEFAULT_SCAN_INTERVAL,
)
from .features import enabled_features, register_enabled

_LOGGER = logging.getLogger(__name__)

# Largest block read in one request. The Modbus limit is 125 registers; stay well under it.
MAX_READ_BLOCK = 50
# Skipped addresses (e.g. disabled hardware) up to this size are read through
# and discarded rather than costing another request.
MAX_READ_GAP = 4
BLOCK_READ_TIMEOUT = 5.0
# Always-enabled input registers: return temp, frequency, power, outdoor temp, flow temp.
# If none of these can be read, the heat pump isn't answering and the poll has failed.
CRITICAL_INPUT_REGISTERS = (0, 1, 3, 6, 9)

_READ_METHODS = {
    "input": "read_input_registers",
    "holding": "read_holding_registers",
    "coil": "read_coils",
}


def plan_reads(
    addresses: list[int], max_block: int = MAX_READ_BLOCK, max_gap: int = MAX_READ_GAP
) -> list[tuple[int, int]]:
    """Group addresses into (start, count) spans, one block read each."""
    spans: list[tuple[int, int]] = []
    for address in sorted(set(addresses)):
        if spans:
            start, count = spans[-1]
            gap = address - (start + count)
            if gap <= max_gap and address + 1 - start <= max_block:
                spans[-1] = (start, address + 1 - start)
                continue
        spans.append((address, 1))
    return spans

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
        # pymodbus >= 3.7 dropped the `method=` kwarg on ModbusSerialClient
        # in favour of `framer=`; translate the stored "rtu"/"ascii" string.
        self.framer = (
            FramerType.ASCII if str(self.method).lower() == "ascii" else FramerType.RTU
        )
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

        # Which hardware features are enabled (options take precedence over data)
        self.features = enabled_features(entry)
        _LOGGER.debug("Enabled features: %s", sorted(self.features))

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        # Serial bus lock: polls and writes must take turns (a serial port can only be opened once at a time)
        self._bus_lock = asyncio.Lock()
        # Block reads the device rejected (warned about once, then read singly)
        self._degraded_spans: set[tuple[str, int, int]] = set()
        # Duration of the last successful poll, for the diagnostics download
        self.last_poll_seconds: float | None = None
        # Create a persistent client reference (not always used; per-fetch clients created)
        if self.connection_type == "tcp":
            self._client = ModbusTcpClient(host=self.host, port=self.port, timeout=10)
        else:
            self._client = ModbusSerialClient(
                framer=self.framer,
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=10,
            )

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            async with self._bus_lock:
                started = time.monotonic()
                data = await asyncio.wait_for(self._fetch_data(), timeout=180.0)
                self.last_poll_seconds = round(time.monotonic() - started, 2)
                return data
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to ASHP at {self.host}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with ASHP: {err}") from err

    async def _fetch_data(self) -> Dict[str, Any]:
        data = {
            "input_registers": {},
            "holding_registers": {},
            "coil_registers": {},
            "last_update": asyncio.get_running_loop().time(),
        }
        
        # Create a fresh client for each fetch to avoid connection issues
        if self.connection_type == "tcp":
            client = ModbusTcpClient(host=self.host, port=self.port, timeout=5)
        else:
            client = ModbusSerialClient(
                framer=self.framer,
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
                target = self.serial_port if self.connection_type != "tcp" else f"{self.host}:{self.port}"
                raise UpdateFailed(f"Failed to connect to ASHP at {target}")
            
            data["input_registers"] = await self._read_addresses(
                client, "input", self._enabled_addresses("input")
            )
            if not any(reg in data["input_registers"] for reg in CRITICAL_INPUT_REGISTERS):
                raise UpdateFailed(
                    "Heat pump did not answer - no input registers could be read. "
                    "Check the wiring/network, unit ID and serial settings"
                )
            data["holding_registers"] = await self._read_addresses(
                client, "holding", self._enabled_addresses("holding")
            )
            data["coil_registers"] = await self._read_addresses(
                client, "coil", self._enabled_addresses("coil")
            )
            data["calculated"] = self._calculate_derived_values(
                data["input_registers"], data["holding_registers"]
            )
            
        except UpdateFailed:
            raise
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

    def _enabled_addresses(self, kind: str) -> list[int]:
        """Addresses to poll for one register type, skipping hardware the user hasn't ticked."""
        if kind == "input":
            return [
                reg_id
                for reg_id in INPUT_REGISTER_MAP
                if register_enabled(self.features, INPUT_REGISTER_FEATURES, reg_id)
            ]
        if kind == "holding":
            return [
                reg_id
                for reg_id, config in HOLDING_REGISTER_MAP.items()
                if config.get("writable", False)
                and register_enabled(self.features, HOLDING_REGISTER_FEATURES, reg_id)
            ]
        return [
            reg_id
            for reg_id in COIL_REGISTER_MAP
            if register_enabled(self.features, COIL_REGISTER_FEATURES, reg_id)
        ]

    async def _read_block(
        self, client: object, kind: str, start: int, count: int
    ) -> tuple[list | None, bool]:
        """Read `count` consecutive registers/coils starting at `start`.

        Returns (values, retry_singly). values is None on failure. retry_singly is
        True only when the device answered with an error (e.g. part of the span is
        not implemented), as opposed to not answering at all.
        """
        read = getattr(client, _READ_METHODS[kind])
        try:
            result = await asyncio.wait_for(
                self.hass.async_add_executor_job(
                    lambda: read(start, count=count, device_id=self.unit_id)
                ),
                timeout=BLOCK_READ_TIMEOUT,
            )
        except Exception as err:  # timeout, lost connection, serial error
            _LOGGER.debug("No answer reading %s %d..%d: %s", kind, start, start + count - 1, err)
            return None, False
        if result.isError():
            _LOGGER.debug("Error reading %s %d..%d: %s", kind, start, start + count - 1, result)
            return None, True
        if kind == "coil":
            return list(result.bits[:count]), False
        # Registers are signed 16-bit
        return [v - 65536 if v > 32767 else v for v in result.registers[:count]], False

    async def _read_addresses(self, client: object, kind: str, addresses: list[int]) -> Dict[int, Any]:
        """Read the given addresses using as few requests as possible.

        Addresses close together are fetched in one block read. If the device
        rejects a block, that block is retried one address at a time so a single
        unimplemented register can't hide its neighbours.
        """
        wanted = set(addresses)
        values: Dict[int, Any] = {}
        for start, count in plan_reads(addresses):
            block, retry_singly = await self._read_block(client, kind, start, count)
            if block is not None:
                for offset, value in enumerate(block):
                    if start + offset in wanted:
                        values[start + offset] = value
                continue
            if not retry_singly:
                # The device didn't answer at all; more requests won't help.
                continue
            if (kind, start, count) not in self._degraded_spans:
                self._degraded_spans.add((kind, start, count))
                _LOGGER.warning(
                    "Heat pump rejected block read of %s %d..%d; reading those one at a time",
                    kind, start, start + count - 1,
                )
            silent = 0
            for address in sorted(a for a in wanted if start <= a < start + count):
                single, _ = await self._read_block(client, kind, address, 1)
                if single is None:
                    silent += 1
                    if silent >= 3:
                        break
                    continue
                silent = 0
                values[address] = single[0]
        return values

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

    async def _do_write_register(self, register: int, value: int) -> bool:
        """Write to a holding register."""
        # Registers are unsigned 16-bit on the wire; negative values (e.g. minimum
        # outdoor temperatures) must be sent as two's complement.
        if not -32768 <= value <= 65535:
            _LOGGER.error("Value %d out of 16-bit range for register %d", value, register)
            return False
        value &= 0xFFFF

        if self.connection_type == "tcp":
            client = ModbusTcpClient(host=self.host, port=self.port, timeout=5)
        else:
            client = ModbusSerialClient(
                framer=self.framer,
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
            return True

        except Exception as err:
            _LOGGER.error("Failed to write register %d: %s", register, err)
            return False
        finally:
            try:
                await self.hass.async_add_executor_job(client.close)
            except Exception:
                pass

    async def _do_write_coil(self, address: int, value: bool) -> bool:
        """Write to a coil register."""
        # Create a fresh client like async_write_register does
        if self.connection_type == "tcp":
            client = ModbusTcpClient(host=self.host, port=self.port, timeout=5)
        else:
            client = ModbusSerialClient(
                framer=self.framer,
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
            return True

        except Exception as err:
            _LOGGER.error("Failed to write coil %d: %s", address, err)
            return False
        finally:
            try:
                await self.hass.async_add_executor_job(client.close)
            except Exception:
                pass

    async def async_write_register(self, register: int, value: int) -> bool:
        """Write to a holding register, taking turns with polling."""
        async with self._bus_lock:
            await asyncio.sleep(0.3)  # let the serial port settle after a poll
            ok = await self._do_write_register(register, value)
        if ok:
            await self.async_request_refresh()
        return ok

    async def async_write_coil(self, address: int, value: bool) -> bool:
        """Write to a coil, taking turns with polling."""
        async with self._bus_lock:
            await asyncio.sleep(0.3)  # let the serial port settle after a poll
            ok = await self._do_write_coil(address, value)
        if ok:
            await self.async_request_refresh()
        return ok
