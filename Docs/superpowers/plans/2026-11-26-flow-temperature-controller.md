# Flow Temperature Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An optional, experimental Zone 1 controller that chooses the fixed flow temperature from outdoor temperature, corrected by room temperature, on a two-temperature schedule.

**Architecture:** Pure logic (`flow_controller.py`, `flow_control_manager.py`) with no Home Assistant imports and injected collaborators, as the flow offset does it. Stage 1 adds a read-only preview sensor on top of the calculation; stage 2 adds the manager and a `climate` entity that writes.

**Tech Stack:** Python, Home Assistant custom integration, pytest for the pure modules.

**Spec:** `docs/superpowers/specs/2026-11-26-flow-temperature-controller-design.md`

## Global Constraints

- Zone 1 only, heating only. Holding register 2 (fixed setpoint, raw = °C × 10, 0.5 °C steps), coil 2 (off = fixed), input 6 outdoor (scale 1), input 17 outdoor when `has_remote_outdoor_sensor` is on (scale 0.1), input 10 == 2 means cooling.
- Writes: 24 a day, 30 minutes apart, via one `WriteLimiter` shared with the flow offset.
- Defaults: 40 °C flow at -3 °C, 28 °C at 15 °C, minimum 25 °C (never below 23), maximum `max_flow_temp` (55). Comfort 20 °C, eco 17 °C.
- Feature key `experimental_flow_controller`, default off, unique_id suffixes listed in `FEATURE_UNIQUE_ID_SUFFIXES`.
- `translations/en.json` is an exact copy of `strings.json`.
- `flow_controller.py` and `flow_control_manager.py` import nothing from Home Assistant; use the `try: from .x / except ImportError: from x` pattern of `trim_controller.py`.
- Never pass `update_before_add=True` to `async_add_entities`.
- Tests: `.venv/bin/pytest tests`. Before each commit also run the `validate` skill.
- Work on a branch `feature/flow-controller`, not `main`. First commit adds the spec and this plan.

All paths below are relative to `custom_components/grant_aerona3/` unless they start with `tests/` or `Docs/`.

## Review Focus

