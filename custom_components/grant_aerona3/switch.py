"""Switch platform for Grant Aerona3 Heat Pump with ashp_ prefixes."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grant Aerona3 switch entities with ashp_ prefixes."""
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Add switch entities for controllable functions based on actual registers
    entities.extend([
        GrantAerona3DHWPrioritySwitch(coordinator, config_entry),
        GrantAerona3DHWConfigurationSwitch(coordinator, config_entry),
        GrantAerona3BackupHeaterSwitch(coordinator, config_entry),
        GrantAerona3FrostProtectionSwitch(coordinator, config_entry),
        GrantAerona3EHSFunctionSwitch(coordinator, config_entry),
        GrantAerona3Terminal2021Switch(coordinator, config_entry),
        GrantAerona3Terminal2425Switch(coordinator, config_entry),
        GrantAerona3Terminal47AlarmSwitch(coordinator, config_entry),
        GrantAerona3Terminal48Pump1Switch(coordinator, config_entry),
        GrantAerona3Terminal49Pump2Switch(coordinator, config_entry),
        GrantAerona3Terminal3WayValveSwitch(coordinator, config_entry),
    ])

    _LOGGER.info("Creating %d ASHP switch entities", len(entities))
    async_add_entities(entities)


class GrantAerona3BaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for Grant Aerona3 switch entities."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "ASHP Grant Aerona3",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "2.0.0",
            "configuration_url": f"http://{self._config_entry.data.get('host', '')}",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if hasattr(self, '_register_id') and hasattr(self, '_on_value'):
            success = await self.coordinator.async_write_register(
                self._register_id, self._on_value
            )
            
            if success:
                _LOGGER.info("Successfully turned on %s", self._attr_name)
            else:
                _LOGGER.error("Failed to turn on %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if hasattr(self, '_register_id') and hasattr(self, '_off_value'):
            success = await self.coordinator.async_write_register(
                self._register_id, self._off_value
            )
            
            if success:
                _LOGGER.info("Successfully turned off %s", self._attr_name)
            else:
                _LOGGER.error("Failed to turn off %s", self._attr_name)


class GrantAerona3DHWPrioritySwitch(GrantAerona3BaseSwitch):
    """Switch for DHW priority setting (Register 26)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the DHW priority switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Priority"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_priority"
        self.entity_id = "switch.ashp_dhw_priority"
        self._attr_icon = "mdi:water-boiler"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 26: DHW production priority setting
        self._register_id = 26
        self._on_value = 1   # DHW priority over space heating
        self._off_value = 0  # DHW unavailable

    @property
    def is_on(self) -> bool:
        """Return true if DHW priority is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode > 0  # Any value > 0 means DHW is available

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        priority_descriptions = {
            0: "DHW is unavailable",
            1: "DHW priority over space heating",
            2: "Space heating priority over DHW"
        }
        
        return {
            "priority_mode": priority_descriptions.get(mode, "Unknown"),
            "register_value": mode,
        }


class GrantAerona3DHWConfigurationSwitch(GrantAerona3BaseSwitch):
    """Switch for DHW configuration type (Register 27)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the DHW configuration switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Heat Pump Only Mode"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_hp_only_mode"
        self.entity_id = "switch.ashp_dhw_heat_pump_only_mode"
        self._attr_icon = "mdi:heat-pump"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 27: Type of configuration to heat the DHW
        self._register_id = 27
        self._on_value = 1   # Heat pump only
        self._off_value = 0  # Heat pump + Heater

    @property
    def is_on(self) -> bool:
        """Return true if heat pump only mode is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 1)
        
        return mode == 1  # Heat pump only

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 1)
        
        config_descriptions = {
            0: "Heat pump + Heater",
            1: "Heat pump only",
            2: "Heater only"
        }
        
        return {
            "dhw_configuration": config_descriptions.get(mode, "Unknown"),
            "register_value": mode,
        }


class GrantAerona3BackupHeaterSwitch(GrantAerona3BaseSwitch):
    """Switch for backup heater function (Register 71)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the backup heater switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Backup Heater Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_backup_heater_enable"
        self.entity_id = "switch.ashp_backup_heater_enable"
        self._attr_icon = "mdi:heating-coil"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 71: Backup heater type of function
        self._register_id = 71
        self._on_value = 1   # Replacement mode
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if backup heater is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode > 0  # Any mode > 0 means enabled

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        heater_modes = {
            0: "Disabled",
            1: "Replacement mode",
            2: "Emergency mode",
            3: "Supplementary mode"
        }
        
        return {
            "backup_heater_mode": heater_modes.get(mode, "Unknown"),
            "register_value": mode,
        }


class GrantAerona3FrostProtectionSwitch(GrantAerona3BaseSwitch):
    """Switch for frost protection (Register 81)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the frost protection switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Frost Protection"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_frost_protection"
        self.entity_id = "switch.ashp_frost_protection"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_icon = "mdi:snowflake-alert"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 81: Freeze protection functions
        self._register_id = 81
        self._on_value = 1   # Enabled during Start-up
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if frost protection is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode > 0  # Any value > 0 means enabled

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        protection_modes = {
            0: "Disabled",
            1: "Enabled during Start-up",
            2: "Enabled during Defrost",
            3: "Enabled during Start-up and Defrost"
        }
        
        return {
            "frost_protection_mode": protection_modes.get(mode, "Unknown"),
            "register_value": mode,
        }


