# Architecture

**Analysis Date:** 2026-04-03

## Pattern Overview

**Overall:** Layered event-driven architecture with a registry/dispatcher pattern at the core.

**Key Characteristics:**
- A central `XRegistry` orchestrator mediates between two transport backends (Cloud WebSocket and LAN mDNS/HTTP) and the HA entity layer
- Device state is pushed to entities via an internal signal dispatcher — entities never poll; they subscribe to signals keyed by `deviceid`
- Device-to-entity mapping is resolved at runtime via a UIID lookup table (`DEVICES` dict in `core/devices.py`), with dynamic class construction via `spec()` for parameterised variants
- Transport selection is automatic: LAN is tried first (1 s timeout); cloud is fallback. Both can be active simultaneously ("duplex" mode)
- Entities are plain Python objects that are added to HA platforms via a deferred `SIGNAL_ADD_ENTITIES` signal, ensuring cloud/LAN connections are established before entities appear in HA

## Layers

**Component Entry Layer:**
- Purpose: HA integration lifecycle — setup, teardown, config validation, service registration
- Location: `custom_components/sonoff/__init__.py`
- Contains: `async_setup`, `async_setup_entry`, `async_unload_entry`, `send_command` service
- Depends on: `XRegistry`, `XCameras`, platform modules
- Used by: Home Assistant core

**Configuration Flow Layer:**
- Purpose: User-facing setup wizard and options panel
- Location: `custom_components/sonoff/config_flow.py`
- Contains: `FlowHandler` (ConfigFlow), `OptionsFlowHandler` (OptionsFlow)
- Depends on: `XRegistryCloud` (for login validation only)
- Used by: HA config entry UI

**Platform Layer:**
- Purpose: One module per HA entity domain; each registers entity classes with HA when `SIGNAL_ADD_ENTITIES` fires
- Location: `custom_components/sonoff/{switch,light,sensor,binary_sensor,climate,cover,fan,number,select,button,remote,alarm_control_panel,media_player}.py`
- Contains: Domain-specific entity subclasses + `async_setup_entry` connecting the dispatcher
- Depends on: `XEntity`, `XRegistry`, `SIGNAL_ADD_ENTITIES`
- Used by: `__init__.py` via `async_forward_entry_setups`

**Core Entity Base:**
- Purpose: Shared HA entity superclass; handles availability, dispatcher subscription, device_info construction, and state write-back
- Location: `custom_components/sonoff/core/entity.py`
- Contains: `XEntity(Entity)` — `internal_update`, `internal_available`, `set_state` (overridden by subclasses), `async_update`
- Depends on: `XRegistry`, `XDevice`
- Used by: All platform entity classes

**Device Registry / Spec Layer:**
- Purpose: Maps device UIIDs to lists of entity classes; constructs per-device entity instances; handles DIY device detection and user class overrides
- Location: `custom_components/sonoff/core/devices.py`
- Contains: `DEVICES` dict (UIID → class list), `spec()` factory, `get_spec()`, `get_custom_spec()`, `setup_diy()`, pre-built `Switch1–4`, `Battery`, `RSSI`, energy spec variants
- Depends on: All platform entity classes (imported at module level)
- Used by: `XRegistry.setup_devices()`

**Registry / Orchestration Layer:**
- Purpose: Central coordinator; owns device dict, cloud + local clients, sends commands with LAN-first logic, dispatches state updates
- Location: `custom_components/sonoff/core/ewelink/__init__.py` (`XRegistry`)
- Contains: `setup_devices`, `send`, `send_bulk`, `send_cloud`, `cloud_connected`, `cloud_update`, `local_update`, `run_forever`, `can_local`, `can_cloud`
- Depends on: `XRegistryCloud`, `XRegistryLocal`, `XRegistryBase`
- Used by: `__init__.py`, all `XEntity` subclasses (via `self.ewelink`)