- Curve points or limits that make no sense (cold outdoor ≥ mild outdoor, min > max): rejected in options; the calculation never divides by zero. (Tasks 1, 3)
- Outdoor register below zero (two's complement) or 65535: -3 reads as -3, 65535 as missing. (Task 1)
- Room sensor reporting `nan`, text or Fahrenheit (68): treated as unavailable. (Task 1)
- Home Assistant restart while controlling: the user's saved setpoint is not overwritten by the controller's own value. (Task 6)
- Turn on twice, or off when never on: no writes, saved state unchanged. (Task 6)

## Deviations from the spec

- The "trim and controller cannot both be enabled" rule starts in stage 2 (Task 7), so the preview can run beside the trim.
- The unit does not report the flow target its own curve is using, so the preview shows measured outgoing water temperature (input 9) for comparison.

---

## Stage 1: preview

### Task 1: The calculation

**Files:** Create `flow_controller.py`; Test `tests/test_flow_controller.py`

**Interfaces (Produces):**
- `Settings(cold_outdoor=-3.0, cold_flow=40.0, mild_outdoor=15.0, mild_flow=28.0, min_flow=25.0, max_flow=55.0)` frozen dataclass
- `settings_error(s: Settings) -> str | None`: `"outdoor_points"` if cold_outdoor >= mild_outdoor, `"flow_points"` if cold_flow < mild_flow, `"flow_limits"` if min_flow >= max_flow
- `base_flow(outdoor: float, s: Settings) -> float`: straight line, extended beyond the points; returns cold_flow if the outdoor points coincide
- `Result(flow, base, target_term, room_term, correction, limited)`; `limited` is -1 (at minimum), 0 or 1 (at maximum)
- `calculate(outdoor, room: float | None, target, correction, s) -> Result`
- `decode_temperature(raw: int | None, scale: float) -> float | None`: None for None or 65535; above 32767 subtract 65536
- `parse_room(text: str | None) -> float | None`: finite and within -10 to 45, else None

- [ ] **Step 1: Write the failing tests** (`fc = load("flow_controller")`, `S = fc.Settings()`)

```python
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
    assert fc.decode_temperature(65535, 1) is None and fc.decode_temperature(None, 1) is None
    assert fc.decode_temperature(65506, 0.1) == -3.0

def test_parse_room():
    assert fc.parse_room("19.7") == 19.7
    for bad in (None, "unknown", "nan", "inf", "68"):
        assert fc.parse_room(bad) is None
```

- [ ] **Step 2:** `.venv/bin/pytest tests/test_flow_controller.py` → FAIL (module missing)
- [ ] **Step 3: Implement.** `flow = base + 1.0*(target-20) + 2.0*(target-room) + correction`; with `room=None`, `flow = base + correction` and both terms are 0. Clamp to `max(min_flow, 23)` and `max_flow`, then round to 0.5. Constants (`TARGET_REFERENCE`, `TARGET_GAIN`, `ROOM_GAIN`) are module level.
- [ ] **Step 4:** tests PASS
- [ ] **Step 5:** Commit `feat: flow controller calculation`

### Task 2: Outdoor average, learned correction, write threshold

**Files:** Modify `flow_controller.py`; Test `tests/test_flow_controller.py`

**Interfaces (Produces):**
- `OutdoorAverage(window_s=3600.0)`: `add(now, value: float)`, `value(now) -> float | None` (mean of samples inside the window)
- `LearnedCorrection(value=0.0)`: attribute `value`; `target_changed(now)`; `update(now, error: float | None, limited: int) -> float` where `error = target - room`
- `should_write(calculated: float, current: float, after_target_change: bool) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
def test_outdoor_average_drops_old_samples():
    a = fc.OutdoorAverage()
    a.add(0, 2); a.add(1800, 4)
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
    assert run(fc.LearnedCorrection(), 0.3, 0) == 0     # inside dead band
    assert run(fc.LearnedCorrection(), 1.6, 0) == 0     # too far from target
    assert run(fc.LearnedCorrection(), None, 0) == 0
    assert run(fc.LearnedCorrection(), 0.5, 1) == 0     # already at maximum
    assert run(fc.LearnedCorrection(), -0.5, 1) == -0.5 # may still come down

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
```

- [ ] **Step 2:** FAIL
- [ ] **Step 3: Implement.** `update` is called every 10 minutes, so it holds the time the current run of eligible, same-sign error started; any pause or sign change clears it; each completed 7200 s moves one 0.5 step and restarts the run. Round the error to 6 places before comparing.
- [ ] **Step 4:** PASS
- [ ] **Step 5:** Commit `feat: flow controller averaging, learned correction, write threshold`

### Task 3: Feature key and options

**Files:** Modify `const.py`, `features.py` (`BOOLEAN_FEATURE_KEYS`), `config_flow.py` (`OptionsFlowHandler`), `strings.json`, `translations/en.json`, `__init__.py` (`FEATURE_UNIQUE_ID_SUFFIXES`); Test `tests/test_flow_controller.py`

**Interfaces:**
- Consumes: `Settings`, `settings_error`
- Produces in `const.py`: `CONF_EXPERIMENTAL_FLOW_CONTROLLER = "experimental_flow_controller"`; `CONF_FC_SENSOR`, `CONF_FC_SCHEDULE`, `CONF_FC_COLD_OUTDOOR`, `CONF_FC_COLD_FLOW`, `CONF_FC_MILD_OUTDOOR`, `CONF_FC_MILD_FLOW`, `CONF_FC_MIN_FLOW` (string values `flow_ctrl_sensor`, `flow_ctrl_schedule`, `flow_ctrl_cold_outdoor`, ...)
- Produces in `features.py`: `flow_controller_settings(entry) -> Settings` (max_flow from `max_flow_temp`)

- [ ] **Step 1:** Add the feature key with `DEFAULT_FEATURES[...] = False`, add it to `BOOLEAN_FEATURE_KEYS`, and register suffixes `("flow_preview",)`.
- [ ] **Step 2:** Add the checkbox to the options `init` step and a new `controller` step, reached after `init` (or after `trim` when both are on), keeping the input gathered so far. Sensor: required temperature `EntitySelector`. Schedule: optional `EntitySelector(domain="schedule")` using `suggested_value` so it can be cleared. Five numbers with the Global Constraints defaults, ranges: outdoor -20 to 25, flow 23 to 60. Show `settings_error` results as form errors. Show the trim step's coil 7 warning here too.
- [ ] **Step 3:** Add strings and error texts for `outdoor_points`, `flow_points`, `flow_limits`; copy to `translations/en.json`.
- [ ] **Step 4: Test the files agree**

```python
def test_translations_match_and_cover_errors():
    root = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "grant_aerona3"
    assert (root / "strings.json").read_text() == (root / "translations" / "en.json").read_text()
    errors = json.loads((root / "strings.json").read_text())["options"]["error"]
    assert {"outdoor_points", "flow_points", "flow_limits"} <= errors.keys()
```

- [ ] **Step 5:** `.venv/bin/pytest tests` PASS, `validate` PASS
- [ ] **Step 6:** Commit `feat: options for the experimental flow controller`

### Task 4: Preview sensor and pre-release

**Files:** Create `flow_preview.py`; Modify `sensor.py` (`async_setup_entry`), `manifest.json`, `README.md`, `Docs/configuration_guide.md`

**Interfaces:**
- Consumes: Tasks 1-3
- Produces: `class FlowInputs(hass, coordinator, entry)` with `outdoor_now() -> float | None` (None when the last poll failed), `room_now(now) -> float | None` (`parse_room`, None if older than 21600 s), `preset_now() -> str` (`"eco"` only when the schedule state is `off`, else `"comfort"`). Task 7 reuses it.
- Produces: `GrantAerona3FlowPreviewSensor`, unique_id `ashp_{entry_id}_flow_preview`, name "Zone 1 suggested flow temperature"

- [ ] **Step 1:** Implement both classes. The sensor adds an outdoor sample on every coordinator update, recalculates when added and every 10 minutes, uses targets 20 / 17, correction 0, and writes nothing. State: `Result.flow`, unknown without an outdoor average. Attributes: `base`, `target_term`, `room_term`, `target`, `preset`, `room`, `outdoor_average`, `limited`, `outgoing_water_temperature`.
- [ ] **Step 2:** Add it in `sensor.py` only when the feature is in `coordinator.features` and a sensor is set.
- [ ] **Step 3:** Confirm no write path: `grep -n "async_write" custom_components/grant_aerona3/flow_preview.py` → no output.
- [ ] **Step 4:** Document the feature, the base points, and that an external thermostat must keep calling for heat. Version `1.4.0b1`.
- [ ] **Step 5:** `.venv/bin/pytest tests` and `validate` PASS; commit `feat: flow controller preview sensor`

**STOP.** Stage 1 goes to the maintainer's heat pump for several days. Publishing it needs their go-ahead. Do not start stage 2 until they have reviewed the preview values; constants may change.

---

## Stage 2: control

### Task 5: Pause the flow offset; share the limiter

**Files:** Modify `flow_offset_manager.py`, `__init__.py`, `number.py`; Test `tests/test_flow_offset_manager.py`

**Interfaces (Produces):** `FlowOffsetManager.suspend() -> None`, `resume() -> None`, attribute `suspended: bool`

- [ ] **Step 1: Write the failing tests** using the existing `make()` helper

```python
def test_suspended_refuses_and_ignores_changes():
    # make, poll once, suspend; set holding[2]=300, coil 2 False; poll three times
    # await async_set_offset(1.0) is False; no writes; baseline unchanged; no tasks created

def test_resume_tolerates_stale_polls():
    # suspend, change holding[3] to 300, resume, poll twice (stale), restore 450, poll
    # baseline["wc"] unchanged and requested_offset unchanged

def test_resume_still_detects_a_real_edit():
    # suspend, resume, set holding[3]=400, poll 7 times -> baseline["wc"]["tm1"] == 40.0
```

Write these bodies in full in the style of the existing tests in that file.

- [ ] **Step 2:** FAIL
- [ ] **Step 3: Implement.** After `resume()`, ignore mismatches until the registers match `applied` once or 5 polls have passed. Move `WriteLimiter()` into `async_setup_entry` and pass it to `_async_setup_flow_offsets`. The offset number's error message names the flow controller when suspended.
- [ ] **Step 4:** all tests PASS
- [ ] **Step 5:** Commit `feat: allow the flow offset to be paused`

### Task 6: Control manager

**Files:** Create `flow_control_manager.py`; Test `tests/test_flow_control_manager.py`

**Interfaces:**
- Consumes: `should_write`, `WriteLimiter`, `suspend/resume`
- Produces: `FlowControlManager(coordinator, store, limiter, clock, offset_manager | None, on_released: Callable[[], None])`
  - `async_load()`, properties `active: bool`, `restore_pending: bool`, `saved: dict | None` (`{"coil": bool, "fixed": int}`)
  - `async_turn_on(flow: float) -> bool`
  - `async_apply(flow: float, after_target_change: bool) -> str`: `written`, `no_change`, `limited`, `write_failed`, `cooling`, `inactive`
  - `async_turn_off() -> bool`, `async_retry_restore() -> bool`
  - `on_coordinator_update() -> None`
  - `next_write_in(now) -> float` (seconds, 0 if allowed; add the query to `WriteLimiter`)

- [ ] **Step 1: Write the failing tests.** Fake coordinator with `async_write_register` and `async_write_coil`, start state coil 2 True, holding[2] = 450.

| Test | Assertion |
|---|---|
| `test_turn_on_saves_then_switches` | saved == `{"coil": True, "fixed": 450}`; writes: register 2 = 360, then coil 2 False |
| `test_turn_on_failure_restores` | coil write fails → returns False, holding[2] back to 450, `active` False, offset resumed |
| `test_turn_on_refused_by_limiter_or_unknown_registers` | False, no writes |
| `test_turn_on_refused_in_cooling` | input[10] = 2 → False, no writes |
| `test_apply_threshold_and_limit` | +0.5 → `no_change`; +2 within 30 min → `limited`; after 1800 s → `written` |
| `test_apply_cooling_and_failure` | `cooling` / `write_failed`, nothing recorded in the limiter |
| `test_turn_off_restores_despite_limiter` | register 2 = 450 then coil 2 True; offset resumed |
| `test_failed_restore_is_retried` | `restore_pending` True, offset still suspended, retry succeeds |
| `test_restart_keeps_original_saved` | new manager on the same store is `active`, offset suspended, `saved["fixed"] == 450` |
| `test_double_on_and_off_when_off` | second on returns True with no writes; off when never on writes nothing |
| `test_external_edit_releases` | after our value is seen once, two polls of a different holding[2] or coil → `active` False, no writes, `on_released` called once |
| `test_stale_poll_after_write_is_not_an_edit` | two polls still showing the old value, then ours → still active |

- [ ] **Step 2:** FAIL
- [ ] **Step 3: Implement.** One `asyncio.Lock`; ignore polls while writing; judge external edits only after a poll has confirmed the written values, or after 5 polls without confirmation. Write the setpoint before the coil, both turning on and restoring. Persist `{version: 1, active, saved, written, restore_pending}` immediately on every change. Releasing after an external edit also resumes the offset manager.
- [ ] **Step 4:** PASS
- [ ] **Step 5:** Commit `feat: flow control manager`

### Task 7: Climate entity, wiring and pre-release

**Files:** Create `flow_control_climate.py`; Modify `climate.py`, `__init__.py`, `config_flow.py`, `strings.json`, `translations/en.json`, `diagnostics.py`, `manifest.json`, `README.md`, `Docs/configuration_guide.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: `FlowInputs`, `LearnedCorrection`, `OutdoorAverage`, `calculate`, `FlowControlManager`
- Produces: climate "Zone 1 flow controller", unique_id `ashp_{entry_id}_flow_controller` (add the `flow_controller` suffix)

- [ ] **Step 1:** Build the entity: modes `heat`/`off` (off until turned on), presets `comfort`/`eco`, target 15 to 25 in 0.5 steps applying to the active preset, `RestoreEntity` for preset temperatures and any manual preset, correction kept in the manager's store. A manual preset holds until the schedule state next changes. Tick every 10 minutes: retry restore, update correction, calculate, `async_apply`; hold if no outdoor average. A target change calls `target_changed`, then ticks at once and keeps `after_target_change` set until the write succeeds or is not needed. Attributes: `calculated_flow`, `written_flow`, `base`, `target_term`, `room_term`, `learned_correction`, `last_reason`, `next_write_in_s`.
- [ ] **Step 2:** `climate.py`: set up trim and controller independently (the trim's early return must not skip the controller).
- [ ] **Step 3:** `__init__.py`: create the manager when the feature is on **or** the store says `active`/`restore_pending`; if the feature is off, turn off (restore) during setup. Unload and restart do not restore. `on_released` raises a persistent notification and sets the entity to off.
- [ ] **Step 4:** Options flow rejects trim plus controller with error `controller_excludes_trim`; extend the Task 3 test to include it.
- [ ] **Step 5:** Diagnostics include the manager's state. Update docs, add a CLAUDE.md section beside the flow offset one. Version `1.4.0b2`.
- [ ] **Step 6:** `.venv/bin/pytest tests` and `validate` PASS; commit `feat: experimental flow temperature controller`
- [ ] **Step 7: Maintainer test on the heat pump:** turn on (curve coil goes off, setpoint written), turn off (previous setpoint and coil return), restart while on, change the setpoint at the remote controller (controller releases), disable in options while on (restores). Publishing needs their go-ahead.
