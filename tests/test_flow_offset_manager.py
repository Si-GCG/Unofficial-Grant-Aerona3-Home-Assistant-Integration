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

    async def async_write_register(self, register, raw):
        if register == self.fail_on:
            return False
        self.writes.append((register, raw))
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


def make(coord=None, store=None, now=0.0, ceiling=55.0):
    coord = coord or FakeCoordinator()
    store = store or FakeStore()
    tasks = []
    clock = {"t": now}
    limiter = fo.WriteLimiter()
    mgr = fm.FlowOffsetManager(
        1, coord, store, lambda: ceiling, limiter, lambda: clock["t"], tasks.append
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
    clock["t"] = 100
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
