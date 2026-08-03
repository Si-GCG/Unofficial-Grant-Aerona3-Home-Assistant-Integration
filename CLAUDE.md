# Grant Aerona3 Home Assistant Integration

Unofficial HACS integration for Grant Aerona3 air-source heat pumps, talking Modbus over serial/TCP. Solo-maintained, no CI — validation is manual (see `.claude/skills/validate`).

## Feature-gating architecture

Users only get entities for hardware they actually own (an unfiltered install creates 150+ entities). Don't add a new register or entity without wiring it into this system:

- Feature keys live in `const.py`: `has_dhw_tank`, `has_buffer`, `has_ehs`, `has_cooling`, `zones` (`"single"`/`"dual"`, exposed internally as the pseudo-feature `zone2`). `DEFAULT_FEATURES` turns everything ON — this is required so existing config entries keep all their entities after an upgrade; don't change these defaults for backward-compat reasons even though a fresh UK install would prefer heating-only/no-DHW defaults (that's handled in the config flow, not here).
- Register gating is data-driven: `INPUT_REGISTER_FEATURES`, `HOLDING_REGISTER_FEATURES`, `COIL_REGISTER_FEATURES` in `const.py` map register ID → tuple of required feature keys (AND semantics — e.g. Zone 2 cooling needs both `has_cooling` and `zone2`). A register absent from its map is core and always enabled/polled.
- `features.py` holds the helpers: `get_feature(entry, key, default)` (options flow value wins over the original data), `enabled_features(entry)`, `register_enabled(features, feature_map, reg_id)`. The coordinator computes `self.features` once; platforms read features from the coordinator, not from the config entry directly.
- **When adding a register**: decide its feature tuple in the relevant `*_REGISTER_FEATURES` dict in `const.py`.
- **When adding a gated hand-written entity** (not register-driven, e.g. a switch built directly in `switch.py`): also add its unique_id suffix to `FEATURE_UNIQUE_ID_SUFFIXES` in `__init__.py`. `_remove_disabled_entities` uses that map to purge registry entries for disabled features on setup — miss it and the entity lingers as "unavailable" forever instead of disappearing.

## Gotchas

- `translations/en.json` must be kept as an exact copy of `strings.json`. Home Assistant loads `translations/` at runtime, not `strings.json` (that file is only for the HA developer-docs tooling) — editing one without the other silently desyncs the UI strings.
- The coordinator only polls a hardcoded subset of coils (`critical_coils` in `coordinator.py`'s `_read_coil_registers`, currently coils 2, 3, 6, 7, 18) to avoid Modbus timeouts, but roughly 20 coil-backed switches exist in `switch.py`. Any switch outside that subset shows stale/last-known state rather than live state — this is a known gap, not a bug you're introducing if you touch nearby code.
- `weather_compensation.py` and `weather_compensation_entities.py` are dead code — nothing imports `weather_compensation_entities`, and only it imports `weather_compensation`. The literal string `"weather_compensation"` appears elsewhere only as part of unrelated entity unique_ids/entity_ids, not as a wire-up. Don't assume these modules are reachable; either finish wiring them or remove them, don't build on top of them as-is.
- `options_flow.py` was removed as dead code already — the options flow lives inside `config_flow.py`'s `OptionsFlowHandler`. Don't recreate a separate file for it.

## Validation

There's no test suite or CI. Before committing, run the `validate` skill (or manually: `python3 -m py_compile` on every file in `custom_components/grant_aerona3/`, plus a JSON load check on `strings.json` and `translations/en.json`).
