# Phase 3: InfluxDB Writer - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver an isolated `InfluxWriter` class that receives `EnergyReading` objects (from Phase 2's extractor) and writes them to InfluxDB 3 Core — asynchronously, without blocking the event loop, with log-and-continue error handling on write failure and a startup connectivity check. No LAN transport wired yet, no daemon integration yet — the write layer only.

</domain>

<decisions>
## Implementation Decisions

### InfluxDB Point Schema

- **D-01:** Measurement name = `device_id` (one measurement per device, as specified in INF-02)
- **D-02:** Tags = `device_id` and `device_name` only (INF-03) — `uiid` and `channel` are NOT tags
- **D-03:** Fields = `power`, `voltage`, `current`, `energy_today` — float values only; `None` values are omitted from the write entirely (not written as null)
- **D-04:** No additional fields — uiid and channel are not written to InfluxDB at all

### Writer Interface

- **D-05:** Class name: `InfluxWriter`
- **D-06:** Constructor: `InfluxWriter(host: str, token: str, database: str)` — takes the three config values directly and creates the `InfluxDB3Client` internally (maps directly to CFG-02 env vars)
- **D-07:** Write method: `write(reading: EnergyReading) -> None` — single reading per call; callers loop over multi-channel lists from `extract_energy_multi()`
- **D-08:** Each `write()` call wraps the synchronous InfluxDB client call in `asyncio.to_thread()` — the event loop is never blocked
- **D-09:** Type trust: writer trusts that `EnergyReading` fields are already `float | None` (Phase 2 extractor guarantees this); no re-casting in writer

### Error Handling

- **D-10:** On any write failure (exception from influxdb3-python): log at ERROR level and return — do not raise, do not crash the daemon (INF-06, PROJECT.md constraint)
- **D-11:** Known pitfall from STATE.md: confirm exact importable exception class from `influxdb_client_3` for the `try/except` — researcher must verify this

### Connectivity Check (CFG-04)

- **D-12:** At daemon startup, perform a query-only check against InfluxDB (e.g., list databases or run a trivial query) — no test point written
- **D-13:** If connectivity check fails: `sys.exit(1)` with a clear error message — daemon refuses to start if InfluxDB is unreachable
- **D-14:** Check runs before the mDNS browser starts — no events accepted until InfluxDB is confirmed reachable

### Testing

- **D-15:** Unit tests with `unittest.mock` (or `pytest-mock`) to mock `InfluxDB3Client` — test write logic, error handling, and None-omission without a live instance
- **D-16:** One integration test marked `@pytest.mark.integration` that hits a real InfluxDB 3 Core instance — skipped automatically unless `INFLUX_HOST` env var is set
- **D-17:** Integration test verifies end-to-end: construct `EnergyReading` → `InfluxWriter.write()` → query InfluxDB → confirm measurement, tags, and field values appear correctly

### Agent's Discretion

- Where exactly to place the `InfluxWriter` module in `src/` (e.g., `src/writer.py` vs `src/influx_writer.py`) — follow the existing flat `src/` module naming pattern (`config.py`, `extractor.py`)
- Which specific InfluxDB API to call for the connectivity check (query endpoint, health endpoint, etc.) — researcher should verify the correct `influxdb3-python` API for a non-write check
- Whether `InfluxWriter` needs a `close()` / `__aenter__`/`__aexit__` for client cleanup, or if `InfluxDB3Client` is stateless enough to not require it

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements (this phase)
- `.planning/REQUIREMENTS.md` §InfluxDB Writer — INF-01 through INF-06 (write behavior, schema, async, error handling)
- `.planning/REQUIREMENTS.md` §Configuration — CFG-04 (startup connectivity check)

### Project Constraints
- `.planning/PROJECT.md` §Constraints — LAN-only, energy-only, immediate write, log-and-continue
- `.planning/PROJECT.md` §Key Decisions — `influxdb3-python==0.18.0` confirmed client; `asyncio.to_thread()` required

### Existing Source (integration points)
- `src/extractor.py` — `EnergyReading` dataclass (the input to `InfluxWriter.write()`); field names and types are the contract
- `src/config.py` — `DeviceConfig` TypedDict with `device_id`, `devicekey`, `device_name`; writer uses `device_id` and `device_name`
- `src/__main__.py` — current daemon entrypoint; shows existing logging format and signal handling pattern

### State / Known Pitfalls
- `.planning/STATE.md` §Accumulated Context — "Confirm exact importable exception class from `influxdb_client_3` for the try/except in writer" (Critical Pitfall #3)

No external API specs referenced during discussion — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/extractor.py:32` — `EnergyReading` dataclass: `device_id: str`, `uiid: int`, `power: float | None`, `voltage: float | None`, `current: float | None`, `energy_today: float | None`, `channel: int | None`
- `src/config.py:10` — `DeviceConfig` TypedDict: `device_id`, `devicekey`, `device_name` — writer receives these to populate `device_name` tag
- `src/__main__.py:14-18` — Logging setup: `basicConfig` with ISO timestamp format; `_LOGGER = logging.getLogger("sonoff_daemon")` pattern

### Established Patterns
- Error handling: `try/except Exception as e: _LOGGER.warning(...)` or `_LOGGER.error(...)` — never bare `except:`, always log and continue
- Logger naming: `_LOGGER = logging.getLogger(__name__)` per module
- Type annotations: Python 3.10+ union syntax (`float | None`, not `Optional[float]`)
- Module layout: flat under `src/` — `config.py`, `extractor.py`; new module should follow: `src/writer.py`
- Testing: `sys.path.insert(0, ...)` in test files to add `src/` to path; `pytest` with no special runner config needed

### Integration Points
- `src/__main__.py:43-74` — `on_update()` callback is where `InfluxWriter.write()` will be called (Phase 4); for Phase 3, writer is tested in isolation
- `influxdb3-python` (pinned `==0.18.0` in STATE.md): `InfluxDB3Client` from `influxdb_client_3` — researcher must confirm exact import path and exception class name

</code_context>

<specifics>
## Specific Ideas

- The user confirmed: trust `EnergyReading` types — extractor guarantees float | None, writer doesn't re-cast
- The user confirmed: `write(reading: EnergyReading)` single-reading interface — caller loops for multi-channel, not the writer
- The user confirmed: query-only startup check (not a write probe) — prefer non-destructive verification
- The user confirmed: `sys.exit(1)` hard fail if InfluxDB unreachable at startup — data loss prevention

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-influxdb-writer*
*Context gathered: 2026-04-03*
