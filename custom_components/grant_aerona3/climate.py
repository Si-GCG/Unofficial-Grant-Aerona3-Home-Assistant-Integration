"""Experimental room-temperature trim for the Grant Aerona3 (Zone 1).

The unit's operating mode and room set point are read-only over Modbus, so this
is not a thermostat. It holds a room target in Home Assistant and slowly moves
the Zone 1 flow offset towards it, within hard limits.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EXPERIMENTAL_FLOW_OFFSET,
    CONF_TRIM_CAP,
    CONF_TRIM_DEAD_BAND,
    CONF_TRIM_ENABLED,
    CONF_TRIM_INTERVAL,
    CONF_TRIM_SENSOR,
    DEFAULT_TRIM_CAP,
    DEFAULT_TRIM_DEAD_BAND,
    DEFAULT_TRIM_INTERVAL,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .features import get_feature
from .trim_controller import decide

_LOGGER = logging.getLogger(__name__)

AT_CAP_TICKS_FOR_HINT = 4

# Newer Home Assistant deprecates the plain temperature attributes in favour of native_*
_NATIVE_TEMPS = hasattr(ClimateEntity, "native_target_temperature")
COOLING_MODE = 2  # input register 10


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add the trim entity only when the experimental offset and the trim are enabled."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    manager = coordinator.flow_offsets.get(1)
    sensor = get_feature(entry, CONF_TRIM_SENSOR, None)
    enabled = (
        CONF_EXPERIMENTAL_FLOW_OFFSET in coordinator.features
        and get_feature(entry, CONF_TRIM_ENABLED, False)
        and sensor
        and manager is not None
    )
    unique_id = f"ashp_{entry.entry_id}_room_trim_zone1"
    if not enabled:
        registry = er.async_get(hass)
        entity_id = registry.async_get_entity_id("climate", DOMAIN, unique_id)
        if entity_id:
            registry.async_remove(entity_id)
        return
    async_add_entities([GrantAerona3RoomTrim(coordinator, entry, manager, sensor, unique_id)])


class GrantAerona3RoomTrim(ClimateEntity, RestoreEntity):
    """Slow room-temperature trim on top of the Zone 1 flow offset."""

    _attr_has_entity_name = True
    _attr_name = "Zone 1 room trim"
    _attr_should_poll = False
    _attr_icon = "mdi:thermostat-auto"
    if _NATIVE_TEMPS:
        _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    else:
        _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_min_temp = 15.0
    _attr_max_temp = 25.0
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator, entry: ConfigEntry, manager, sensor: str, unique_id: str) -> None:
        self._coordinator = coordinator
        self._manager = manager
        self._sensor = sensor
        self._interval = int(get_feature(entry, CONF_TRIM_INTERVAL, DEFAULT_TRIM_INTERVAL))
        self._dead_band = float(get_feature(entry, CONF_TRIM_DEAD_BAND, DEFAULT_TRIM_DEAD_BAND))
        self._cap = float(get_feature(entry, CONF_TRIM_CAP, DEFAULT_TRIM_CAP))
        self._attr_unique_id = unique_id
        self._attr_hvac_mode = HVACMode.OFF  # safe default: the user turns it on deliberately
        self._set_target(20.0)
        self._last_reason = "off"
        self._at_cap_ticks = 0
        self._pending_reset = False  # offset must return to 0 (turned off, or a fail-safe)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            if last.state == HVACMode.HEAT:
                self._attr_hvac_mode = HVACMode.HEAT
            target = last.attributes.get(ATTR_TEMPERATURE)
            if target is not None:
                self._set_target(float(target))
        self._manager.trim_active = self._attr_hvac_mode == HVACMode.HEAT
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_tick, timedelta(minutes=self._interval)
            )
        )
        self.async_on_remove(
            async_track_state_change_event(self.hass, [self._sensor], self._async_sensor_changed)
        )

    @callback
    def _async_sensor_changed(self, event: Event) -> None:
        self.async_write_ha_state()

    def _read_sensor(self, now: datetime) -> tuple[float | None, float | None]:
        state = self.hass.states.get(self._sensor)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None, None
        try:
            room = float(state.state)
        except ValueError:
            return None, None
        seen = max(state.last_updated, getattr(state, "last_reported", state.last_updated))
        return room, (now - seen).total_seconds()

    def _set_target(self, value: float) -> None:
        self._target = value
        if not _NATIVE_TEMPS:
            self._attr_target_temperature = value

    @property
    def native_target_temperature(self) -> float:
        return self._target

    @property
    def native_current_temperature(self) -> float | None:
        return self._read_sensor(dt_util.utcnow())[0]

    if not _NATIVE_TEMPS:

        @property
        def current_temperature(self) -> float | None:
            return self._read_sensor(dt_util.utcnow())[0]

    async def _async_tick(self, now: datetime) -> None:
        room, age = self._read_sensor(now)
        input_regs = (self._coordinator.data or {}).get("input_registers", {})
        low, high = self._manager.offset_limits()
        decision = decide(
            low=low,
            high=high,
            enabled=self._attr_hvac_mode == HVACMode.HEAT,
            cooling=input_regs.get(10) == COOLING_MODE,
            room=room,
            room_age_s=age,
            target=self._target,
            current_offset=self._manager.requested_offset,
            pending_reset=self._pending_reset,
            dead_band=self._dead_band,
            cap=self._cap,
        )
        self._last_reason = decision.reason
        self._at_cap_ticks = self._at_cap_ticks + 1 if decision.reason == "at_cap" else 0
        if decision.new_offset is not None:
            if await self._manager.async_set_offset(decision.new_offset):
                if decision.new_offset == 0.0:
                    self._pending_reset = False
            else:
                _LOGGER.warning("Room trim could not change the flow offset (%s)", decision.reason)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._attr_hvac_mode = hvac_mode
        self._manager.trim_active = hvac_mode == HVACMode.HEAT
        if hvac_mode == HVACMode.OFF:
            self._last_reason = "off"
            self._pending_reset = self._manager.requested_offset != 0
            if self._pending_reset and await self._manager.async_set_offset(0.0):
                self._pending_reset = False  # if refused, the next tick retries
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (target := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._set_target(float(target))
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "offset": self._manager.offset,
            "requested_offset": self._manager.requested_offset,
            "last_reason": self._last_reason,
            "sensor": self._sensor,
            "base_curve_hint": (
                "Offset at its limit for several checks in a row; consider adjusting the base curve"
                if self._at_cap_ticks >= AT_CAP_TICKS_FOR_HINT
                else None
            ),
        }
