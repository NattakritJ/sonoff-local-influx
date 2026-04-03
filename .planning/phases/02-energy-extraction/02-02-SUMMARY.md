---
phase: 02-energy-extraction
plan: 02
subsystem: extractor
tags: [tdd, multi-channel, energy-extraction, DualR3, SPM-4Relay]
dependency_graph:
  requires: [02-01]
  provides: [extract_energy_multi, EXT-05]
  affects: [src/extractor.py, tests/test_extractor.py]
tech_stack:
  added: []
  patterns: [TDD red-green, pure-function extension]
key_files:
  created: []
  modified:
    - src/extractor.py
    - tests/test_extractor.py
decisions:
  - "extract_energy_multi() skips absent channels (all three params None) rather than returning EnergyReading with all-None fields — cleaner InfluxDB writes"
  - "energy_today is always None for DualR3/SPM-4Relay (cloud-only energy history for these UIIDs via LAN)"
  - "channel field uses 1-based integers matching Sonoff device labelling convention"
metrics:
  duration: 4 min
  completed: "2026-04-03"
  tasks: 2
  files_modified: 2
---

# Phase 02 Plan 02: extract_energy_multi DualR3/SPM-4Relay Summary

**One-liner:** `extract_energy_multi()` for UIID 126 (DualR3) and 130 (SPM-4Relay) — per-channel EnergyReading list with actPow_0N/current_0N/voltage_0N ×0.01 scaling and 1-based channel tags.

## What Was Built

Extended `src/extractor.py` with `extract_energy_multi()` — a pure function that reads multi-channel energy params from DualR3 and SPM-4Relay devices and returns a `list[EnergyReading]`, one per channel where any param is present.

Key additions:
- `_MULTI_CHANNEL_UIIDS = {126: 2, 130: 4}` — channel count lookup
- `_MULTI_PARAM_SUFFIXES = ["_00", "_01", "_02", "_03"]` — positional param suffixes
- `extract_energy_multi(device_id, uiid, params) -> list[EnergyReading]` — exported function

## TDD Execution

**RED:** Added Tests 14–23 covering both UIIDs, all edge cases (partial channels, no params, string coercion, unsupported UIID, regression). Committed at `92be8d6`.

**GREEN:** Implemented `extract_energy_multi()` in `src/extractor.py`. All 28 tests pass (18 Plan 01 + 10 Plan 02). Committed at `cc39c47`.

**REFACTOR:** No refactoring needed — implementation was clean in one pass.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `92be8d6` | test | Add failing tests for extract_energy_multi DualR3/SPM-4Relay (Tests 14-23) |
| `cc39c47` | feat | Implement extract_energy_multi — all 28 tests pass |

## Decisions Made

1. **Absent channels skipped (not returned with None fields)** — A channel is only included if at least one of actPow, current, or voltage is present. This avoids writing noise points to InfluxDB.

2. **energy_today always None for multi-channel UIIDs** — DualR3 and SPM-4Relay do not expose dayKwh via LAN (it's cloud-only). Documented in function docstring.

3. **1-based channel integer** — `channel = ch_idx + 1` aligns with how Sonoff labels outlets in their UI (1, 2, 3, 4 not 0-indexed).

## Test Coverage

| Test | Description | Result |
|------|-------------|--------|
| 14 | DualR3 both channels → 2 EnergyReadings, channel=1,2 | ✅ |
| 15 | DualR3 ch1: actPow_00=2300 → power=23.0, correct scaling | ✅ |
| 16 | DualR3 ch2: actPow_01=1150 → power=11.5, correct scaling | ✅ |
| 17 | DualR3 only ch1 params → list of 1 | ✅ |
| 18 | DualR3 no params → empty list | ✅ |
| 19 | SPM-4Relay all 4 channels → list of 4, channels 1-4 | ✅ |
| 20 | SPM-4Relay channels 1+3 only → 2 EnergyReadings | ✅ |
| 21 | String raw values coerced to float | ✅ |
| 22 | Unsupported UIID → empty list (no error) | ✅ |
| 23 | Plan 01 regression check — all exports still available | ✅ |

Total: 28/28 tests pass.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `extract_energy_multi()` is fully implemented with no placeholder values.

## Self-Check: PASSED

- `src/extractor.py` — FOUND
- `tests/test_extractor.py` — FOUND (402 lines, 28 tests)
- Commit `92be8d6` — FOUND (test RED commit)
- Commit `cc39c47` — FOUND (feat GREEN commit)
- All 28 tests pass: `PYTHONPATH=src python3 -m pytest tests/test_extractor.py -v` → 28 passed
- Export check: `from extractor import EnergyReading, extract_energy, extract_energy_multi; print('OK')` → OK