**Transport: Cloud:**
- Purpose: Authenticates with eWeLink cloud API, maintains a WebSocket connection, sends/receives device state as JSON
- Location: `custom_components/sonoff/core/ewelink/cloud.py` (`XRegistryCloud`)
- Contains: `login`, `login_token`, `get_devices`, `get_homes`, `send` (WS), `set_device` (HTTP), `run_forever`, `connect`, `_process_ws_msg`, `ResponseWaiter`
- Depends on: `aiohttp`, `XRegistryBase`
- Used by: `XRegistry`

**Transport: LAN:**
- Purpose: Discovers devices on the local network via mDNS/zeroconf, sends commands via HTTP POST, decrypts AES-CBC payloads for non-DIY devices
- Location: `custom_components/sonoff/core/ewelink/local.py` (`XRegistryLocal`)
- Contains: `start` (mDNS browser), `_handler1/2/3` (discovery pipeline), `send` (HTTP), `encrypt`/`decrypt`, `decrypt_msg`
- Depends on: `zeroconf`, `cryptography`, `aiohttp`, `XRegistryBase`
- Used by: `XRegistry`

**Transport Base / Dispatcher:**
- Purpose: Shared infrastructure: async signal dispatcher, sequence counter, aiohttp session holder
- Location: `custom_components/sonoff/core/ewelink/base.py` (`XRegistryBase`, `XDevice`)
- Contains: `dispatcher_connect`, `dispatcher_send`, `dispatcher_wait`, `sequence()`, `XDevice` TypedDict
- Used by: `XRegistryCloud`, `XRegistryLocal`, `XRegistry`

**Camera Transport (Special-case):**
- Purpose: Controls Sonoff camera pan/tilt via UDP broadcast; runs in a dedicated daemon thread
- Location: `custom_components/sonoff/core/ewelink/camera.py` (`XCameras`)
- Contains: `send`, `datagram_received`, UDP socket management
- Used by: `__init__.py` → `send_command` service

## Data Flow

**Device State Update (Cloud → Entity):**

1. `XRegistryCloud.run_forever` receives a WebSocket JSON message
2. `_process_ws_msg` identifies `action=update` or `action=sysmsg` and calls `dispatcher_send(SIGNAL_UPDATE, msg)`
3. `XRegistry.cloud_update` receives the signal, looks up the device dict by `deviceid`, updates `device["online"]` / `params`, then calls `dispatcher_send(did, params)`
4. `XEntity.internal_update(params)` fires for every entity subscribed to that `deviceid`
5. Entity calls `set_state(params)` if the params keys intersect `entity.params`, then calls `_async_write_ha_state()` if anything changed

**Device State Update (LAN → Entity):**

1. `XRegistryLocal._handler3` processes mDNS TXT record, calls `dispatcher_send(SIGNAL_UPDATE, msg)`
2. `XRegistry.local_update` decrypts if needed, resolves the real device, updates timing fields (`localping`, `localfail`, `localrecv`), calls `dispatcher_send(realid, params)`
3. Same `XEntity.internal_update` path as cloud

**Command: HA → Device:**

1. HA calls `entity.async_turn_on/off()` or similar
2. Entity calls `self.ewelink.send(device, params)` (or `send_bulk`, `send_cloud`)
3. `XRegistry.send` checks `can_local` and `can_cloud`; tries LAN first (1 s timeout), falls back to cloud WebSocket
4. `XRegistryLocal.send` does `POST http://<host>/zeroconf/<command>` with JSON payload (encrypted if `devicekey` present)
5. `XRegistryCloud.send` sends JSON over the persistent WebSocket, waits for sequence-matched response

**Initialization Flow:**

1. `async_setup` — validates HA version, stores global config, creates `XCameras`, imports YAML credentials as config entry if needed, registers `send_command` service
2. `async_setup_entry` — creates `XRegistry` + session, logs into cloud (if password set), forwards to all platform `async_setup_entry` functions, loads device list (cloud → cache fallback), calls `registry.setup_devices(devices)` to build entity objects, starts `cloud.start()` / `local.start()`, waits for connection, then fires `SIGNAL_ADD_ENTITIES`
3. Platform `async_setup_entry` — connects `SIGNAL_ADD_ENTITIES` to the HA `add_entities` callback, filtered by `isinstance(entity, <PlatformEntity>)`

## Key Abstractions

