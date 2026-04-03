"""
conftest.py for the tests/ package.

Stubs the homeassistant module BEFORE tests/__init__.py is imported,
so legacy HA tests/__init__.py can be loaded without errors in environments
where homeassistant is not installed.

Also adds src/ to sys.path so daemon modules (extractor, config, ewelink)
are importable without installation.
"""
import sys
import os
from types import ModuleType

# Add src/ to PYTHONPATH for daemon test imports
_src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


def _make_stub(name: str) -> ModuleType:
    if name not in sys.modules:
        mod = ModuleType(name)
        mod.__path__ = []  # type: ignore[attr-defined]
        sys.modules[name] = mod
    return sys.modules[name]


# Stub homeassistant hierarchy used by tests/__init__.py
_ha = _make_stub("homeassistant")
_ha_cfg = _make_stub("homeassistant.config_entries")
_ha_helpers = _make_stub("homeassistant.helpers")
_ha_entity = _make_stub("homeassistant.helpers.entity")
_ha_core = _make_stub("homeassistant.core")

# Minimal classes so tests/__init__.py doesn't fail on import
class _HomeAssistant:
    def __init__(self, *args, **kwargs):
        self.data = {}

class _Entity:
    pass

_ha_cfg.HomeAssistant = _HomeAssistant  # type: ignore[attr-defined]
_ha_entity.Entity = _Entity  # type: ignore[attr-defined]
