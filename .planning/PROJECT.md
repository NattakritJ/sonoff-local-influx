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

### Active

- [ ] Standalone daemon entrypoint (no HA) — strips all HA lifecycle code
- [ ] Docker image with env var configuration (InfluxDB URL, token, bucket; device list)
- [ ] Wire LAN transport → energy extractor → InfluxWriter into main event loop
- [ ] Configurable device list (specific device IDs/IPs — no auto-discover)
- [ ] Support both encrypted and plain LAN protocols (auto-detect per device)
- [ ] Structured logging with log-and-continue on InfluxDB write failure
- [ ] Graceful shutdown (SIGTERM/SIGINT handling)

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
| Docker-only deployment | Simplest reproducible environment; no system Python management | — Pending |
| LAN-only (no cloud fallback) | Simpler auth model; no eWeLink credentials needed | — Pending |

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
*Last updated: 2026-04-03 — Phase 3 complete: InfluxWriter async write layer (writer.py, 18 unit tests, 4 integration tests, requirements pinned)*
