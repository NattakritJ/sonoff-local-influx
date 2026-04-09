# SonoffLAN-InfluxDB

## What This Is

A standalone Python daemon that listens for energy telemetry from Sonoff smart devices on the local network and writes the data to an InfluxDB 3 Core instance. It replaces the Home Assistant integration layer entirely — no HA, no config entries, no entity system — just device discovery, protocol handling, and time-series data ingestion. Runs as a Docker container configured entirely via environment variables.

## Core Value

Reliable, low-latency energy data from Sonoff LAN devices flowing into InfluxDB 3 — every event written immediately, no HA dependency.

## Requirements

### Validated

- ✓ LAN device discovery via mDNS (`_ewelink._tcp.local.`) — existing
- ✓ AES-128-CBC decryption of encrypted LAN payloads (non-DIY devices) — existing
- ✓ Plain JSON LAN protocol support (DIY / older devices) — existing
- ✓ Energy metrics extraction (power, voltage, current, energy) from device params — existing
- ✓ Async event loop with `asyncio` + `aiohttp` — existing

### Validated in Phase 2: Energy Extraction

- ✓ `EnergyReading` dataclass with `power`, `voltage`, `current`, `energy_today`, `channel` fields
- ✓ `extract_energy()` pure function for all single-channel UIIDs (32, 182, 190, 226, 262, 276, 277, 7032) with correct ×1/×0.01 scaling and string→float coercion
- ✓ `extract_energy_multi()` for multi-channel UIIDs 126 (DualR3, 2ch) and 130 (SPM-4Relay, 4ch) with per-channel `EnergyReading` and ×0.01 scaling
- ✓ Zero HA/ewelink imports in extractor — fully standalone pure-function module
- ✓ 28-test TDD suite covering all UIIDs, edge cases, and type coercion

### Validated in Phase 3: InfluxDB Writer

- ✓ `InfluxWriter` class with async `write()` and `check_connectivity()` — never blocks event loop
- ✓ `asyncio.to_thread()` wraps all synchronous `InfluxDBClient3` calls (INF-05)
- ✓ Point schema: measurement=device_id, tags={device_id, device_name}, fields={power, voltage, current, energy_today} (INF-01, INF-02, INF-03)
- ✓ None field values omitted from Point — no null writes (INF-04)
- ✓ Log-and-continue error handling: exceptions caught, logged at ERROR, never propagated (INF-06)
- ✓ `check_connectivity()` raises `RuntimeError("InfluxDB unreachable...")` on failure
- ✓ `influxdb3-python==0.18.0` pinned in requirements.txt (CFG-04)
- ✓ Integration test suite with auto-skip when `INFLUX_HOST` unset — CI-safe
- ✓ 18-test TDD unit suite + 4 integration tests verified against live InfluxDB 3 Core

### Validated in Phase 4: Integration + Docker

- ✓ `SonoffDaemon` class wires ewelink LAN transport → `extract_energy()`/`extract_energy_multi()` → `InfluxWriter.write()` in a single async event loop (OPS-03, OPS-04)
- ✓ `parse_influx_config()` reads `INFLUX_HOST`, `INFLUX_TOKEN`, `INFLUX_DATABASE` with fail-fast per-variable error messages (CFG-04)
- ✓ Heartbeat loop logs write counter every 60 seconds
- ✓ Graceful SIGTERM/SIGINT shutdown within 10 seconds
- ✓ Structured INFO log per write: `WRITE | device_id (name) | ch=- | power=X W | ...`
- ✓ `Dockerfile` — `python:3.12-slim-bookworm`, non-root `sonoff` user, layer-cache optimized (DOC-01, DOC-02)
- ✓ `docker-compose.yml` — `network_mode: host` for mDNS multicast, `env_file: .env`, log rotation (DOC-03, DOC-04)
- ✓ `.env.example` — all 4 required env vars documented with inline comments and examples (DOC-05)
- ✓ All 4 dependencies pinned in `requirements.txt` with `==` version specifiers

### Validated in Phase 6: POWCT Grid Backfeed

- ✓ `EnergyReading.energy_backfeed_today: float | None` field added (default `None`, backward-compatible with all other UIIDs)
- ✓ UIID 190 backfeed branch in `extract_energy()` with three-way power-flow logic: export → negative sign encoding; consumption → positive; both-zero → `EnergyReading(power=0.0)` (never `None`)
- ✓ `dayPowerSupply` → `energy_backfeed_today = round(val × 0.01, 4)` when present, `None` when absent
- ✓ `writer.write()` includes `energy_backfeed_today` in InfluxDB point when non-None; omits when None
- ✓ 8 new TDD tests (39 total) covering all UIID 190 backfeed cases — zero regressions in other UIIDs

### Validated in Phase 7: Direct Connection Without mDNS

