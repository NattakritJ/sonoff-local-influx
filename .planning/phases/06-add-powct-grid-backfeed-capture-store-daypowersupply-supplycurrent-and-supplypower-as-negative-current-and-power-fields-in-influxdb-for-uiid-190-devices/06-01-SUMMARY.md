---
phase: 06
plan: 01
subsystem: extractor+writer
tags: [tdd, uiid-190, backfeed, sign-encoding, energy, influxdb]
dependency_graph:
  requires: []
  provides: [energy_backfeed_today field, UIID 190 backfeed extraction, writer backfeed write]
  affects: [src/extractor.py, src/writer.py, tests/test_extractor.py]
tech_stack:
  added: []
  patterns: [sign-encoding power/current for grid export, three-way power-flow logic]
key_files:
  created: []
  modified:
    - src/extractor.py
    - src/writer.py
    - tests/test_extractor.py
decisions:
  - "D-04/D-05 upheld: negative sign in existing power/current fields — no new supply_power field"
  - "D-06 upheld: logic inline in extract_energy() — no new helper function"
  - "D-09 upheld: both power+supplyPower non-zero uses consumption values silently"
  - "D-10 upheld: field named energy_backfeed_today (not energy_supply_today)"
  - "D-13 upheld: both-zero case returns EnergyReading with 0.0 explicitly, never None"
  - "UIID 190 dayKwh handled inline in new branch — independent of _HAS_DAY_KWH general path"
metrics:
  duration: 5 min
  completed: "2026-04-04"
  tasks: 2
  files_modified: 3
requirements: [EXT-06]
---

# Phase 6 Plan 01: UIID 190 Backfeed Extraction + Writer Extension Summary

**One-liner:** Sign-encoded grid backfeed (supplyPower/supplyCurrent → negative power/current) with energy_backfeed_today field for UIID 190 devices, written to InfluxDB via extended writer.

## What Was Built

Extended the UIID 190 (SONOFF POWCT) energy extraction pipeline to capture grid export (backfeed) metrics alongside existing grid consumption data:

1. **`EnergyReading` dataclass** — added `energy_backfeed_today: float | None = None` field (default None ensures backward compatibility with all other UIIDs)

2. **`extract_energy()` UIID 190 branch** — three-way power-flow logic:
   - **Grid export** (`supplyPower > 0, power == 0`): power and current set to negative values (sign-encoded); e.g. `supplyPower=5000` → `power=-50.0`
   - **Consumption** (`power > 0, supplyPower == 0`): unchanged positive values
   - **Both-zero** (idle): `power=0.0, current=0.0` returned explicitly — never None (D-13)
   - **Both non-zero** (defensive): uses consumption values silently (D-09)
   - `dayPowerSupply` → `energy_backfeed_today = round(val * 0.01, 4)` when present

3. **`writer.write()`** — extended to include `energy_backfeed_today` in InfluxDB point fields when non-None

## Tasks Completed

| Task | Type | Commit | Description |
|------|------|--------|-------------|
| 1 RED | TDD | c7ad2a2 | 8 failing backfeed tests in test_extractor.py |
| 1 GREEN | TDD | 53f389a | EnergyReading + extract_energy() UIID 190 backfeed branch |
| 2 | auto | 206a70c | writer.write() energy_backfeed_today field |

## Test Results

```
39 passed in tests/test_extractor.py (31 pre-existing + 8 new backfeed tests)
18 passed in tests/test_writer.py (all unit tests — no regression)
85 total — 5 pre-existing integration test failures unrelated to this plan
```

## Deviations from Plan

None — plan executed exactly as written. The UIID 190 branch was implemented inline in `extract_energy()` as specified (D-06). All 8 specified test cases written and passing.

## Known Stubs

None — all fields are fully wired. `energy_backfeed_today` is populated from real device params (`dayPowerSupply`) and written to InfluxDB when non-None.

## Self-Check

- [x] `src/extractor.py` contains `energy_backfeed_today` field in dataclass
- [x] `src/writer.py` contains `energy_backfeed_today` in fields dict
- [x] `tests/test_extractor.py` contains `test_uiid_190_backfeed` tests (8 total)
- [x] All commits exist in git log
- [x] `pytest tests/test_extractor.py` passes with 39 tests

## Self-Check: PASSED
