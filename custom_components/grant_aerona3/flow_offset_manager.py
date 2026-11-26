"""Per-zone flow offset: stored baseline, applied offset, hand-edit detection.

No Home Assistant imports: collaborators (coordinator, store, clock, task
scheduler) are injected so the logic can be unit-tested.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

try:  # package import (Home Assistant)
    from .flow_offset import (
        MismatchTracker,
        WriteLimiter,
        offset_limits,
        shift_curve,
        shift_fixed,
    )
except ImportError:  # loaded by file path in the unit tests
    from flow_offset import (
        MismatchTracker,
        WriteLimiter,
        offset_limits,
        shift_curve,
        shift_fixed,
    )

_LOGGER = logging.getLogger(__name__)

SCALE = 0.1
STORE_VERSION = 1


@dataclass(frozen=True)
class ZoneRegisters:
    """Holding registers and WC-enable coil of one heating zone."""

    fixed: int
    tm1: int
    tm2: int
    wc_coil: int


ZONE_FLOW_REGISTERS = {
    1: ZoneRegisters(fixed=2, tm1=3, tm2=4, wc_coil=2),
    2: ZoneRegisters(fixed=7, tm1=8, tm2=9, wc_coil=3),
}


def _to_raw(value: float) -> int:
    return int(round(value / SCALE))


class FlowOffsetManager:
    """Shifts a zone's heating flow temperature by a stored offset."""

    def __init__(
        self,
        zone: int,
        coordinator: Any,
        store: Any,
        ceiling: Callable[[], float],
        limiter: WriteLimiter,
        clock: Callable[[], float],
        create_task: Callable[[Any], Any],
    ) -> None:
        self._regs = ZONE_FLOW_REGISTERS[zone]
        self._coordinator = coordinator
        self._store = store
        self._ceiling = ceiling
        self._limiter = limiter
        self._clock = clock
        self._create_task = create_task
        self._tracker = MismatchTracker()
        self._lock = asyncio.Lock()
        self._requested = 0.0
        # Curve as the user set it (offset 0), and the values last written per mode
        self.baseline: dict[str, dict[str, float]] = {}
        self.applied: dict[str, dict[str, float]] = {}
        self._last_mode: Optional[str] = None
        self._writing = False
        self.trim_active = False  # set by the climate trim entity
        self._suspect = False  # a write failed part-way: don't judge registers as hand edits

    # -- state ----------------------------------------------------------
    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if stored and stored.get("version") == STORE_VERSION:
            self._requested = float(stored.get("requested_offset", 0.0))
            self.baseline = {k: dict(v) for k, v in stored.get("baseline", {}).items()}
            self.applied = {k: dict(v) for k, v in stored.get("applied", {}).items()}

    def _save(self) -> None:
        self._store.async_delay_save(self._data, 1)

    def _data(self) -> dict:
        return {
            "version": STORE_VERSION,
            "requested_offset": self._requested,
            "baseline": self.baseline,
            "applied": self.applied,
        }

    @property
    def requested_offset(self) -> float:
        return self._requested

    @property
    def mode(self) -> Optional[str]:
        """'wc' when the zone uses the climatic curve, 'fixed' otherwise, None if unknown."""
        coils = (self._coordinator.data or {}).get("coil_registers", {})
        value = coils.get(self._regs.wc_coil)
        if value is None:
            return None
        return "wc" if value else "fixed"

    def offset_limits(self) -> tuple[float, float]:
        """Offsets usable in the current mode; unbounded while the baseline is unknown."""
        base = self.baseline.get(self.mode or self._last_mode or "")
        if not base:
            return float("-inf"), float("inf")
        return offset_limits(list(base.values()), self._ceiling_for(base))

    @property
    def offset(self) -> float:
        """Effective offset: the smaller-magnitude shift actually applied after clamping."""
        mode = self.mode or self._last_mode or ""
        base, app = self.baseline.get(mode), self.applied.get(mode)
        if not base or not app:
            return self._requested
        return min((round(app[k] - base[k], 1) for k in base), key=abs)

    # -- register helpers ----------------------------------------------
    def _raw(self, register: int) -> Optional[int]:
        return (self._coordinator.data or {}).get("holding_registers", {}).get(register)

    def _register_for(self, key: str) -> int:
        return {"tm1": self._regs.tm1, "tm2": self._regs.tm2, "fixed": self._regs.fixed}[key]

    def _read_current(self, mode: str) -> Optional[dict[str, float]]:
        keys = ("tm1", "tm2") if mode == "wc" else ("fixed",)
        out = {}
        for key in keys:
            raw = self._raw(self._register_for(key))
            if raw is None:
                return None
            out[key] = round(raw * SCALE, 1)
        return out

    def _target(self, mode: str, base: dict[str, float], requested: float) -> dict[str, float]:
        """Register values for an offset. Never clamps below the user's own baseline.

        The offset stops where any value would hit a limit, so the curve never tilts.
        """
        ceiling = self._ceiling_for(base)
        low, high = offset_limits(list(base.values()), ceiling)
        requested = max(low, min(requested, high))
        if mode == "wc":
            tm1, tm2 = shift_curve(base["tm1"], base["tm2"], requested, ceiling)
            return {"tm1": round(tm1, 1), "tm2": round(tm2, 1)}
        return {"fixed": round(shift_fixed(base["fixed"], requested, ceiling), 1)}

    def _ceiling_for(self, base: dict[str, float]) -> float:
        return max(self._ceiling(), *base.values())

    # -- writing --------------------------------------------------------
    async def _apply(self, mode: str, requested: float) -> tuple[bool, bool]:
        """Write the shifted values for a mode. Returns (ok, wrote_anything)."""
        current = self._read_current(mode)
        if current is None:
            return False, False
        base = self.baseline.get(mode)
        if not base:
            base = self.baseline[mode] = dict(current)
        target = self._target(mode, base, requested)
        last = self.applied.get(mode, {})
        wrote = False
        self._writing = True
        try:
            for key, value in target.items():
                if last.get(key) == value and abs(current[key] - value) < 0.05:
                    continue
                if not await self._coordinator.async_write_register(
                    self._register_for(key), _to_raw(value)
                ):
                    self._suspect = True
                    return False, wrote
                wrote = True
        finally:
            self._writing = False
        self.applied[mode] = dict(target)
        return True, wrote

    async def async_set_offset(self, requested: float) -> bool:
        async with self._lock:
            mode = self.mode
            if mode is None or self._read_current(mode) is None:
                return False
            now = self._clock()
            if not self._limiter.can_write(now):
                return False
            ok, wrote = await self._apply(mode, requested)
            if not ok:
                return False
            self._requested = requested
            self._suspect = False
            self._tracker.reset()
            if wrote:
                self._limiter.record(now)
            self._save()
            return True

    # -- polling --------------------------------------------------------
    def on_coordinator_update(self) -> None:
        if self._writing:
            return
        mode = self.mode
        if mode is None:
            return
        current = self._read_current(mode)
        if current is None:
            return
        previous, self._last_mode = self._last_mode, mode
        if not self.baseline.get(mode):
            self.baseline[mode] = dict(current)
            self.applied[mode] = dict(current)
            if self._requested and previous is None:
                self._requested = 0.0
            self._save()
        elif mode not in self.applied:
            # Restart (trust the stored offset) or first visit to this mode (registers are unshifted)
            self.applied[mode] = (
                self._target(mode, self.baseline[mode], self._requested)
                if previous is None
                else dict(current)
            )
        if previous is not None and previous != mode:
            self._tracker.reset()
            if self._target(mode, self.baseline[mode], self._requested) != current:
                self._create_task(self._reapply(mode))
            return
        if self._suspect:
            return
        if self._tracker.update(current == self.applied[mode]):
            _LOGGER.info("Zone flow curve edited outside the integration; adopting it as the new baseline")
            self.baseline[mode] = dict(current)
            self.applied[mode] = dict(current)
            self._requested = 0.0
            self._tracker.reset()
            self._save()

    async def _reapply(self, mode: str) -> None:
        """Carry the shared offset across a WC/fixed mode flip."""
        async with self._lock:
            if self.mode != mode:
                return
            ok, wrote = await self._apply(mode, self._requested)
            if ok and wrote:
                self._limiter.record(self._clock())
            if ok:
                self._save()
