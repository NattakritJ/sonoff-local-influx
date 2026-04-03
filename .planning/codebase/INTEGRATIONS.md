# External Integrations

**Analysis Date:** 2026-04-03

## APIs & External Services

### eWeLink Cloud API (Coolkit Technologies)

The primary external service. All cloud communication is implemented in `custom_components/sonoff/core/ewelink/cloud.py`.

- **REST API (v2):**
  - Base URLs (region-dependent): `https://cn-apia.coolkit.cn`, `https://as-apia.coolkit.cc`, `https://us-apia.coolkit.cc`, `https://eu-apia.coolkit.cc`
  - Login: `POST /v2/user/login` — email/phone + password; HMAC-SHA256 signed payload
  - Token login: `GET /v2/user/profile` — bearer token auth
  - Get homes: `GET /v2/family`
  - Get devices: `GET /v2/device/thing`
  - Set device state: `POST /v2/device/thing/status`
  - Auth: `Authorization: Sign <base64(hmac-sha256(body, app_secret))>` for login; `Authorization: Bearer <token>` for subsequent calls; `X-CK-Appid` header always present
  - App ID: hardcoded default `R8Oq3y0eSZSYdKccHlrQzT1ACCOUT9Gv` (overridable via YAML `appid`/`appsecret`)

- **WebSocket API (persistent bidirectional):**
  - Dispatch endpoint: `https://{region}-dispa.coolkit.{cc,cn}/dispatch/app` → returns WebSocket domain/port
  - WebSocket: `wss://{domain}:{port}/api/ws`
  - Handshake action: `userOnline` (sends auth token, apikey, appid, nonce, ts)
  - Inbound actions: `update` (device state change), `sysmsg` (online status), responses to commands
  - Outbound actions: `update` (set device param), `query` (request device state)
  - Heartbeat: server-directed ping/pong at configurable interval (default 90s aiohttp heartbeat)
  - Region routing: phone country-code → region (cn/as/us/eu) table in `cloud.py` lines 39–245
  - Reconnect strategy: exponential backoff (15s → 30s → 1m → 2m → 4m → 8m → 16m → 32m → 64m)

### Sonoff Devices — Local LAN HTTP API

Implemented in `custom_components/sonoff/core/ewelink/local.py`.

- **Discovery:** mDNS/DNS-SD via `_ewelink._tcp.local.` service type using `zeroconf`
  - Filters: only `ewelink_*` service names (devices broadcasting their presence)
  - Device ID extracted from service name characters 8–18
- **HTTP Commands:** `POST http://{device_ip}:{port}/zeroconf/{command}`
  - Default port: `8081`; some devices use a different port
  - Commands: `switch`, `switches`, `transmit`, `dimmable`, `light`, `fan`, `getState`, `sledonline`, `statistics`, `getHoursKwh`, `startup`, `pulse`, `uiActive`, etc.
  - Payload: JSON `{sequence, deviceid, selfApikey, data}` — data may be AES-128-CBC encrypted
- **Encryption (non-DIY devices):**
  - Key: MD5 of `devicekey` (per-device secret from cloud, or from YAML config)
  - IV: 16 random bytes; PKCS7-padded AES-CBC encryption
  - `encrypt()` / `decrypt()` in `local.py` lines 28–57
- **DIY devices:** plaintext JSON, no encryption, no devicekey required
- **Camera devices (GK-200MP2-B):** UDP broadcast/unicast PTZ protocol implemented separately in `custom_components/sonoff/core/ewelink/camera.py`
  - Broadcast address: `255.255.255.255:32108` for hello/discovery
  - Custom binary frame protocol (not HTTP/REST)

## Data Storage

### Databases

- **None directly.** The integration stores data via Home Assistant's built-in state machine and entity registry.

### File Storage

- **HA Local Storage (`Store` API):** Device list cached to disk after each successful cloud sync
  - Path: `<HA_config_dir>/storage/sonoff/<username>.json`
  - Format: JSON array of device dicts from eWeLink API
  - Used as fallback when cloud is unavailable (`__init__.py` lines 224–242)
  - HA `Store` version: `1`

### Caching

- **In-memory device registry:** `XRegistry.devices` dict (`core/ewelink/__init__.py`) — holds all known devices and their live parameter state
- **Response waiter futures:** `ResponseWaiter._waiters` dict in `cloud.py` — short-lived asyncio futures keyed by sequence number, used to correlate WebSocket responses to commands

## Authentication & Identity

**eWeLink Account Auth:**
- Login: `POST /v2/user/login` with email or phone + password, HMAC-SHA256 signed with app secret
- Response: access token (`at`) + user metadata (apikey, countryCode) stored in `XRegistryCloud.auth`
- Token reuse: bearer token used for all subsequent REST and WebSocket calls
- Token-only mode: special username `"token"`, password `"<region>:<token>"` — skips password login, calls `GET /v2/user/profile` for validation
- Multi-account: multiple config entries supported; each has its own `XRegistry` and auth state
- Country code → region mapping: phone prefix table maps to `cn`/`as`/`us`/`eu` regions (`cloud.py`)
- Config entry stores: `username`, `password`, `country_code` (added automatically after first login)

