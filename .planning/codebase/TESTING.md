# Testing Patterns

**Analysis Date:** 2026-04-03

## Test Framework

**Runner:**
- `pytest` (version not pinned in project; no `pyproject.toml` or `requirements-test.txt` found)
- Config: `tests/pytest.ini`

**Assertion Library:**
- Built-in `assert` statements only — no `pytest.raises` or `unittest.TestCase` usage observed

**Run Commands:**
```bash
pytest tests/          # Run all tests
pytest tests/ -x       # Stop at first failure (default via addopts)
pytest tests/test_entity.py::test_simple_switch   # Run a single test
```

**pytest.ini settings:**
```ini
[pytest]
addopts = -x -p no:cacheprovider
# -x stops at first failure
# -p no:cacheprovider prevents creating .cache folder
```

## Test File Organization

**Location:** All tests live in `tests/` — separate from `custom_components/sonoff/`

**Naming:**
- Files: `test_<topic>.py`
- Functions: `test_<device_or_feature>()`, with issue numbers when testing bug fixes: `test_issue_1160()`, `test_issus_1313()`

**Structure:**
```
tests/
├── __init__.py          # Shared fixtures: DummyRegistry, init(), save_to(), DEVICEID
├── pytest.ini           # pytest configuration
├── test_backward.py     # HA version compatibility and public API surface tests (4 tests)
├── test_climate.py      # Climate entity tests (5 tests)
├── test_energy.py       # Energy reporting/decoding tests (6 tests)
├── test_entity.py       # Comprehensive entity tests across all device types (61 tests)
└── test_misc.py         # Miscellaneous unit tests: crypto, bulk send, registry (6 tests)
```

Total: **82 test functions**

## Test Structure

**Suite Organization:**
Tests are plain functions — no class-based grouping:
```python
def test_simple_switch():
    entities = get_entitites({"extra": {"uiid": 1}, "params": {"switch": "on"}})
    switch: XSwitch = entities[0]
    assert switch.state == "on"

def test_issue_1160():
    payload = XRegistryLocal.decrypt_msg({...}, "9b0810bc-...")
    assert payload == {"switches": [{"outlet": 0, "switch": "off"}]}
```

**Setup Pattern:**
Each test uses the `init()` helper from `tests/__init__.py` to construct a device and registry with a minimal fake HA instance:
```python
reg, entities = init(
    {"extra": {"uiid": 15}, "params": {"currentTemperature": "22.5"}},
    {"devices": {DEVICEID: {"reporting": {"temperature": [5, 60, 0.5]}}}}
)
```

Or the local wrapper `get_entitites()` from `test_entity.py` when the registry isn't needed:
```python
def get_entitites(device: Union[dict, list], config: dict = None) -> list:
    return init(device, config)[1]
```

**Teardown:** None — each test creates a fresh registry; no shared state cleanup needed.

## Mocking

**Framework:** No mocking library used. Mocking is done by hand via subclassing.

**Primary Mock: `DummyRegistry`** (`tests/__init__.py`):
```python
class DummyRegistry(XRegistry):
    def __init__(self):
        super().__init__(None)
        self.send_args = None

    async def send(self, *args, **kwargs):
        self.send_args = args

    async def send_cloud(self, *args, **kwargs):
        self.send_args = args

    def call(self, coro):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(coro)
        loop.close()
        return self.send_args
```

**Usage Pattern — Capturing Send Calls:**
```python
reg: DummyRegistry = light.ewelink
result = reg.call(light.async_turn_on(brightness=128))
assert result[1] == {"bright": 50, "colorR": 255, ...}
```

**What to Mock:**
- `registry.send` / `registry.send_cloud` — to capture outbound commands without network
- `time.time` — to simulate time-based reporting intervals: `time.time = lambda: 30`
- `asyncio.create_task` — patched globally in `init()` to avoid event loop dependency
- `asyncio.get_running_loop` — patched globally in `init()` for thread-safety in tests
- Logger methods captured via `save_to()`: `remote._LOGGER.warning = save_to(logger_warning)`

**What NOT to Mock:**
- Entity class behavior — tests exercise real `set_state`, `internal_update`, `async_turn_on`
- HA state machine — tests use a real (minimal) `HomeAssistant("")` instance
- Dispatcher/signal system — real `dispatcher_connect` / `dispatcher_send` is used throughout

## Fixtures and Factories

**`init()` factory** (`tests/__init__.py`):
The central test factory. Builds a full entity setup from a raw device dict:
```python
def init(device: dict, config: dict = None) -> (XRegistry, List[XEntity]):
    # Fills in defaults: name, deviceid, online, extra.uiid, params.staMac
    # Creates DummyRegistry
    # Calls reg.setup_devices(devices) to instantiate entity classes
    # Attaches entities to a minimal HomeAssistant() instance
    # Returns (reg, entities)
```

**`save_to()` helper** (`tests/__init__.py`):
Captures call arguments into a list — used for logger/send interception:
```python
def save_to(store: list):
    return lambda *args, **kwargs: store.append({**dict(enumerate(args)), **kwargs})
```

