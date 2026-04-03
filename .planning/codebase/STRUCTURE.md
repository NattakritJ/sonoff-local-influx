# Codebase Structure

**Analysis Date:** 2026-04-03

## Directory Layout

```
SonoffLAN-influx/
├── custom_components/
│   └── sonoff/                   # HA custom component root
│       ├── __init__.py           # Component setup, config schema, service
│       ├── manifest.json         # HA integration manifest (domain, version, deps)
│       ├── config_flow.py        # GUI setup wizard + options flow
│       ├── diagnostics.py        # HA diagnostics endpoint
│       ├── system_health.py      # HA system health + debug web view
│       ├── services.yaml         # send_command service schema
│       ├── alarm_control_panel.py
│       ├── binary_sensor.py
│       ├── button.py
│       ├── climate.py
│       ├── cover.py
│       ├── fan.py
│       ├── light.py              # Largest platform file (1273 lines)
│       ├── media_player.py
│       ├── number.py
│       ├── remote.py
│       ├── select.py
│       ├── sensor.py
│       ├── switch.py
│       ├── core/
│       │   ├── const.py          # DOMAIN and config key constants
│       │   ├── devices.py        # UIID→entity-class mapping + spec() factory
│       │   ├── entity.py         # XEntity base class (all HA entities inherit this)
│       │   ├── xutils.py         # aiohttp session factory, source hash, log helpers
│       │   └── ewelink/
│       │       ├── __init__.py   # XRegistry (central orchestrator)
│       │       ├── base.py       # XRegistryBase, XDevice TypedDict, dispatcher
│       │       ├── cloud.py      # XRegistryCloud — eWeLink cloud WebSocket client
│       │       ├── local.py      # XRegistryLocal — LAN mDNS + HTTP client
│       │       └── camera.py     # XCameras — UDP camera PTZ control (daemon thread)
│       └── translations/         # i18n JSON files (20+ locales)
│           ├── en.json
│           └── *.json
├── tests/
│   ├── __init__.py
│   ├── test_backward.py          # Backward-compatibility tests
│   ├── test_climate.py
│   ├── test_energy.py
│   ├── test_entity.py
│   └── test_misc.py
└── hacs.json                     # HACS distribution metadata
```

## Directory Purposes

**`custom_components/sonoff/`:**
- Purpose: The HA custom component package. All files here are loaded by HA.
- Contains: Component entry point, 12 platform modules, config flow, support utilities
- Key files: `__init__.py` (lifecycle), `manifest.json` (HA metadata), `config_flow.py` (UI)

**`custom_components/sonoff/core/`:**
- Purpose: Core logic that is platform-agnostic — the registry, entity base, constants, and utilities
- Contains: `XEntity` base, `XRegistry` orchestrator, device spec table, constants, session factory
- Key files: `entity.py`, `devices.py`, `const.py`

**`custom_components/sonoff/core/ewelink/`:**
- Purpose: All communication with eWeLink devices — cloud WebSocket, LAN mDNS/HTTP, camera UDP, and the base dispatcher/TypedDict definitions
- Contains: `XRegistry` (orchestrator), `XRegistryCloud`, `XRegistryLocal`, `XCameras`, `XRegistryBase`, `XDevice`
- Key files: `__init__.py` (XRegistry), `cloud.py`, `local.py`

**`custom_components/sonoff/translations/`:**
- Purpose: HA UI localisation strings for config flow and options flow steps
- Contains: One JSON per locale (en, ru, de, fr, zh, etc.)
- Generated: No — maintained manually
- Committed: Yes

**`tests/`:**
- Purpose: Unit tests for specific entity classes and encoding logic
- Contains: Pytest test modules for energy decoding, entity state, backward-compat, misc helpers
- Key files: `test_energy.py`, `test_entity.py`

## Key File Locations

**Entry Points:**
- `custom_components/sonoff/__init__.py`: Component setup; `async_setup`, `async_setup_entry`, `async_unload_entry`
- `custom_components/sonoff/config_flow.py`: GUI onboarding; `FlowHandler`, `OptionsFlowHandler`

**Configuration:**
- `custom_components/sonoff/manifest.json`: Integration domain (`sonoff`), version (`3.11.1`), HA dependencies (`http`, `zeroconf`)
- `custom_components/sonoff/core/const.py`: All string constants (`DOMAIN`, `CONF_*`, `CONF_MODES`)
- `custom_components/sonoff/services.yaml`: `send_command` service parameter schema

**Core Logic:**
- `custom_components/sonoff/core/ewelink/__init__.py`: `XRegistry` — command routing, update handling, LAN keepalive loop
- `custom_components/sonoff/core/ewelink/cloud.py`: eWeLink cloud API client (REST login + WebSocket state)
- `custom_components/sonoff/core/ewelink/local.py`: LAN discovery (mDNS) + HTTP command sender + AES decrypt
- `custom_components/sonoff/core/devices.py`: `DEVICES` dict, `spec()`, `get_spec()` — the device-to-entity resolution table

**Entity Base:**
- `custom_components/sonoff/core/entity.py`: `XEntity` — availability, dispatcher subscription, `set_state`, device_info

