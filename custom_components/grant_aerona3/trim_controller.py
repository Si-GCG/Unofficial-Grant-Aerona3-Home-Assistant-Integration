"""Room-trim decision logic (no Home Assistant imports, unit-testable)."""
from __future__ import annotations

from dataclasses import dataclass

try:  # package import (Home Assistant)
    from .flow_offset import next_trim_offset
except ImportError:  # loaded by file path in the unit tests
    from flow_offset import next_trim_offset


@dataclass(frozen=True)
class TrimDecision:
    """new_offset None means 'make no change'."""

    new_offset: float | None
    reason: str


def _to_zero(current_offset: float, reason: str) -> TrimDecision:
    return TrimDecision(0.0 if current_offset != 0 else None, reason)


def decide(
    *,
    enabled: bool,
    cooling: bool,
    room: float | None,
    room_age_s: float | None,
    target: float,
    current_offset: float,
    dead_band: float,
    cap: float,
    stale_after_s: float = 7200.0,
    step: float = 0.5,
) -> TrimDecision:
    """Decide what the trim should do on this tick."""
    if not enabled:
        return _to_zero(current_offset, "off")
    if cooling:
        return TrimDecision(None, "cooling")
    if room is None:
        return _to_zero(current_offset, "sensor_unavailable")
    if room_age_s is None or room_age_s > stale_after_s:
        return _to_zero(current_offset, "sensor_stale")
    proposed = next_trim_offset(current_offset, room, target, dead_band, step, cap)
    if proposed != current_offset:
        return TrimDecision(proposed, "stepped")
    if abs(round(target - room, 6)) > dead_band:
        return TrimDecision(None, "at_cap")
    return TrimDecision(None, "in_dead_band")
