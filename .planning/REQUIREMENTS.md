# Requirements — SonoffLAN-InfluxDB

**Project:** SonoffLAN-InfluxDB standalone daemon
**Version:** v1
**Last updated:** 2026-04-03

---

## v1 Requirements

### LAN Transport

- [ ] **LAN-01**: Daemon discovers configured Sonoff devices on the local network via mDNS (`_ewelink._tcp.local.`) at startup
- [ ] **LAN-02**: Daemon receives energy update events in real-time from discovered devices (event-driven, no polling)
- [ ] **LAN-03**: Daemon decrypts AES-128-CBC encrypted LAN payloads (non-DIY devices) using per-device `devicekey`
- [ ] **LAN-04**: Daemon handles plain-JSON LAN payloads (DIY and older devices) without decryption
- [ ] **LAN-05**: Daemon auto-detects whether a device uses encrypted or plain protocol per the mDNS TXT `encrypt` field
- [ ] **LAN-06**: Daemon only processes devices in the configured device list; unknown devices are silently ignored

### Energy Extraction

- [ ] **EXT-01**: Daemon extracts `power` (Watts), `voltage` (Volts), and `current` (Amperes) from device params for all supported UIIDs
- [ ] **EXT-02**: Daemon extracts `energy_today` (kWh) from devices that push daily accumulator params (`dayKwh`)
- [ ] **EXT-03**: Daemon applies correct per-UIID scaling: POWR2/S40 (UIIDs 32, 182) pass through ×1; POWR3/S61/DualR3/SPM variants (UIIDs 126, 130, 190, 226, 262, 276, 277, 7032) multiply by 0.01
- [ ] **EXT-04**: Daemon coerces all extracted metric values to `float` before writing to prevent InfluxDB field type conflicts
- [ ] **EXT-05**: Daemon tags multi-channel devices (DualR3, SPM-4Relay) with a `channel` tag per reading

### InfluxDB Writer

- [ ] **INF-01**: Daemon writes each energy event to InfluxDB 3 Core immediately on receipt (no batching)
- [ ] **INF-02**: Each InfluxDB write uses a per-device measurement name (one measurement per device, named by `device_id`)
- [ ] **INF-03**: Each InfluxDB point includes a `device_id` tag and a `device_name` tag (if configured)
- [ ] **INF-04**: Daemon authenticates with InfluxDB 3 using a token and writes to the configured bucket
- [ ] **INF-05**: InfluxDB write uses `asyncio.to_thread()` to avoid blocking the asyncio event loop
- [ ] **INF-06**: On InfluxDB write failure, daemon logs the error and continues without crashing

### Configuration

- [ ] **CFG-01**: All configuration is provided via environment variables (no config files inside the container)
- [ ] **CFG-02**: Required env vars: `INFLUX_HOST`, `INFLUX_TOKEN`, `INFLUX_DATABASE`, `SONOFF_DEVICES` (JSON list of device configs with `device_id`, `devicekey`, and optional `device_name`)
- [ ] **CFG-03**: Daemon fails fast at startup with a clear error message if any required env var is missing or malformed
- [ ] **CFG-04**: Daemon performs a connectivity check to InfluxDB at startup and fails fast if unreachable

### Runtime & Operations

- [ ] **OPS-01**: Daemon runs as an always-on process (not a cron script)
- [ ] **OPS-02**: Daemon handles SIGTERM and SIGINT for graceful shutdown (clean exit within 10 seconds)
- [ ] **OPS-03**: Daemon emits structured log lines for key events: startup, device discovery, each energy write, write failures
- [ ] **OPS-04**: Daemon logs a periodic heartbeat (write counter every 60 seconds) for operational visibility

### Docker Packaging

- [ ] **DOC-01**: Daemon is packaged as a Docker image based on `python:3.12-slim-bookworm`
- [ ] **DOC-02**: Docker image is configured via environment variables only
- [ ] **DOC-03**: `docker-compose.yml` uses `network_mode: host` to enable mDNS multicast (Linux production)
- [ ] **DOC-04**: Repository includes `.env.example` documenting all required and optional env vars
- [ ] **DOC-05**: Repository includes pinned `requirements.txt` with all dependencies

### Codebase Migration

- [ ] **MIG-01**: All Home Assistant code is removed (platform files, config_flow, entity.py, __init__.py HA integration, translations, manifest.json)
- [ ] **MIG-02**: LAN transport files (`ewelink/base.py`, `ewelink/local.py`) are extracted and stripped of all HA imports
- [ ] **MIG-03**: `devices.py` and all HA entity class files are removed; energy extraction logic is reimplemented in a standalone `extractor.py`

---

## v2 Requirements (Deferred)

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

| REQ-ID | Phase | Notes |
|--------|-------|-------|
| LAN-01 – LAN-06 | Phase 1: LAN Transport | |
| EXT-01 – EXT-05 | Phase 2: Energy Extraction | |
| INF-01 – INF-06 | Phase 3: InfluxDB Writer | |
| CFG-01 – CFG-04 | Phase 1 (CFG-01–03), Phase 3 (CFG-04) | |
| OPS-01 – OPS-04 | Phase 1 (OPS-01–02), Phase 4 Integration (OPS-03–04) | |
| DOC-01 – DOC-05 | Phase 4: Docker Packaging | |
| MIG-01 – MIG-03 | Phase 1: LAN Transport | |
