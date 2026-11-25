"""Diagnostics for the Grant Aerona3 integration (Settings > Devices & Services > Download diagnostics)."""
from __future__ import annotations

from typing import Any

import pymodbus
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_integration

from .const import (
    COIL_REGISTER_MAP,
    DOMAIN,
    HOLDING_REGISTER_MAP,
    INPUT_REGISTER_MAP,
)
from .coordinator import plan_reads
from .error_codes import ERROR_REGISTER_IDS, decode_error

# The IP address and serial device path identify the user's network/hardware.
TO_REDACT = {CONF_HOST, "serial_port"}

_REGISTER_MAPS = {
    "input": INPUT_REGISTER_MAP,
    "holding": HOLDING_REGISTER_MAP,
    "coil": COIL_REGISTER_MAP,
}
_DATA_KEYS = {
    "input": "input_registers",
    "holding": "holding_registers",
    "coil": "coil_registers",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    integration = await async_get_integration(hass, DOMAIN)
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    by_platform: dict[str, dict[str, int]] = {}
    for reg_entry in entities:
        counts = by_platform.setdefault(reg_entry.domain, {"total": 0, "disabled": 0})
        counts["total"] += 1
        if reg_entry.disabled_by is not None:
            counts["disabled"] += 1

    diagnostics: dict[str, Any] = {
        "versions": {
            "integration": str(integration.version),
            "home_assistant": HA_VERSION,
            "pymodbus": pymodbus.__version__,
        },
        "config_entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "entities": by_platform,
    }

    if coordinator is None:
        diagnostics["coordinator"] = "not loaded (setup failed or the entry is disabled)"
        return diagnostics

    diagnostics["enabled_features"] = sorted(coordinator.features)
    diagnostics["polling"] = {
        "update_interval_seconds": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
        "last_update_success": coordinator.last_update_success,
        "last_exception": str(coordinator.last_exception) if coordinator.last_exception else None,
        "last_poll_seconds": coordinator.last_poll_seconds,
        "rejected_block_reads": sorted(
            f"{kind} {start}..{start + count - 1}"
            for kind, start, count in coordinator._degraded_spans
        ),
    }

    data = coordinator.data or {}
    registers: dict[str, Any] = {}
    plan: dict[str, list[str]] = {}
    for kind, register_map in _REGISTER_MAPS.items():
        enabled = coordinator._enabled_addresses(kind)
        values = data.get(_DATA_KEYS[kind], {})
        plan[kind] = [f"{start}..{start + count - 1}" for start, count in plan_reads(enabled)]
        registers[kind] = {
            "values": {
                f"{address}: {register_map[address]['name']}": values[address]
                for address in sorted(values)
                if address in register_map
            },
            "enabled_but_no_value": [
                f"{address}: {register_map[address]['name']}"
                for address in sorted(enabled)
                if address not in values
            ],
        }
    diagnostics["planned_reads"] = plan
    history = []
    for address in ERROR_REGISTER_IDS:
        raw = data.get("input_registers", {}).get(address)
        if raw is None:
            history.append(None)
            continue
        decoded = decode_error(raw)
        history.append(
            "empty"
            if decoded is None
            else f"{decoded.code or 'unrecognised'} (0x{decoded.raw:04X}, "
            f"{'confirmed' if decoded.confirmed else 'inferred'}): {decoded.description}"
        )
    diagnostics["error_history_newest_first"] = history
    diagnostics["registers"] = registers
    return diagnostics
