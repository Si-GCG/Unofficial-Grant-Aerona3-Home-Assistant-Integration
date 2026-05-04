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

from .const import DOMAIN, MANUFACTURER, MODEL, SW_VERSION
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

    # Holding Register switches (configuration parameters)
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

    # Coil Register switches (enable/disable features)
    entities.extend([
        GrantAerona3ClimateCompensationZone1Switch(coordinator, config_entry),
        GrantAerona3AntiLegionellaSwitch(coordinator, config_entry),
        GrantAerona3WaterSetpointControlSwitch(coordinator, config_entry),
        GrantAerona3FrostProtectionOutdoorSwitch(coordinator, config_entry),
        GrantAerona3FrostProtectionWaterSwitch(coordinator, config_entry),
        GrantAerona3HumidityCompensationSwitch(coordinator, config_entry),
        # Terminal enable switches
        GrantAerona3RemoteControllerSwitch(coordinator, config_entry),
        GrantAerona3MixingValveSwitch(coordinator, config_entry),
        GrantAerona3DHWTankProbeSwitch(coordinator, config_entry),
        GrantAerona3OutdoorProbeSwitch(coordinator, config_entry),
        GrantAerona3BufferTankProbeSwitch(coordinator, config_entry),
        GrantAerona3MixWaterProbeSwitch(coordinator, config_entry),
        GrantAerona3RS485ModbusSwitch(coordinator, config_entry),
        GrantAerona3HumiditySensorSwitch(coordinator, config_entry),
        GrantAerona3DHWRemoteContactSwitch(coordinator, config_entry),
        GrantAerona3DualSetPointSwitch(coordinator, config_entry),
        GrantAerona3FlowSwitchSwitch(coordinator, config_entry),
        GrantAerona3NightModeSwitch(coordinator, config_entry),
        GrantAerona3LowTariffSwitch(coordinator, config_entry),
        GrantAerona3EHSTerminalSwitch(coordinator, config_entry),
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
            "sw_version": SW_VERSION,
            "configuration_url": f"http://{self._config_entry.data.get('host', '')}",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if not hasattr(self, '_register_id'):
            _LOGGER.error("Switch %s has no register ID defined", self._attr_name)
            return

        # Check if this is a coil or holding register
        if hasattr(self, '_register_type') and self._register_type == "coil":
            success = await self.coordinator.async_write_coil(
                self._register_id, self._on_value
            )
        else:
            success = await self.coordinator.async_write_register(
                self._register_id, self._on_value
            )
        
        if success:
            _LOGGER.info("Successfully turned on %s", self._attr_name)
        else:
            _LOGGER.error("Failed to turn on %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if not hasattr(self, '_register_id'):
            _LOGGER.error("Switch %s has no register ID defined", self._attr_name)
            return

        # Check if this is a coil or holding register
        if hasattr(self, '_register_type') and self._register_type == "coil":
            success = await self.coordinator.async_write_coil(
                self._register_id, self._off_value
            )
        else:
            success = await self.coordinator.async_write_register(
                self._register_id, self._off_value
            )
        
        if success:
            _LOGGER.info("Successfully turned off %s", self._attr_name)
        else:
            _LOGGER.error("Failed to turn off %s", self._attr_name)


# ============================================================================
# HOLDING REGISTER SWITCHES
# ============================================================================

class GrantAerona3DHWPrioritySwitch(GrantAerona3BaseSwitch):
    """Switch for DHW priority setting (Holding Register 26)."""

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
        
        return mode > 0

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
    """Switch for DHW configuration type (Holding Register 27)."""

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
        
        return mode == 1

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
    """Switch for backup heater function (Holding Register 71)."""

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
        
        return mode > 0

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
    """Switch for freeze protection functions (Holding Register 81)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the frost protection switch."""
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Freeze Protection"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_freeze_protection"
        self.entity_id = "switch.ashp_freeze_protection"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_icon = "mdi:snowflake-alert"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_id = 81
        self._on_value = 1   # Enabled during Start-up
        self._off_value = 0  # Disabled

    @property
    def is_on(self) -> bool:
        """Return true if freeze protection is enabled."""
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
        
        protection_modes = {
            0: "Disabled",
            1: "Enabled during Start-up",
            2: "Enabled during Defrost",
            3: "Enabled during Start-up and Defrost"
        }
        
        return {
            "freeze_protection_mode": protection_modes.get(mode, "Unknown"),
            "register_value": mode,
        }


class GrantAerona3EHSFunctionSwitch(GrantAerona3BaseSwitch):
    """Switch for EHS (External Heat Source) function (Holding Register 84)."""

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
    """Switch for Terminal 20-21 remote contact (Holding Register 91)."""

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
    """Switch for Terminal 24-25 heating/cooling mode (Holding Register 92)."""

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
    """Switch for Terminal 47 alarm output (Holding Register 93)."""

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
    """Switch for Terminal 48 Pump1 (Holding Register 94)."""

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
    """Switch for Terminal 49 Pump2 (Holding Register 95)."""

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
    """Switch for Terminal 50-51-52 DHW 3way valve (Holding Register 96)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW 3-Way Valve"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_3way_valve"
        self.entity_id = "switch.ashp_dhw_3way_valve"
        self._attr_icon = "mdi:valve"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_id = 96
        self._on_value = 1
        self._off_value = 1  # Only valid value per spec (min=1, max=1)

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return True  # Default to enabled as per documentation

        holding_regs = self.coordinator.data.get("holding_registers", {})
        mode = holding_regs.get(self._register_id, 1)

        return mode == 1

    async def async_turn_off(self, **kwargs: Any) -> None:
        _LOGGER.warning("DHW 3-way valve (register 96) only supports value 1 per spec — cannot turn off")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Controls DHW 3-way valve operation",
            "default_state": "Enabled (as per manufacturer default)",
        }


# ============================================================================
# COIL REGISTER SWITCHES
# ============================================================================

class GrantAerona3ClimateCompensationZone1Switch(GrantAerona3BaseSwitch):
    """Switch for climatic curve (weather compensation) Zone 1 (Coil 2)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Climate Compensation Zone 1"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_climate_comp_zone1"
        self.entity_id = "switch.ashp_climate_compensation_zone1"
        self._attr_icon = "mdi:chart-bell-curve"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 2
        self._on_value = True   # Climatic curve enabled
        self._off_value = False  # Fixed set point

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable weather compensation for Zone 1",
            "when_off": "Uses fixed water temperature set point",
            "when_on": "Adjusts water temperature based on outdoor temperature",
        }


class GrantAerona3AntiLegionellaSwitch(GrantAerona3BaseSwitch):
    """Switch for anti-legionella function (Coil 6)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Anti-Legionella"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_anti_legionella"
        self.entity_id = "switch.ashp_anti_legionella"
        self._attr_icon = "mdi:bacteria"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 6
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Periodically heats DHW to kill legionella bacteria",
            "temperature_setpoint": "See Holding Register 36",
        }


class GrantAerona3WaterSetpointControlSwitch(GrantAerona3BaseSwitch):
    """Switch for water vs room setpoint control (Coil 7)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Water Setpoint Control"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_water_setpoint_control"
        self.entity_id = "switch.ashp_water_setpoint_control"
        self._attr_icon = "mdi:thermometer-water"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 7
        self._on_value = True   # Water setpoint
        self._off_value = False  # Room setpoint

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return True  # Default per documentation
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, True)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "when_on": "HP turns ON/OFF based on water temperature",
            "when_off": "HP turns ON/OFF based on room temperature",
        }


