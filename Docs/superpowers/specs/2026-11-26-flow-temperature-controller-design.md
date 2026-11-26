# Flow temperature controller (outdoor plus room): design

Status: draft for approval, 2026-11-26. Items marked **(my call)** were not discussed; check those.

## Intent and why

Many heat pump owners control house temperature through the flow temperature, and products such as Homely do it for them over Modbus. This integration is for people who do not have a smart controller. It should offer the same kind of control from Home Assistant: the user sets a room temperature and a schedule, and the integration chooses the fixed flow temperature.

## Goals

1. Choose the Zone 1 fixed flow temperature from outdoor temperature, corrected by room temperature.
2. Follow a schedule with a daytime and a lower setback temperature.
3. Stay within the user's flow limits and the existing write limit.
4. Be optional, off by default and experimental.

## Non-goals

- Learning the house, weather forecasts, early start, tariffs, hot water.
- Switching the heat pump on or off. No Modbus command for this was found; a relay on terminals 20-21 is out of scope.
- Zone 2 and cooling **(my call)**.

## Anti-goals

- Two things writing the same register.
- Frequent writes or a flow temperature that hunts up and down.
- Leaving the user unable to get their previous setup back.

## Constraints

- Fixed setpoint: Zone 1 holding register 2, 0.5 °C steps. Curve/fixed selection: coil 2 (off = fixed).
- Outdoor temperature: input register 6 (whole degrees). Input register 17 (0.1 °C) is used instead when the remote outdoor sensor feature is on **(my call)**.
- Writes: at most 24 a day, at least 30 minutes apart, with the existing grace window (`WriteLimiter`). One limiter is shared with the flow offset.
- The unit still decides when to run. Any external room thermostat must keep calling for heat, or this controller has no effect.
- At minimum flow the unit can still heat while there is demand; the controller cannot stop it.
- If Home Assistant stops, the unit keeps the last setpoint written.

## Approaches

| Approach | Trade-off |
|---|---|
| A. Room only (wider existing trim) | Least work, but reacts only after the room has drifted. |
| **B. Outdoor sets it, room corrects it (chosen)** | Responds to weather at once; needs two more settings and more testing. |
| C. Learn the house | Closest to Homely; needs weeks of data and is hard to test. Could be added on top of B. |

The maintainer chose B.

## Design

### What the user sets up (options flow)

| Setting | Default |
|---|---|
| Enable flow temperature controller | off |
| Room temperature sensor | none (required) |
| Flow at cold point | 40 °C at -3 °C outside |
| Flow at mild point | 28 °C at 15 °C outside |
| Minimum flow | 25 °C (never below 23) |
| Maximum flow | the existing `max_flow_temp` (55 °C) |
| Schedule (a Home Assistant schedule helper) | none |

All defaults are **(my call)**. The controller and the room trim cannot both be enabled; the options flow rejects that. If coil 7 is on room set point, show the same warning the trim shows and still allow it.

### The entity

One `climate` entity, "Zone 1 flow controller", modes `heat` and `off`, off until the user turns it on.

- Presets `comfort` (default 20 °C) and `eco` (default 17 °C). With a schedule: on = comfort, off = eco. Without one, comfort applies unless the user or an automation picks eco. Two temperatures only **(my call)**.
- Setting the temperature changes the active preset's value. Targets survive restarts.
- A manually chosen preset lasts until the schedule next changes **(my call)**.
- Attributes: calculated flow, written flow, each part of the sum below, reason for the last decision, and when the next write is allowed.

### The calculation (my call on every number)

    flow = base(outdoor)
         + 1.0 x (target - 20)
         + 2.0 x (target - room)
         + learned correction

then clamped to the minimum and maximum, and rounded to 0.5 °C.

- `base(outdoor)`: a straight line through the user's two points, continued beyond them and limited only by the clamp. Outdoor temperature is averaged over the last hour.
- Learned correction: starts at 0. Moves 0.5 °C every 2 hours (up if the room is too cold, down if too warm) while it is more than 0.3 °C from target, within ±8 °C. It is stored across restarts.
- It does not move while the room is more than 1.5 °C from target, for 3 hours after a target change (so night setback does not distort it), or while the result is already at a limit in that direction.
- Recalculate every 10 minutes. Write only if the result differs from the unit's value by at least 1.0 °C, or by 0.5 °C after a target change.

The constants live in one place so they can be tuned after testing. They are not user settings in the first release.

### Turning on and off

- On: save the current coil 2 state and fixed setpoint, then switch Zone 1 to fixed mode **(my call: switch it rather than ask the user to)** and write the calculated flow.
- If turning on fails part-way, restore what was saved and stay off.
- Off: restore the saved setpoint and coil state. This restore is not blocked by the write limit, and is retried each tick until it succeeds.
- While on, the Zone 1 flow offset number refuses changes and its hand-edit detection is paused, so it does not adopt the controller's writes as a new baseline.
- The saved state is stored, so a restart does not lose it. Disabling the feature in options while on restores it first.

### When things go wrong

| Situation | Behaviour |
|---|---|
| Room sensor unavailable or older than 6 h | Use outdoor temperature and the learned correction only |
| Outdoor temperature unavailable | Hold the current setpoint |
| Poll or write fails | Retry on the next tick; report it in the attributes |
| Write limit reached | Wait; attributes show when it can write |
| Setpoint or coil 2 changed outside the integration (two polls) | Turn the controller off, keep the user's value, raise a persistent notification **(my call)** |
| Unit in cooling mode | Do nothing |

### Code shape

- `flow_controller.py`: the calculation and decisions, no Home Assistant imports, covered by pytest.
- A feature key `experimental_flow_controller`, default off, with its unique_id suffix in `FEATURE_UNIQUE_ID_SUFFIXES`.
- `strings.json` and `translations/en.json` kept identical; user documentation covers the thermostat and base-point setup.

## Staging (my call)

1. **Preview only:** a sensor shows the flow the controller would write, and writes nothing. Run it for several days beside current weather compensation.
2. **Control:** the climate entity writes. Pre-release, tested on the maintainer's heat pump.
3. Full release only after real cold-weather use.

In stage 1 the learned correction stays at 0, because nothing is being changed for it to learn from. There is no climate entity yet, so the targets are fixed at 20 °C and 17 °C, switched by the schedule.

## Left to the builder

- Store layout, helper names and how the offset manager is paused.
- Where the climate class lives (`climate.py` or a new module).