class GrantAerona3EHSFunctionSwitch(GrantAerona3BaseSwitch):
    """Switch for EHS (External Heat Source) function (Register 84)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the EHS function switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP EHS Function"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_ehs_function"
        self.entity_id = "switch.ashp_ehs_function"
        self._attr_icon = "mdi:heat-wave"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 84: EHS type of function
        self._register_id = 84
        self._on_value = 1   # Replacement mode
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if EHS function is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        ehs_modes = {
            0: "Disabled",
            1: "Replacement mode",
            2: "Supplementary mode"
        }
        
        return {
            "ehs_mode": ehs_modes.get(mode, "Unknown"),
            "register_value": mode,
        }


class GrantAerona3Terminal2021Switch(GrantAerona3BaseSwitch):
    """Switch for Terminal 20-21 remote contact (Register 91)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Terminal 20-21 switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Terminal 20-21 Remote Contact"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_terminal_20_21"
        self.entity_id = "switch.ashp_terminal_20_21_remote_contact"
        self._attr_icon = "mdi:electric-switch"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 91: Terminal 20-21
        self._register_id = 91
        self._on_value = 1   # ON/OFF remote contact
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if terminal function is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode > 0


class GrantAerona3Terminal2425Switch(GrantAerona3BaseSwitch):
    """Switch for Terminal 24-25 heating/cooling mode (Register 92)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Terminal 24-25 switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Terminal 24-25 Mode Control"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_terminal_24_25"
        self.entity_id = "switch.ashp_terminal_24_25_mode_control"
        self._attr_icon = "mdi:electric-switch"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 92: Terminal 24-25
        self._register_id = 92
        self._on_value = 1   # Cooling CLOSE/Heating OPEN
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if terminal mode control is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode > 0


class GrantAerona3Terminal47AlarmSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 47 alarm output (Register 93)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Terminal 47 alarm switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Terminal 47 Alarm Output"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_terminal_47_alarm"
        self.entity_id = "switch.ashp_terminal_47_alarm_output"
        self._attr_icon = "mdi:alarm-light"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 93: Terminal 47
        self._register_id = 93
        self._on_value = 1   # Alarm output
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if alarm output is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode > 0


class GrantAerona3Terminal48Pump1Switch(GrantAerona3BaseSwitch):
    """Switch for Terminal 48 Pump1 (Register 94)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Terminal 48 Pump1 switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Terminal 48 Pump1 Zone1"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_terminal_48_pump1"
        self.entity_id = "switch.ashp_terminal_48_pump1_zone1"
        self._attr_icon = "mdi:pump"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 94: Terminal 48 Pump1
        self._register_id = 94
        self._on_value = 1   # Additional water pump1 for Zone1
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if Pump1 is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode == 1


