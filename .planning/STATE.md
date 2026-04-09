---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 07
current_plan: 1
status: verifying
stopped_at: Completed 07-02-PLAN.md — Phase 7 complete, all 11 plans done, project milestone v1.0 achieved
last_updated: "2026-04-09T04:37:33.670Z"
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 11
  completed_plans: 11
  percent: 100
---

# STATE — SonoffLAN-InfluxDB

**Project:** SonoffLAN-InfluxDB standalone daemon
**Status:** Phase complete — ready for verification
**Last updated:** 2026-04-03 - Added Phase 5: Static IP + Polling Mode

---

## Project Reference

**Core value:** Reliable, low-latency energy data from Sonoff LAN devices flowing into InfluxDB 3 — every event written immediately, no HA dependency.

**Reference:** `.planning/PROJECT.md`

---

## Current Position

Phase: 07 (direct-connection-without-mdns-if-already-knowing-device-s-ip) — COMPLETE
Plan: 2 of 2 — ALL PLANS DONE
**Current phase:** 07
**Current plan:** 2
**Phase status:** Complete — milestone v1.0 achieved

```
Progress: [██████████] 100%
                     ▲
               ALL 7 PHASES COMPLETE — PROJECT MILESTONE v1.0
```

---

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | LAN Transport Foundation | ✅ Complete |
| 2 | Energy Extraction | ✅ Complete (2/2 plans done) |
| 3 | InfluxDB Writer | ✅ Complete (2/2 plans done) |
| 4 | Integration + Docker | ✅ Complete (2/2 plans done) |
| 5 | Static IP + Polling Mode | ✅ Complete (superseded by Phase 7) |
| 6 | POWCT Grid Backfeed Capture | ✅ Complete (1/1 plans done) |
| 7 | Direct Connection without mDNS | ✅ Complete (2/2 plans done) |

---

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files | Completed |
|-------|------|----------|-------|-------|-----------|
| 01 | 01 | 8 min | 2 | 4 | 2026-04-03 |
| 01 | 02 | 5 min | 2 | 2 | 2026-04-03 |
| 02 | 01 | 5 min | 1 | 6 | 2026-04-03 |
| 02 | 02 | 4 min | 2 | 2 | 2026-04-03 |
| 03 | 01 | 2 min | 2 | 3 | 2026-04-03 |
| 03 | 02 | 15 min | 2 | 3 | 2026-04-03 |
| 04 | 01 | 2 min | 3 | 3 | 2026-04-03 |
| 04 | 02 | 5 min | 3 | 3 | 2026-04-03 |

- Plans completed: 11
- Phases completed: 7
- Requirements satisfied: 35 / 35 (MIG-01, MIG-02, MIG-03, LAN-01, LAN-02, LAN-03, LAN-04, LAN-05, LAN-06, CFG-01, CFG-02, CFG-03, CFG-04, OPS-01, OPS-02, OPS-03, OPS-04, EXT-01, EXT-02, EXT-03, EXT-04, EXT-05, EXT-06, INF-01, INF-02, INF-03, INF-04, INF-05, INF-06, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, LAN-07, LAN-09)

---
| Phase 04 P02 | 5min | 3 tasks | 3 files |
| Phase 06 P01 | 5min | 2 tasks | 3 files |
| Phase 07 P01 | 8min | 1 tasks | 2 files |
| Phase 07 P02 | 30min | 3 tasks | 3 files |

## Accumulated Context

### Key Decisions Logged

