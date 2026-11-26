"""Reloading after an options change.

__init__.py and coordinator.py import Home Assistant, which isn't installed here,
so these tests pull the relevant code out of the source with ast.
"""
import ast
import asyncio
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "custom_components" / "grant_aerona3"


def _tree(filename):
    return ast.parse((PACKAGE / filename).read_text())


def test_options_change_reloads_through_home_assistant():
    # Calling setup directly failed on real hardware: HA must run it as a config entry setup
    node = next(
        n for n in _tree("__init__.py").body
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "async_reload_entry"
    )
    node.returns = None
    for arg in node.args.args:
        arg.annotation = None
    reloaded, direct = [], []

    class Entries:
        async def async_reload(self, entry_id):
            reloaded.append(entry_id)

    async def direct_call(*args):
        direct.append(args)
        return True

    namespace = {"async_setup_entry": direct_call, "async_unload_entry": direct_call}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "__init__.py", "exec"), namespace)
    hass = type("Hass", (), {"config_entries": Entries()})()
    entry = type("Entry", (), {"entry_id": "abc"})()
    asyncio.run(namespace["async_reload_entry"](hass, entry))
    assert reloaded == ["abc"] and direct == []


def test_coordinator_is_given_its_config_entry():
    call = next(
        n for n in ast.walk(_tree("coordinator.py"))
        if isinstance(n, ast.Call) and ast.unparse(n.func) == "super().__init__"
    )
    assert {k.arg: ast.unparse(k.value) for k in call.keywords}.get("config_entry") == "entry"