class GrantAerona3Terminal49Pump2Switch(GrantAerona3BaseSwitch):
    """Switch for Terminal 49 Pump2 (Register 95)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Terminal 49 Pump2 switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Terminal 49 Pump2 Zone2"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_terminal_49_pump2"
        self.entity_id = "switch.ashp_terminal_49_pump2_zone2"
        self._attr_icon = "mdi:pump"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 95: Terminal 49 Pump2
        self._register_id = 95
        self._on_value = 1   # Additional water pump2 for Zone2
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if Pump2 is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode == 1


class GrantAerona3Terminal3WayValveSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 50-51-52 DHW 3way valve (Register 96)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the DHW 3way valve switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW 3-Way Valve"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_3way_valve"
        self.entity_id = "switch.ashp_dhw_3way_valve"
        self._attr_icon = "mdi:valve"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - Register 96: Terminal 50-51-52 DHW 3way valve
        self._register_id = 96
        self._on_value = 1   # Enabled
        self._off_value = 0  # Disabled (though default seems to be 1)

    @property
    def is_on(self) -> bool:
        """Return true if DHW 3way valve is enabled."""
        if not self.coordinator.data:
            return True  # Default to enabled as per documentation
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 1)  # Default 1 per doc
        
        return mode == 1

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "description": "Controls DHW 3-way valve operation",
            "default_state": "Enabled (as per manufacturer default)",
        }
    """Base class for Grant Aerona3 switch entities."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "ASHP Grant Aerona3",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "2.0.0",
            "configuration_url": f"http://{self._config_entry.data.get('host', '')}",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if hasattr(self, '_register_id') and hasattr(self, '_on_value'):
            success = await self.coordinator.async_write_register(
                self._register_id, self._on_value
            )
            
            if success:
                _LOGGER.info("Successfully turned on %s", self._attr_name)
            else:
                _LOGGER.error("Failed to turn on %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if hasattr(self, '_register_id') and hasattr(self, '_off_value'):
            success = await self.coordinator.async_write_register(
                self._register_id, self._off_value
            )
            
            if success:
                _LOGGER.info("Successfully turned off %s", self._attr_name)
            else:
                _LOGGER.error("Failed to turn off %s", self._attr_name)


class GrantAerona3HeatingModeSwitch(GrantAerona3BaseSwitch):
    """Switch for heating mode on/off."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the heating mode switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Heating Mode"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_heating_mode"
        self.entity_id = "switch.ashp_heating_mode"
        self._attr_icon = "mdi:radiator"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping
        self._register_id = 40  # Adjust based on your heat pump
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        """Return true if heating mode is on."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode == self._on_value


class GrantAerona3DHWModeSwitch(GrantAerona3BaseSwitch):
    """Switch for DHW (Domestic Hot Water) mode."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the DHW mode switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Mode"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_mode"
        self.entity_id = "switch.ashp_dhw_mode"
        self._attr_icon = "mdi:water-boiler"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping
        self._register_id = 41  # Adjust based on your heat pump
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        """Return true if DHW mode is on."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode == self._on_value


class GrantAerona3WeatherCompensationSwitch(GrantAerona3BaseSwitch):
    """Switch for weather compensation."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the weather compensation switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Weather Compensation"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_weather_compensation"
        self.entity_id = "switch.ashp_weather_compensation"
        self._attr_icon = "mdi:weather-partly-cloudy"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping
        self._register_id = 42  # Adjust based on your heat pump
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        """Return true if weather compensation is on."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode == self._on_value


class GrantAerona3EcoModeSwitch(GrantAerona3BaseSwitch):
    """Switch for eco mode."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the eco mode switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Eco Mode"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_eco_mode"
        self.entity_id = "switch.ashp_eco_mode"
        self._attr_icon = "mdi:leaf"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping
        self._register_id = 43  # Adjust based on your heat pump
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        """Return true if eco mode is on."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode == self._on_value


class GrantAerona3BoostModeSwitch(GrantAerona3BaseSwitch):
    """Switch for boost mode."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the boost mode switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Boost Mode"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_boost_mode"
        self.entity_id = "switch.ashp_boost_mode"
        self._attr_icon = "mdi:rocket-launch"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping
        self._register_id = 44  # Adjust based on your heat pump
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        """Return true if boost mode is on."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode == self._on_value


class GrantAerona3FrostProtectionSwitch(GrantAerona3BaseSwitch):
    """Switch for frost protection."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the frost protection switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Frost Protection"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_frost_protection"
        self.entity_id = "switch.ashp_frost_protection"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_icon = "mdi:snowflake-alert"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - based on const.py register 81
        self._register_id = 81
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        """Return true if frost protection is on."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode > 0  # Any value > 0 means enabled


class GrantAerona3BackupHeaterSwitch(GrantAerona3BaseSwitch):
    """Switch for backup heater enable/disable."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the backup heater switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Backup Heater Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_backup_heater_enable"
        self.entity_id = "switch.ashp_backup_heater_enable"
        self._attr_icon = "mdi:heating-coil"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping - based on const.py register 84
        self._register_id = 84
        self._on_value = 1  # Replacement mode
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if backup heater is enabled."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode > 0  # Any mode > 0 means enabled


class GrantAerona3HolidayModeSwitch(GrantAerona3BaseSwitch):
    """Switch for holiday mode."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the holiday mode switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Holiday Mode"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_holiday_mode"
        self.entity_id = "switch.ashp_holiday_mode"
        self._attr_icon = "mdi:palm-tree"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping
        self._register_id = 45  # Adjust based on your heat pump
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        """Return true if holiday mode is on."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode == self._on_value


class GrantAerona3QuietModeSwitch(GrantAerona3BaseSwitch):
    """Switch for quiet mode."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the quiet mode switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Quiet Mode"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_quiet_mode"
        self.entity_id = "switch.ashp_quiet_mode"
        self._attr_icon = "mdi:volume-off"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Register mapping
        self._register_id = 46  # Adjust based on your heat pump
        self._on_value = 1
        self._off_value = 0

    @property
    def is_on(self) -> bool:
        """Return true if quiet mode is on."""
        if not self.coordinator.data:
            return False
        
        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 0)
        
        return mode == self._on_value

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "description": "Reduces compressor speed for quieter operation",
            "impact": "May reduce heating efficiency when enabled",
        }