**`XDevice` (TypedDict):**
- Purpose: The device dict shared between registry and entities — acts as a mutable state bag
- Examples: `custom_components/sonoff/core/ewelink/base.py`
- Fields: `deviceid`, `extra.uiid`, `params`, `online`, `local`, `host`, `devicekey`, `localping`, `localfail`, `parent`

**`XEntity`:**
- Purpose: Base class for all HA entities; handles dispatcher subscription in `__init__`, availability in `internal_available`, and state write-back in `internal_update`
- Examples: `custom_components/sonoff/core/entity.py`
- Pattern: Subclasses override `set_state(params)` and optionally `internal_available()`

**`spec()` factory function:**
- Purpose: Dynamically creates subclasses with overridden class-level attributes (`param`, `uid`, `channel`, `multiply`, etc.) or swapped HA base class (e.g. `XSwitch` → `LightEntity`)
- Examples: `custom_components/sonoff/core/devices.py` — every `Switch1`, `Battery`, `LED`, `EnergyDay` etc. is produced by `spec()`
- Pattern: `spec(XSensor, param="power", multiply=0.01, round=2)` returns a new anonymous type

**`ResponseWaiter`:**
- Purpose: Correlates outbound cloud WS commands with their async responses using sequence numbers
- Examples: `custom_components/sonoff/core/ewelink/cloud.py`
- Pattern: `asyncio.Future` stored in `_waiters[sequence]`; resolved by `_set_response` when response arrives

**Signal dispatcher:**
- Purpose: Simple in-process pub/sub replacing HA's dispatcher. Signals are either well-known strings (`SIGNAL_ADD_ENTITIES`, `SIGNAL_CONNECTED`, `SIGNAL_UPDATE`) or device IDs
- Examples: `custom_components/sonoff/core/ewelink/base.py` — `dispatcher_connect`, `dispatcher_send`

## Entry Points

**`async_setup` (`__init__.py:104`):**
- Triggers: HA loading the `sonoff` domain from `configuration.yaml`
- Responsibilities: Global config validation, camera init, YAML→config-entry migration, service registration

**`async_setup_entry` (`__init__.py:182`):**
- Triggers: HA processing a config entry (on startup or after options change)
- Responsibilities: Registry creation, cloud login, platform forwarding, device loading, transport start, entity add

**Platform `async_setup_entry` (e.g., `switch.py:10`):**
- Triggers: Called by `async_forward_entry_setups` for each of the 12 platforms
- Responsibilities: Connect `SIGNAL_ADD_ENTITIES` signal → HA `add_entities`, filtered by entity type

## Error Handling

**Strategy:** Fail-safe with reconnect loops. Missing devices, bad params, or transport errors are logged and skipped rather than raising to HA.

**Patterns:**
- Cloud `run_forever`: exponential back-off (15 s → 32 m) on `fails` counter; raises `ConfigEntryAuthFailed` only on 406 WS error
- `setup_devices`: per-device `try/except` logs `can't setup device` and continues
- `local.send`: returns error string literals (`"timeout"`, `"E#CON"`, `"E#CRE"`) instead of raising; `XRegistry.send` uses the return value to fall back to cloud
- `XEntity.__init__`: catches `Exception` from `internal_update` with `_LOGGER.error`

## Cross-Cutting Concerns

**Logging:** `logging.getLogger(__name__)` per module; all significant events (cloud connect/disconnect, LAN discovery, send/receive) are logged at DEBUG with device ID prefix (e.g. `1000xxxxxx <= Cloud3 | {...}`)

**Validation:** Device params validated implicitly via `params.keys() & entity.params` set intersection; no schema enforcement on incoming device state

**Authentication:** eWeLink username/password → Bearer token stored in HA config entry `data`; token refreshed by re-login in `run_forever` loop; HMAC-SHA256 request signing in `cloud.py:sign()`

**Encryption:** LAN payloads for non-DIY devices use AES-128-CBC with key = `md5(devicekey)`, IV per-message; implemented in `core/ewelink/local.py:encrypt/decrypt`

---

*Architecture analysis: 2026-04-03*
