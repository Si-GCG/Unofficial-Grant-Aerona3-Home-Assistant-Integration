# Flow offset and room-temperature trim: design

Status: draft for approval, 2026-11-25. Covers backlog item 1 in part. `water_heater` is a separate, later piece.

## Intent and why

The maintainer runs weather compensation (WC) only. The room stat (EPH, set to 30°C) always calls for heat, so the heat pump never throttles on room temperature. The curve alone decides how much heat goes into the circuit. This is the usual "low and slow" technique. Many other users do the same with the fixed flow temperature setting, adjusting that one number until the house is comfortable.

Today that adjustment means editing raw Modbus registers (Tm1/Tm2 or the fixed setpoint) by hand. Users on the Renewable Heating Hub have written scripts that nudge the flow temperature from the room temperature. This integration should offer that natively, safely.

Mode, room set temperatures and DHW mode (input registers 10-13) are read-only: they are set at the unit's remote controller. A conventional thermostat that sets the unit's mode or room target is not possible over Modbus. What is writable is the flow side: the fixed setpoint, the curve points, and the curve-enable coils.

## Goals

1. A per-zone **flow offset** that shifts the whole heating flow temperature up or down in 0.5°C steps, in both modes:
   - WC mode: shift Tm1 (max flow) and Tm2 (min flow) together (parallel shift of the curve).
   - Fixed-flow mode: shift the fixed setpoint.
2. An optional **room trim controller**, exposed as a `climate` entity, that moves the offset slowly based on a user-chosen room temperature sensor and a target held in Home Assistant.
3. Safe by construction: bounded, rate-limited, fails back to zero offset.

## Non-goals

- Setting the unit's operating mode, room set temperature or on/off (not writable).
- Cooling-curve offsets in the first release (heating only; cooling can follow the same helper later).
- A fast or "clever" controller. No PID tuning UI, no learning.
- `water_heater` (separate piece, built afterwards).

## Anti-goals (would make this a failure even if it works)

- The loop hunting up and down, or flash-wearing the unit with frequent writes.
- Leaving a high offset applied when the sensor goes stale or the unit stops answering.
- A `climate` entity whose "target temperature" silently means flow temperature.
- Following the heat pump's own remote-controller room reading (inputs 33/34). On the maintainer's unit it reads 23.5°C against a true 19.7°C because the controller sits in a warm cupboard.

## Constraints from the codebase and hardware

- Curve registers per zone (holding, 0.5°C steps, flow temps limited to 23-60°C): Zone 1 fixed setpoint 2, Tm1 3, Tm2 4, Te1 5, Te2 6; Zone 2 has its own. Heating-only for v1.
- Feature gating (see CLAUDE.md): Zone 2 offset needs `zone2`; any new hand-written entity needs its unique_id suffix added to `FEATURE_UNIQUE_ID_SUFFIXES` in `__init__.py`.
- All writes go through `coordinator.async_write_register`; the coordinator already polls these holding registers, so the applied values are readable.
- WC vs fixed is selected by the heating curve-enable coils (Zone 1 coil 2, Zone 2 coil 3). The helper must read these to choose which registers to shift.
- `translations/en.json` must stay an exact copy of `strings.json`.
- Unknown: whether Modbus holding-register writes persist to the unit's non-volatile memory. Treat every write as potentially wearing it.
- No test suite. Validation is the `validate` skill plus manual testing on the maintainer's TCP unit; the serial tester has not yet reported on v1.2.2+.

## Approaches considered

1. **Offset numbers only.** Safe and small, but the room trim stays in user scripts. Does not deliver what the maintainer wants.
2. **Climate entity with the controller built in, in one go.** Turnkey, but the riskiest to release untested, and every tuning change needs a release.
3. **Layered (chosen).** Offset numbers first as the foundation, built on one shared helper. A `climate` entity, optional and off by default, runs a slow trim loop on top. Each layer can be tested on the maintainer's unit before testers see it.

## Design (as decided, and my calls)

### Foundation: flow offset (decided)

- One `number` entity per zone: "Zone N flow offset", range −5.0 to +5.0°C, step 0.5, default 0. Entity category config.
- A shared helper computes the target register values from the baseline and offset, clamps each flow value to 23-60°C, and keeps Tm1 ≥ Tm2.
- Writes only when the computed register value differs from what the unit reports.
- **Write cap (decided by the maintainer, to begin with):** at most 24 offset changes per day, at least 30 minutes between changes, applied to manual changes and the trim loop alike. No hardware spike is planned: existing number entities already write holding registers, and a power-cycle test would not reveal wear. Revisit the cap if real use shows it is too tight or too loose. **Grace window (added after first hardware test):** a correction made within 120 s of a change (at most 3 per change) replaces that change and uses no extra slot, so a mis-click can be undone; the 30-minute clock still runs from the first change.

### Flow temperature limits (maintainer input, 2026-11-25)

The register table allows 23-60°C and Grant's installer manual (page 34) states a 60°C maximum in heating mode; 55°C is the rated test point, not a documented limit. The maintainer believes the practical range is 23-55°C. To avoid guessing: the floor is 23°C, and the helper clamps to a **configurable maximum flow temperature, default 55°C, adjustable up to 60°C** (options flow). The trim and the manual offset can therefore never push flow above 55°C unless the user raises the ceiling. The builder should read this setting alongside the 23°C floor wherever the clamp is applied.

