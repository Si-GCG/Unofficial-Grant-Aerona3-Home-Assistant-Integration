"""Flow-temperature controller maths (no Home Assistant imports, unit-testable)."""
from __future__ import annotations

import math
from dataclasses import dataclass

try:  # package import (Home Assistant)
    from .flow_offset import FLOOR_C
except ImportError:  # loaded by file path in the unit tests
    from flow_offset import FLOOR_C

TARGET_REFERENCE = 20.0  # room target the curve points describe
TARGET_GAIN = 1.0  # flow degrees per degree of target above/below the reference
ROOM_GAIN = 2.0  # flow degrees per degree the room is below target
ROOM_MIN, ROOM_MAX = -10.0, 45.0


@dataclass(frozen=True)
class Settings:
    cold_outdoor: float = -3.0
    cold_flow: float = 40.0
    mild_outdoor: float = 15.0
    mild_flow: float = 28.0
    min_flow: float = 25.0
    max_flow: float = 55.0


@dataclass(frozen=True)
class Result:
    flow: float
    base: float
    target_term: float
    room_term: float
    correction: float
    limited: int  # -1 at the minimum, 1 at the maximum


def settings_error(s: Settings) -> str | None:
    if s.cold_outdoor >= s.mild_outdoor:
        return "outdoor_points"
    if s.cold_flow < s.mild_flow:
        return "flow_points"
    if s.min_flow >= s.max_flow:
        return "flow_limits"
    return None


def base_flow(outdoor: float, s: Settings) -> float:
    """Straight line through the two points, continued beyond them."""
    span = s.mild_outdoor - s.cold_outdoor
    if not span:
        return s.cold_flow
    return s.cold_flow + (outdoor - s.cold_outdoor) * (s.mild_flow - s.cold_flow) / span


def calculate(
    outdoor: float, room: float | None, target: float, correction: float, s: Settings
) -> Result:
    """Flow temperature for now. Without a room reading only outdoor and correction count."""
    base = base_flow(outdoor, s)
    target_term = room_term = 0.0
    if room is not None:
        target_term = TARGET_GAIN * (target - TARGET_REFERENCE)
        room_term = ROOM_GAIN * (target - room)
    raw = base + target_term + room_term + correction
    low = max(s.min_flow, FLOOR_C)
    high = max(s.max_flow, low)
    limited = -1 if raw <= low else 1 if raw >= high else 0
    flow = round(max(low, min(raw, high)) * 2) / 2
    return Result(flow, round(base, 2), round(target_term, 2), round(room_term, 2), correction, limited)


def decode_temperature(raw: int | None, scale: float) -> float | None:
    """Signed register value in degrees; 65535 means no reading."""
    if raw is None or raw == 65535:
        return None
    if raw > 32767:
        raw -= 65536
    return round(raw * scale, 1)


def parse_room(text: str | None) -> float | None:
    """A plausible Celsius room reading, or None."""
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or not ROOM_MIN <= value <= ROOM_MAX:
        return None
    return value


class OutdoorAverage:
    """Mean outdoor temperature over a rolling window."""

    def __init__(self, window_s: float = 3600.0) -> None:
        self.window_s = window_s
        self._samples: list[tuple[float, float]] = []

    def add(self, now: float, value: float) -> None:
        self._samples.append((now, value))
        self._trim(now)

    def value(self, now: float) -> float | None:
        self._trim(now)
        if not self._samples:
            return None
        return sum(v for _, v in self._samples) / len(self._samples)

    def _trim(self, now: float) -> None:
        self._samples = [s for s in self._samples if now - s[0] <= self.window_s]


class LearnedCorrection:
    """Slow offset that makes up for curve points that are a bit wrong."""

    STEP = 0.5
    PERIOD_S = 7200.0
    DEAD_BAND = 0.3
    MAX_ERROR = 1.5
    LIMIT = 8.0
    HOLD_AFTER_TARGET_S = 10800.0

    def __init__(self, value: float = 0.0) -> None:
        self.value = value
        self._since: float | None = None
        self._sign = 0
        self._hold_until = float("-inf")

    def target_changed(self, now: float) -> None:
        self._hold_until = now + self.HOLD_AFTER_TARGET_S
        self._since = None

    def update(self, now: float, error: float | None, limited: int) -> float:
        """error is target minus room; call this regularly."""
        sign = 0
        if error is not None:
            size = abs(round(error, 6))
            if self.DEAD_BAND < size <= self.MAX_ERROR:
                sign = 1 if error > 0 else -1
        if sign == 0 or sign == limited:
            self._since = None
            return self.value
        if self._since is None or sign != self._sign:
            self._since, self._sign = max(now, self._hold_until), sign
        elif now - self._since >= self.PERIOD_S:
            self.value = max(-self.LIMIT, min(self.value + sign * self.STEP, self.LIMIT))
            self._since = now
        return self.value


def should_write(calculated: float, current: float, after_target_change: bool) -> bool:
    """Ignore small differences, to save writes."""
    threshold = 0.5 if after_target_change else 1.0
    return abs(calculated - current) >= threshold - 1e-9
