# Requirements — SonoffLAN-InfluxDB

**Project:** SonoffLAN-InfluxDB standalone daemon
**Version:** v1
**Last updated:** 2026-04-03

---

## v1 Requirements

### LAN Transport

- [x] **LAN-01**: Daemon discovers configured Sonoff devices on the local network via mDNS (`_ewelink._tcp.local.`) at startup
- [x] **LAN-02**: Daemon receives energy update events in real-time from discovered devices (event-driven, no polling)
- [x] **LAN-03**: Daemon decrypts AES-128-CBC encrypted LAN payloads (non-DIY devices) using per-device `devicekey`
- [x] **LAN-04**: Daemon handles plain-JSON LAN payloads (DIY and older devices) without decryption
- [x] **LAN-05**: Daemon auto-detects whether a device uses encrypted or plain protocol per the mDNS TXT `encrypt` field
- [x] **LAN-06**: Daemon only processes devices in the configured device list; unknown devices are silently ignored

### Energy Extraction

- [x] **EXT-01**: Daemon extracts `power` (Watts), `voltage` (Volts), and `current` (Amperes) from device params for all supported UIIDs
- [x] **EXT-02**: Daemon extracts `energy_today` (kWh) from devices that push daily accumulator params (`dayKwh`)
- [x] **EXT-03**: Daemon applies correct per-UIID scaling: POWR2/S40 (UIIDs 32, 182) pass through ×1; POWR3/S61/DualR3/SPM variants (UIIDs 126, 130, 190, 226, 262, 276, 277, 7032) multiply by 0.01
- [x] **EXT-04**: Daemon coerces all extracted metric values to `float` before writing to prevent InfluxDB field type conflicts
- [x] **EXT-05**: Daemon tags multi-channel devices (DualR3, SPM-4Relay) with a `channel` tag per reading

### InfluxDB Writer

- [x] **INF-01**: Daemon writes each energy event to InfluxDB 3 Core immediately on receipt (no batching)
- [x] **INF-02**: Each InfluxDB write uses a per-device measurement name (one measurement per device, named by `device_id`)
- [x] **INF-03**: Each InfluxDB point includes a `device_id` tag and a `device_name` tag (if configured)
- [x] **INF-04**: Daemon authenticates with InfluxDB 3 using a token and writes to the configured bucket
- [x] **INF-05**: InfluxDB write uses `asyncio.to_thread()` to avoid blocking the asyncio event loop
- [x] **INF-06**: On InfluxDB write failure, daemon logs the error and continues without crashing

### Configuration

- [x] **CFG-01**: All configuration is provided via environment variables (no config files inside the container)
- [x] **CFG-02**: Required env vars: `INFLUX_HOST`, `INFLUX_TOKEN`, `INFLUX_DATABASE`, `SONOFF_DEVICES` (JSON list of device configs with `device_id`, `devicekey`, and optional `device_name`)
- [x] **CFG-03**: Daemon fails fast at startup with a clear error message if any required env var is missing or malformed
- [x] **CFG-04**: Daemon performs a connectivity check to InfluxDB at startup and fails fast if unreachable

### Runtime & Operations

- [x] **OPS-01**: Daemon runs as an always-on process (not a cron script)
- [x] **OPS-02**: Daemon handles SIGTERM and SIGINT for graceful shutdown (clean exit within 10 seconds)
- [x] **OPS-03**: Daemon emits structured log lines for key events: startup, device discovery, each energy write, write failures
- [x] **OPS-04**: Daemon logs a periodic heartbeat (write counter every 60 seconds) for operational visibility

### Docker Packaging

- [x] **DOC-01**: Daemon is packaged as a Docker image based on `python:3.12-slim-bookworm`
- [x] **DOC-02**: Docker image is configured via environment variables only
- [x] **DOC-03**: `docker-compose.yml` uses `network_mode: host` to enable mDNS multicast (Linux production)
- [x] **DOC-04**: Repository includes `.env.example` documenting all required and optional env vars
- [x] **DOC-05**: Repository includes pinned `requirements.txt` with all dependencies

### Codebase Migration

- [x] **MIG-01**: All Home Assistant code is removed (platform files, config_flow, entity.py, __init__.py HA integration, translations, manifest.json)
- [x] **MIG-02**: LAN transport files (`ewelink/base.py`, `ewelink/local.py`) are extracted and stripped of all HA imports
- [x] **MIG-03**: `devices.py` and all HA entity class files are removed; energy extraction logic is reimplemented in a standalone `extractor.py`

---

## v2 Requirements

