# Flow Offset and Room Trim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-zone flow-temperature offset (number entities) and an optional room-temperature trim loop (`climate` entity) that moves that offset slowly.

**Architecture:** A pure-Python module (`flow_offset.py`, no Home Assistant imports) holds the curve maths, write limiter, hand-edit detector and trim step, so it can be unit-tested with plain pytest. A `FlowOffsetManager` per zone owns the stored baseline and applied offset and writes through the coordinator. Platforms (`number`, `climate`) are thin wrappers over the manager.

**Tech Stack:** Python 3.14, Home Assistant custom integration (`Store`, `CoordinatorEntity`, `RestoreEntity`), pytest for the pure modules only.

**Spec:** `Docs/superpowers/specs/2026-11-25-flow-offset-and-room-trim-design.md` (read it first; this plan refers to its section names).

## Global Constraints

- Flow floor 23.0°C; ceiling is the option `max_flow_temp`, default 55.0, allowed 30.0–60.0, step 0.5.
- Offset range −5.0 to +5.0, step 0.5, default 0. Only Tm1 and Tm2 (or the fixed setpoint) move; **Te1/Te2 are never written**. Cooling registers are never written.
- Zone 1 registers: fixed 2, Tm1 3, Tm2 4, WC-enable coil 2. Zone 2: fixed 7, Tm1 8, Tm2 9, WC-enable coil 3. Coil value 1 = climatic (WC) curve, 0 = fixed. Register scale 0.1 (raw 450 = 45.0°C). Coil 7: 0 = room set point, 1 = water set point (default 1).
- Write cap: at most 24 offset changes in a rolling 24 hours, at least 1800 s between changes; applies to manual changes and the trim loop; only successful writes count.
- Trim defaults: interval 30 min, dead band 0.3°C, step 0.5°C, cap ±3.0°C; sensor stale after 2 h. Trim `climate` HVAC modes: `heat`, `off` only.
- Never default the trim sensor to input registers 33/34.
- `strings.json` and `translations/en.json` stay identical. New hand-written entities get their unique_id suffix in `FEATURE_UNIQUE_ID_SUFFIXES` (`__init__.py`); `Platform.CLIMATE` is added to `PLATFORMS`.
- Do not pass `update_before_add=True`. Do not bump the version or tag a release (release only on the maintainer's request).
- Commit messages end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Run the `validate` skill before every commit that touches `custom_components/`.

## Review Focus

1. Registers read back as missing (`None`) right after startup or a failed poll: no writes, no hand-edit reset, offset keeps its stored value. (Task 3)
2. Home Assistant restart with an offset applied: stored offset reloaded, registers match baseline+offset, nothing is reset or rewritten. (Task 3)
3. Trim sensor state `unknown`, `unavailable`, non-numeric, or older than 2 h: offset returns to 0, no exception. (Task 5)
4. A write of the Tm1/Tm2 pair fails halfway: the failed write is not counted against the cap, state is not recorded as applied, and the next tick retries. (Task 3)
5. Unit is in cooling mode (input register 10 = 2): the trim does nothing. (Task 5)

---

### Task 1: Pure curve maths

**Files:**
- Create: `custom_components/grant_aerona3/flow_offset.py`
- Create: `tests/conftest.py`, `tests/test_flow_offset.py`

**Interfaces:**
- Produces (all in `flow_offset.py`): `FLOOR_C: float = 23.0`; `clamp_flow(value: float, ceiling: float) -> float`; `shift_curve(tm1: float, tm2: float, offset: float, ceiling: float) -> tuple[float, float]`; `shift_fixed(fixed: float, offset: float, ceiling: float) -> float`; `effective_offset(base: float, applied: float) -> float`.

- [ ] **Step 1: Set up test tooling.** Create a venv and install pytest: `python3 -m venv .venv && .venv/bin/pip install pytest`. Make sure `.venv/` is in `.gitignore`. `tests/conftest.py` must load `flow_offset.py` (and later modules that import no Home Assistant code) by file path with `importlib.util.spec_from_file_location`, because importing the package would run `__init__.py`, which needs Home Assistant. Expose a `load(name)` helper.
- [ ] **Step 2: Write failing tests** in `tests/test_flow_offset.py`: `test_shift_curve_parallel` (`shift_curve(45, 30, 1, 55) == (46, 31)`), `test_shift_curve_floor` (`(45, 30, -10, 55) == (35, 23)`), `test_shift_curve_ceiling` (`(45, 30, 12, 55) == (55, 42)`), `test_shift_curve_keeps_tm1_not_below_tm2` (`(24, 23, -5, 55) == (23, 23)` and `(55, 50, 5, 55) == (55, 55)`), `test_shift_fixed_clamps` (`shift_fixed(45, 20, 55) == 55`, `shift_fixed(30, -20, 55) == 23`), `test_effective_offset` (`effective_offset(45, 46.5) == 1.5`).
- [ ] **Step 3: Run** `.venv/bin/pytest tests -v`; expected: collection/import FAIL.
- [ ] **Step 4: Implement** the five names above. Tm2 is clamped first; Tm1 is `max(clamp(tm1+offset), tm2_new)`.
- [ ] **Step 5: Run** the tests; expected: all PASS.
- [ ] **Step 6: Commit** `tests/`, `flow_offset.py`, `.gitignore`.

### Task 2: Write limiter, mismatch tracker, trim step

**Files:**
- Modify: `custom_components/grant_aerona3/flow_offset.py`
- Modify: `tests/test_flow_offset.py`

**Interfaces:**
- Produces: `class WriteLimiter(max_per_day: int = 24, min_interval_s: float = 1800.0)` with `can_write(now: float) -> bool` and `record(now: float) -> None` (rolling 86400 s window; `now` in seconds); `class MismatchTracker(polls_required: int = 2)` with `update(matches: bool) -> bool` (True once `polls_required` consecutive mismatches; a match resets the count) and `reset() -> None`; `next_trim_offset(current: float, room: float, target: float, dead_band: float, step: float, cap: float) -> float`.

- [ ] **Step 1: Write failing tests:** `test_limiter_min_interval` (record at t=0; `can_write(1799)` False; `can_write(1800)` True), `test_limiter_daily_cap` (24 records spaced 1800 s apart from t=0 fill the window; `can_write(24*1800)` is False until the first record is more than 86400 s old; `can_write(86400+1)` True), `test_mismatch_needs_two_polls` (`update(False)` False then True; a `update(True)` in between resets), `test_trim_steps_up_when_cold` (`next_trim_offset(0, 19.0, 21.0, 0.3, 0.5, 3.0) == 0.5`), `test_trim_steps_down_when_warm` (`(0, 22.0, 21.0, ...) == -0.5`), `test_trim_holds_inside_dead_band` (`(1.0, 21.2, 21.0, ...) == 1.0`), `test_trim_respects_cap` (`(3.0, 18.0, 21.0, ...) == 3.0` and `(-3.0, 25.0, 21.0, ...) == -3.0`).
- [ ] **Step 2: Run** them; expected: FAIL (names not defined).
- [ ] **Step 3: Implement** the three names. Dead band is exclusive: an error exactly equal to `dead_band` holds.
- [ ] **Step 4: Run** the full suite; expected: all PASS.
- [ ] **Step 5: Commit.**

### Task 3: FlowOffsetManager (baseline, persistence, applying)

**Files:**
- Create: `custom_components/grant_aerona3/flow_offset_manager.py` (no Home Assistant imports; collaborators injected)
- Modify: `custom_components/grant_aerona3/const.py` (add `ZONE_FLOW_REGISTERS = {1: ZoneRegisters(fixed=2, tm1=3, tm2=4, wc_coil=2), 2: ZoneRegisters(fixed=7, tm1=8, tm2=9, wc_coil=3)}` as a small frozen dataclass or NamedTuple, plus `CONF_MAX_FLOW_TEMP = "max_flow_temp"`, `DEFAULT_MAX_FLOW_TEMP = 55.0`)
- Create: `tests/test_flow_offset_manager.py` (with a fake coordinator and fake store)

**Interfaces:**
- Consumes: Task 1 and 2 names. Coordinator contract: `coordinator.data["holding_registers"]` (raw ints by address), `coordinator.data["coil_registers"]` (bools by address), `await coordinator.async_write_register(register: int, raw: int) -> bool`. Store contract: `await store.async_load() -> dict | None`, `await store.async_save(data: dict) -> None`.
- Produces: `class FlowOffsetManager(zone: int, coordinator, store, ceiling: Callable[[], float], limiter: WriteLimiter, clock: Callable[[], float])` with `async async_load() -> None`; properties `offset: float` (effective, after clamping) and `requested_offset: float`; `async async_set_offset(requested: float) -> bool` (False if refused by the limiter, a write failed, or data is unavailable); `on_coordinator_update() -> None` (hand-edit detection); `mode: str` (`"wc"` or `"fixed"`, from the zone's WC coil).
- Store schema (my call; keep it versioned): `{"version": 1, "requested_offset": float, "baseline": {"wc": {"tm1": float, "tm2": float}, "fixed": {"fixed": float}}}` — separate baselines per mode.

- [ ] **Step 1: Write failing tests** with fakes: `test_set_offset_writes_pair_in_wc_mode` (WC coil on, Tm1=450, Tm2=300 raw, `async_set_offset(1.0)` writes registers 3→460 and 4→310, `offset == 1.0`), `test_set_offset_fixed_mode_writes_only_fixed` (coil off, fixed raw 450 → register 2 gets 460, registers 3/4 untouched), `test_effective_offset_after_clamp` (the effective offset in WC mode is the smaller-magnitude of the two applied shifts, keeping the sign of the request: baseline 45/30, ceiling 55, request +5 → `offset == 5.0`; baseline 54/50, request +5 → Tm1 55 (+1), Tm2 55 (+5), so `offset == 1.0` while `requested_offset == 5.0`), `test_rate_limited_set_returns_false` (second call within 1800 s returns False and writes nothing), `test_failed_write_not_counted` (fake write returns False on the second register: result False, limiter has no new record, stored offset unchanged), `test_hand_edit_adopted_after_two_polls` (registers changed externally; first `on_coordinator_update()` keeps offset, second adopts the new values as baseline and sets offset to 0 and saves), `test_no_reset_when_registers_missing` (holding data lacks the register: nothing changes), `test_restart_restores_without_writing` (store holds offset 1.0 and baseline 45/30, registers read 460/310: after `async_load()` and an update, no writes and `offset == 1.0`), `test_mode_flip_uses_separate_baseline` (flip coil from on to off: next set uses the fixed baseline; WC registers untouched).
- [ ] **Step 2: Run** and confirm they fail.
- [ ] **Step 3: Implement `FlowOffsetManager`** in `flow_offset_manager.py` per the Interfaces above. First load: if the store is empty, take the baseline from the current registers (when available). Pair writes set an internal `_writing` flag so `on_coordinator_update()` ignores polls during a write. Compare read-back against the *clamped* expected values (Task 1 functions). A failed write leaves the stored offset unchanged and does not call `limiter.record`.
- [ ] **Step 4: Run** the full suite; expected: all PASS.
- [ ] **Step 5: Validate and commit** (run the `validate` skill; commit `const.py`, the new module and tests).

### Task 4: Flow offset number entities (releasable stage 1)

**Files:**
- Modify: `custom_components/grant_aerona3/__init__.py` (create managers, attach to the coordinator, extend `FEATURE_UNIQUE_ID_SUFFIXES`), `number.py`, `strings.json`, `translations/en.json`

**Interfaces:**
- Consumes: Task 3's `FlowOffsetManager`.
- Produces: `coordinator.flow_offsets: dict[int, FlowOffsetManager]` (key = zone, Zone 2 only when `FEATURE_ZONE2` is enabled); `class GrantAerona3FlowOffsetNumber(CoordinatorEntity, NumberEntity)` in `number.py` with unique_id `f"ashp_{entry.entry_id}_flow_offset_zone{zone}"` (and `_zone2` for Zone 2 so the suffix is `flow_offset_zone2`).

- [ ] **Step 1: In `__init__.py`**, before forwarding platforms, build one `Store(hass, 1, f"{DOMAIN}_flow_offset_{entry.entry_id}_zone{zone}")` and one shared `WriteLimiter` per config entry, create the managers, `await manager.async_load()`, and register `coordinator.async_add_listener(manager.on_coordinator_update)`. The ceiling callable reads `get_feature(entry, CONF_MAX_FLOW_TEMP, DEFAULT_MAX_FLOW_TEMP)` each call. Add `"flow_offset_zone2"` to the `FEATURE_ZONE2` tuple in `FEATURE_UNIQUE_ID_SUFFIXES`.
- [ ] **Step 2: In `number.py`** add the entity: range −5.0..+5.0, step 0.5, `NumberMode.BOX`, unit °C, `EntityCategory.CONFIG`, name "Zone N flow offset", `native_value` returns `manager.offset`, `async_set_native_value` calls `manager.async_set_offset` and, when it returns False, raises `HomeAssistantError` with a translated message explaining the write cap. Attributes: `requested_offset`, `mode`, `baseline`. Create the Zone 1 entity always and the Zone 2 entity only when `FEATURE_ZONE2` is in `coordinator.features`. Use the shared device-info style already used in `number.py`.
- [ ] **Step 3: Strings** for the entity name, the cap error message and any attribute labels, in both `strings.json` and `translations/en.json`, identical.
- [ ] **Step 4: Validate** with the `validate` skill; expected: all three checks pass.
- [ ] **Step 5: Manual check on the maintainer's unit** (cannot be automated): with weather compensation on, set Zone 1 offset to +0.5 and confirm registers 3 and 4 each rise by 0.5°C and Te1/Te2 (5, 6) are unchanged; set it back to 0 and confirm both return to their original values; confirm a second change within 30 minutes is refused with the cap message.
- [ ] **Step 6: Commit** (stage 1 complete).

### Task 5: Options for the trim

**Files:**
- Modify: `custom_components/grant_aerona3/const.py`, `config_flow.py` (`OptionsFlowHandler`), `strings.json`, `translations/en.json`

**Interfaces:**
- Produces constants in `const.py`: `CONF_MAX_FLOW_TEMP` (already added), `CONF_TRIM_ENABLED = "room_trim_enabled"` (default False), `CONF_TRIM_SENSOR = "room_trim_sensor"` (entity id string), `CONF_TRIM_INTERVAL = "room_trim_interval_min"` (default 30), `CONF_TRIM_DEAD_BAND = "room_trim_dead_band"` (default 0.3), `CONF_TRIM_CAP = "room_trim_cap"` (default 3.0).

- [ ] **Step 1: Extend the `init` step** with `max_flow_temp` (`vol.Range(min=30.0, max=60.0)`) and `room_trim_enabled`. When trim is enabled, store the submitted values on the handler and continue to a new `async_step_trim`; otherwise create the entry as today.
- [ ] **Step 2: Add `async_step_trim`** with an `EntitySelector` limited to `domain="sensor", device_class="temperature"` (required, no default), interval (10–240 min), dead band (0.1–1.0), cap (0.5–5.0). Read coil 7 from `coordinator.data["coil_registers"].get(7)`; if it is `False` (room set point), pass `description_placeholders` carrying the warning text so the form shows it, but still allow submission. The step finishes with `async_create_entry` merging both steps' values.
- [ ] **Step 3: Strings** for every new field, description and the warning, in both files, identical. The warning text says the unit's own room reading may be unrepresentative and suggests water set point.
- [ ] **Step 4: Validate** and commit. Manual check: the options form appears, the extra step only appears when trim is enabled, and the warning shows only when coil 7 reads off.

### Task 6: Room trim climate entity (stage 2)

**Files:**
- Create: `custom_components/grant_aerona3/climate.py`, `custom_components/grant_aerona3/trim_controller.py` (HA-free decision function, tested)
- Modify: `__init__.py` (`Platform.CLIMATE` in `PLATFORMS`; remove a leftover `room_trim_zone1` registry entry when trim is disabled; add its suffix handling), `strings.json`, `translations/en.json`
- Create: `tests/test_trim_controller.py`

**Interfaces:**
- Consumes: Tasks 2, 3, 5.
- Produces in `trim_controller.py`: `@dataclass class TrimDecision: new_offset: float | None; reason: str` and `decide(*, enabled: bool, cooling: bool, room: float | None, room_age_s: float | None, target: float, current_offset: float, dead_band: float, cap: float, stale_after_s: float = 7200.0, step: float = 0.5) -> TrimDecision`. `new_offset=None` means "make no change". `reason` is one of `"off"`, `"cooling"`, `"sensor_unavailable"`, `"sensor_stale"`, `"in_dead_band"`, `"stepped"`, `"at_cap"`.
- Produces `class GrantAerona3RoomTrim(ClimateEntity, RestoreEntity)` in `climate.py`, Zone 1 only for v1 (my call; Zone 2 reuses the same pieces later), unique_id `f"ashp_{entry.entry_id}_room_trim_zone1"`.

- [ ] **Step 1: Write failing tests** in `tests/test_trim_controller.py`: `test_off_returns_zero_offset` (`enabled=False`, `current_offset=1.5` → `new_offset == 0.0`, reason `"off"`), `test_cooling_does_nothing` (`cooling=True` → `new_offset is None`, reason `"cooling"`), `test_unavailable_sensor_returns_zero` (`room=None` → `0.0`, reason `"sensor_unavailable"`), `test_stale_sensor_returns_zero` (`room_age_s=7201` → `0.0`, `"sensor_stale"`), `test_cold_room_steps_up` (room 19.0, target 21.0, offset 0 → `0.5`, `"stepped"`), `test_in_dead_band_holds` (room 21.2 → `None`, `"in_dead_band"`), `test_pinned_at_cap_reports_reason` (offset 3.0, room 18.0, cap 3.0 → `None`, reason `"at_cap"`).
- [ ] **Step 2: Run** and confirm they fail; **Step 3: implement `decide`** using `next_trim_offset`; **Step 4: run** and confirm they pass.
- [ ] **Step 5: Implement the climate entity.** `hvac_modes = [HVACMode.HEAT, HVACMode.OFF]`; `current_temperature` from the configured sensor state (float, else None); `target_temperature` held in the entity, restored with `RestoreEntity`, min 15, max 25, step 0.5, default 20.0. A `async_track_time_interval` (interval from options) calls `decide(...)` with `cooling` true when `coordinator.data["input_registers"].get(10) == 2`, then `manager.async_set_offset(new_offset)` when `new_offset is not None`. Turning HVAC off immediately calls `async_set_offset(0.0)`. Attributes: `offset`, `requested_offset`, `last_reason`, and `base_curve_hint` set to `"Offset at limit for several hours; consider adjusting the base curve"` once `at_cap` has been the reason for 4 consecutive ticks. While trim is on, set the number entity's attribute `controlled_by_trim: true`.
- [ ] **Step 6: Wire up** `Platform.CLIMATE` in `PLATFORMS`; the climate platform creates the entity only when `CONF_TRIM_ENABLED` is true and a sensor is configured; otherwise it removes any existing `room_trim_zone1` registry entry. Reload the entry when options change (reuse the existing update listener if present).
- [ ] **Step 7: Validate**, run the full pytest suite, and commit.
- [ ] **Step 8: Manual check on the maintainer's unit:** enable trim with the Average Room Temperature sensor and a target 1°C above it; confirm one 0.5°C step appears on the next interval, and that disabling the sensor entity returns the offset to 0 at the next tick.

### Task 7: Documentation

**Files:**
- Modify: `README.md`, `Docs/configuration_guide.md`, `CLAUDE.md`

- [ ] **Step 1: README and configuration guide:** document the flow offset (what it shifts, ±5, 0.5 steps, the write cap), the trim (off by default, how to pick a room sensor, defaults, fail-safe), and the "fix the base curve first" guidance including the 4-value curve explanation from the spec's "Baseline quality" section. State that Te1/Te2 and cooling are untouched.
- [ ] **Step 2: CLAUDE.md** — add one Gotchas bullet: offsets are shifted by `FlowOffsetManager` from a stored baseline; changing Tm1/Tm2/fixed registers elsewhere resets the baseline (two-poll rule); pure logic lives in `flow_offset.py` and is tested with `.venv/bin/pytest tests`; update the "no test suite" line in the Validation section to mention these tests.
- [ ] **Step 3: Validate and commit.**
