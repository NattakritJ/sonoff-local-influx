# Roadmap: SonoffLAN-InfluxDB

## Overview

Brownfield transformation of the AlexxIT/SonoffLAN Home Assistant integration into a standalone asyncio daemon. Four phases follow the natural dependency chain: strip HA imports and validate the LAN transport first, then build the energy extraction layer in isolation, then wire the InfluxDB write path, then integrate everything into a Docker-packaged daemon. Each phase delivers a fully testable, independently verifiable capability.

## Phases

- [x] **Phase 1: LAN Transport Foundation** - Strip HA code, validate standalone mDNS + AES decrypt works clean (completed 2026-04-03)
- [x] **Phase 2: Energy Extraction** - Pure extractor module covering all UIIDs with correct scaling (completed 2026-04-03)
- [x] **Phase 3: InfluxDB Writer** - Isolated async-safe write layer tested against live InfluxDB 3 Core (completed 2026-04-03)
- [x] **Phase 4: Integration + Docker** - Wire all components into a deployable daemon image (completed 2026-04-03)
- [ ] **Phase 5: Static IP + Polling Mode** - Allow devices to be configured with a static IP; poll via HTTP at a fixed interval as an alternative to mDNS push (works on macOS and in Docker on any OS)

## Phase Details

### Phase 1: LAN Transport Foundation
**Goal**: A standalone Python process discovers configured Sonoff devices via mDNS and decrypts their LAN payloads — no HA imports anywhere, no InfluxDB yet; output to logs only
**Depends on**: Nothing (first phase)
**Requirements**: MIG-01, MIG-02, MIG-03, LAN-01, LAN-02, LAN-03, LAN-04, LAN-05, LAN-06, CFG-01, CFG-02, CFG-03, OPS-01, OPS-02
**Success Criteria** (what must be TRUE):
  1. `python -c "import ewelink.local"` in a clean venv (no `homeassistant` package) succeeds without error
  2. Daemon starts, reads `SONOFF_DEVICES` env var, and logs a startup event; fails immediately with a clear message if any required env var is missing
  3. Configured Sonoff devices appear in the log as discovered within 10 seconds of startup; unconfigured devices produce no log output
  4. Encrypted (non-DIY) and plain-JSON (DIY) device payloads are both decoded and logged correctly; protocol is auto-detected per device
  5. Daemon exits cleanly within 10 seconds on SIGTERM or SIGINT
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Extract clean `src/ewelink/` package from HA codebase; add `requirements.txt`
- [x] 01-02-PLAN.md — Config loading, async daemon entrypoint, mDNS wiring, SIGTERM shutdown

### Phase 2: Energy Extraction
**Goal**: A pure-function extractor module that converts raw Sonoff device params into typed `EnergyReading` values with correct per-UIID scaling — fully unit-testable with no I/O
**Depends on**: Phase 1
**Requirements**: EXT-01, EXT-02, EXT-03, EXT-04, EXT-05
**Success Criteria** (what must be TRUE):
  1. `extract_energy()` returns correct `power`, `voltage`, `current` floats for all supported UIIDs (32, 126, 130, 182, 190, 226, 262, 276, 277, 7032)
  2. POWR3/S61/DualR3/SPM variants (UIIDs 126, 130, 190, 226, 262, 276, 277, 7032) produce values scaled by ×0.01; POWR2/S40 (UIIDs 32, 182) pass through ×1
  3. String, integer, and float raw inputs all produce `float` output — no `TypeError` or field type mismatch possible
  4. Multi-channel devices (DualR3, SPM-4Relay) emit one `EnergyReading` per channel with a `channel` tag set correctly
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — EnergyReading dataclass + extract_energy() for all single-channel UIIDs (32, 182, 190, 226, 262, 276, 277, 7032) with per-UIID scaling + type coercion
- [x] 02-02-PLAN.md — extract_energy_multi() for multi-channel DualR3 (UIID 126) and SPM-4Relay (UIID 130) with channel tag

### Phase 3: InfluxDB Writer
**Goal**: An isolated `InfluxWriter` class that writes energy events to InfluxDB 3 Core asynchronously, with correct schema, without blocking the event loop, and with log-and-continue error handling
**Depends on**: Phase 2
**Requirements**: INF-01, INF-02, INF-03, INF-04, INF-05, INF-06, CFG-04
**Success Criteria** (what must be TRUE):
  1. A manually-constructed `EnergyReading` is written to a live InfluxDB 3 Core instance and appears in a query with the correct measurement name, `device_id` tag, `device_name` tag, and float field values
  2. Each write uses `asyncio.to_thread()` — the event loop is not blocked during write operations
  3. When InfluxDB is unreachable or returns an error, the writer logs the error at ERROR level and returns without raising — the caller is unaffected
  4. Daemon fails fast at startup with a clear error if the InfluxDB connectivity check fails
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — TDD: InfluxWriter class with async write(), check_connectivity(), error handling + 17 unit tests (mocked)
- [x] 03-02-PLAN.md — Integration test against live InfluxDB 3 Core; update requirements.txt + pytest.ini

