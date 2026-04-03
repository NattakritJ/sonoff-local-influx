# Project Research Summary

**Project:** SonoffLAN-InfluxDB
**Domain:** IoT telemetry bridge daemon — LAN event-driven → time-series DB
**Researched:** 2026-04-03
**Confidence:** HIGH

## Executive Summary

This is a brownfield extraction project: strip the HA integration layer from AlexxIT/SonoffLAN (v3.11.1) and rewire the surviving LAN transport (`ewelink/local.py` + `ewelink/base.py`) into a minimal standalone asyncio daemon that writes Sonoff energy telemetry to InfluxDB 3 Core. The architecture is a flat, three-layer pipeline — Config → Daemon → (LAN Transport | InfluxDB Writer) — with no HA imports anywhere in the new package. The existing codebase already solves the hard problems (mDNS discovery, AES-128-CBC decryption, multi-device event dispatch); the build task is primarily code surgery plus a new write layer.

The recommended approach is: copy only `base.py` and `local.py` into a new `ewelink/` package at the project root; implement five new modules (`config.py`, `daemon.py`, `extractor.py`, `writer.py`, `__main__.py`); package as a `python:3.12-slim-bookworm` Docker image configured entirely by env vars. InfluxDB writes use `influxdb3-python==0.18.0` (the v3-native client) in synchronous mode, offloaded to a thread via `asyncio.to_thread()` to avoid blocking the event loop. All data lands in a single `sonoff_energy` measurement table with `device_id` and `device_name` tags.

The two primary risks are: (1) residual HA imports in the carried-over files silently crashing startup — mitigated by testing each module in a clean venv without `homeassistant` installed; and (2) the `influxdb3-python` write method being synchronous and blocking the asyncio event loop — mitigated by wrapping every write in `asyncio.to_thread()`. A third operational risk — mDNS multicast being silently dropped in Docker bridge mode — is fully mitigated by requiring `network_mode: host` in the compose file and documenting Linux-only for production.

---

## Key Findings

### Recommended Stack

The carry-forward dependencies (`zeroconf 0.148.0`, `aiohttp 3.13.5`, `cryptography 46.0.6`) are all stable and already used in the source codebase. The only net-new dependency is `influxdb3-python 0.18.0`, the official InfluxData Python client for the v3 API. It is the only client that targets the `/api/v3/write_lp` endpoint — the legacy v2 client (`influxdb-client`) will silently fail against a v3 server. Python 3.12 is the correct runtime target: 3.13 is latest but `pyarrow` wheels (pulled in by influxdb3-python) occasionally lag; 3.11 is the project minimum but 3.12 is preferred for performance gains in the InfluxDB client docs. Alpine base image must be avoided — `cryptography` and `pyarrow` both require pre-built wheels not available on musl libc.

**Core technologies:**
- `Python 3.12` + `asyncio` (stdlib) — runtime and event loop; no alternative
- `zeroconf 0.148.0` — mDNS discovery via `AsyncServiceBrowser`; already validated in source
- `aiohttp 3.13.5` — HTTP POST to devices (LAN commands); already validated in source
- `cryptography 46.0.6` — AES-128-CBC decryption of encrypted device payloads; stable API
- `influxdb3-python 0.18.0` — v3-native InfluxDB write client; **only option for InfluxDB 3 Core**
- `pydantic-settings` — env var schema validation at startup; typed config with fail-fast errors
- `python:3.12-slim-bookworm` — Docker base image; pre-built wheels for all C-extension deps

**Critical version notes:**
- Do NOT use `influxdb-client` (v2 package) — different endpoint, different auth model, silent write failures against v3 server
- Do NOT use Alpine base — no pre-built `cryptography` or `pyarrow` wheels on musl libc

### Expected Features

**Must have (table stakes):**
- mDNS device discovery via `AsyncServiceBrowser` (`_ewelink._tcp.local.`) — no other discovery path exists
- AES-128-CBC decryption of encrypted LAN payloads — all non-DIY Sonoff devices encrypt; missing this = no data
- Plain JSON payload support (DIY/older devices) — auto-detect by `encrypt` field in TXT record
- Per-UIID energy param scaling — POWR2/S40 deliver pre-scaled floats; POWR3/S61/DualR3 deliver integer-cents needing ×0.01
- `sonoff_energy` InfluxDB writes with `device_id` tag — primary queryable schema
- Explicit device list from env var config — security requirement; unknown devices silently ignored
- `asyncio.to_thread()` offload for InfluxDB write — prevents event loop stall under write pressure
- Log-and-continue on write failure — InfluxDB unavailability must not crash daemon
- SIGTERM / SIGINT graceful shutdown — required for clean Docker container stop

