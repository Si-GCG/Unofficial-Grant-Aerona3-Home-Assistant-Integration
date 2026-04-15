"""Climate platform for Grant Aerona3 Heat Pump with register map scaling and limits."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    OPERATING_MODES,
    HOLDING_REGISTER_MAP,
    INPUT_REGISTER_MAP,
)
from .coordinator import GrantAerona3Coordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class ZoneClimateConfig:
    """Configuration for a zone climate entity."""

    zone_number: int
    name: str
    supports_cooling: bool
    heating_setpoint_reg: int
    cooling_setpoint_reg: int
    current_temp_reg: int
    fallback_temp_reg: int


def get_scaled_register(
    registers: dict[int, Any], reg_map: dict[int, dict], reg_id: int
) -> Optional[float]:
    reg_info = reg_map.get(reg_id, {})
    scale = reg_info.get("scale", 1)
    value = registers.get(reg_id)
    return value * scale if value is not None else None


def get_reg_min_max_step(reg_id: int) -> tuple[float, float, float]:
    reg_info = HOLDING_REGISTER_MAP.get(reg_id, {})
    return (
        reg_info.get("min", 0),
        reg_info.get("max", 100),
        reg_info.get("step", 1),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GrantAerona3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Get configuration with defaults for backward compatibility
    options = config_entry.options or {}
    enable_zone_1 = options.get("enable_zone_1", True)
    zone_1_cooling = options.get("zone_1_cooling", False)
    enable_zone_2 = options.get("enable_zone_2", False)
    zone_2_cooling = options.get("zone_2_cooling", False)
    enable_dhw = options.get("enable_dhw", False)

    entities = []

    # Zone 1
    if enable_zone_1:
        config_z1 = ZoneClimateConfig(
            zone_number=1,
            name="ASHP Zone 1",
            supports_cooling=zone_1_cooling,
            heating_setpoint_reg=2,
            cooling_setpoint_reg=12,
            current_temp_reg=11,
            fallback_temp_reg=0,
        )
        entities.append(GrantAerona3ZoneClimate(coordinator, config_entry, config_z1))

    # Zone 2
    if enable_zone_2:
        config_z2 = ZoneClimateConfig(
            zone_number=2,
            name="ASHP Zone 2",
            supports_cooling=zone_2_cooling,
            heating_setpoint_reg=7,
            cooling_setpoint_reg=17,
            current_temp_reg=12,
            fallback_temp_reg=0,
        )
        entities.append(GrantAerona3ZoneClimate(coordinator, config_entry, config_z2))

    # DHW
    if enable_dhw:
        entities.append(GrantAerona3DHWClimate(coordinator, config_entry))

    _LOGGER.info("Creating %d ASHP climate entities", len(entities))
    async_add_entities(entities)


class GrantAerona3BaseClimate(CoordinatorEntity, ClimateEntity):
    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_precision = 0.5

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "ASHP Grant Aerona3",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "2.0.0",
            "configuration_url": f"http://{self._config_entry.data.get('host', '')}",
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class GrantAerona3ZoneClimate(GrantAerona3BaseClimate):
    """Climate entity for heating/cooling zones."""

    def __init__(
        self,
        coordinator: GrantAerona3Coordinator,
        config_entry: ConfigEntry,
        zone_config: ZoneClimateConfig,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._zone_config = zone_config
        self._attr_name = zone_config.name
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_zone_{zone_config.zone_number}"
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

        # Build HVAC modes dynamically
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        if zone_config.supports_cooling:
            self._attr_hvac_modes.append(HVACMode.COOL)
            self._attr_hvac_modes.append(HVACMode.AUTO)

        min_temp, max_temp, step = get_reg_min_max_step(zone_config.heating_setpoint_reg)
        self._attr_min_temp = min_temp
        self._attr_max_temp = max_temp
        self._attr_target_temperature_step = step

    @property
    def current_temperature(self) -> Optional[float]:
        if not self.coordinator.data:
            return None
        input_regs = self.coordinator.data.get("input_registers", {})
        room_temp = get_scaled_register(
            input_regs, INPUT_REGISTER_MAP, self._zone_config.current_temp_reg
        )
        if room_temp is not None and room_temp > 0:
            return round(room_temp, 1)
        fallback_temp = get_scaled_register(
            input_regs, INPUT_REGISTER_MAP, self._zone_config.fallback_temp_reg
        )
        if fallback_temp is not None and fallback_temp > 0:
            return round(fallback_temp, 1)
        return 21.0

    @property
    def target_temperature(self) -> Optional[float]:
        if not self.coordinator.data:
            return None
        holding_regs = self.coordinator.data.get("holding_registers", {})
        current_mode = self._get_current_mode()
        if current_mode == "heating":
            target = get_scaled_register(
                holding_regs, HOLDING_REGISTER_MAP, self._zone_config.heating_setpoint_reg
            )
        elif current_mode == "cooling":
            target = get_scaled_register(
                holding_regs, HOLDING_REGISTER_MAP, self._zone_config.cooling_setpoint_reg
            )
        else:
            target = get_scaled_register(
                holding_regs, HOLDING_REGISTER_MAP, self._zone_config.heating_setpoint_reg
            )
        if target is not None and target > 0:
            return round(target, 1)
        return self._attr_min_temp

    def _get_current_mode(self) -> str:
        if not self.coordinator.data:
            return "heating"
        input_regs = self.coordinator.data.get("input_registers", {})
        mode = input_regs.get(10, 1)
        if mode == 1:
            return "heating"
        elif mode == 2:
            return "cooling"
        else:
            return "heating"

    @property
    def hvac_mode(self) -> HVACMode:
        if not self.coordinator.data:
            return HVACMode.OFF
        input_regs = self.coordinator.data.get("input_registers", {})
        mode = input_regs.get(10, 0)
        power = get_scaled_register(input_regs, INPUT_REGISTER_MAP, 3)
        frequency = get_scaled_register(input_regs, INPUT_REGISTER_MAP, 1)
        if mode == 0 or ((power or 0) < 100 and (frequency or 0) == 0):
            return HVACMode.OFF
        elif mode == 1:
            return HVACMode.HEAT
        elif mode == 2:
            return HVACMode.COOL
        else:
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        if not self.coordinator.data:
            return HVACAction.OFF
        input_regs = self.coordinator.data.get("input_registers", {})
        frequency = get_scaled_register(input_regs, INPUT_REGISTER_MAP, 1)
        power = get_scaled_register(input_regs, INPUT_REGISTER_MAP, 3)
        mode = input_regs.get(10, 1)
        if (frequency or 0) > 0 or (power or 0) > 200:
            if mode == 2:
                return HVACAction.COOLING
            else:
                return HVACAction.HEATING
        else:
            return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        current_mode = self._get_current_mode()
        if current_mode == "heating":
            register_id = self._zone_config.heating_setpoint_reg
        else:
            register_id = self._zone_config.cooling_setpoint_reg

        reg_info = HOLDING_REGISTER_MAP.get(register_id, {})
        scale = reg_info.get("scale", 1)
        register_value = int(temperature / scale)

        success = await self.coordinator.async_write_register(register_id, register_value)
        if success:
            _LOGGER.info(
                "Set Zone %d target temperature to %s°C (register %d)",
                self._zone_config.zone_number,
                temperature,
                register_id,
            )
        else:
            _LOGGER.error(
                "Failed to set Zone %d target temperature to %s°C",
                self._zone_config.zone_number,
                temperature,
            )

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}
        input_regs = self.coordinator.data.get("input_registers", {})
        holding_regs = self.coordinator.data.get("holding_registers", {})
        return {
            "zone": f"Zone {self._zone_config.zone_number}",
            "flow_temperature": get_scaled_register(input_regs, INPUT_REGISTER_MAP, 9),
            "return_temperature": get_scaled_register(input_regs, INPUT_REGISTER_MAP, 0),
            "outdoor_temperature": get_scaled_register(input_regs, INPUT_REGISTER_MAP, 6),
            "compressor_frequency": get_scaled_register(input_regs, INPUT_REGISTER_MAP, 1),
            "current_power": get_scaled_register(input_regs, INPUT_REGISTER_MAP, 3),
            "operation_mode": OPERATING_MODES.get(input_regs.get(10, 0), "Unknown"),
            "heating_setpoint": get_scaled_register(
                holding_regs, HOLDING_REGISTER_MAP, self._zone_config.heating_setpoint_reg
            ),
            "cooling_setpoint": get_scaled_register(
                holding_regs, HOLDING_REGISTER_MAP, self._zone_config.cooling_setpoint_reg
            ),
            "supports_cooling": self._zone_config.supports_cooling,
        }


class GrantAerona3DHWClimate(GrantAerona3BaseClimate):
    """Climate entity for DHW (Domestic Hot Water) control."""

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_name = "ASHP DHW Tank"
        self._attr_unique_id = f"ashp_{config_entry.entry_id}_dhw_tank"
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
        ]
        min_temp, max_temp, step = get_reg_min_max_step(28)
        self._attr_min_temp = min_temp
        self._attr_max_temp = max_temp
        self._attr_target_temperature_step = step

    @property
    def current_temperature(self) -> Optional[float]:
        if not self.coordinator.data:
            return None
        input_regs = self.coordinator.data.get("input_registers", {})
        temp = get_scaled_register(input_regs, INPUT_REGISTER_MAP, 16)
        if temp is not None and temp > 0:
            return round(temp, 1)
        return 50.0

    @property
    def target_temperature(self) -> Optional[float]:
        if not self.coordinator.data:
            return None
        holding_regs = self.coordinator.data.get("holding_registers", {})
        input_regs = self.coordinator.data.get("input_registers", {})
        dhw_mode = input_regs.get(13, 1) if input_regs else 1
        if dhw_mode == 1:
            target = get_scaled_register(holding_regs, HOLDING_REGISTER_MAP, 28)
        elif dhw_mode == 2:
            target = get_scaled_register(holding_regs, HOLDING_REGISTER_MAP, 29)
        elif dhw_mode == 3:
            target = get_scaled_register(holding_regs, HOLDING_REGISTER_MAP, 31)
        else:
            target = get_scaled_register(holding_regs, HOLDING_REGISTER_MAP, 28)
        if target is not None and target > 0:
            return round(target, 1)
        return self._attr_min_temp

    @property
    def hvac_mode(self) -> HVACMode:
        if not self.coordinator.data:
            return HVACMode.OFF
        input_regs = self.coordinator.data.get("input_registers", {})
        holding_regs = self.coordinator.data.get("holding_registers", {})
        dhw_priority = holding_regs.get(26, 0)
        dhw_mode = input_regs.get(13, 0)
        if dhw_priority > 0 and dhw_mode > 0:
            return HVACMode.HEAT
        else:
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        if not self.coordinator.data:
            return HVACAction.OFF
        input_regs = self.coordinator.data.get("input_registers", {})
        current_temp = self.current_temperature or 0
        target_temp = self.target_temperature or 0
        power = get_scaled_register(input_regs, INPUT_REGISTER_MAP, 3)
        if current_temp < target_temp - 1 and (power or 0) > 200:
            return HVACAction.HEATING
        elif current_temp >= target_temp:
            return HVACAction.IDLE
        else:
            return HVACAction.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        if not (self._attr_min_temp <= temperature <= self._attr_max_temp):
            _LOGGER.error(
                "DHW temperature %s°C outside allowed range %s-%s°C",
                temperature, self._attr_min_temp, self._attr_max_temp
            )
            return
        register_value = int(temperature * 10)
        input_regs = self.coordinator.data.get("input_registers", {}) if self.coordinator.data else {}
        dhw_mode = input_regs.get(13, 1)
        if dhw_mode == 1:
            register_id = 28
        elif dhw_mode == 2:
            register_id = 29
        elif dhw_mode == 3:
            register_id = 31
        else:
            register_id = 28
        success = await self.coordinator.async_write_register(register_id, register_value)
        if success:
            _LOGGER.info("Set DHW target temperature to %s°C (register %d, mode %d)", temperature, register_id, dhw_mode)
        else:
            _LOGGER.error("Failed to set DHW target temperature to %s°C", temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            mode_value = 0
            register_id = 26
        elif hvac_mode == HVACMode.HEAT:
            mode_value = 1
            register_id = 26
        else:
            _LOGGER.error("Unsupported DHW HVAC mode: %s", hvac_mode)
            return
        success = await self.coordinator.async_write_register(register_id, mode_value)
        if success:
            _LOGGER.info("Set DHW HVAC mode to %s (register %d = %d)", hvac_mode, register_id, mode_value)
        else:
            _LOGGER.error("Failed to set DHW HVAC mode to %s", hvac_mode)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}
        input_regs = self.coordinator.data.get("input_registers", {})
        holding_regs = self.coordinator.data.get("holding_registers", {})
        dhw_modes = {
            0: "Off",
            1: "Comfort",
            2: "Economy",
            3: "Boost"
        }
        return {
            "dhw_mode": dhw_modes.get(input_regs.get(13, 0), "Unknown"),
            "tank_temperature": self.current_temperature,
            "heating_active": self.hvac_action == HVACAction.HEATING,
            "power_consumption": get_scaled_register(input_regs, INPUT_REGISTER_MAP, 3),
            "dhw_priority": holding_regs.get(26, 0),
            "comfort_setpoint": get_scaled_register(holding_regs, HOLDING_REGISTER_MAP, 28),
            "economy_setpoint": get_scaled_register(holding_regs, HOLDING_REGISTER_MAP, 29),
            "boost_setpoint": get_scaled_register(holding_regs, HOLDING_REGISTER_MAP, 31),
            "dhw_hysteresis": get_scaled_register(holding_regs, HOLDING_REGISTER_MAP, 30),
        }
