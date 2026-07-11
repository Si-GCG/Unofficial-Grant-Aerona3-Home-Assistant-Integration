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
    CONF_HAS_DHW_TANK,
    CONF_HAS_BUFFER,
    CONF_HAS_EHS,
    CONF_HAS_COOLING,
    CONF_ZONES,
    DEFAULT_FEATURES,
    ZONES_SINGLE,
    ZONES_DUAL,
)
from .features import get_feature

_LOGGER = logging.getLogger(__name__)

INTEGRATION_VERSION = "1.1.4"

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

STEP_FEATURES_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HAS_DHW_TANK, default=True): cv.boolean,
        vol.Required(CONF_HAS_BUFFER, default=False): cv.boolean,
        vol.Required(CONF_HAS_EHS, default=False): cv.boolean,
        vol.Required(CONF_HAS_COOLING, default=False): cv.boolean,
        vol.Required(CONF_ZONES, default=ZONES_SINGLE): vol.In([ZONES_SINGLE, ZONES_DUAL]),
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

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._connection_data: dict[str, Any] = {}
        self._title: str = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial (connection) step."""
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

                self._connection_data = user_input
                self._title = info["title"]
                return await self.async_step_features()

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

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user tick the hardware their installation actually has."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._title,
                data={**self._connection_data, **user_input},
            )

        return self.async_show_form(
            step_id="features",
            data_schema=STEP_FEATURES_DATA_SCHEMA,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Grant Aerona3 options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry = self.config_entry
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=get_feature(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
                    vol.Optional(
                        "flow_rate_lpm",
                        default=get_feature(entry, "flow_rate_lpm", 34.0),
                    ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=100.0)),
                    vol.Required(
                        CONF_HAS_DHW_TANK,
                        default=get_feature(entry, CONF_HAS_DHW_TANK, DEFAULT_FEATURES[CONF_HAS_DHW_TANK]),
                    ): cv.boolean,
                    vol.Required(
                        CONF_HAS_BUFFER,
                        default=get_feature(entry, CONF_HAS_BUFFER, DEFAULT_FEATURES[CONF_HAS_BUFFER]),
                    ): cv.boolean,
                    vol.Required(
                        CONF_HAS_EHS,
                        default=get_feature(entry, CONF_HAS_EHS, DEFAULT_FEATURES[CONF_HAS_EHS]),
                    ): cv.boolean,
                    vol.Required(
                        CONF_HAS_COOLING,
                        default=get_feature(entry, CONF_HAS_COOLING, DEFAULT_FEATURES[CONF_HAS_COOLING]),
                    ): cv.boolean,
                    vol.Required(
                        CONF_ZONES,
                        default=get_feature(entry, CONF_ZONES, DEFAULT_FEATURES[CONF_ZONES]),
                    ): vol.In([ZONES_SINGLE, ZONES_DUAL]),
                }
            ),
        )



class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""