- ✓ `DeviceConfig.ip: str` optional field — `parse_config()` conditionally stores it from device JSON when present (CFG-05, LAN-08)
- ✓ `parse_poll_interval()` — reads `SONOFF_POLL_INTERVAL` with default 10s, `sys.exit(1)` on non-integer/zero/negative (CFG-05)
- ✓ `SonoffDaemon._poll_device()` — loops `XRegistryLocal.send(getState)`, logs `POLL FAILED`/`POLL ERROR` at WARNING, propagates `CancelledError` cleanly (LAN-07)
- ✓ `SonoffDaemon.run()` splits devices by `ip` presence — `AsyncZeroconf` only created when at least one device lacks `ip` (LAN-09)
- ✓ Both transport modes coexist in the same daemon instance — polling + mDNS simultaneously (LAN-07)
- ✓ Polling tasks cancelled/awaited on SIGTERM — same shutdown lifecycle as heartbeat (LAN-07)
- ✓ Bug fix: `devicekey` only included in `XDevice` dict when non-empty — prevents accidental AES encryption on keyless/DIY devices
- ✓ `.env.example` documents `SONOFF_POLL_INTERVAL` and `ip` field with mixed-mode examples (DOC-05)
- ✓ 87 unit tests passing across all phases — zero regressions

### Active

(none — all milestone v1.0 requirements delivered, Phase 7 complete)

### Out of Scope

- eWeLink Cloud API — LAN-only; no cloud dependency
- Home Assistant integration — entire HA platform layer removed
- Non-energy data (switch state, temperature, humidity, motion) — energy metrics only for now
- Auto-discovery of unknown devices — explicit config list only
- Batched writes / write buffering — immediate write per event
- InfluxDB instance management — target an existing server only
- Camera PTZ control — HA-specific feature, removed

## Context

This project is a **brownfield transformation** of the [AlexxIT/SonoffLAN](https://github.com/AlexxIT/SonoffLAN) Home Assistant custom integration (v3.11.1). The existing codebase provides:

- **LAN transport** (`core/ewelink/local.py`) — mDNS discovery via `zeroconf`, HTTP POST to devices, AES-128-CBC encryption/decryption. This is the core reusable module.
- **Device spec registry** (`core/devices.py`) — maps UIIDs to entity classes, energy params extraction logic. Energy params identified: `power`, `voltage`, `current`, `energyUsage`/`hundredDayData`.
- **Registry/dispatcher** (`core/ewelink/__init__.py`, `base.py`) — async signal bus. Will be simplified; HA-specific parts stripped.

The HA entity layer (`__init__.py`, all platform files, `config_flow.py`, `entity.py`, translations) will be removed entirely.

**Target environment:**
- Docker container on local network with access to Sonoff devices and InfluxDB 3 Core server
- InfluxDB 3 Core already provisioned — program only writes to it
- Python 3.11+

**Key dependency decisions:**
- `influxdb3-python` (official InfluxDB 3 client) for writes
- `zeroconf` for mDNS discovery (already used)
- `aiohttp` for LAN HTTP POST to devices (already used)
- `cryptography` for AES decryption (already used)

## Constraints

- **Protocol:** LAN only — no eWeLink cloud account required
- **Data:** Energy metrics only — `power`, `voltage`, `current`, `energyUsage`
- **Config:** Docker env vars only — no config files inside the container
- **InfluxDB:** v3 Core API (not v1 or v2 line protocol via legacy endpoint)
- **Devices:** Explicit list in config — not zero-config auto-discovery
- **Write strategy:** Immediate per-event — no buffering or batching
- **Error handling:** Log-and-continue — InfluxDB failures do not crash the daemon

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Reuse `core/ewelink/local.py` LAN transport | Core protocol work already done and tested | — Pending |
| Strip all HA code rather than wrapping it | Avoid HA import chain; reduces dependencies by ~15 packages | — Pending |
| `influxdb3-python` client | Official v3 client; supports InfluxDB 3 write API with token auth | Validated in Phase 3 — pinned at 0.18.0 |
| Per-device measurements in InfluxDB | Easier to query per-device; avoids tag cardinality issues | Validated in Phase 3 — measurement=device_id confirmed |
| Docker-only deployment | Simplest reproducible environment; no system Python management | Validated in Phase 4 — Dockerfile + docker-compose.yml delivered |
| LAN-only (no cloud fallback) | Simpler auth model; no eWeLink credentials needed | Validated in Phase 4 — XRegistryLocal only, no cloud imports |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-09 — Phase 7 complete: static-IP polling mode. Devices with `ip` set bypass mDNS entirely via HTTP polling; devices without `ip` continue on mDNS push. Both modes coexist. 87/87 unit tests pass. Milestone v1.0 complete.*
