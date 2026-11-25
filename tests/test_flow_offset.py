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