**Platform Files (each follows the same pattern):**
- `custom_components/sonoff/switch.py`: `XSwitch`, `XSwitches`, `XToggle`, `XBoolSwitch`, etc.
- `custom_components/sonoff/sensor.py`: `XSensor`, `XCloudEnergy`, `XConnection`, button event sensors, etc.
- `custom_components/sonoff/light.py`: All light variants — `XLight`, `XLightB05B`, `XLightL1`, `XZigbeeLight`, etc. (1273 lines, most complex platform)
- `custom_components/sonoff/climate.py`: `XClimateTH`, `XClimateNS`, `XThermostat`, `XThermostatTRVZB`

**Testing:**
- `tests/test_energy.py`: Energy decode logic for `XCloudEnergy` variants
- `tests/test_entity.py`: `XEntity` state and availability logic

## Naming Conventions

**Files:**
- Platform modules: `{ha_platform_name}.py` (matches HA domain name, e.g. `binary_sensor.py`, `alarm_control_panel.py`)
- Core modules: `{purpose}.py` — `entity.py`, `devices.py`, `const.py`, `xutils.py`
- Transport clients: `{channel}.py` — `cloud.py`, `local.py`, `camera.py`

**Classes:**
- Entity classes: `X{Description}` prefix — `XSwitch`, `XSensor`, `XLightB05B`, `XClimateTH`
- Registry classes: `XRegistry{Scope}` — `XRegistry`, `XRegistryCloud`, `XRegistryLocal`, `XRegistryBase`
- TypedDict: `XDevice` (singular, no suffix)
- Config flow: `FlowHandler`, `OptionsFlowHandler` (HA convention, no X prefix)

**Constants:**
- Config keys: `CONF_{NAME}` (matching HA `homeassistant.const` style)
- Signals: `SIGNAL_{EVENT}` — `SIGNAL_CONNECTED`, `SIGNAL_UPDATE`, `SIGNAL_ADD_ENTITIES`
- Spec shortcuts: `UpperCamelCase` globals in `devices.py` — `Switch1`, `Battery`, `LED`, `RSSI`, `EnergyDay`
- Pre-built spec lists: `SPEC_{VARIANT}` — `SPEC_SWITCH`, `SPEC_1CH`, `SPEC_4CH`, `SPEC_NSP`

**Functions:**
- HA lifecycle hooks: `async_setup`, `async_setup_entry`, `async_unload_entry`, `async_update_options` (HA naming requirement)
- Internal helpers: `snake_case` — `get_spec`, `setup_diy`, `internal_unique_devices`

## Module Organization

Each **platform file** follows this structure:
1. `PARALLEL_UPDATES = 0` — disables HA semaphore throttling
2. `async_setup_entry(hass, config_entry, add_entities)` — connects `SIGNAL_ADD_ENTITIES` dispatcher to `add_entities`, filtered by `isinstance(e, <PlatformBase>)`
3. One or more `X{Name}(XEntity, {PlatformEntity})` classes, each with:
   - Class-level `params: set` — device param keys this entity cares about
   - Class-level `uid: str` — suffix for `unique_id` and entity naming
   - `set_state(params: dict)` — update `_attr_*` attributes from device params
   - `async_turn_on/off` or equivalent action methods calling `self.ewelink.send(...)`

**How platform files relate to core:**

```
Platform file                   Core
───────────────────────────────────────────────────────
switch.py::async_setup_entry ──▶ XRegistry.dispatcher_connect(SIGNAL_ADD_ENTITIES)
XSwitch(XEntity, SwitchEntity)
  └─ XEntity.__init__         ──▶ XRegistry.dispatcher_connect(deviceid, internal_update)
  └─ set_state(params)            (called from XEntity.internal_update when params match)
  └─ async_turn_on()          ──▶ XRegistry.send(device, {"switch": "on"})
                                   ├─▶ XRegistryLocal.send(...)   [LAN first]
                                   └─▶ XRegistryCloud.send(...)   [cloud fallback]
```

**`core/devices.py` is the binding layer** — it imports entity classes from *all* platform files and maps UIIDs to lists of classes. `XRegistry.setup_devices()` calls `get_spec(device)` which returns these lists and instantiates every entity class by calling `cls(registry, device)`.

## Where to Add New Code

**New device UIID support:**
- Add entry to `DEVICES` dict in `custom_components/sonoff/core/devices.py`
- Reuse existing `spec()` variants or create new entity classes in the appropriate platform file
- Import the new class in `devices.py`

**New entity class for an existing platform:**
- Add class to the relevant platform file (e.g. `custom_components/sonoff/switch.py`)
- Import it in `custom_components/sonoff/core/devices.py`
- Reference it in relevant `DEVICES` entries

**New HA platform (e.g. `event.py`):**
- Create `custom_components/sonoff/event.py` following the standard pattern (PARALLEL_UPDATES, async_setup_entry, entity class)
- Add `"event"` to `PLATFORMS` list in `custom_components/sonoff/__init__.py`

**New config constant:**
- Add to `custom_components/sonoff/core/const.py`

**New core utility:**
- Add to `custom_components/sonoff/core/xutils.py`

**New test:**
- Add to `tests/test_{area}.py`, following existing pytest patterns

## Special Directories

**`custom_components/sonoff/translations/`:**
- Purpose: HA config flow UI strings for all supported locales
- Generated: No
- Committed: Yes

**`tests/`:**
- Purpose: Pytest unit tests — not deployed with the integration, only used during development
- Generated: No
- Committed: Yes

**`.planning/`:**
- Purpose: GSD planning artifacts (this document lives here)
- Generated: Yes (by GSD tooling)
- Committed: Project-dependent

---

*Structure analysis: 2026-04-03*
