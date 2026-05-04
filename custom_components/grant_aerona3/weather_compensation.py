# weather_compensation.py

from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

class WeatherCompensationMode(Enum):
    DISABLED = "disabled"
    WEATHER_COMPENSATION = "weather_compensation"

@dataclass
class HeatingCurveConfig:
    name: str
    min_outdoor_temp: float
    max_outdoor_temp: float
    min_flow_temp: float
    max_flow_temp: float

class LinearHeatingCurve:
    def __init__(self, config: HeatingCurveConfig):
        self.config = config

    def calculate_flow_temperature(self, outdoor_temp: float) -> float:
        outdoor_temp = max(self.config.min_outdoor_temp, min(self.config.max_outdoor_temp, outdoor_temp))
        if outdoor_temp <= self.config.min_outdoor_temp:
            return self.config.max_flow_temp
        elif outdoor_temp >= self.config.max_outdoor_temp:
            return self.config.min_flow_temp
        temp_range = self.config.max_outdoor_temp - self.config.min_outdoor_temp
        flow_range = self.config.max_flow_temp - self.config.min_flow_temp
        outdoor_ratio = (outdoor_temp - self.config.min_outdoor_temp) / temp_range
        target_flow = self.config.max_flow_temp - (outdoor_ratio * flow_range)
        return round(target_flow, 1)

    def get_curve_points(self, num_points: int = 10) -> list[Tuple[float, float]]:
        points = []
        for i in range(num_points):
            outdoor_temp = self.config.min_outdoor_temp + (
                (self.config.max_outdoor_temp - self.config.min_outdoor_temp) * i / (num_points - 1)
            )
            flow_temp = self.calculate_flow_temperature(outdoor_temp)
            points.append((outdoor_temp, flow_temp))
        return points

class WeatherCompensationController:
    def __init__(self, hass: HomeAssistant, coordinator, config: Dict[str, Any]):
        self.hass = hass
        self.coordinator = coordinator
        self.config = config
        self.enabled = config.get("weather_compensation", False)
        self.primary_curve = None
        self.secondary_curve = None
        self.active_curve = "primary"
        self.boost_active = False
        self.boost_end_time: Optional[datetime] = None
        self.last_outdoor_temp = None
        self.last_flow_temp = None
        self.last_update = None
        self.calculation_count = 0
        self._setup_done = False
        self._cancel_listener = None

    async def async_setup(self):
        if not self.enabled:
            _LOGGER.info("Weather compensation disabled in configuration")
            return
        self.primary_curve = LinearHeatingCurve(
            HeatingCurveConfig(
                name="Primary",
                min_outdoor_temp=self.config.get("wc_min_outdoor_temp", -5.0),
                max_outdoor_temp=self.config.get("wc_max_outdoor_temp", 18.0),
                min_flow_temp=self.config.get("wc_min_flow_temp", 25.0),
                max_flow_temp=self.config.get("wc_max_flow_temp", 45.0),
            )
        )
        if self.config.get("dual_weather_compensation", False):
            self.secondary_curve = LinearHeatingCurve(
                HeatingCurveConfig(
                    name="Boost",
                    min_outdoor_temp=self.config.get("boost_min_outdoor_temp", -10.0),
                    max_outdoor_temp=self.config.get("boost_max_outdoor_temp", 10.0),
                    min_flow_temp=self.config.get("boost_min_flow_temp", 35.0),
                    max_flow_temp=self.config.get("boost_max_flow_temp", 55.0),
                )
            )
        self._cancel_listener = async_track_time_interval(self.hass, self._async_update_weather_compensation, timedelta(seconds=60))
        self._setup_done = True
        _LOGGER.info("Weather compensation system initialized.")

    async def _async_update_weather_compensation(self, now):
        try:
            outdoor_temp = await self._get_outdoor_temperature()
            if outdoor_temp is None:
                _LOGGER.warning("Could not get outdoor temperature for weather compensation")
                return
            target_flow_temp = self._calculate_target_flow_temperature(outdoor_temp)
            self.last_outdoor_temp = outdoor_temp
            self.last_flow_temp = target_flow_temp
            self.last_update = dt_util.now()
            self.calculation_count += 1
            # Handle boost timeout
            if self.boost_active and self.boost_end_time and dt_util.now() > self.boost_end_time:
                await self.deactivate_boost_mode("timeout")
            _LOGGER.debug(
                "Weather compensation updated: outdoor=%.1f°C, target_flow=%.1f°C, curve=%s",
                outdoor_temp, target_flow_temp, self.active_curve
            )
        except Exception as err:
            _LOGGER.error("Error updating weather compensation: %s", err)

    async def _get_outdoor_temperature(self) -> Optional[float]:
        input_regs = self.coordinator.data.get("input_registers", {})
        raw = input_regs.get(6)
        if raw is not None:
            scale = 1  # Adjust if your register map uses a scale
            return raw * scale if scale else float(raw)
        return None

    def _calculate_target_flow_temperature(self, outdoor_temp: float) -> float:
        if self.boost_active and self.secondary_curve:
            return self.secondary_curve.calculate_flow_temperature(outdoor_temp)
        return self.primary_curve.calculate_flow_temperature(outdoor_temp)

    async def activate_boost_mode(self, duration_minutes: int = 120, reason: str = "manual"):
        if not self.secondary_curve:
            _LOGGER.warning("Cannot activate boost mode: no secondary curve configured")
            return False
        self.boost_active = True
        self.active_curve = "secondary"
        self.boost_end_time = dt_util.now() + timedelta(minutes=duration_minutes)
        await self._async_update_weather_compensation(None)
        self.hass.bus.async_fire("ashp_weather_compensation_boost_activated", {
            "reason": reason,
            "duration_minutes": duration_minutes,
            "curve_name": self.secondary_curve.config.name
        })
        _LOGGER.info("Weather compensation boost activated for %d minutes. Reason: %s", duration_minutes, reason)
        return True

    async def deactivate_boost_mode(self, reason: str = "manual"):
        if not self.boost_active:
            return
        self.boost_active = False
        self.active_curve = "primary"
        self.boost_end_time = None
        await self._async_update_weather_compensation(None)
        self.hass.bus.async_fire("ashp_weather_compensation_boost_deactivated", {
            "reason": reason,
            "curve_name": self.primary_curve.config.name
        })
        _LOGGER.info("Weather compensation boost deactivated. Reason: %s", reason)

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "active_curve": self.active_curve,
            "curve_name": (self.secondary_curve.config.name if self.boost_active and self.secondary_curve else self.primary_curve.config.name),
            "boost_active": self.boost_active,
            "boost_remaining_minutes": self._get_boost_remaining_minutes(),
            "last_outdoor_temp": self.last_outdoor_temp,
            "last_flow_temp": self.last_flow_temp,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "calculation_count": self.calculation_count,
            "primary_curve_points": self.primary_curve.get_curve_points() if self.primary_curve else [],
            "secondary_curve_points": self.secondary_curve.get_curve_points() if self.secondary_curve else [],
        }

    def _get_boost_remaining_minutes(self) -> Optional[int]:
        if not self.boost_active or not self.boost_end_time:
            return None
        remaining = (self.boost_end_time - dt_util.now()).total_seconds()
        return max(0, int(remaining / 60))

    def async_stop(self) -> None:
        """Cancel the periodic update listener."""
        if self._cancel_listener:
            self._cancel_listener()
            self._cancel_listener = None

    def is_enabled(self) -> bool:
        return self.enabled and self._setup_done
