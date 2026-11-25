"""Pure flow-temperature offset maths (no Home Assistant imports, unit-testable)."""
from __future__ import annotations

FLOOR_C = 23.0


def clamp_flow(value: float, ceiling: float) -> float:
    """Clamp a flow temperature to the unit's floor and the configured ceiling."""
    return max(FLOOR_C, min(value, ceiling))


def shift_curve(tm1: float, tm2: float, offset: float, ceiling: float) -> tuple[float, float]:
    """Shift the weather-compensation curve in parallel; Tm1 never falls below Tm2."""
    new_tm2 = clamp_flow(tm2 + offset, ceiling)
    new_tm1 = max(clamp_flow(tm1 + offset, ceiling), new_tm2)
    return new_tm1, new_tm2


def shift_fixed(fixed: float, offset: float, ceiling: float) -> float:
    """Shift the fixed flow setpoint."""
    return clamp_flow(fixed + offset, ceiling)


def effective_offset(base: float, applied: float) -> float:
    """Offset actually in effect for one register."""
    return applied - base
