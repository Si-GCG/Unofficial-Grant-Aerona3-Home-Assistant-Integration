"""Config flow for Grant Aerona3 Heat Pump integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ModbusException

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_UNIT_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DEFAULT_SCAN_INTERVAL,
    CONF_CONNECTION_TYPE,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_METHOD,
    CONF_PARITY,
    CONF_STOPBITS,
)

_LOGGER = logging.getLogger(__name__)

INTEGRATION_VERSION = "1.1.1"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONNECTION_TYPE, default="tcp"): vol.In(["tcp", "serial"]),
        vol.Optional(CONF_HOST, default=""): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
        # Serial options - only used if connection_type == 'serial'
        vol.Optional(CONF_SERIAL_PORT, default="/dev/ttyUSB0"): cv.string,
        vol.Optional(CONF_BAUDRATE, default=19200): vol.All(vol.Coerce(int)),
        vol.Optional(CONF_BYTESIZE, default=8): vol.All(vol.Coerce(int)),
        vol.Optional(CONF_METHOD, default="rtu"): cv.string,
        vol.Optional(CONF_PARITY, default="N"): cv.string,
        vol.Optional(CONF_STOPBITS, default=2): vol.All(vol.Coerce(int)),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    connection_type = data.get(CONF_CONNECTION_TYPE, "tcp")
    host = data.get(CONF_HOST, "")
    port = data.get(CONF_PORT, DEFAULT_PORT)
    unit_id = data[CONF_UNIT_ID]
    serial_port = data.get(CONF_SERIAL_PORT)
    baudrate = data.get(CONF_BAUDRATE)
    bytesize = data.get(CONF_BYTESIZE)
    method = data.get(CONF_METHOD)
    parity = data.get(CONF_PARITY)
    stopbits = data.get(CONF_STOPBITS)

    # Test the connection
    if connection_type == "tcp":
        if not host:
            raise CannotConnect("Host required for TCP connection")
        client = ModbusTcpClient(host=host, port=port, timeout=5)
    else:
        client = ModbusSerialClient(
            method=method,
            port=serial_port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=5,
        )

    try:
        if not await hass.async_add_executor_job(client.connect):
            raise CannotConnect("Failed to connect to heat pump")

        # Try to read a register to verify communication
        result = await hass.async_add_executor_job(
            lambda: client.read_input_registers(address=0, count=1, device_id=unit_id)
        )

        if result.isError():
            raise CannotConnect("Failed to read from heat pump - check Unit ID")

        _LOGGER.info("Successfully connected to Grant Aerona3 (%s)", "serial" if connection_type == "serial" else f"{host}:{port}")

    except ModbusException as err:
        _LOGGER.error("Modbus error connecting - %s", err)
        raise CannotConnect(f"Modbus communication error: {err}") from err
    except Exception as err:
        _LOGGER.error("Unexpected error connecting - %s", err)
        raise CannotConnect(f"Unexpected error: {err}") from err
    finally:
        await hass.async_add_executor_job(client.close)

    # Return info that you want to store in the config entry.
    # Store relevant values depending on connection type
    base = {
        "title": f"ASHP Grant Aerona3 ({serial_port if connection_type=='serial' else host})",
        "connection_type": connection_type,
        "unit_id": unit_id,
        "scan_interval": data[CONF_SCAN_INTERVAL],
    }
    if connection_type == "tcp":
        base.update({"host": host, "port": port})
    else:
        base.update({
            "serial_port": serial_port,
            "baudrate": baudrate,
            "bytesize": bytesize,
            "method": method,
            "parity": parity,
            "stopbits": stopbits,
        })
    return base


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Grant Aerona3 Heat Pump."""

    VERSION = 1  # Home Assistant expects an integer here

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if already configured
                if user_input.get(CONF_CONNECTION_TYPE) == "serial":
                    unique = f"serial:{user_input.get(CONF_SERIAL_PORT)}"
                else:
                    unique = f"{user_input.get(CONF_HOST)}:{user_input.get(CONF_PORT)}"
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors,
            description_placeholders={
                "integration_name": "Grant Aerona3 Heat Pump (ASHP)",
                "version": INTEGRATION_VERSION,
                "features": "All entities will have 'ashp_' prefixes for better organisation"
            }
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Grant Aerona3 options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
                    vol.Optional(
                        "flow_rate_lpm",
                        default=self.config_entry.options.get(
                            "flow_rate_lpm",
                            self.config_entry.data.get("flow_rate_lpm", 34.0)
                        ),
                    ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=100.0)),
                }
            ),
        )



class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""