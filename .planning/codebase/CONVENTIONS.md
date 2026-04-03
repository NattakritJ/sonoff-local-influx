# Coding Conventions

**Analysis Date:** 2026-04-03

## Naming Patterns

**Files:**
- Platform files are named after HA domains: `switch.py`, `sensor.py`, `light.py`, `cover.py`, `fan.py`, `climate.py`, etc.
- Core infrastructure lives under `core/`: `entity.py`, `devices.py`, `const.py`, `xutils.py`
- eWeLink protocol files live under `core/ewelink/`: `__init__.py`, `base.py`, `cloud.py`, `local.py`, `camera.py`
- Test files follow `test_<topic>.py` convention: `test_entity.py`, `test_misc.py`, `test_energy.py`, `test_climate.py`, `test_backward.py`

**Classes:**
- All custom entity classes are prefixed with `X`: `XEntity`, `XSwitch`, `XSensor`, `XLight`, `XFan`, `XCover`, `XRegistry`, `XDevice`
- Registry classes follow `XRegistry<Variant>`: `XRegistry`, `XRegistryBase`, `XRegistryCloud`, `XRegistryLocal`
- Device-specific variants are named `X<Platform><DeviceType>`: `XLightL1`, `XLightB05B`, `XSwitchTH`, `XSwitchPOWR3`, `XCoverDualR3`
- `spec()` factory results are PascalCase module-level constants: `Switch1`, `Battery`, `LED`, `RSSI`, `EnergyDay`
- Compound spec groups use `SPEC_<DESCRIPTOR>` pattern: `SPEC_SWITCH`, `SPEC_1CH`, `SPEC_4CH`, `SPEC_NSP`

**Functions:**
- HA lifecycle: `async_setup_entry` (snake_case, required HA interface)
- Entity update paths: `set_state`, `internal_update`, `internal_available`, `internal_parent_update` (snake_case)
- HA async entity actions: `async_turn_on`, `async_turn_off`, `async_set_value`, `async_press`, `async_update` (HA interface names)
- Registry methods: `dispatcher_connect`, `dispatcher_send`, `dispatcher_wait`, `send_bulk`, `send_cloud` (snake_case)
- Helper/converter functions are lowercase: `conv()`, `spec()`, `parse_float()`, `decrypt()`, `encrypt()`

**Variables:**
- Module-level signal constants are `SIGNAL_<EVENT>`: `SIGNAL_CONNECTED`, `SIGNAL_UPDATE`, `SIGNAL_ADD_ENTITIES`
- Module-level lookup dicts are `UPPER_CASE`: `DEVICE_CLASSES`, `UNITS`, `DEVICES`, `DEVICE_CLASS`, `ENTITY_CATEGORIES`, `ICONS`, `NAMES`, `BUTTON_STATES`
- Logger always named `_LOGGER = logging.getLogger(__name__)`
- HA integration constant: `PARALLEL_UPDATES = 0` in every platform file
- Type-hinted local variables use descriptive names: `did`, `deviceid`, `params`, `entities`, `ewelink`, `device`
- `_attr_*` prefix for HA cached entity properties: `_attr_is_on`, `_attr_native_value`, `_attr_device_class`, etc.

**Type Annotations:**
- Function signatures use Python 3.10+ union syntax: `str | None`, `asyncio.Task | None`
- TypedDict used for `XDevice` in `core/ewelink/base.py`
- Type annotations used selectively — heavily on return types and complex params, lightly on simple locals
- Inline type comments used in tests: `switch: XSwitch = entities[0]`, `temp: XSensor = next(...)`
- `Optional[type]` from `typing` still present in some older code (e.g., `sensor.py`)

## Code Style

**Formatting:**
- No formatter config file detected (no `.prettierrc`, `pyproject.toml`, or `black.toml`)
- Code uses 4-space indentation throughout
- Line length is generally kept short-to-medium; multi-line imports use grouped parentheses

**Linting:**
- No `.flake8`, `.pylintrc`, or `ruff.toml` detected
- IDE suppression comments (`# noinspection PyAbstractClass`, `# noinspection PyTypeChecker`, `# noinspection DuplicatedCode`) are used extensively — these are PyCharm-style annotations

## Import Organization

**Order observed across platform files:**
1. Standard library (`asyncio`, `time`, `logging`, `json`, `threading`)
2. Third-party (`aiohttp`, `voluptuous`, `homeassistant.*`)
3. Local relative imports (`.core.const`, `.core.entity`, `.core.ewelink`, etc.)

