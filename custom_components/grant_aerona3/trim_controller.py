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
    pending_reset: bool = False,
    low: float = float("-inf"),
    high: float = float("inf"),
    stale_after_s: float = 21600.0,
    step: float = 0.5,
) -> TrimDecision:
    """Decide what the trim should do on this tick."""
    if not enabled:
        # Off leaves a manual offset alone; only a just-requested reset (pending_reset) zeroes it
        return _to_zero(current_offset, "off") if pending_reset else TrimDecision(None, "off")
    if cooling:
        return TrimDecision(None, "cooling")
    if room is None:
        return _to_zero(current_offset, "sensor_unavailable")
    if room_age_s is None or room_age_s > stale_after_s:
        return _to_zero(current_offset, "sensor_stale")
    # Step from what the curve can really take, so a request beyond it costs no extra ticks
    current = max(low, min(current_offset, high))
    proposed = max(low, min(next_trim_offset(current, room, target, dead_band, step, cap), high))
    if proposed != current:
        return TrimDecision(proposed, "stepped")
    if abs(round(target - room, 6)) > dead_band:
        return TrimDecision(None, "at_cap")
    return TrimDecision(None, "in_dead_band")
