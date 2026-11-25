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