class GrantAerona3FrostProtectionOutdoorSwitch(GrantAerona3BaseSwitch):
    """Switch for frost protection by outdoor temperature (Coil 9)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Frost Protection (Outdoor)"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_frost_outdoor"
        self.entity_id = "switch.ashp_frost_protection_outdoor"
        self._attr_icon = "mdi:snowflake-thermometer"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 9
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Activates heating when outdoor temperature drops too low",
            "related_settings": "See Holding Registers 54-56",
        }


class GrantAerona3FrostProtectionWaterSwitch(GrantAerona3BaseSwitch):
    """Switch for frost protection by water temperature (Coil 10)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Frost Protection (Water)"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_frost_water"
        self.entity_id = "switch.ashp_frost_protection_water"
        self._attr_icon = "mdi:pipe-leak"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 10
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Activates heating when outgoing water temperature drops too low",
            "related_settings": "See Holding Registers 52, 57",
        }


class GrantAerona3HumidityCompensationSwitch(GrantAerona3BaseSwitch):
    """Switch for room humidity compensation (Coil 13)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Humidity Compensation"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_humidity_comp"
        self.entity_id = "switch.ashp_humidity_compensation"
        self._attr_icon = "mdi:water-percent"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 13
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return True  # Default per documentation
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, True)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Adjusts water temperature based on room humidity",
            "related_settings": "See Holding Registers 60-62 for humidity values",
        }
    

class GrantAerona3RemoteControllerSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 1-2-3 Remote Controller (Coil 16)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Remote Controller Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_remote_controller"
        self.entity_id = "switch.ashp_remote_controller_enable"
        self._attr_icon = "mdi:remote"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 16
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return True  # Default enabled per documentation
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, True)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable Remote Controller on terminals 1-2-3",
            "default_state": "Enabled (required for normal operation)",
        }


class GrantAerona3MixingValveSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 4-5-6 3-way mixing valve (Coil 17)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP 3-Way Mixing Valve Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_mixing_valve"
        self.entity_id = "switch.ashp_mixing_valve_enable"
        self._attr_icon = "mdi:valve"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 17
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable 3-way mixing valve on terminals 4-5-6",
            "pcb_terminals": "4, 5, 6",
        }


class GrantAerona3DHWTankProbeSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 7-8 DHW tank temperature probe (Coil 18)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Tank Probe Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_tank_probe"
        self.entity_id = "switch.ashp_dhw_tank_probe_enable"
        self._attr_icon = "mdi:thermometer"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 18
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable DHW tank temperature probe on terminals 7-8",
            "pcb_terminals": "7, 8",
        }


class GrantAerona3OutdoorProbeSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 9-10 Outdoor air temperature probe (Coil 19)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Outdoor Probe Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_outdoor_probe"
        self.entity_id = "switch.ashp_outdoor_probe_enable"
        self._attr_icon = "mdi:thermometer"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 19
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable outdoor temperature probe (additional) on terminals 9-10",
            "pcb_terminals": "9, 10",
        }


class GrantAerona3BufferTankProbeSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 11-12 Buffer tank temperature probe (Coil 20)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Buffer Tank Probe Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_buffer_tank_probe"
        self.entity_id = "switch.ashp_buffer_tank_probe_enable"
        self._attr_icon = "mdi:thermometer"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 20
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable buffer tank temperature probe on terminals 11-12",
            "pcb_terminals": "11, 12",
            "note": "Related to Holding Register 41 (Main water pump configuration)",
        }


class GrantAerona3MixWaterProbeSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 13-14 Mix water temperature probe (Coil 21)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Mix Water Probe Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_mix_water_probe"
        self.entity_id = "switch.ashp_mix_water_probe_enable"
        self._attr_icon = "mdi:thermometer"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 21
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable mix water temperature probe on terminals 13-14",
            "pcb_terminals": "13, 14",
        }


class GrantAerona3RS485ModbusSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 15-16-32 RS485 Modbus (Coil 22)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP RS485 Modbus Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_rs485_modbus"
        self.entity_id = "switch.ashp_rs485_modbus_enable"
        self._attr_icon = "mdi:serial-port"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 22
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable RS485 Modbus communication on terminals 15-16-32",
            "pcb_terminals": "15, 16, 32",
            "warning": "This integration uses RS485 - keep this enabled",
        }


class GrantAerona3HumiditySensorSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 17-18 Humidity sensor (Coil 23)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Humidity Sensor Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_humidity_sensor"
        self.entity_id = "switch.ashp_humidity_sensor_enable"
        self._attr_icon = "mdi:water-percent"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 23
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable humidity sensor on terminals 17-18",
            "pcb_terminals": "17, 18",
        }


class GrantAerona3DHWRemoteContactSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 19-18 DHW remote contact (Coil 24)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Remote Contact Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_remote_contact"
        self.entity_id = "switch.ashp_dhw_remote_contact_enable"
        self._attr_icon = "mdi:water-boiler-alert"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 24
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable DHW remote contact on terminals 19-18",
            "pcb_terminals": "19, 18",
        }


class GrantAerona3DualSetPointSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 22-23 Dual set point control (Coil 25)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Dual Set Point Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dual_set_point"
        self.entity_id = "switch.ashp_dual_set_point_enable"
        self._attr_icon = "mdi:thermometer-lines"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 25
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable dual set point control on terminals 22-23",
            "pcb_terminals": "22, 23",
        }


class GrantAerona3FlowSwitchSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 26-27 Flow switch (Coil 26)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Flow Switch Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_flow_switch"
        self.entity_id = "switch.ashp_flow_switch_enable"
        self._attr_icon = "mdi:pipe-valve"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 26
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return True  # Default enabled per documentation
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, True)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable flow switch on terminals 26-27",
            "pcb_terminals": "26, 27",
        }


class GrantAerona3NightModeSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 28-29 Night mode (Coil 27)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Night Mode Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_night_mode"
        self.entity_id = "switch.ashp_night_mode_enable"
        self._attr_icon = "mdi:weather-night"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 27
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable night mode terminal input on terminals 28-29",
            "pcb_terminals": "28, 29",
            "note": "Limits compressor frequency - see Holding Register 37",
        }


class GrantAerona3LowTariffSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 30-31 Low tariff (Coil 28)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP Low Tariff Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_low_tariff"
        self.entity_id = "switch.ashp_low_tariff_enable"
        self._attr_icon = "mdi:currency-usd-off"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 28
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable low tariff terminal input on terminals 30-31",
            "pcb_terminals": "30, 31",
            "note": "Boosts temperatures when external signal active - see Holding Registers 24-25",
        }


class GrantAerona3EHSTerminalSwitch(GrantAerona3BaseSwitch):
    """Switch for Terminal 41-42 EHS (Coil 29)."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP EHS Terminal Enable"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_ehs_terminal"
        self.entity_id = "switch.ashp_ehs_terminal_enable"
        self._attr_icon = "mdi:heat-wave"
        self._attr_entity_category = EntityCategory.CONFIG
        
        self._register_type = "coil"
        self._register_id = 29
        self._on_value = True
        self._off_value = False

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        
        coil_regs = self.coordinator.data.get("coil_registers", {})
        return coil_regs.get(self._register_id, False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "description": "Enable EHS (External Heat Source) on terminals 41-42",
            "pcb_terminals": "41, 42",
        }   