### Baseline and persistence (my call)

The unit has no offset concept, so Home Assistant has to remember the baseline: the curve values as they were at offset 0. Store the baseline (Tm1, Tm2, fixed setpoint) and the applied offset in the config entry's `Store`. If the registers read back values different from baseline + stored offset, someone edited the curve by hand: adopt the new values as the baseline and reset the offset to 0, and log it once. This is why the offset is never derived from a single register.

### Details settled after the builder check (all my calls)

- **Mode flips (WC to fixed or back):** the Store keeps a separate baseline per mode. Only the active mode's registers are shifted and checked for hand edits; the inactive set is left untouched. The offset itself is shared, so it carries across the flip.
- **Hand-edit detection:** compare the read-back against the *clamped* expected values (after the 23-60°C limits and Tm1 ≥ Tm2). Ignore polls while a write pair is in flight, and treat a mismatch as a hand edit only if it persists for two consecutive polls.
- **Number vs climate:** one shared offset state. While the trim climate entity is on, it owns the offset: the number entity shows the value but a manual change is overwritten at the next tick, and the entity says so in its attributes. Turning the trim off leaves the offset where it is unless the user also asks for a reset to 0.
- **Te1/Te2:** deliberately not shifted. Only flow temperatures move, so the curve shifts parallel.
- **Displayed offset:** show the *effective* offset (after clamping), and the requested value in an attribute, so the UI never shows +5 when only +2 was applied.

### Baseline quality and the Te1/Te2 decision (maintainer input, 2026-11-25)

- **Te1/Te2 stay fixed by the offset, on purpose.** The curve is four values: (Te1, Tm1) at the cold end and (Te2, Tm2) at the mild end, flat outside them. Shifting Tm1 and Tm2 together raises flow at every outdoor temperature, including the flat ends. Shifting Te1/Te2 moves the curve sideways, which changes nothing at the cold extreme where more heat is most often wanted. It is not a good answer to "the house is too cold".
- **A slope control is a different tool.** If the house is right at mild outdoor temperatures but cold in hard frost, the fix is a steeper curve (raise Tm1 alone). That stays a manual edit through the existing number entities for now. A manual "cold-end boost" number may come later; it is not part of the trim loop, to avoid two interacting controls.
- **Installer curves are often wrong.** The initial curve is set by the installer from the system design and is frequently far from what the house needs (the maintainer's was 45°C at −3°C, much too hot). The offset is therefore for fine trimming around a baseline the user has already corrected. Documentation must tell users to fix the base curve first. Hand-edit detection already adopts a manually edited curve as the new baseline and resets the offset to 0, which is the intended workflow.
- **Cap-pinned signal.** If the trim sits at its cap for several hours, the climate entity shows an attribute saying the offset is at its limit and the base curve probably needs adjusting. The cap is not raised automatically.

### Optional room trim controller (decided: optional, off by default; my calls: parameters)

- A `climate` entity, created only when the user enables it in the options flow and picks a room temperature sensor.
- Current temperature: the chosen HA sensor. Target temperature: held in HA (restored across restarts). HVAC modes: `heat` and `off` only, meaning trim on or off. Turning it off returns the offset to 0.
- Loop: every 30 minutes (my call), if the sensor is fresh, compare room vs target. Move the offset by one 0.5°C step towards the target when the error exceeds a ±0.3°C dead band (my call). No integral or derivative terms.
- Hard cap on the offset, default ±3°C (my call, below the ±5 manual range).
- Fail-safe: if the sensor is unavailable or older than 6 hours, or the coordinator poll fails, return the offset to 0 and show it in the climate entity's attributes.
- Interval, dead band and cap are options-flow settings, not constants.

### Unit interaction to check before the controller ships (open, for the builder)

Coil 7 ("HP unit turns on/off based on room set point or water set point") should be on water set point for this to behave as expected, since the unit's own room reading is skewed. Context from the maintainer: most installs put the controller next to the DHW tank, in a cupboard or attic, so its room reading is unrepresentative almost everywhere. Water set point (the register default) is therefore the common setup, the warning should rarely fire, and the trim must never default to inputs 33/34 as its room sensor. Decided by the maintainer: if the coil is on room set point, the options flow shows a warning but the trim is still allowed to run (no refusal). The builder should read the coil on the maintainer's unit to confirm its current state.

## Changes after the first overnight test (2026-11-26, approved by the maintainer)

- The offset is limited as a whole, not value by value: it stops where any shifted flow value would leave the 23 °C to maximum range, so the curve never tilts. The trim steps from, and stops at, that limit.
- The stale-sensor window is 6 hours, not 2. An unchanged average-helper reading had reset the offset although nothing was broken. The cost is that a silently dead sensor takes longer to notice.

## Staging

1. Helper and the flow offset numbers (this is a releasable pre-release by itself).
2. Climate trim controller, off by default, as a second pre-release.
3. `water_heater` afterwards, designed separately.

Each stage is tested on the maintainer's own heat pump before testers hear about it, and nothing is promoted to a full release without the serial tester's report.

## Left to the builder

- Exact helper API and where it lives (likely a new module beside `coordinator.py`).
- Store schema and migration.
- How the flow offset behaves when the unit is in cooling mode (v1 should simply not touch cooling registers).
- Strings, translations and README/docs changes, kept in step per CLAUDE.md.
