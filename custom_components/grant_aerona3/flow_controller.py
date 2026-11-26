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
