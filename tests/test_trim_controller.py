from conftest import load

tc = load("trim_controller")


def decide(**kw):
    args = dict(
        enabled=True, cooling=False, room=19.0, room_age_s=60.0, target=21.0,
        current_offset=0.0, dead_band=0.3, cap=3.0, pending_reset=False,
    )
    args.update(kw)
    return tc.decide(**args)


def test_off_with_pending_reset_returns_zero_offset():
    d = decide(enabled=False, current_offset=1.5, pending_reset=True)
    assert d.new_offset == 0.0 and d.reason == "off"


def test_off_without_pending_reset_leaves_manual_offset():
    d = decide(enabled=False, current_offset=1.5)
    assert d.new_offset is None and d.reason == "off"


def test_cooling_does_nothing():
    d = decide(cooling=True)
    assert d.new_offset is None and d.reason == "cooling"


def test_unavailable_sensor_returns_zero():
    d = decide(room=None, current_offset=1.0)
    assert d.new_offset == 0.0 and d.reason == "sensor_unavailable"


def test_stale_sensor_returns_zero():
    d = decide(room_age_s=21601, current_offset=1.0)
    assert d.new_offset == 0.0 and d.reason == "sensor_stale"


def test_cold_room_steps_up():
    d = decide()
    assert d.new_offset == 0.5 and d.reason == "stepped"


def test_in_dead_band_holds():
    d = decide(room=21.2)
    assert d.new_offset is None and d.reason == "in_dead_band"


def test_pinned_at_cap_reports_reason():
    d = decide(room=18.0, current_offset=3.0)
    assert d.new_offset is None and d.reason == "at_cap"


def test_zero_offset_when_already_zero_is_no_change():
    d = decide(enabled=False, current_offset=0.0, pending_reset=True)
    assert d.new_offset is None and d.reason == "off"


def test_unchanged_sensor_is_trusted_for_six_hours():
    # an average sensor holding one value for 2h28m reset the offset on real hardware
    d = decide(room_age_s=21599, current_offset=-1.0)
    assert d.new_offset == -0.5 and d.reason == "stepped"


def test_does_not_step_below_the_curve_limit():
    d = decide(room=23.0, current_offset=-2.0, low=-2.0, high=18.0)
    assert d.new_offset is None and d.reason == "at_cap"


def test_step_up_starts_from_the_limit_when_request_is_beyond_it():
    d = decide(current_offset=-3.0, low=-2.0, high=18.0)
    assert d.new_offset == -1.5 and d.reason == "stepped"


def test_does_not_step_above_the_curve_limit():
    d = decide(room=18.0, current_offset=1.0, low=-2.0, high=1.0)
    assert d.new_offset is None and d.reason == "at_cap"