**Local Device Auth:**
- Per-device `devicekey` (UUID) from eWeLink cloud — used as AES key derivation input
- DIY devices: no auth; unencrypted local HTTP
- Config allows manual `devicekey` override per device in YAML `devices` section

**App Identity:**
- Default App ID: `R8Oq3y0eSZSYdKccHlrQzT1ACCOUT9Gv` (value of `APP[0]` in `cloud.py`)
- App secret: embedded (obfuscated derivation in `sign()` function, `cloud.py` lines 289–297) or overridable via YAML `appid`/`appsecret`

## Monitoring & Observability

**Error Tracking:**
- Python `logging` module; logger named `custom_components.sonoff.*` and per-module loggers
- Optional `DebugView` (`system_health.py`): in-memory ring buffer (10,000 lines) of debug logs, served via a randomized HA HTTP endpoint (`/api/sonoff/<uuid>`) with query filters (`?q=`, `?t=`)

**Logs:**
- Standard Python logging at DEBUG/WARNING/ERROR levels
- Debug logging activated per config entry option `debug: true` → enables `setup_debug()` which injects the `DebugView` handler
- Private fields (`mac`, `ssid`, `bssid`, etc.) filtered from log args (`PRIVATE_KEYS` in `core/const.py`)

**System Health:**
- HA System Health integration (`system_health.py`): reports version, cloud online/total device counts, local online/total device counts via HA's System Health panel

**Diagnostics:**
- HA Diagnostics integration (`diagnostics.py`): structured device/config dump for bug reporting; redacts `password`, `username`, `devicekey`, and `PRIVATE_KEYS` fields

## CI/CD & Deployment

**Hosting:**
- Runs inside Home Assistant (any platform: Linux, Docker, Raspberry Pi, etc.)
- Distributed via HACS (Home Assistant Community Store) or manual file copy

**CI Pipeline:**
- Not detected — no GitHub Actions, Makefile, or CI config files in repository

## Internal Subsystem Integrations

**XRegistry ↔ XRegistryCloud + XRegistryLocal:**
- `XRegistry` (`core/ewelink/__init__.py`) owns both `XRegistryCloud` and `XRegistryLocal`
- Uses internal dispatcher pattern (`dispatcher_connect` / `dispatcher_send`) for signal-based event routing
- Signals: `SIGNAL_CONNECTED` (connection status change), `SIGNAL_UPDATE` (device state update), `SIGNAL_ADD_ENTITIES` (new HA entity registration), plus per-device-ID signals

**XRegistry ↔ HA Entity Layer:**
- Each `XEntity` subclass (`core/entity.py`) registers its `internal_update` callback via `ewelink.dispatcher_connect(deviceid, self.internal_update)`
- `XEntity.internal_available()` checks both cloud and local reachability via `ewelink.can_cloud()` / `ewelink.can_local()`
- Entities call `ewelink.send()` / `ewelink.send_bulk()` / `ewelink.send_cloud()` for command dispatch

**XRegistry dual-path command routing:**
- `XRegistry.send()` tries LAN first (1s timeout), falls back to cloud if LAN times out or fails
- Mode override: `"local"`, `"cloud"`, or `"auto"` (default) per config entry option
- `send_bulk()` coalesces multi-switch commands within a 100ms window to avoid redundant sends

**HA Platform Integrations:**
- Platforms loaded (in order): `sensor`, `alarm_control_panel`, `binary_sensor`, `button`, `climate`, `cover`, `fan`, `light`, `media_player`, `remote`, `switch`, `number`, `select`
- Sensor loaded first to ensure RF/Zigbee bridge parents are registered before children (`__init__.py` comment)
- Each platform module calls `ewelink.dispatcher_connect(SIGNAL_ADD_ENTITIES, ...)` to receive new entities

**HA Component Dependencies (manifest.json):**
- `http` — Used for `HomeAssistantView` debug endpoint registration
- `zeroconf` — Shared HA zeroconf instance acquired via `zeroconf.async_get_instance(hass)`

**Device Caching ↔ HA Storage:**
- `homeassistant.helpers.storage.Store` persists device list (`__init__.py`)
- On startup: loads from cloud → saves to Store; if cloud fails, loads from Store

## Webhooks & Callbacks

**Incoming:**
- None — the integration is a client only; it does not expose incoming webhook endpoints

**Outgoing:**
- WebSocket persistent connection to eWeLink cloud (device state updates pushed server→client)
- Local HTTP POST to device LAN endpoints (command delivery)
- UDP broadcast to camera devices (PTZ discovery/commands)

## Environment Configuration

**Required (for cloud mode):**
- eWeLink account `username` (email or phone number)
- eWeLink account `password`

**Optional YAML overrides (`configuration.yaml`):**
- `appid` / `appsecret` — Custom eWeLink developer app credentials
- `default_class` — Override default entity class (e.g., `"light"` instead of `"switch"`)
- `sensors` — List of custom device params to expose as sensors
- `rfbridge` — Per-channel RF bridge sensor configuration
- `devices` — Per-device overrides: `name`, `device_class`, `devicekey`, `reporting`

**Secrets location:**
- eWeLink credentials stored in HA Config Entry data (HA's encrypted config entry storage)
- Device keys stored in YAML `devices` config or pulled from eWeLink cloud at startup

---

*Integration audit: 2026-04-03*
