---
phase: 03-influxdb-writer
plan: "02"
subsystem: testing
tags: [influxdb3-python, pytest, integration-testing, pyarrow]

# Dependency graph
requires:
  - phase: 03-01
    provides: InfluxWriter class with async write() and check_connectivity() under src/writer.py
provides:
  - Integration test suite (4 tests) against live InfluxDB 3 Core, auto-skip without INFLUX_HOST
  - Pinned influxdb3-python==0.18.0 in requirements.txt
  - Registered 'integration' pytest marker in tests/pytest.ini
affects:
  - 04-integration-docker

# Tech tracking
tech-stack:
  added: [influxdb3-python==0.18.0, pyarrow (transitive, used via column() API)]
  patterns:
    - Integration tests use pytestmark + skipif on env var — zero friction in CI
    - PyArrow Table accessed via column() not to_pydict() to avoid nanosecond timestamp serialisation error

key-files:
  created:
    - tests/test_writer_integration.py
  modified:
    - requirements.txt
    - tests/pytest.ini

key-decisions:
  - "column() used instead of to_pydict() on PyArrow results — to_pydict() crashes with nanosecond timestamp columns in pyarrow ≥14"
  - "Integration tests auto-skip when INFLUX_HOST unset — no CI config changes needed"
  - "influxdb3-python==0.18.0 pinned explicitly to match writer.py import of InfluxDBClient3 class name"

patterns-established:
  - "Integration test pattern: pytestmark = pytest.mark.skipif(not os.environ.get('KEY'), reason='...')"
  - "PyArrow query result traversal: use result.column('field_name').to_pylist() not result.to_pydict()"

requirements-completed: [INF-01, INF-02, INF-03, INF-04, INF-05, INF-06, CFG-04]

# Metrics
duration: 15min
completed: 2026-04-03
---

# Phase 3 Plan 02: InfluxDB Writer Integration Test Summary

**4-test integration suite against live InfluxDB 3 Core that auto-skips in CI, with PyArrow column() fix for nanosecond timestamp compatibility**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-03T11:10:00Z
- **Completed:** 2026-04-03T11:25:00Z
- **Tasks:** 1 auto + 1 human-verify checkpoint (approved)
- **Files modified:** 3

## Accomplishments
- 4 integration tests written covering: connectivity-live, connectivity-bad-host, write+query single reading, write with None fields omitted
- Integration tests skip automatically when `INFLUX_HOST` env var is unset — 46 unit tests pass, 4 skipped (no live server)
- `requirements.txt` updated with `influxdb3-python==0.18.0` pinned alongside existing aiohttp/cryptography/zeroconf
- `tests/pytest.ini` registers the `integration` marker — no `PytestUnknownMarkWarning` in CI output
- Human checkpoint approved: integration tests confirmed passing against a live InfluxDB 3 Core instance

## Task Commits

Each task was committed atomically:

1. **Task 1: Add integration test + update requirements.txt + pytest.ini** - `ba6fc2a` (feat)
2. **Fix: PyArrow nanosecond timestamp bug** - `4f8f32b` (fix — auto-fix Rule 1)

**Task 2 (human-verify checkpoint):** Approved by user — no additional commit.

## Files Created/Modified
- `tests/test_writer_integration.py` — 4 integration tests against live InfluxDB 3 Core; auto-skip without `INFLUX_HOST`
- `requirements.txt` — Added `influxdb3-python==0.18.0`; all 4 deps now pinned
- `tests/pytest.ini` — Registered `integration` marker to suppress `PytestUnknownMarkWarning`

## Decisions Made
- Used `result.column('field_name').to_pylist()` instead of `result.to_pydict()` — PyArrow `to_pydict()` raises `ArrowInvalid` on nanosecond timestamp columns in pyarrow ≥14; `column()` avoids the serialisation path entirely
- Used `pytestmark = pytest.mark.skipif(not os.environ.get('INFLUX_HOST'), ...)` at module level — all 4 tests in the file skip as one unit, no per-test decoration needed
- Kept `influxdb3-python==0.18.0` pinned (not `>=`) to lock the `InfluxDBClient3` class name which changed in other versions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PyArrow nanosecond timestamp crash in integration test query verification**
- **Found during:** Task 1 (test_write_and_query_single_reading execution against live server)
- **Issue:** `result.to_pydict()` in influxdb3-python 0.18.0 raises `pyarrow.lib.ArrowInvalid: Casting from timestamp[ns] to timestamp[us, tz=UTC] would lose data` on InfluxDB 3 Core results because timestamps are nanosecond precision
- **Fix:** Replaced all `result.to_pydict()` calls with `result.column('col').to_pylist()` which accesses columns directly without going through the timestamp cast path
- **Files modified:** `tests/test_writer_integration.py`
- **Verification:** Integration tests passed against live InfluxDB 3 Core after fix; unit test count unchanged (46 pass, 4 skip)
- **Committed in:** `4f8f32b`

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Necessary fix for PyArrow version compatibility. No scope creep — test logic unchanged, only result access pattern corrected.

## Issues Encountered
- PyArrow nanosecond timestamp incompatibility between `to_pydict()` and InfluxDB 3 Core query results — resolved via `column()` API (see Deviations above)

## User Setup Required
None - no external service configuration required for unit/CI runs. Integration tests require:
- `INFLUX_HOST` — live InfluxDB 3 Core URL (e.g., `http://localhost:8086`)
- `INFLUX_TOKEN` — auth token
- `INFLUX_DATABASE` — test database name (e.g., `sonoff_test`)

## Next Phase Readiness
- Phase 3 complete: `InfluxWriter` fully implemented (17 unit tests) and validated end-to-end (4 integration tests pass against live InfluxDB 3 Core)
- All Phase 3 requirements satisfied: INF-01 through INF-06, CFG-04
- Phase 4 (Integration + Docker) can proceed: `src/writer.py`, `src/extractor.py`, `src/ewelink/` are all production-ready
- No blockers

---
*Phase: 03-influxdb-writer*
*Completed: 2026-04-03*