**Pattern:**
- Standard library imports are grouped at top, blank line, then third-party/HA, blank line, then local
- Local imports always use relative paths (`.core.const` not `custom_components.sonoff.core.const`)
- Tests use absolute paths: `from custom_components.sonoff.switch import XSwitch`

**No path aliases** configured.

## Error Handling

**Patterns:**
- Broad `except Exception` is common for resilience — the pattern is to silently swallow and return/pass, not re-raise:
  ```python
  try:
      value = float(value)
  except Exception:
      return
  ```
- Bare `except:` (no exception type) appears in a few sensor set_state methods: `except: pass`
- `_LOGGER.error(...)` with `exc_info=e` used for device init failures
- `_LOGGER.warning(...)` with `exc_info=e` for non-critical failures
- `_LOGGER.debug(...)` for normal operational messages

## Logging

**Framework:** `logging` (stdlib), using `logging.getLogger(__name__)` as `_LOGGER`

**Patterns:**
- Debug: device-id prefixed messages with pipe delimiters: `f"{did} <= Cloud3 | %s | {seq}"`
- Warning: setup failures: `f"{did} !! can't setup device"`
- Error: initialization failures with exc_info for full traceback
- f-strings mixed with `%s` formatting: `_LOGGER.debug(f"{did} <= Cloud3 | %s | {seq}", params)` — the `%s` is lazy-evaluated by the logging framework; the f-string prefix provides context

## Comments

**When to Comment:**
- GitHub issue references are common: `# https://github.com/AlexxIT/SonoffLAN/issues/1160`
- Inline comments explain non-obvious device protocol behaviors
- Multi-line section headers in `light.py` use `###...###` banners with category labels
- Class-level docstrings used sparingly — only for complex classes like `XSensor`
- `# noinspection` comments used to suppress IDE warnings on abstract method stubs

**JSDoc/TSDoc:** Not applicable (Python codebase).

## Function Design

**Size:** Functions are generally compact (5–30 lines). `set_state` methods tend to be short (10–20 lines). Long methods appear in `cloud.py` and `local.py` for protocol handling.

**Parameters:**
- `set_state(self, params: dict)` is the universal entity update interface
- `async_turn_on` always accepts `**kwargs` to absorb unexpected HA keyword args
- Core registry methods use keyword-only args for optional params: `params_lan: dict = None, cmd_lan: str = None`

**Return Values:**
- Entity methods return `None`
- Registry send methods return `str | None` (`"online"` on success, `None`/error on failure)
- `can_cloud()` / `can_local()` return `bool`

## Module Design

**Exports:**
- Platform modules expose entity classes directly without an `__all__`
- `core/ewelink/__init__.py` re-exports `XRegistry`, `XDevice`, `XRegistryLocal`, `SIGNAL_*` for convenience
- `test_backward.py` uses wildcard imports (`from custom_components.sonoff import *`) explicitly to test public API surface

**Barrel Files:**
- `core/ewelink/__init__.py` acts as a barrel for the ewelink subpackage
- No other barrel files present

## Common Patterns & Idioms

**Entity Specialization via `spec()`:**
The `spec()` factory in `core/devices.py` creates class variants without writing new classes:
```python
Battery = spec(XSensor, param="battery")
RSSI = spec(XSensor, param="rssi", enabled=False)
Switch1 = spec(XSwitches, channel=0, uid="1")
EnergyDay = spec(XEnergyTotal, param="dayKwh", uid="energy_day", multiply=0.01, round=2)
```

**Device UIID Registry:**
The `DEVICES` dict in `core/devices.py` maps integer UIIDs to lists of entity classes:
```python
DEVICES = {
    1: SPEC_SWITCH,
    2: SPEC_2CH,
    5: [XSwitch, LED, RSSI, spec(XSensor, param="power"), ...],
}
```

**Dispatcher Signal Pattern:**
All state updates travel through a simple string-keyed dispatcher:
```python
ewelink.dispatcher_connect(deviceid, self.internal_update)
ewelink.dispatcher_send(deviceid, params)
```

**`_attr_*` Properties:**
All entity state is stored via `_attr_*` attributes set directly, never via property setters. This is the standard HA 2021.12+ pattern:
```python
self._attr_is_on = params["switch"] == "on"
self._attr_native_value = value
self._attr_available = available
```

**HA Version Branching:**
Version compatibility is handled inline with tuple comparisons:
```python
if (MAJOR_VERSION, MINOR_VERSION) >= (2024, 2):
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE_RANGE | ClimateEntityFeature.TURN_ON | ...
else:
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
```

---

*Convention analysis: 2026-04-03*