**Should have (differentiators):**
- `device_name` tag from config — human-readable labels in Grafana without knowing device IDs
- `channel` tag for multi-channel devices (DualR3, SPM-4Relay) — per-channel Grafana queries
- Startup InfluxDB connectivity check — fail fast with clear error before accepting any device events
- Write counter heartbeat log line — operational visibility ("N events written in last 60s")
- All energy values coerced to `float` before write — prevents InfluxDB field type conflict errors

**Defer to v2+:**
- POWR3 LAN energy history poll (`POST /zeroconf/getHoursKwh`) — high complexity, single device model
- Non-energy data (switch state, temperature, humidity)
- Auto-discovery / zero-config mode
- eWeLink cloud connection or cloud energy history blobs

### Architecture Approach

The architecture is a flat pipeline with clear component boundaries and no shared mutable state between the LAN transport and the write layer. The only two files carried over from the source codebase are `ewelink/base.py` (dispatcher, `XDevice` TypedDict — zero HA imports) and `ewelink/local.py` (mDNS, decryption, HTTP — one relative import path change required). Everything else is new. The `SonoffDaemon` class replaces `XRegistry` as the lifecycle owner and dispatcher consumer; it wires `SIGNAL_UPDATE` callbacks from `XRegistryLocal` to an `InfluxWriter` via a pure-function `extract_energy()` extractor. State is instance-scoped only — no module globals, no class-level mutable attributes.

**Major components:**
1. **Config** (`config.py`) — `Settings(BaseSettings)`: validates all env vars at startup; immutable after init; process exits on missing required vars
2. **LAN Transport** (`ewelink/local.py`, `ewelink/base.py`) — mDNS discovery, AES decrypt, HTTP POST; carried over with import path fix only
3. **Params Extractor** (`extractor.py`) — pure function `extract_energy(params, device_cfg) → EnergyReading | None`; handles per-UIID scaling; fully unit-testable with no I/O
4. **InfluxDB Writer** (`writer.py`) — `InfluxWriter` wraps `InfluxDBClient3`; builds `Point`, calls write via `asyncio.to_thread()`; catches all exceptions and logs
5. **Daemon** (`daemon.py`) — `SonoffDaemon`: owns event loop lifecycle, wires components, handles SIGTERM/SIGINT via `asyncio.Event`
6. **Entrypoint** (`__main__.py`) — `asyncio.run(main())`: parse config, construct daemon, run

**Build order implied by dependencies:** Config → Transport → Extractor → Writer → Daemon → Docker

### Critical Pitfalls

1. **Wrong InfluxDB client** — `influxdb-client` (v2) vs `influxdb3-python` (v3) have near-identical names but incompatible APIs; v2 writes silently fail against a v3 server. Fix: pin `influxdb3-python==0.18.0` in `requirements.txt`; verify `import influxdb_client_3` resolves correctly.

2. **Blocking InfluxDB write on event loop** — `InfluxDBClient3.write()` is synchronous; calling it from `on_lan_update` blocks the event loop, delaying mDNS callbacks and dropping device events under write pressure. Fix: always wrap with `await asyncio.to_thread(self._client.write, point)`.

3. **HA import chain residue** — A single surviving `from homeassistant.xxx import ...` anywhere in the imported module tree crashes the process at startup. `devices.py` is the main risk — it imports all 12 HA platform files. Fix: copy only `base.py` and `local.py`; verify each in a clean venv (`python -c "import ewelink.local"`) with no `homeassistant` package installed.

4. **mDNS multicast blocked in Docker bridge mode** — Docker bridge networking silently drops UDP multicast; `zeroconf` starts without error but discovers nothing. Fix: require `network_mode: host` in `docker-compose.yml`; document that production deployment requires a Linux host (Docker Desktop on macOS/Windows does not support layer-2 multicast even with host networking).

5. **InfluxDB field type conflict on first write** — InfluxDB 3 locks field types on first write per table; Sonoff firmware occasionally sends `power` as a string (`"23.5"`) or integer (`0`). Fix: always coerce all metric values to `float(value)` in the extractor before populating `Point.field()`.

**Notable moderate pitfalls:**
- `asyncio.get_event_loop()` in carried-over code raises `RuntimeError` on Python 3.12+ outside a running loop — replace with `asyncio.get_running_loop()` inside coroutines
- `LAN send()` uses recursive retry (10 levels) — refactor to iterative loop to prevent `RecursionError` on flaky networks
- AES decryption with wrong `devicekey` silently produces garbage bytes → `json.JSONDecodeError` — wrap in `try/except` and log at ERROR level

