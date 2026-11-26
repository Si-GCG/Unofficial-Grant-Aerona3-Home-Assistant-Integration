from conftest import load

fo = load("flow_offset")


def test_shift_curve_parallel():
    assert fo.shift_curve(45, 30, 1, 55) == (46, 31)


def test_shift_curve_floor():
    assert fo.shift_curve(45, 30, -10, 55) == (35, 23)


def test_shift_curve_ceiling():
    assert fo.shift_curve(45, 30, 12, 55) == (55, 42)


def test_shift_curve_keeps_tm1_not_below_tm2():
    assert fo.shift_curve(24, 23, -5, 55) == (23, 23)
    assert fo.shift_curve(55, 50, 5, 55) == (55, 55)


def test_shift_fixed_clamps():
    assert fo.shift_fixed(45, 20, 55) == 55
    assert fo.shift_fixed(30, -20, 55) == 23


def test_effective_offset():
    assert fo.effective_offset(45, 46.5) == 1.5


def test_limiter_min_interval():
    lim = fo.WriteLimiter()
    lim.record(0)
    assert lim.can_write(1799) is False
    assert lim.can_write(1800) is True


def test_limiter_daily_cap():
    lim = fo.WriteLimiter()
    for i in range(24):
        lim.record(i * 1800)
    assert lim.can_write(24 * 1800) is False
    assert lim.can_write(86400 + 1) is True


def test_mismatch_needs_two_polls():
    t = fo.MismatchTracker()
    assert t.update(False) is False
    assert t.update(False) is True
    t.reset()
    assert t.update(False) is False
    assert t.update(True) is False
    assert t.update(False) is False


def test_trim_steps_up_when_cold():
    assert fo.next_trim_offset(0, 19.0, 21.0, 0.3, 0.5, 3.0) == 0.5


def test_trim_steps_down_when_warm():
    assert fo.next_trim_offset(0, 22.0, 21.0, 0.3, 0.5, 3.0) == -0.5


def test_trim_holds_inside_dead_band():
    assert fo.next_trim_offset(1.0, 21.2, 21.0, 0.3, 0.5, 3.0) == 1.0
    assert fo.next_trim_offset(1.0, 20.7, 21.0, 0.3, 0.5, 3.0) == 1.0


def test_trim_respects_cap():
    assert fo.next_trim_offset(3.0, 18.0, 21.0, 0.3, 0.5, 3.0) == 3.0
    assert fo.next_trim_offset(-3.0, 25.0, 21.0, 0.3, 0.5, 3.0) == -3.0


def test_grace_correction_replaces_change_and_does_not_count():
    lim = fo.WriteLimiter()
    lim.record(0)
    assert lim.can_write(60) is True
    lim.record(60)
    assert len(lim._times) == 1
    assert lim.can_write(1000) is False  # the 30-minute clock still runs from the first change


def test_grace_expires_after_two_minutes():
    lim = fo.WriteLimiter()
    lim.record(0)
    assert lim.can_write(119) is True
    assert lim.can_write(121) is False


def test_grace_corrections_are_limited_to_three():
    lim = fo.WriteLimiter()
    lim.record(0)
    for t in (10, 20, 30):
        assert lim.can_write(t) is True
        lim.record(t)
    assert lim.can_write(40) is False


def test_new_change_after_window_resets_grace():
    lim = fo.WriteLimiter()
    lim.record(0)
    lim.record(10)
    lim.record(2000)  # a genuine new change
    assert len(lim._times) == 2
    assert lim.can_write(2030) is True
