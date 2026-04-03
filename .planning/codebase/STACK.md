# Technology Stack

**Analysis Date:** 2026-04-03

## Languages

**Primary:**
- Python 3 - All component logic, entity definitions, protocol implementations

**Secondary:**
- JSON - Translation files (`custom_components/sonoff/translations/*.json`), manifest, HACS config

## Runtime

**Environment:**
- Home Assistant Core (minimum version 2023.2.0, enforced in `custom_components/sonoff/__init__.py` line 105)
- Python asyncio event loop (all I/O is async-native via `asyncio`, `aiohttp`)

**Package Manager:**
- None explicit - no `requirements.txt`, `pyproject.toml`, or `setup.cfg` present
- Dependencies are declared in `custom_components/sonoff/manifest.json` (`requirements: []`) — all runtime libraries are provided by Home Assistant itself

## Frameworks

**Core:**
- Home Assistant Custom Component Framework (≥2023.2.0) - Entity lifecycle, config entries, state machine, service registry

**Testing:**
- pytest - Test runner configured in `tests/pytest.ini`
  - Options: `-x` (stop on first failure), `-p no:cacheprovider`
  - No explicit version pinned; relies on HA's bundled pytest environment

**Build/Dev:**
- Not applicable — no build pipeline, no transpilation, no bundler

## Key Dependencies

**Provided by Home Assistant (not declared in manifest `requirements`):**

- `aiohttp` - Async HTTP client/server; used for:
  - `ClientSession` for all HTTP calls to eWeLink cloud REST API (`core/ewelink/cloud.py`, `core/ewelink/local.py`)
  - WebSocket client (`ClientWebSocketResponse`) for persistent cloud connection
  - `web.Request` / `web.Response` for the debug HTTP view (`system_health.py`)
  - `multidict.CIMultiDict` for custom User-Agent header injection (`core/xutils.py`)

- `cryptography` - AES-128-CBC encryption/decryption for local LAN device payloads
  - `cryptography.hazmat.primitives.ciphers` (Cipher, algorithms, modes)
  - `cryptography.hazmat.primitives.padding` (PKCS7)
  - Used in `custom_components/sonoff/core/ewelink/local.py` (`encrypt()`, `decrypt()` functions)

- `zeroconf` (HA dependency declared in `manifest.json`) - mDNS/DNS-SD service discovery for LAN devices
  - `zeroconf.ServiceStateChange`, `zeroconf.Zeroconf`
  - `zeroconf.asyncio.AsyncServiceBrowser`, `AsyncServiceInfo`
  - Used in `custom_components/sonoff/core/ewelink/local.py` to discover `_ewelink._tcp.local.` services

- `voluptuous` - Config schema validation for YAML configuration
  - Used in `custom_components/sonoff/__init__.py` (`CONFIG_SCHEMA`) and `config_flow.py`

- `multidict` - HTTP header dictionary (case-insensitive); used in `core/xutils.py` for User-Agent header

**Standard Library (relevant):**
- `asyncio` - Task scheduling, futures, event loop primitives throughout all core modules
- `base64`, `hashlib`, `hmac`, `json` - eWeLink API signature/auth (`cloud.py`)
- `os` (urandom) - IV generation for AES encryption (`local.py`)
- `socket` - UDP datagram socket for camera PTZ commands (`camera.py`)
- `threading` - Camera command thread (`camera.py`)
- `time` - Local device ping/TTL management (`ewelink/__init__.py`)
- `logging` - Python standard logging, augmented with custom `DebugView` handler (`system_health.py`)

## Configuration

**Environment:**
- No `.env` file; all runtime configuration flows through:
  - Home Assistant Config Entries (username, password, country_code, mode)
  - Optional `configuration.yaml` YAML block for advanced overrides (appid, appsecret, rfbridge, devices, sensors)
  - Home Assistant's local `Store` API (`homeassistant.helpers.storage.Store`) caches device list to disk at `<HA_config>/storage/sonoff/<username>.json`

**Build:**
- No build configuration files (no `Makefile`, `tox.ini`, `pyproject.toml`)
- Test config only: `tests/pytest.ini`

## Platform Requirements

**Development:**
- Home Assistant installation (≥2023.2.0) as runtime host
- Python 3.10+ (implied by HA 2023.2 minimum, uses `TypedDict`, `X | Y` union syntax in `base.py`)
- Network access to local LAN (for mDNS discovery and HTTP to devices on port 8081)
- Network access to eWeLink cloud APIs (optional, for cloud mode)

**Production:**
- Deployed as a HACS custom integration: copy `custom_components/sonoff/` into HA `<config>/custom_components/`
- Minimum Home Assistant 2023.2.0
- HA dependencies auto-resolved: `http` and `zeroconf` HA components (declared in `manifest.json`)
- Component version: `3.11.1` (from `custom_components/sonoff/manifest.json`)

---

*Stack analysis: 2026-04-03*
