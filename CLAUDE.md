<!-- GSD:project-start source:PROJECT.md -->
## Project

**SonoffLAN-InfluxDB**

A standalone Python daemon that listens for energy telemetry from Sonoff smart devices on the local network and writes the data to an InfluxDB 3 Core instance. It replaces the Home Assistant integration layer entirely — no HA, no config entries, no entity system — just device discovery, protocol handling, and time-series data ingestion. Runs as a Docker container configured entirely via environment variables.

**Core Value:** Reliable, low-latency energy data from Sonoff LAN devices flowing into InfluxDB 3 — every event written immediately, no HA dependency.

### Constraints

- **Protocol:** LAN only — no eWeLink cloud account required
- **Data:** Energy metrics only — `power`, `voltage`, `current`, `energyUsage`
- **Config:** Docker env vars only — no config files inside the container
- **InfluxDB:** v3 Core API (not v1 or v2 line protocol via legacy endpoint)
- **Devices:** Explicit list in config — not zero-config auto-discovery
- **Write strategy:** Immediate per-event — no buffering or batching
- **Error handling:** Log-and-continue — InfluxDB failures do not crash the daemon
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3 - All component logic, entity definitions, protocol implementations
- JSON - Translation files (`custom_components/sonoff/translations/*.json`), manifest, HACS config
## Runtime
- Home Assistant Core (minimum version 2023.2.0, enforced in `custom_components/sonoff/__init__.py` line 105)
- Python asyncio event loop (all I/O is async-native via `asyncio`, `aiohttp`)
- None explicit - no `requirements.txt`, `pyproject.toml`, or `setup.cfg` present
- Dependencies are declared in `custom_components/sonoff/manifest.json` (`requirements: []`) — all runtime libraries are provided by Home Assistant itself
## Frameworks
- Home Assistant Custom Component Framework (≥2023.2.0) - Entity lifecycle, config entries, state machine, service registry
- pytest - Test runner configured in `tests/pytest.ini`
- Not applicable — no build pipeline, no transpilation, no bundler
## Key Dependencies
- `aiohttp` - Async HTTP client/server; used for:
- `cryptography` - AES-128-CBC encryption/decryption for local LAN device payloads
- `zeroconf` (HA dependency declared in `manifest.json`) - mDNS/DNS-SD service discovery for LAN devices
- `voluptuous` - Config schema validation for YAML configuration
- `multidict` - HTTP header dictionary (case-insensitive); used in `core/xutils.py` for User-Agent header
- `asyncio` - Task scheduling, futures, event loop primitives throughout all core modules
- `base64`, `hashlib`, `hmac`, `json` - eWeLink API signature/auth (`cloud.py`)
- `os` (urandom) - IV generation for AES encryption (`local.py`)
- `socket` - UDP datagram socket for camera PTZ commands (`camera.py`)
- `threading` - Camera command thread (`camera.py`)
- `time` - Local device ping/TTL management (`ewelink/__init__.py`)
- `logging` - Python standard logging, augmented with custom `DebugView` handler (`system_health.py`)
## Configuration
- No `.env` file; all runtime configuration flows through:
- No build configuration files (no `Makefile`, `tox.ini`, `pyproject.toml`)
- Test config only: `tests/pytest.ini`
## Platform Requirements
- Home Assistant installation (≥2023.2.0) as runtime host
- Python 3.10+ (implied by HA 2023.2 minimum, uses `TypedDict`, `X | Y` union syntax in `base.py`)
- Network access to local LAN (for mDNS discovery and HTTP to devices on port 8081)
- Network access to eWeLink cloud APIs (optional, for cloud mode)
- Deployed as a HACS custom integration: copy `custom_components/sonoff/` into HA `<config>/custom_components/`
- Minimum Home Assistant 2023.2.0
- HA dependencies auto-resolved: `http` and `zeroconf` HA components (declared in `manifest.json`)
- Component version: `3.11.1` (from `custom_components/sonoff/manifest.json`)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Platform files are named after HA domains: `switch.py`, `sensor.py`, `light.py`, `cover.py`, `fan.py`, `climate.py`, etc.
- Core infrastructure lives under `core/`: `entity.py`, `devices.py`, `const.py`, `xutils.py`
- eWeLink protocol files live under `core/ewelink/`: `__init__.py`, `base.py`, `cloud.py`, `local.py`, `camera.py`
- Test files follow `test_<topic>.py` convention: `test_entity.py`, `test_misc.py`, `test_energy.py`, `test_climate.py`, `test_backward.py`
- All custom entity classes are prefixed with `X`: `XEntity`, `XSwitch`, `XSensor`, `XLight`, `XFan`, `XCover`, `XRegistry`, `XDevice`
- Registry classes follow `XRegistry<Variant>`: `XRegistry`, `XRegistryBase`, `XRegistryCloud`, `XRegistryLocal`
- Device-specific variants are named `X<Platform><DeviceType>`: `XLightL1`, `XLightB05B`, `XSwitchTH`, `XSwitchPOWR3`, `XCoverDualR3`
- `spec()` factory results are PascalCase module-level constants: `Switch1`, `Battery`, `LED`, `RSSI`, `EnergyDay`
- Compound spec groups use `SPEC_<DESCRIPTOR>` pattern: `SPEC_SWITCH`, `SPEC_1CH`, `SPEC_4CH`, `SPEC_NSP`
- HA lifecycle: `async_setup_entry` (snake_case, required HA interface)
- Entity update paths: `set_state`, `internal_update`, `internal_available`, `internal_parent_update` (snake_case)
- HA async entity actions: `async_turn_on`, `async_turn_off`, `async_set_value`, `async_press`, `async_update` (HA interface names)
- Registry methods: `dispatcher_connect`, `dispatcher_send`, `dispatcher_wait`, `send_bulk`, `send_cloud` (snake_case)
- Helper/converter functions are lowercase: `conv()`, `spec()`, `parse_float()`, `decrypt()`, `encrypt()`
- Module-level signal constants are `SIGNAL_<EVENT>`: `SIGNAL_CONNECTED`, `SIGNAL_UPDATE`, `SIGNAL_ADD_ENTITIES`
- Module-level lookup dicts are `UPPER_CASE`: `DEVICE_CLASSES`, `UNITS`, `DEVICES`, `DEVICE_CLASS`, `ENTITY_CATEGORIES`, `ICONS`, `NAMES`, `BUTTON_STATES`
- Logger always named `_LOGGER = logging.getLogger(__name__)`
- HA integration constant: `PARALLEL_UPDATES = 0` in every platform file
- Type-hinted local variables use descriptive names: `did`, `deviceid`, `params`, `entities`, `ewelink`, `device`
- `_attr_*` prefix for HA cached entity properties: `_attr_is_on`, `_attr_native_value`, `_attr_device_class`, etc.
- Function signatures use Python 3.10+ union syntax: `str | None`, `asyncio.Task | None`
- TypedDict used for `XDevice` in `core/ewelink/base.py`
- Type annotations used selectively — heavily on return types and complex params, lightly on simple locals
- Inline type comments used in tests: `switch: XSwitch = entities[0]`, `temp: XSensor = next(...)`
- `Optional[type]` from `typing` still present in some older code (e.g., `sensor.py`)
## Code Style
- No formatter config file detected (no `.prettierrc`, `pyproject.toml`, or `black.toml`)
- Code uses 4-space indentation throughout
- Line length is generally kept short-to-medium; multi-line imports use grouped parentheses
- No `.flake8`, `.pylintrc`, or `ruff.toml` detected
- IDE suppression comments (`# noinspection PyAbstractClass`, `# noinspection PyTypeChecker`, `# noinspection DuplicatedCode`) are used extensively — these are PyCharm-style annotations
## Import Organization
- Standard library imports are grouped at top, blank line, then third-party/HA, blank line, then local
- Local imports always use relative paths (`.core.const` not `custom_components.sonoff.core.const`)
- Tests use absolute paths: `from custom_components.sonoff.switch import XSwitch`
## Error Handling
- Broad `except Exception` is common for resilience — the pattern is to silently swallow and return/pass, not re-raise:
- Bare `except:` (no exception type) appears in a few sensor set_state methods: `except: pass`
- `_LOGGER.error(...)` with `exc_info=e` used for device init failures
- `_LOGGER.warning(...)` with `exc_info=e` for non-critical failures
- `_LOGGER.debug(...)` for normal operational messages
## Logging
- Debug: device-id prefixed messages with pipe delimiters: `f"{did} <= Cloud3 | %s | {seq}"`
- Warning: setup failures: `f"{did} !! can't setup device"`
- Error: initialization failures with exc_info for full traceback
- f-strings mixed with `%s` formatting: `_LOGGER.debug(f"{did} <= Cloud3 | %s | {seq}", params)` — the `%s` is lazy-evaluated by the logging framework; the f-string prefix provides context
## Comments
- GitHub issue references are common: `# https://github.com/AlexxIT/SonoffLAN/issues/1160`
- Inline comments explain non-obvious device protocol behaviors
- Multi-line section headers in `light.py` use `###...###` banners with category labels
- Class-level docstrings used sparingly — only for complex classes like `XSensor`
- `# noinspection` comments used to suppress IDE warnings on abstract method stubs
## Function Design
- `set_state(self, params: dict)` is the universal entity update interface
- `async_turn_on` always accepts `**kwargs` to absorb unexpected HA keyword args
- Core registry methods use keyword-only args for optional params: `params_lan: dict = None, cmd_lan: str = None`
- Entity methods return `None`
- Registry send methods return `str | None` (`"online"` on success, `None`/error on failure)
- `can_cloud()` / `can_local()` return `bool`
## Module Design
- Platform modules expose entity classes directly without an `__all__`
- `core/ewelink/__init__.py` re-exports `XRegistry`, `XDevice`, `XRegistryLocal`, `SIGNAL_*` for convenience
- `test_backward.py` uses wildcard imports (`from custom_components.sonoff import *`) explicitly to test public API surface
- `core/ewelink/__init__.py` acts as a barrel for the ewelink subpackage
- No other barrel files present
## Common Patterns & Idioms
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- A central `XRegistry` orchestrator mediates between two transport backends (Cloud WebSocket and LAN mDNS/HTTP) and the HA entity layer
- Device state is pushed to entities via an internal signal dispatcher — entities never poll; they subscribe to signals keyed by `deviceid`
- Device-to-entity mapping is resolved at runtime via a UIID lookup table (`DEVICES` dict in `core/devices.py`), with dynamic class construction via `spec()` for parameterised variants
- Transport selection is automatic: LAN is tried first (1 s timeout); cloud is fallback. Both can be active simultaneously ("duplex" mode)
- Entities are plain Python objects that are added to HA platforms via a deferred `SIGNAL_ADD_ENTITIES` signal, ensuring cloud/LAN connections are established before entities appear in HA
## Layers
- Purpose: HA integration lifecycle — setup, teardown, config validation, service registration
- Location: `custom_components/sonoff/__init__.py`
- Contains: `async_setup`, `async_setup_entry`, `async_unload_entry`, `send_command` service
- Depends on: `XRegistry`, `XCameras`, platform modules
- Used by: Home Assistant core
- Purpose: User-facing setup wizard and options panel
- Location: `custom_components/sonoff/config_flow.py`
- Contains: `FlowHandler` (ConfigFlow), `OptionsFlowHandler` (OptionsFlow)
- Depends on: `XRegistryCloud` (for login validation only)
- Used by: HA config entry UI
- Purpose: One module per HA entity domain; each registers entity classes with HA when `SIGNAL_ADD_ENTITIES` fires
- Location: `custom_components/sonoff/{switch,light,sensor,binary_sensor,climate,cover,fan,number,select,button,remote,alarm_control_panel,media_player}.py`
- Contains: Domain-specific entity subclasses + `async_setup_entry` connecting the dispatcher
- Depends on: `XEntity`, `XRegistry`, `SIGNAL_ADD_ENTITIES`
- Used by: `__init__.py` via `async_forward_entry_setups`
- Purpose: Shared HA entity superclass; handles availability, dispatcher subscription, device_info construction, and state write-back
- Location: `custom_components/sonoff/core/entity.py`
- Contains: `XEntity(Entity)` — `internal_update`, `internal_available`, `set_state` (overridden by subclasses), `async_update`
- Depends on: `XRegistry`, `XDevice`
- Used by: All platform entity classes
- Purpose: Maps device UIIDs to lists of entity classes; constructs per-device entity instances; handles DIY device detection and user class overrides
- Location: `custom_components/sonoff/core/devices.py`
- Contains: `DEVICES` dict (UIID → class list), `spec()` factory, `get_spec()`, `get_custom_spec()`, `setup_diy()`, pre-built `Switch1–4`, `Battery`, `RSSI`, energy spec variants
- Depends on: All platform entity classes (imported at module level)
- Used by: `XRegistry.setup_devices()`
- Purpose: Central coordinator; owns device dict, cloud + local clients, sends commands with LAN-first logic, dispatches state updates
- Location: `custom_components/sonoff/core/ewelink/__init__.py` (`XRegistry`)
- Contains: `setup_devices`, `send`, `send_bulk`, `send_cloud`, `cloud_connected`, `cloud_update`, `local_update`, `run_forever`, `can_local`, `can_cloud`
- Depends on: `XRegistryCloud`, `XRegistryLocal`, `XRegistryBase`
- Used by: `__init__.py`, all `XEntity` subclasses (via `self.ewelink`)
- Purpose: Authenticates with eWeLink cloud API, maintains a WebSocket connection, sends/receives device state as JSON
- Location: `custom_components/sonoff/core/ewelink/cloud.py` (`XRegistryCloud`)
- Contains: `login`, `login_token`, `get_devices`, `get_homes`, `send` (WS), `set_device` (HTTP), `run_forever`, `connect`, `_process_ws_msg`, `ResponseWaiter`
- Depends on: `aiohttp`, `XRegistryBase`
- Used by: `XRegistry`
- Purpose: Discovers devices on the local network via mDNS/zeroconf, sends commands via HTTP POST, decrypts AES-CBC payloads for non-DIY devices
- Location: `custom_components/sonoff/core/ewelink/local.py` (`XRegistryLocal`)
- Contains: `start` (mDNS browser), `_handler1/2/3` (discovery pipeline), `send` (HTTP), `encrypt`/`decrypt`, `decrypt_msg`
- Depends on: `zeroconf`, `cryptography`, `aiohttp`, `XRegistryBase`
- Used by: `XRegistry`
- Purpose: Shared infrastructure: async signal dispatcher, sequence counter, aiohttp session holder
- Location: `custom_components/sonoff/core/ewelink/base.py` (`XRegistryBase`, `XDevice`)
- Contains: `dispatcher_connect`, `dispatcher_send`, `dispatcher_wait`, `sequence()`, `XDevice` TypedDict
- Used by: `XRegistryCloud`, `XRegistryLocal`, `XRegistry`
- Purpose: Controls Sonoff camera pan/tilt via UDP broadcast; runs in a dedicated daemon thread
- Location: `custom_components/sonoff/core/ewelink/camera.py` (`XCameras`)
- Contains: `send`, `datagram_received`, UDP socket management
- Used by: `__init__.py` → `send_command` service
## Data Flow
## Key Abstractions
- Purpose: The device dict shared between registry and entities — acts as a mutable state bag
- Examples: `custom_components/sonoff/core/ewelink/base.py`
- Fields: `deviceid`, `extra.uiid`, `params`, `online`, `local`, `host`, `devicekey`, `localping`, `localfail`, `parent`
- Purpose: Base class for all HA entities; handles dispatcher subscription in `__init__`, availability in `internal_available`, and state write-back in `internal_update`
- Examples: `custom_components/sonoff/core/entity.py`
- Pattern: Subclasses override `set_state(params)` and optionally `internal_available()`
- Purpose: Dynamically creates subclasses with overridden class-level attributes (`param`, `uid`, `channel`, `multiply`, etc.) or swapped HA base class (e.g. `XSwitch` → `LightEntity`)
- Examples: `custom_components/sonoff/core/devices.py` — every `Switch1`, `Battery`, `LED`, `EnergyDay` etc. is produced by `spec()`
- Pattern: `spec(XSensor, param="power", multiply=0.01, round=2)` returns a new anonymous type
- Purpose: Correlates outbound cloud WS commands with their async responses using sequence numbers
- Examples: `custom_components/sonoff/core/ewelink/cloud.py`
- Pattern: `asyncio.Future` stored in `_waiters[sequence]`; resolved by `_set_response` when response arrives
- Purpose: Simple in-process pub/sub replacing HA's dispatcher. Signals are either well-known strings (`SIGNAL_ADD_ENTITIES`, `SIGNAL_CONNECTED`, `SIGNAL_UPDATE`) or device IDs
- Examples: `custom_components/sonoff/core/ewelink/base.py` — `dispatcher_connect`, `dispatcher_send`
## Entry Points
- Triggers: HA loading the `sonoff` domain from `configuration.yaml`
- Responsibilities: Global config validation, camera init, YAML→config-entry migration, service registration
- Triggers: HA processing a config entry (on startup or after options change)
- Responsibilities: Registry creation, cloud login, platform forwarding, device loading, transport start, entity add
- Triggers: Called by `async_forward_entry_setups` for each of the 12 platforms
- Responsibilities: Connect `SIGNAL_ADD_ENTITIES` signal → HA `add_entities`, filtered by entity type
## Error Handling
- Cloud `run_forever`: exponential back-off (15 s → 32 m) on `fails` counter; raises `ConfigEntryAuthFailed` only on 406 WS error
- `setup_devices`: per-device `try/except` logs `can't setup device` and continues
- `local.send`: returns error string literals (`"timeout"`, `"E#CON"`, `"E#CRE"`) instead of raising; `XRegistry.send` uses the return value to fall back to cloud
- `XEntity.__init__`: catches `Exception` from `internal_update` with `_LOGGER.error`
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
