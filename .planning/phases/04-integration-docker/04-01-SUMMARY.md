---
phase: 04-integration-docker
plan: "01"
subsystem: infra
tags: [asyncio, aiohttp, influxdb, zeroconf, ewelink, daemon]

# Dependency graph
requires:
  - phase: 01-lan-transport
    provides: XRegistryLocal, SIGNAL_UPDATE, mDNS discovery
  - phase: 02-energy-extraction
    provides: extract_energy(), extract_energy_multi(), EnergyReading
  - phase: 03-influxdb-writer
    provides: InfluxWriter.write(), check_connectivity(), close()
provides:
  - SonoffDaemon class wiring all three components into a single event loop
  - parse_influx_config() reading INFLUX_HOST/TOKEN/DATABASE from env vars
  - Heartbeat loop logging write counter every 60 seconds
  - requirements.txt with all 4 deps pinned at exact versions
affects: [04-integration-docker-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - asyncio.ensure_future() for fire-and-forget InfluxDB writes from sync _on_update callback
    - asyncio.Event for SIGTERM/SIGINT shutdown coordination
    - frozenset for O(1) UIID lookup in _MULTI_CHANNEL_UIIDS

key-files:
  created: []
  modified:
    - src/config.py
    - src/__main__.py
    - requirements.txt

key-decisions:
  - "asyncio.ensure_future() used in sync _on_update() to schedule async writes without blocking mDNS callback"
  - "Multi-channel UIIDs (126, 130) checked via frozenset constant _MULTI_CHANNEL_UIIDS for clarity and O(1) lookup"
  - "writer.write() never raises — success log line placed after write() call, relying on writer's internal error handling"

patterns-established:
  - "SonoffDaemon: class-based daemon with run(), _on_update(), _write_reading(), _heartbeat() separation"
  - "parse_influx_config(): fail-fast pattern matching parse_config() — print individual ERROR lines, sys.exit(1)"

requirements-completed: [OPS-03, OPS-04]

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 4 Plan 01: Integration — SonoffDaemon Summary

**SonoffDaemon class wiring ewelink mDNS transport → energy extractor → InfluxWriter with fail-fast env-var config and 60s heartbeat**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-03T11:55:37Z
- **Completed:** 2026-04-03T11:57:26Z
- **Tasks:** 3 completed
- **Files modified:** 3

## Accomplishments

- `parse_influx_config()` added to `config.py` — reads INFLUX_HOST, INFLUX_TOKEN, INFLUX_DATABASE from env vars with fail-fast error output per missing var
- `SonoffDaemon` class rewrites `__main__.py` — `_on_update()` routes UIIDs to `extract_energy()` or `extract_energy_multi()`, schedules `_write_reading()` via `asyncio.ensure_future()`
- `requirements.txt` pinned at exact installed versions — `aiohttp==3.13.5`, `cryptography==44.0.3`, `influxdb3-python==0.18.0`, `zeroconf==0.148.0`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add parse_influx_config() to config.py** - `81178e9` (feat)
2. **Task 2: Rewrite __main__.py as SonoffDaemon** - `47e095f` (feat)
3. **Task 3: Pin requirements.txt** - `259a3ec` (chore)

## Files Created/Modified

- `src/config.py` — Added `parse_influx_config()` returning `(host, token, database)` tuple from env vars; follows same fail-fast pattern as `parse_config()`
- `src/__main__.py` — Fully rewritten as `SonoffDaemon` class; old logging-only implementation replaced with real data pipeline wiring all three prior-phase components
- `requirements.txt` — Replaced range specifiers with exact `==` pins matching installed venv versions

## Decisions Made

- `asyncio.ensure_future()` used inside the synchronous `_on_update()` callback to schedule async `_write_reading()` calls without converting the mDNS callback to async
- `frozenset({126, 130})` constant `_MULTI_CHANNEL_UIIDS` defined at module level — cleaner than inline set literal and O(1) lookup
- `writer.write()` never raises (guaranteed by Phase 3 design) so success log line is placed unconditionally after the await — no try/except needed in `_write_reading()`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

The plan's verification command (`python -c "... import __main__"`) imports the running interpreter's `__main__` rather than `src/__main__.py` when run as a subprocess. Verified structure using `importlib.util.spec_from_file_location()` instead — all attributes confirmed present. This is a test-harness limitation, not a code issue.

## Next Phase Readiness

- All components wired; daemon will write real energy data to InfluxDB when started against live devices
- Phase 4 Plan 02 (Docker packaging) can proceed — `Dockerfile`, `docker-compose.yml`, and operational documentation remain
- Watch: `docker stop` must deliver SIGTERM to PID 1 — verify `CMD ["python", "-m", "sonoff_daemon"]` with `exec` form in Dockerfile

---
*Phase: 04-integration-docker*
*Completed: 2026-04-03*

## Self-Check: PASSED

- ✅ `src/config.py` — exists, exports `parse_influx_config()`
- ✅ `src/__main__.py` — exists, contains `SonoffDaemon` class with all 4 methods
- ✅ `requirements.txt` — exists, 4 pinned dependencies
- ✅ `04-01-SUMMARY.md` — this file
- ✅ Commit `81178e9` — feat: parse_influx_config()
- ✅ Commit `47e095f` — feat: SonoffDaemon rewrite
- ✅ Commit `259a3ec` — chore: pin requirements.txt
- ✅ 46 unit tests pass
