# STATE — SonoffLAN-InfluxDB

**Project:** SonoffLAN-InfluxDB standalone daemon
**Status:** Planning complete — ready to execute
**Last updated:** 2026-04-03

---

## Project Reference

**Core value:** Reliable, low-latency energy data from Sonoff LAN devices flowing into InfluxDB 3 — every event written immediately, no HA dependency.

**Reference:** `.planning/PROJECT.md`

---

## Current Position

**Current phase:** Phase 1 — LAN Transport Foundation
**Current plan:** None (not started)
**Phase status:** Not started

```
Progress: [ Phase 1 ] → [ Phase 2 ] → [ Phase 3 ] → [ Phase 4 ]
              ▲
           CURRENT
```

---

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | LAN Transport Foundation | Not started |
| 2 | Energy Extraction | Pending |
| 3 | InfluxDB Writer | Pending |
| 4 | Integration + Docker | Pending |

---

## Performance Metrics

- Plans completed: 0
- Phases completed: 0
- Requirements satisfied: 0 / 33

---

## Accumulated Context

### Key Decisions Logged
- Reuse `ewelink/base.py` and `ewelink/local.py` only — all other HA files removed
- `influxdb3-python==0.18.0` is the only correct client for InfluxDB 3 Core (not `influxdb-client`)
- `asyncio.to_thread()` required for every InfluxDB write to avoid blocking the event loop
- `network_mode: host` required in docker-compose for mDNS multicast (Linux only)
- `python:3.12-slim-bookworm` base image (not Alpine — `cryptography` + `pyarrow` need pre-built wheels)

### Critical Pitfalls to Watch
1. **Phase 1:** Verify no residual `homeassistant` imports survive in `base.py`/`local.py` — run `python -c "import ewelink.local"` in a clean venv immediately
2. **Phase 1:** `zeroconf.async_get_instance(hass)` call in `local.py` — must be replaced with a directly-owned `Zeroconf()` instance if present
3. **Phase 3:** Confirm exact importable exception class from `influxdb_client_3` for the `try/except` in writer
4. **Phase 4:** Confirm `docker stop` triggers SIGTERM to PID 1 correctly — verify <10s exit

### Todos
- None yet

### Blockers
- None

---

## Session Continuity

**To resume:** Read `.planning/ROADMAP.md` for phase goals and success criteria. Current phase is Phase 1. Run `/gsd-plan-phase 1` to begin.