### Phase 4: Integration + Docker
**Goal**: All components wired into `SonoffDaemon` with a `__main__.py` entrypoint, packaged as a Docker image with `network_mode: host`, configured entirely by env vars — end-to-end energy events flow from real devices into InfluxDB
**Depends on**: Phase 3
**Requirements**: OPS-03, OPS-04, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05
**Success Criteria** (what must be TRUE):
  1. `docker compose up` on a Linux host starts the daemon; it discovers configured Sonoff devices and writes energy events to InfluxDB 3 Core within 60 seconds
  2. Each energy write produces a structured log line; write failures log at ERROR but do not stop the daemon
  3. A heartbeat log line appears every 60 seconds reporting the write counter
  4. `docker stop` sends SIGTERM; the container exits cleanly within 10 seconds
  5. `.env.example` documents every required and optional env var; `requirements.txt` has all dependencies pinned
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Wire extractor + writer into SonoffDaemon; add InfluxDB env var parsing; heartbeat; pin requirements.txt
- [x] 04-02-PLAN.md — Docker packaging: Dockerfile, docker-compose.yml, .env.example; human-verify checkpoint

### Phase 5: Static IP + Polling Mode
**Goal**: Devices configured with a static `ip` field bypass mDNS entirely and are polled via HTTP `getState` at a fixed interval — enabling Docker and macOS deployments where mDNS multicast is unavailable
**Depends on**: Phase 4
**Requirements**: CFG-05, LAN-07, LAN-08, LAN-09
**Success Criteria** (what must be TRUE):
  1. A device with `"ip":"192.168.x.x"` in `SONOFF_DEVICES` is polled via HTTP and writes energy readings without any mDNS involvement
  2. `SONOFF_POLL_INTERVAL` env var (default 10s) controls the polling cadence; startup log confirms the interval in use
  3. A device without `ip` continues to use mDNS push as before — both modes coexist in the same daemon instance
  4. `docker compose up --build` on macOS successfully writes data when devices have static IPs configured
  5. Polling failures (HTTP timeout, device offline) log a warning and retry on the next interval — daemon never crashes
**Plans**: TBD (run `/gsd:plan-phase` to generate)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. LAN Transport Foundation | 2/2 | Complete   | 2026-04-03 |
| 2. Energy Extraction | 2/2 | Complete   | 2026-04-03 |
| 3. InfluxDB Writer | 2/2 | Complete   | 2026-04-03 |
| 4. Integration + Docker | 2/2 | Complete   | 2026-04-03 |
| 5. Static IP + Polling Mode | 0/? | Pending    | — |

### Phase 6: Add POWCT grid backfeed capture: store dayPowerSupply, supplyCurrent and supplyPower as negative current and power fields in InfluxDB for uiid 190 devices

**Goal:** Extend UIID 190 (SONOFF POWCT) energy extraction to capture grid backfeed metrics — sign-encoding `supplyPower`/`supplyCurrent` as negative `power`/`current` values in InfluxDB, and adding a new `energy_backfeed_today` field from `dayPowerSupply` — enabling a single Grafana `power` query to show both consumption (positive) and export (negative)
**Requirements**: EXT-06
**Depends on:** Phase 5
**Plans:** 1/1 plans complete

Plans:
- [x] 06-01-PLAN.md — TDD: extend EnergyReading + extract_energy() UIID 190 backfeed branch + writer.write() energy_backfeed_today field

### Phase 7: Direct connection without mDNS if already knowing device's IP

**Goal:** Enable devices configured with a static `ip` field to bypass mDNS discovery entirely and be polled via HTTP getState at a fixed interval — making the daemon usable on macOS and in Docker environments where mDNS multicast is unavailable, while mDNS push mode continues to work for devices without a static IP
**Requirements**: CFG-05, LAN-07, LAN-08, LAN-09
**Depends on:** Phase 6
**Plans:** 2/2 plans complete

Plans:
- [x] 07-01-PLAN.md — TDD: ip field in DeviceConfig + parse_poll_interval() with unit tests
- [x] 07-02-PLAN.md — Wire polling tasks + conditional mDNS in SonoffDaemon.run(); update .env.example
