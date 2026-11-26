"""Load HA-free modules of the integration by file path.

Importing the package would run its __init__.py, which needs Home Assistant.
"""
import importlib.util
import pathlib
import sys

_PKG = pathlib.Path(__file__).resolve().parent.parent / "custom_components" / "grant_aerona3"


def load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
