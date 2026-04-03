"""
Root-level conftest.py for the standalone daemon test suite.

Stubs the homeassistant module so legacy tests/__init__.py can be imported
without errors (it's used by the original HA integration tests but is not
needed for the new daemon tests). Also adds src/ to sys.path.
"""
import sys
import os
from types import ModuleType

# Add src/ to PYTHONPATH so daemon modules are importable without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Stub homeassistant and related modules so tests/__init__.py doesn't crash.
# The original HA integration tests require homeassistant to be installed,
# but new daemon tests (test_extractor.py, etc.) have no such dependency.
def _make_stub_module(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = mod
    return mod


# Stub the minimum needed by tests/__init__.py
_ha = _make_stub_module("homeassistant")
_ha_cfg = _make_stub_module("homeassistant.config_entries")
_ha_helpers = _make_stub_module("homeassistant.helpers")
_ha_entity = _make_stub_module("homeassistant.helpers.entity")

# Provide dummy classes used in tests/__init__.py
class _HomeAssistant:
    def __init__(self, *args, **kwargs):
        self.data = {}

class _Entity:
    pass

_ha_cfg.HomeAssistant = _HomeAssistant  # type: ignore[attr-defined]
_ha_entity.Entity = _Entity  # type: ignore[attr-defined]