---

## Implications for Roadmap

Based on research, suggested phase structure (5 phases, ~6 milestones total):

### Phase 1: Foundation — Standalone Entrypoint + LAN Transport
**Rationale:** Nothing else can run until HA imports are severed and the mDNS listener is operational in a clean Python environment. This is the highest-risk phase (import chain surgery) and must be validated first.
**Delivers:** A standalone Python process that discovers configured Sonoff devices via mDNS and decrypts their LAN payloads — no InfluxDB yet; output to stdout/logs.
**Features addressed:** mDNS discovery, AES decryption, plain JSON support, explicit device list config, graceful SIGTERM shutdown
**Pitfalls to avoid:** #5 HA import chain residue, #6 zeroconf singleton ownership, #7 `get_event_loop` deprecation, #15 zeroconf thread safety
**Validation gate:** `python -c "import ewelink.local"` in clean venv succeeds; daemon starts and logs discovered device events.

### Phase 2: Energy Extraction + Schema
**Rationale:** Extracting and scaling energy params from raw device payloads is pure logic that must be correct before any data reaches InfluxDB. Isolated unit-testable layer with no I/O dependencies.
**Delivers:** `extractor.py` with `extract_energy()` covering all supported UIIDs (32, 126, 130, 182, 190, 226, 262, 276, 277, 7032) and their scaling rules; `EnergyReading` dataclass; unit test suite.
**Features addressed:** Per-UIID scaling, multi-channel channel tag, float coercion
**Pitfalls to avoid:** #10 field type conflict (coerce to float here), #9 class-level state leakage in tests
**Validation gate:** Unit tests cover all scaling branches; string/int/float input all produce correct float output.

### Phase 3: InfluxDB Writer
**Rationale:** Isolated writer layer tested against a real or mocked InfluxDB 3 instance before being wired into the daemon.
**Delivers:** `writer.py` with `InfluxWriter` using `influxdb3-python`; correct `sonoff_energy` schema; async-safe write via `asyncio.to_thread()`; log-and-continue error handling.
**Stack:** `influxdb3-python==0.18.0`, synchronous write mode
**Pitfalls to avoid:** #1 wrong client package, #2 v2/v3 terminology mismatch, #3 blocking write on event loop, #11 silent batch error swallowing
**Validation gate:** Writer successfully writes a point to a live InfluxDB 3 Core instance; write failure logs error and does not raise.

### Phase 4: Integration — Full Daemon Pipeline
**Rationale:** Wire Phase 1 (transport) + Phase 2 (extractor) + Phase 3 (writer) together in `daemon.py`. First integration test of the complete end-to-end flow.
**Delivers:** `SonoffDaemon` class; `__main__.py` entrypoint; `config.py` with `Settings(BaseSettings)`; integration test that injects a fake mDNS event and asserts the InfluxDB point lands correctly.
**Features addressed:** All table-stakes features; `device_name` tag from config; write counter log
**Pitfalls to avoid:** #8 recursive retry in LAN send, #12 AES decryption silent failure, #13 asyncio task leak
**Validation gate:** End-to-end integration test passes; real device event appears in InfluxDB 3 with correct measurement/tags/fields.

### Phase 5: Docker Packaging + Deployment
**Rationale:** Docker is the only target deployment environment; packaging finalizes the deliverable and validates the mDNS networking requirement.
**Delivers:** `Dockerfile` (python:3.12-slim-bookworm), `docker-compose.yml` with `network_mode: host`, `.env.example`, `requirements.txt` with pinned versions.
**Pitfalls to avoid:** #4 mDNS multicast in bridge mode, #14 macOS Docker Desktop layer-2 limitation, #16 missing SIGTERM handling
**Validation gate:** `docker compose up` on a Linux host; daemon discovers devices and writes to InfluxDB 3; `docker stop` exits cleanly within 5 seconds.

### Phase Ordering Rationale

- **Config before transport:** `Settings(BaseSettings)` is the dependency of everything else; fail-fast validation at the module boundary prevents wasted debugging time.
- **Extractor before writer:** Pure-function extraction layer is the only component fully testable in isolation with no external services. Build and validate it before introducing InfluxDB.
- **Writer before daemon:** Test the write path in isolation against a real InfluxDB 3 instance to confirm the `influxdb3-python` integration works correctly before wiring it into the full event flow.
- **Docker last:** Packaging depends on all logic being stable; the mDNS networking requirement (host mode) is the final validation gate.

### Research Flags

