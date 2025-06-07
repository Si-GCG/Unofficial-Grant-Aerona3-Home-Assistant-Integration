"""Config flow for Grant Aerona3 Heat Pump integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST

from .const import DOMAIN

class GrantAerona3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Grant Aerona3."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Grant Aerona3 Test",
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
            })
        )