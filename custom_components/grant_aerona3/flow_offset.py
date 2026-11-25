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


class WriteLimiter:
    """Rolling-window cap on offset changes (flash-wear protection)."""

    WINDOW_S = 86400.0

    def __init__(self, max_per_day: int = 24, min_interval_s: float = 1800.0) -> None:
        self.max_per_day = max_per_day
        self.min_interval_s = min_interval_s
        self._times: list[float] = []

    def can_write(self, now: float) -> bool:
        self._times = [t for t in self._times if now - t < self.WINDOW_S]
        if self._times and now - self._times[-1] < self.min_interval_s:
            return False
        return len(self._times) < self.max_per_day

    def record(self, now: float) -> None:
        self._times.append(now)


class MismatchTracker:
    """Confirms a hand edit only after several consecutive mismatching polls."""

    def __init__(self, polls_required: int = 2) -> None:
        self.polls_required = polls_required
        self._count = 0

    def update(self, matches: bool) -> bool:
        self._count = 0 if matches else self._count + 1
        return self._count >= self.polls_required

    def reset(self) -> None:
        self._count = 0


def next_trim_offset(
    current: float, room: float, target: float, dead_band: float, step: float, cap: float
) -> float:
    """One trim step towards the target; holds inside the (exclusive) dead band."""
    error = round(target - room, 6)
    if error > dead_band:
        proposed = current + step
    elif error < -dead_band:
        proposed = current - step
    else:
        return current
    return max(-cap, min(cap, proposed))
