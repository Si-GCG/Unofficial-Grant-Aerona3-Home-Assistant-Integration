"""Preview of the flow temperature controller: shows what it would choose.

Read-only on purpose. Nothing here writes to the heat pump.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FC_SCHEDULE,
    CONF_FC_SENSOR,
    CONF_HAS_REMOTE_OUTDOOR_SENSOR,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .features import flow_controller_settings, get_feature
from .flow_controller import (
    OutdoorAverage,
    calculate,
    decode_temperature,
    outdoor_temperature,
    parse_room,
    preset_for,
)

INTERVAL = timedelta(minutes=10)
TARGETS = {"comfort": 20.0, "eco": 17.0}
ROOM_STALE_S = 21600.0


class FlowInputs:
    """What the controller reads: outdoor, room and schedule."""

    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._sensor = get_feature(entry, CONF_FC_SENSOR, None)
        self._schedule = get_feature(entry, CONF_FC_SCHEDULE, None)

    def outdoor_now(self) -> float | None:
        if not self._coordinator.last_update_success:
            return None
        return outdoor_temperature(
            self._coordinator.data, CONF_HAS_REMOTE_OUTDOOR_SENSOR in self._coordinator.features
        )

    def room_now(self, now: datetime) -> float | None:
        state = self._hass.states.get(self._sensor)
        if state is None:
            return None
        seen = max(state.last_updated, getattr(state, "last_reported", state.last_updated))
        if (now - seen).total_seconds() > ROOM_STALE_S:
            return None
        return parse_room(state.state)

    def preset_now(self) -> str:
        state = self._hass.states.get(self._schedule) if self._schedule else None
        return preset_for(state.state if state else None)


class GrantAerona3FlowPreviewSensor(CoordinatorEntity, SensorEntity):
    """The flow temperature the controller would choose for Zone 1."""

    _attr_has_entity_name = True
    _attr_name = "Zone 1 suggested flow temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-auto"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._settings = flow_controller_settings(entry)
        self._average = OutdoorAverage()
        self._inputs: FlowInputs | None = None
        self._attr_unique_id = f"ashp_{entry.entry_id}_flow_preview"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "ASHP",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }
        self._attr_native_value = None
        self._attr_extra_state_attributes: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._inputs = FlowInputs(self.hass, self.coordinator, self._entry)
        self.async_on_remove(async_track_time_interval(self.hass, self._async_tick, INTERVAL))
        self._sample()
        self._recalculate()

    def _sample(self) -> None:
        outdoor = self._inputs.outdoor_now()
        if outdoor is not None:
            self._average.add(time.monotonic(), outdoor)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sample()
        if self._attr_native_value is None:
            self._recalculate()
        super()._handle_coordinator_update()

    @callback
    def _async_tick(self, now: datetime) -> None:
        self._recalculate()
        self.async_write_ha_state()

    def _recalculate(self) -> None:
        average = self._average.value(time.monotonic())
        if average is None:
            self._attr_native_value = None
            return
        preset = self._inputs.preset_now()
        target = TARGETS[preset]
        room = self._inputs.room_now(dt_util.utcnow())
        result = calculate(average, room, target, 0.0, self._settings)
        inputs = (self.coordinator.data or {}).get("input_registers", {})
        self._attr_native_value = result.flow
        self._attr_extra_state_attributes = {
            "base": result.base,
            "target_term": result.target_term,
            "room_term": result.room_term,
            "target": target,
            "preset": preset,
            "room": room,
            "outdoor_average": round(average, 1),
            "limited": {-1: "minimum", 0: None, 1: "maximum"}[result.limited],
            "outgoing_water_temperature": decode_temperature(inputs.get(9), 1),
        }
