import asyncio

from conftest import load

fo = load("flow_offset")
fm = load("flow_offset_manager")


class FakeCoordinator:
    def __init__(self, holding=None, coils=None):
        self.data = {
            "holding_registers": dict(holding if holding is not None else {2: 450, 3: 450, 4: 300}),
            "coil_registers": dict(coils if coils is not None else {2: True}),
        }
        self.writes = []
        self.fail_on = None  # register address whose write should fail
        self.refreshes = True  # False mimics the debounced refresh not having run yet

    async def async_write_register(self, register, raw):
        await asyncio.sleep(0)  # let other tasks interleave, like the real bus lock
        if register == self.fail_on:
            return False
        self.writes.append((register, raw))
        if self.refreshes:
            self.data["holding_registers"][register] = raw
        return True


class FakeStore:
    def __init__(self, data=None):
        self._data = data
        self.saved = None

    async def async_load(self):
        return self._data

    def async_delay_save(self, data_func, delay=0):
        self.saved = data_func()


def make(coord=None, store=None, now=0.0, ceiling=55.0, limiter=None):
    coord = coord or FakeCoordinator()
    store = store or FakeStore()
    tasks = []
    clock = {"t": now}
    limiter = limiter or fo.WriteLimiter()
    ceiling_fn = ceiling if callable(ceiling) else (lambda: ceiling)
    mgr = fm.FlowOffsetManager(
        1, coord, store, ceiling_fn, limiter, lambda: clock["t"], tasks.append
    )
    asyncio.run(mgr.async_load())
    return mgr, coord, store, limiter, clock, tasks


def test_set_offset_writes_pair_in_wc_mode():
    mgr, coord, *_ = make()
    assert asyncio.run(mgr.async_set_offset(1.0)) is True
    assert sorted(coord.writes) == [(3, 460), (4, 310)]
    assert mgr.offset == 1.0


def test_set_offset_fixed_mode_writes_only_fixed():
    mgr, coord, *_ = make(FakeCoordinator(coils={2: False}))
    assert asyncio.run(mgr.async_set_offset(1.0)) is True
    assert coord.writes == [(2, 460)]


def test_effective_offset_after_clamp():
    mgr, *_ = make(FakeCoordinator(holding={2: 450, 3: 540, 4: 500}))
    asyncio.run(mgr.async_set_offset(5.0))
    assert mgr.offset == 1.0
    assert mgr.requested_offset == 5.0
    mgr2, *_ = make()
    asyncio.run(mgr2.async_set_offset(5.0))
    assert mgr2.offset == 5.0


def test_rate_limited_set_returns_false():
    mgr, coord, _, _, clock, _ = make()
    assert asyncio.run(mgr.async_set_offset(0.5)) is True
    clock["t"] = 300  # past the 2-minute grace window, inside the 30-minute gap
    n = len(coord.writes)
    assert asyncio.run(mgr.async_set_offset(1.0)) is False
    assert len(coord.writes) == n


def test_failed_write_not_counted_and_no_baseline_corruption():
    coord = FakeCoordinator()
    mgr, _, _, limiter, clock, _ = make(coord)
    coord.fail_on = 4
    assert asyncio.run(mgr.async_set_offset(1.0)) is False
    assert mgr.requested_offset == 0.0
    clock["t"] = 1  # a record would block this
    assert limiter.can_write(1900) is True and limiter._times == []
    for _ in range(3):
        mgr.on_coordinator_update()
    assert mgr.baseline["wc"] == {"tm1": 45.0, "tm2": 30.0}


def test_hand_edit_adopted_after_two_polls():
    mgr, coord, store, *_ = make()
    asyncio.run(mgr.async_set_offset(1.0))
    coord.data["holding_registers"].update({3: 480, 4: 330})
    mgr.on_coordinator_update()
    assert mgr.offset == 1.0
    mgr.on_coordinator_update()
    assert mgr.offset == 0.0
    assert mgr.baseline["wc"] == {"tm1": 48.0, "tm2": 33.0}
    assert store.saved["requested_offset"] == 0.0


def test_no_reset_when_registers_missing():
    mgr, coord, *_ = make()
    asyncio.run(mgr.async_set_offset(1.0))
    coord.data["holding_registers"].clear()
    for _ in range(3):
        mgr.on_coordinator_update()
    assert mgr.offset == 1.0


