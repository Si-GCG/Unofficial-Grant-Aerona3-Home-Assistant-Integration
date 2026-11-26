from conftest import load

load("flow_offset")
fc = load("flow_controller")
S = fc.Settings()


def test_base_line():
    assert fc.base_flow(-3, S) == 40 and fc.base_flow(15, S) == 28
    assert fc.base_flow(6, S) == 34 and fc.base_flow(18, S) == 26


def test_room_below_target_raises_flow():
    r = fc.calculate(6, 19, 20, 0, S)
    assert (r.flow, r.base, r.target_term, r.room_term, r.limited) == (36, 34, 0, 2, 0)


def test_setback_hits_minimum():
    r = fc.calculate(6, 20, 17, 0, S)
    assert (r.flow, r.limited) == (25, -1)


def test_maximum_and_rounding():
    assert fc.calculate(-10, 18, 20, 0, S).flow == 48.5
    r = fc.calculate(-10, 18, 20, 0, fc.Settings(max_flow=45))
    assert (r.flow, r.limited) == (45, 1)


def test_no_room_uses_outdoor_and_correction_only():
    assert fc.calculate(6, None, 17, 1.5, S).flow == 35.5


def test_never_below_unit_floor():
    assert fc.calculate(30, None, 20, 0, fc.Settings(min_flow=10)).flow == 23


def test_bad_settings():
    assert fc.settings_error(S) is None
    assert fc.settings_error(fc.Settings(cold_outdoor=15)) == "outdoor_points"
    assert fc.settings_error(fc.Settings(cold_flow=20)) == "flow_points"
    assert fc.settings_error(fc.Settings(min_flow=55)) == "flow_limits"
    assert fc.base_flow(0, fc.Settings(cold_outdoor=15)) == 40


def test_decoding():
    assert fc.decode_temperature(65533, 1) == -3
    assert fc.decode_temperature(65535, 1) is None
    assert fc.decode_temperature(None, 1) is None
    assert fc.decode_temperature(65506, 0.1) == -3.0


def test_parse_room():
    assert fc.parse_room("19.7") == 19.7
    for bad in (None, "unknown", "nan", "inf", "68"):
        assert fc.parse_room(bad) is None
