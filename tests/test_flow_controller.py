import json
import pathlib

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


def test_outdoor_average_drops_old_samples():
    a = fc.OutdoorAverage()
    a.add(0, 2)
    a.add(1800, 4)
    assert a.value(1800) == 3 and a.value(4000) == 4 and a.value(9000) is None


def test_correction_steps_every_two_hours():
    c = fc.LearnedCorrection()
    assert c.update(0, 0.5, 0) == 0 and c.update(7199, 0.5, 0) == 0
    assert c.update(7200, 0.5, 0) == 0.5
    assert c.update(14400, 0.5, 0) == 1.0


def run(c, error, limited=0, start=0, steps=1):
    c.update(start, error, limited)
    return c.update(start + 7200 * steps, error, limited)


def test_correction_pauses():
    assert run(fc.LearnedCorrection(), 0.3, 0) == 0  # inside dead band
    assert run(fc.LearnedCorrection(), 1.6, 0) == 0  # too far from target
    assert run(fc.LearnedCorrection(), None, 0) == 0
    assert run(fc.LearnedCorrection(), 0.5, 1) == 0  # already at maximum
    assert run(fc.LearnedCorrection(), -0.5, 1) == -0.5  # may still come down


def test_correction_restarts_when_error_changes_sign():
    c = fc.LearnedCorrection()
    c.update(0, 0.5, 0)
    assert c.update(3600, -0.5, 0) == 0
    assert c.update(7200, -0.5, 0) == 0
    assert c.update(10800, -0.5, 0) == -0.5


def test_correction_waits_after_target_change():
    c = fc.LearnedCorrection()
    c.target_changed(0)
    c.update(0, 0.5, 0)
    assert c.update(10799, 0.5, 0) == 0
    assert c.update(10800 + 7200, 0.5, 0) == 0.5


def test_correction_is_bounded():
    assert run(fc.LearnedCorrection(8.0), 0.5) == 8.0
    assert run(fc.LearnedCorrection(-8.0), -0.5) == -8.0


def test_write_threshold():
    assert not fc.should_write(35.5, 35.0, False) and fc.should_write(36.0, 35.0, False)
    assert fc.should_write(35.5, 35.0, True) and not fc.should_write(35.0, 35.0, True)


def test_translations_match_and_cover_errors():
    root = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "grant_aerona3"
    assert (root / "strings.json").read_text() == (root / "translations" / "en.json").read_text()
    options = json.loads((root / "strings.json").read_text())["options"]
    assert {"outdoor_points", "flow_points", "flow_limits"} <= options["error"].keys()
    assert "experimental_flow_controller" in options["step"]["init"]["data"]
    assert "flow_ctrl_sensor" in options["step"]["controller"]["data"]


def test_outdoor_source():
    data = {"input_registers": {6: 65533, 17: 55}, "coil_registers": {19: True}}
    assert fc.outdoor_temperature(data, True) == 5.5
    assert fc.outdoor_temperature(data, False) == -3
    data["coil_registers"][19] = False  # probe terminal not enabled: register 17 means nothing
    assert fc.outdoor_temperature(data, True) == -3
    data["coil_registers"][19] = True
    data["input_registers"][17] = 65535
    assert fc.outdoor_temperature(data, True) == -3
    assert fc.outdoor_temperature(None, True) is None


def test_preset_follows_schedule():
    assert fc.preset_for("off") == "eco"
    for state in ("on", None, "unavailable"):
        assert fc.preset_for(state) == "comfort"