**Standard patterns (skip research-phase) — all phases:**
All five phases are well-researched. The domain (asyncio daemon, InfluxDB 3 write, Docker networking) has high-quality official documentation and the source codebase was read directly. No phase requires a `/gsd-research-phase` call.

**Specific validation points to confirm during implementation:**
- Phase 1: Confirm `base.py` dispatcher has no hidden HA imports after path changes — run clean-venv import test immediately
- Phase 3: Confirm `InfluxDBClient3.from_env()` raises `ValueError` (not silent failure) on missing env vars — test before wiring to daemon config
- Phase 5: Confirm `docker stop` triggers SIGTERM to PID 1 correctly — verify container exits in <10s

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions verified live on PyPI (2026-04-03); Docker Hub tags verified; `influxdb3-python` source read directly |
| Features | HIGH | Energy param map extracted directly from `devices.py` v3.11.1 and `sensor.py`; InfluxDB 3 schema docs official |
| Architecture | HIGH | Source files `local.py`, `base.py`, `__init__.py` all read directly; asyncio + pydantic-settings patterns from official docs |
| Pitfalls | HIGH | Critical pitfalls derived from direct codebase analysis + official docs; all have concrete detection and prevention steps |

**Overall confidence: HIGH**

### Gaps to Address

- **Exact `local.py` import surgery:** ARCHITECTURE.md identifies the one relative import to change (`from .base import ...`), but the full `local.py` import graph should be re-verified in a clean venv during Phase 1 — there may be additional transitive imports not visible from a static read.
- **`zeroconf.async_get_instance(hass)` call location:** PITFALLS.md flags that `local.py` may call this HA-specific function; if present it must be replaced with a directly-owned `Zeroconf()` instance. Exact line not confirmed — verify during Phase 1 extraction.
- **Device update frequency under stable load:** FEATURES.md notes "may slow to 30–60s under stable load" with MEDIUM confidence. No official Sonoff firmware docs available. Not a blocker — daemon is purely event-driven and this only affects data granularity.
- **`InfluxDBClient3` exception type:** PITFALLS.md references `InfluxDBError`; confirm the exact importable exception class name from `influxdb_client_3` during Phase 3 writer implementation to ensure the `try/except` catches the right type.

---

## Data Schema Recommendation

```
measurement: sonoff_energy
  tag:   device_id    (string)   — indexed; primary filter key in queries
  tag:   device_name  (string)   — human label from config; optional, omit if not configured
  tag:   channel      (int)      — multi-channel devices only (DualR3/SPM-4Relay); omit for single-channel
  field: power        (float64)  — Watts, already-scaled to physical units at write time
  field: voltage      (float64)  — Volts, already-scaled
  field: current      (float64)  — Amperes, already-scaled
  field: energy_today (float64)  — kWh, already-scaled; only for UIIDs that push dayKwh
  timestamp: nanosecond UTC      — daemon receive time (devices do not include authoritative timestamp)
```

**Scaling rules (applied in `extractor.py` before write):**
- UIID 32 (POWR2), 182 (S40): `power`/`voltage`/`current` already floats — pass through ×1
- UIID 190 (POWR3), 276 (S61STPF), 126 (DualR3), 130 (SPM-4Relay), 7032, 262, 277: multiply by 0.01
- All cumulative kWh fields (`dayKwh`, `weekKwh`, `monthKwh`, `yearKwh`): multiply by 0.01
- Always coerce result to `float()` before calling `Point.field()` — prevents type conflict errors

---

## Sources

### Primary (HIGH confidence)
- `custom_components/sonoff/core/ewelink/local.py` v3.11.1 — LAN transport mechanics, handler pipeline
- `custom_components/sonoff/core/ewelink/base.py` v3.11.1 — dispatcher API, XDevice TypedDict
- `custom_components/sonoff/core/devices.py` v3.11.1 — UIID energy param map, scaling constants
- `custom_components/sonoff/sensor.py` v3.11.1 — units, scaling, decode logic
- https://github.com/InfluxCommunity/influxdb3-python — official v3 client source (read directly)
- https://pypi.org/project/influxdb3-python/ — verified version 0.18.0 live
- https://docs.influxdata.com/influxdb3/core/ — InfluxDB 3 Core write API, schema design
- https://hub.docker.com/_/python/tags — Docker base image tags verified

### Secondary (MEDIUM confidence)
- Community observations on Sonoff device update cadence (2–60s range) — no official firmware docs
- `.planning/codebase/CONCERNS.md` — codebase fragile areas (asyncio, recursion, global state)
- `.planning/codebase/INTEGRATIONS.md` — import chain and external integration audit

---
*Research completed: 2026-04-03*
*Ready for roadmap: yes*
