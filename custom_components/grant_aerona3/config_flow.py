"""Config flow."""
import voluptuous as vol
from homeassistant import config_entries

class GrantAerona3ConfigFlow(config_entries.ConfigFlow, domain="grant_aerona3"):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Test", data=user_input)
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("host"): str})
        )