- Reuse `ewelink/base.py` and `ewelink/local.py` only — all other HA files removed
- `influxdb3-python==0.18.0` is the only correct client for InfluxDB 3 Core (not `influxdb-client`)
- `asyncio.to_thread()` required for every InfluxDB write to avoid blocking the event loop
- `network_mode: host` required in docker-compose for mDNS multicast (Linux only)
- `python:3.12-slim-bookworm` base image (not Alpine — `cryptography` + `pyarrow` need pre-built wheels)
- **[Phase 1]** base.py and local.py copied verbatim — both confirmed already free of HA imports
- **[Phase 1]** AsyncZeroconf owns zeroconf instance — no HA hass reference required in standalone daemon
- **[Phase 2 P01]** EnergyReading is @dataclass; extract_energy() pure function with per-UIID scale factors (×1 or ×0.01); returns None on unrecognised UIIDs or empty params
- **[Phase 2 P01]** tests/__init__.py wrapped with try/except — HA integration tests coexist with daemon tests without requiring homeassistant installed
- **[Phase 2 P02]** extract_energy_multi() skips absent channels — avoids noise in InfluxDB writes
- **[Phase 2 P02]** energy_today always None for DualR3/SPM-4Relay (UIID 126/130) via LAN — cloud-only energy history
- **[Phase 2 P02]** Multi-channel EnergyReading.channel uses 1-based integers matching Sonoff device outlet labelling
- **[Phase 3 P01]** InfluxDBClient3 is the correct class name in influxdb3-python 0.18.0 (plan had typo InfluxDB3Client)
- **[Phase 3 P01]** asyncio.to_thread() wraps all synchronous InfluxDB3 client calls (write + get_server_version)
- **[Phase 3 P01]** Empty points (all fields None) skip client.write() entirely — no partial writes to InfluxDB
- **[Phase 3 P02]** column() used instead of to_pydict() on PyArrow query results — to_pydict() crashes with nanosecond timestamp columns in pyarrow ≥14
- **[Phase 3 P02]** Integration tests auto-skip when INFLUX_HOST unset via pytestmark skipif — no CI config changes needed
- **[Phase 4 P01]** asyncio.ensure_future() used in sync _on_update() to schedule async _write_reading() without blocking mDNS callback
- **[Phase 4 P01]** frozenset({126, 130}) as _MULTI_CHANNEL_UIIDS constant for O(1) UIID routing in _on_update()
- **[Phase 4 P01]** writer.write() never raises — success log placed unconditionally after await in _write_reading()
- **[Phase 4 P02]** python:3.12-slim-bookworm (not Alpine) — cryptography and pyarrow require pre-built wheels unavailable on Alpine musl libc
- **[Phase 4 P02]** python -u (unbuffered) in Dockerfile CMD ensures immediate log output in docker logs without buffering delay
- **[Phase 4 P02]** env_file: .env in docker-compose — secrets stay outside the image; user copies .env.example to .env
- **[Phase 4 P02]** Log rotation (10m/3 files) in docker-compose — prevents disk fill on long-running daemon
- **[Phase 6 P01]** D-04/D-05: sign-encoding backfeed in existing power/current fields — no new supply_power field; supplyPower=5000 → power=-50.0
- **[Phase 6 P01]** D-13: both-zero case for UIID 190 returns EnergyReading(power=0.0, current=0.0) explicitly — never None (only exception to "return None if no energy" rule)
- **[Phase 6 P01]** UIID 190 dayKwh handled inline in new backfeed branch — independent of _HAS_DAY_KWH general path (190 removed from that path effectively)
- **[Phase 7 P01]** ip field stored via post-append mutation (`validated[-1]["ip"] = dev["ip"]`) — avoids ip=None in DeviceConfig when absent; preserves total=False semantics
- **[Phase 7 P01]** No IP format validation at parse time — invalid IPs cause connection failure at runtime (per D-02 spec)
- **[Phase 7 P01]** parse_poll_interval() default 10s; int(raw) coercion means "10.5" fails via ValueError → sys.exit(1)
- **[Phase 7 P02]** Empty devicekey omitted from XDevice in _poll_device() — empty string triggered AES encryption in XRegistryLocal.send(), causing HTTP 400 from device; fix: conditionally include devicekey only when non-empty (commit 0be4211)
- **[Phase 7 P02]** Polling task lifecycle mirrors heartbeat: create_task → store in list → cancel all on shutdown → await with CancelledError suppressed
- **[Phase 7 P02]** AsyncZeroconf never instantiated when all devices have static IPs — guard `if mdns_devices:` prevents unnecessary mDNS startup

### Critical Pitfalls to Watch

1. ~~**Phase 1:** Verify no residual `homeassistant` imports survive in `base.py`/`local.py`~~ ✅ RESOLVED — zero HA imports confirmed
2. ~~**Phase 1:** `zeroconf.async_get_instance(hass)` call in `local.py`~~ ✅ RESOLVED — AsyncZeroconf used directly
3. ~~**Phase 3:** Confirm exact importable exception class from `influxdb_client_3` for the `try/except` in writer~~ ✅ RESOLVED — `InfluxDBError` importable from `influxdb_client_3` top-level; class name is `InfluxDBClient3` not `InfluxDB3Client`
4. ~~**Phase 4:** Confirm `docker stop` triggers SIGTERM to PID 1 correctly — verify <10s exit~~ ✅ RESOLVED — exec-form CMD confirmed; container exits cleanly on docker stop

### Roadmap Evolution

- Phase 6 added: Add POWCT grid backfeed capture: store dayPowerSupply, supplyCurrent and supplyPower as negative current and power fields in InfluxDB for uiid 190 devices
- Phase 7 added: Direct connection without mDNS if already knowing device's IP

### Todos

- None yet

### Blockers

- None

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260403-r2z | commit | 2026-04-03 | 6c172df | [260403-r2z-commit](./quick/260403-r2z-commit/) |
| 260403-s3b | fix InfluxDB table name — use device_name | 2026-04-03 | 5ef9eaa | [260403-s3b](./quick/260403-s3b-fix-influxdb-table-name-use-device-name-/) |
| 260403-s9b | trim numeric data to two decimal places | 2026-04-03 | 1ab8025 | [260403-s9b-trim-numeric-data-to-two-decimal-places](./quick/260403-s9b-trim-numeric-data-to-two-decimal-places/) |
| 260403-u5d | add LOG_LEVEL env var support | 2026-04-03 | 7f4d959 | [260403-u5d-add-loglevel-into-config](./quick/260403-u5d-add-loglevel-into-config/) |

---

## Session Continuity

**Stopped at:** Completed 07-02-PLAN.md — Phase 7 complete, all 11 plans done, project milestone v1.0 achieved
**To resume:** Project complete. All 7 phases, 11 plans done. Static-IP polling mode live-tested and working. Daemon ready for production deployment.
