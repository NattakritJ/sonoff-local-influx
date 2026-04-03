# Phase 3: InfluxDB Writer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 03-influxdb-writer
**Areas discussed:** InfluxDB point schema, Writer interface design, Connectivity check, Testing strategy

---

## InfluxDB Point Schema

### Tags

| Option | Description | Selected |
|--------|-------------|----------|
| device_id + device_name only | Minimal tags — aligns exactly with INF-02/INF-03; uiid/channel are dimensional data, not query dimensions | ✓ |
| Add channel as tag too | Enables per-channel filtering in queries | |
| All four as tags | device_id, device_name, uiid, channel — maximum queryability | |

**User's choice:** `device_id` and `device_name` only

### Fields

| Option | Description | Selected |
|--------|-------------|----------|
| Float metrics only | power, voltage, current, energy_today; None values omitted from write | ✓ |
| Include uiid + channel as fields | power/voltage/current/energy_today + uiid and channel as integer fields | |
| Include channel as field | power/voltage/current/energy_today + channel as integer field | |

**User's choice:** Float metrics only (power, voltage, current, energy_today); None values omitted

### Input Type Defensiveness

| Option | Description | Selected |
|--------|-------------|----------|
| Trust EnergyReading types | Phase 2 extractor guarantees float \| None; writer just skips None | ✓ |
| Re-cast floats in writer | Explicitly cast each field to float even though extractor already did it | |
| Strict validation + raise | Raise ValueError if any field that should be float is not | |

**User's choice:** Trust EnergyReading types

**Notes:** User said "ensure parsing no problem" — confirmed that Phase 2 extractor already handles all type coercion; writer should trust the contract.

---

## Writer Interface Design

### Method Signature

| Option | Description | Selected |
|--------|-------------|----------|
| write(reading) — single reading | One reading at a time; caller loops for multi-channel | ✓ |
| write(readings) — list always | Takes a list; handles both single (list of 1) and multi (list of N) uniformly | |
| Two separate methods | write_one() for single-channel + write_multi() for multi-channel | |

**User's choice:** `write(reading: EnergyReading)` — single reading per call

### Constructor

| Option | Description | Selected |
|--------|-------------|----------|
| Init with host/token/database | InfluxWriter(host, token, database) — creates client internally | ✓ |
| Init with pre-built client | Accepts a pre-built InfluxDB3Client (more testable via injection) | |
| from_env() classmethod | Reads env vars directly inside the class | |

**User's choice:** `InfluxWriter(host: str, token: str, database: str)` — direct config values

**Notes:** Maps cleanly to CFG-02 env vars (INFLUX_HOST, INFLUX_TOKEN, INFLUX_DATABASE).

---

## Connectivity Check

### Check Method

| Option | Description | Selected |
|--------|-------------|----------|
| Query-only check (no write) | Ping/query InfluxDB (e.g. list databases); no write; fail fast if unreachable | ✓ |
| Write a test point on startup | Proves full write path works; if fails, sys.exit(1) | |
| HTTP reachability only | Just check URL is reachable via HTTP GET | |

**User's choice:** Query-only check — no test point written to InfluxDB at startup

### Failure Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| sys.exit(1) — hard fail | Daemon refuses to start if InfluxDB unreachable | ✓ |
| Log and continue | Same log-and-continue as write failures | |

**User's choice:** `sys.exit(1)` with clear error message

---

## Testing Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Mocks + optional live integration test | Unit tests with mocks + @pytest.mark.integration test skipped unless INFLUX_HOST set | ✓ |
| Live instance only | All tests require real InfluxDB instance | |
| Mocks only | Mock influxdb3-python entirely; no live instance | |

**User's choice:** Mocks for unit tests + one `@pytest.mark.integration` test that hits a real InfluxDB 3 Core instance (skipped automatically unless `INFLUX_HOST` env var is set)

---

## Agent's Discretion

- Module filename within `src/` (e.g., `writer.py` vs `influx_writer.py`)
- Specific InfluxDB API call for connectivity check (researcher to verify)
- Whether `InfluxWriter` needs explicit `close()` or async context manager

## Deferred Ideas

None