**`await_()` helper** (`tests/test_entity.py`):
Runs an async coroutine synchronously in a fresh event loop:
```python
def await_(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
```

**`DEVICEID` constant** (`tests/__init__.py`): `"1000123abc"` — default device ID used across all tests.

**Test Data:** Raw device param dicts are inline within each test — no shared fixture files. This makes each test self-contained and easy to understand at a glance.

## Coverage

**Requirements:** None enforced — no `--cov` flag in `pytest.ini` and no `coverage` config detected.

**View Coverage:**
```bash
pytest tests/ --cov=custom_components/sonoff --cov-report=term-missing
```

**What IS covered:**
- All major entity types: switch, sensor, light, fan, cover, climate, binary sensor, number, select, remote, button
- Cloud and local update dispatch paths via `dispatcher_send(SIGNAL_UPDATE, ...)`
- Cloud connectivity change (`SIGNAL_CONNECTED`) propagating to entity availability
- The `spec()` factory and `DEVICES` map resolution
- Energy decoding across 5 different hardware models (POW1, POWR2, DualR3, SPM, POWR3)
- Cryptography: `encrypt()`, `decrypt()`, `XRegistryLocal.decrypt_msg()`
- Bulk send coalescing (`send_bulk`)
- DIY device discovery via local LAN
- Reporting/filtering logic (zigbee-style min/max interval and delta)
- HA version compatibility tests (2023.2, 2024.1, 2024.2, 2024.8)
- TRVZB climate entity including string temperature parsing (FW 1.4.0+)

**Known Coverage Gaps:**
- `core/ewelink/cloud.py` — no tests for cloud authentication, HTTP retries, or WebSocket handling
- `core/ewelink/local.py` — no tests for mDNS discovery or LAN HTTP send path
- `core/ewelink/camera.py` — camera setup and RTSP URL construction untested
- `config_flow.py` — config entry UI flow untested
- `diagnostics.py` — diagnostics dump function untested
- `system_health.py` — system health reporting untested
- `__init__.py` — `async_setup_entry`, service calls, YAML import path untested
- Error paths in `setup_devices` (malformed devices, missing UIID)

## Test Types

**Unit Tests:**
The majority of tests are functional unit tests: instantiate one device, assert entity properties and state values.

**Behavioral/Scenario Tests:**
Tests simulate multi-step device interactions by calling `dispatcher_send(SIGNAL_UPDATE, ...)` repeatedly:
```python
# Simulate cloud update
switch.ewelink.cloud.dispatcher_send(
    SIGNAL_UPDATE, {"deviceid": DEVICEID, "params": {"switch": "off"}}
)
assert switch.state == "off"

# Simulate local update
fan.ewelink.local.dispatcher_send(
    SIGNAL_UPDATE, {"deviceid": DEVICEID, "params": {"fan": "off"}}
)
assert fan.state == "off"
```

**Regression Tests:**
Many tests are named after GitHub issues: `test_issue_1160`, `test_issue_1333`, `test_issue1235`, `test_issue1386`. These reproduce specific bugs.

**Backward Compatibility Tests** (`test_backward.py`):
Verifies the public API surface hasn't been accidentally removed and that HA version requirements are met:
```python
def test_backward():
    assert (MAJOR_VERSION, MINOR_VERSION) >= (2023, 2)
    assert XSwitch
    assert async_setup_entry
    assert FlowHandler
```

**Integration Tests:** None — no end-to-end tests against real devices or real HA setup.

**E2E Tests:** Not present.

## Common Patterns

**Async Testing:**
Async coroutines are run via `DummyRegistry.call()` (for send operations) or `await_()` (for full async entity methods):
```python
registry: DummyRegistry = light.ewelink
assert registry.call(light.async_turn_on())[1] == {"state": "on"}

# or for non-send coroutines:
await_(light.async_turn_on(brightness=128))
assert registry.send_args[1] == {...}
```

**State Assertion Pattern:**
Entity state is inspected both directly on the entity and via the HA state machine:
```python
# Direct entity attribute
assert switch.state == "on"
assert switch.unique_id == DEVICEID
assert switch.native_value == -39

# Via HA state machine (after async_write_ha_state)
state = sensor.hass.states.get(sensor.entity_id)
assert state.state == "2.1"
assert state.attributes == {"device_class": "voltage", "friendly_name": "..."}
```

**Searching for Entity by Type or UID:**
Tests use `next(e for e in entities if ...)` rather than positional indexing for non-primary entities:
```python
temp: XSensor = next(e for e in entities if e.uid == "temperature")
cover = next(e for e in entities if isinstance(e, XCoverDualR3))
fan: XFan = next(e for e in entities if isinstance(e, XFan))
```

**Error/Warning Testing:**
Logger calls are intercepted using `save_to()`:
```python
logger_warning = []
remote._LOGGER.warning = save_to(logger_warning)
# ... trigger the code ...
assert logger_warning[0][0] == "Can't find payload_off: dummy"
```

---

*Testing analysis: 2026-04-03*
