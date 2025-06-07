"""Config flow for Grant Aerona3 Heat Pump integration."""
from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from pymodbus.client import ModbusTcpClient

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Setup schema with all required fields
STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
})


async def validate_connection(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    def _test_connection():
        """Test connection to the Modbus device."""
        client = ModbusTcpClient(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            timeout=10
        )

        try:
            if not client.connect():
                raise CannotConnect("Failed to connect to Modbus device")

            # Try to read a register to verify communication
            result = client.read_input_registers(
                address=0,
                count=1,
                slave=data[CONF_SLAVE_ID]
            )

            if result.isError():
                raise CannotConnect("Failed to read from Modbus device")

            return True

        finally:
            client.close()

    # Test connection in executor to avoid blocking
    await hass.async_add_executor_job(_test_connection)

    # Return info that you want to store in the config entry
    return {"title": f"Grant Aerona3 ({data[CONF_HOST]})"}


class GrantAerona3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Grant Aerona3."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_connection(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if already configured
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"], 
                    data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={
                "description": "Enter your Grant Aerona3 heat pump's network details. All registers will be automatically configured as entities."
            }
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""