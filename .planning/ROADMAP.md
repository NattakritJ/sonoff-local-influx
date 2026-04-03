# Roadmap: SonoffLAN-InfluxDB

## Overview

Brownfield transformation of the AlexxIT/SonoffLAN Home Assistant integration into a standalone asyncio daemon. Four phases follow the natural dependency chain: strip HA imports and validate the LAN transport first, then build the energy extraction layer in isolation, then wire the InfluxDB write path, then integrate everything into a Docker-packaged daemon. Each phase delivers a fully testable, independently verifiable capability.

## Phases

- [x] **Phase 1: LAN Transport Foundation** - Strip HA code, validate standalone mDNS + AES decrypt works clean (completed 2026-04-03)
- [x] **Phase 2: Energy Extraction** - Pure extractor module covering all UIIDs with correct scaling (completed 2026-04-03)
- [x] **Phase 3: InfluxDB Writer** - Isolated async-safe write layer tested against live InfluxDB 3 Core (completed 2026-04-03)
- [ ] **Phase 4: Integration + Docker** - Wire all components into a deployable daemon image

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
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. LAN Transport Foundation | 2/2 | Complete   | 2026-04-03 |
| 2. Energy Extraction | 2/2 | Complete   | 2026-04-03 |
| 3. InfluxDB Writer | 2/2 | Complete   | 2026-04-03 |
| 4. Integration + Docker | 0/TBD | Not started | - |