### Static IP + HTTP Polling Mode

- [ ] **CFG-05**: Each device entry in `SONOFF_DEVICES` accepts an optional `ip` field; when present, mDNS discovery is skipped for that device and the daemon connects directly to the configured IP
- [ ] **LAN-07**: When a device has a configured `ip`, the daemon polls it via HTTP POST to `http://{ip}:8081/zeroconf/getState` at a fixed interval (configurable via `SONOFF_POLL_INTERVAL` env var, default 10 seconds)
- [ ] **LAN-08**: The polling interval is configurable per-daemon via `SONOFF_POLL_INTERVAL` env var (integer seconds, default 10); applies to all statically-configured devices
- [ ] **LAN-09**: Static IP polling and mDNS push modes can coexist in the same daemon — devices with `ip` set use polling; devices without `ip` use mDNS discovery as before

---

## v3 Requirements (Deferred)

- POWR3 LAN energy history polling (`POST /zeroconf/getHoursKwh`) — high complexity, single device model
- Non-energy data ingestion (switch state, temperature, humidity, motion)
- Auto-discovery mode (zero-config, no device list required)
- eWeLink cloud connection and cloud energy history
- Multi-bucket InfluxDB routing (per-device buckets)
- Prometheus metrics endpoint
- InfluxDB write batching / buffering option

---

## Out of Scope

- eWeLink cloud API — LAN-only; no cloud credentials required or supported
- Home Assistant — entire HA platform removed; this is a standalone daemon
- Non-energy Sonoff data (switch state, motion, temperature, humidity) — energy only in v1
- Auto-discovery of devices not in config — explicit list only for security
- InfluxDB instance management — connects to an existing server only
- Camera PTZ control — HA-specific feature, not relevant
- Sonoff camera streams — out of scope
- macOS production deployment — Docker host networking for mDNS requires Linux; macOS dev use only

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| MIG-01 | Phase 1: LAN Transport Foundation | Complete |
| MIG-02 | Phase 1: LAN Transport Foundation | Complete |
| MIG-03 | Phase 1: LAN Transport Foundation | Complete |
| LAN-01 | Phase 1: LAN Transport Foundation | Complete |
| LAN-02 | Phase 1: LAN Transport Foundation | Complete |
| LAN-03 | Phase 1: LAN Transport Foundation | Complete |
| LAN-04 | Phase 1: LAN Transport Foundation | Complete |
| LAN-05 | Phase 1: LAN Transport Foundation | Complete |
| LAN-06 | Phase 1: LAN Transport Foundation | Complete |
| CFG-01 | Phase 1: LAN Transport Foundation | Complete |
| CFG-02 | Phase 1: LAN Transport Foundation | Complete |
| CFG-03 | Phase 1: LAN Transport Foundation | Complete |
| OPS-01 | Phase 1: LAN Transport Foundation | Complete |
| OPS-02 | Phase 1: LAN Transport Foundation | Complete |
| EXT-01 | Phase 2: Energy Extraction | Complete |
| EXT-02 | Phase 2: Energy Extraction | Complete |
| EXT-03 | Phase 2: Energy Extraction | Complete |
| EXT-04 | Phase 2: Energy Extraction | Complete |
| EXT-05 | Phase 2: Energy Extraction | Complete |
| INF-01 | Phase 3: InfluxDB Writer | Complete |
| INF-02 | Phase 3: InfluxDB Writer | Complete |
| INF-03 | Phase 3: InfluxDB Writer | Complete |
| INF-04 | Phase 3: InfluxDB Writer | Complete |
| INF-05 | Phase 3: InfluxDB Writer | Complete |
| INF-06 | Phase 3: InfluxDB Writer | Complete |
| CFG-04 | Phase 3: InfluxDB Writer | Complete |
| OPS-03 | Phase 4: Integration + Docker | Complete |
| OPS-04 | Phase 4: Integration + Docker | Complete |
| DOC-01 | Phase 4: Integration + Docker | Complete |
| DOC-02 | Phase 4: Integration + Docker | Complete |
| DOC-03 | Phase 4: Integration + Docker | Complete |
| DOC-04 | Phase 4: Integration + Docker | Complete |
| DOC-05 | Phase 4: Integration + Docker | Complete |
| CFG-05 | Phase 5: Static IP + Polling Mode | Pending |
| LAN-07 | Phase 5: Static IP + Polling Mode | Pending |
| LAN-08 | Phase 5: Static IP + Polling Mode | Pending |
| LAN-09 | Phase 5: Static IP + Polling Mode | Pending |