def test_restart_restores_without_writing():
    store = FakeStore(
        {"version": 1, "requested_offset": 1.0, "baseline": {"wc": {"tm1": 45.0, "tm2": 30.0}}}
    )
    mgr, coord, *_ = make(FakeCoordinator(holding={2: 450, 3: 460, 4: 310}), store)
    for _ in range(3):
        mgr.on_coordinator_update()
    assert coord.writes == []
    assert mgr.offset == 1.0


def test_mode_flip_applies_offset_to_new_mode_only():
    store = FakeStore(
        {
            "version": 1,
            "requested_offset": 1.0,
            "baseline": {"wc": {"tm1": 45.0, "tm2": 30.0}, "fixed": {"fixed": 45.0}},
        }
    )
    mgr, coord, _, _, _, tasks = make(
        FakeCoordinator(holding={2: 450, 3: 460, 4: 310}), store
    )
    mgr.on_coordinator_update()
    coord.data["coil_registers"][2] = False
    mgr.on_coordinator_update()
    for coro in tasks:
        asyncio.run(coro)
    assert coord.writes == [(2, 460)]


def test_ceiling_below_baseline_not_pulled_down():
    mgr, coord, store, *_ = make(FakeCoordinator(holding={2: 450, 3: 580, 4: 300}))
    for _ in range(3):
        mgr.on_coordinator_update()
    assert mgr.baseline["wc"] == {"tm1": 58.0, "tm2": 30.0}
    assert mgr.requested_offset == 0.0 and coord.writes == []
    asyncio.run(mgr.async_set_offset(0.5))
    assert coord.writes == [(4, 305)]  # Tm1 is never taken below its own baseline


def test_ceiling_change_does_not_adopt_offset_into_baseline():
    box = {"c": 55.0}
    mgr, coord, *_ = make(FakeCoordinator(holding={2: 450, 3: 540, 4: 300}), ceiling=lambda: box["c"])
    asyncio.run(mgr.async_set_offset(3.0))
    box["c"] = 60.0
    for _ in range(3):
        mgr.on_coordinator_update()
    assert mgr.baseline["wc"] == {"tm1": 54.0, "tm2": 30.0}
    assert mgr.requested_offset == 3.0


def test_flip_back_with_zero_offset_reapplies():
    mgr, coord, _, _, clock, tasks = make()
    asyncio.run(mgr.async_set_offset(2.0))  # WC: 470/320
    coord.data["coil_registers"][2] = False
    mgr.on_coordinator_update()
    for coro in tasks:
        asyncio.run(coro)
    tasks.clear()
    clock["t"] = 5000
    asyncio.run(mgr.async_set_offset(0.0))  # fixed mode back to baseline
    coord.data["coil_registers"][2] = True
    mgr.on_coordinator_update()
    for coro in tasks:
        asyncio.run(coro)
    assert coord.data["holding_registers"][3] == 450
    assert coord.data["holding_registers"][4] == 300
    for _ in range(3):
        mgr.on_coordinator_update()
    assert mgr.baseline["wc"] == {"tm1": 45.0, "tm2": 30.0}


def test_write_counted_even_if_data_not_refreshed():
    coord = FakeCoordinator()
    coord.refreshes = False
    mgr, _, _, limiter, *_ = make(coord)
    assert asyncio.run(mgr.async_set_offset(1.0)) is True
    assert len(limiter._times) == 1


def test_concurrent_sets_are_serialised():
    mgr, coord, *_ = make(limiter=fo.WriteLimiter(grace_s=0))  # grace off: second set must be refused

    async def both():
        return await asyncio.gather(mgr.async_set_offset(1.0), mgr.async_set_offset(2.0))

    assert asyncio.run(both()) == [True, False]
    assert sorted(coord.writes) == [(3, 460), (4, 310)]


def test_correction_within_grace_is_allowed_and_not_counted():
    mgr, coord, _, limiter, clock, _ = make()
    assert asyncio.run(mgr.async_set_offset(-0.5)) is True
    clock["t"] = 45
    assert asyncio.run(mgr.async_set_offset(0.0)) is True
    assert mgr.offset == 0.0
    assert len(limiter._times) == 1
