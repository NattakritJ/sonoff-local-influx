---
phase: 02-energy-extraction
plan: 01
subsystem: energy-extractor
tags: [tdd, energy, extractor, pure-function, dataclass]
dependency_graph:
  requires: [src/ewelink package (Phase 1)]
  provides: [src/extractor.py, EnergyReading, extract_energy]
  affects: [02-02, Phase 3 InfluxDB writer]
tech_stack:
  added: [dataclasses (stdlib), pytest 9.0.2]
  patterns: [pure-function, dataclass, per-uiid-scaling, tdd-red-green]
key_files:
  created:
    - src/extractor.py
    - tests/test_extractor.py
    - tests/conftest.py
    - conftest.py
    - pytest.ini
  modified:
    - tests/__init__.py
decisions:
  - "EnergyReading is a @dataclass (not NamedTuple) for mutability in Phase 3 writer"
  - "scale factor applied inline in extract_energy() — no intermediate dict lookup"
  - "Returns None (not raises) on missing fields — caller decides how to handle"
  - "Fixed tests/__init__.py with try/except around HA imports (Rule 3 auto-fix)"
  - "Root pytest.ini + tests/conftest.py added to enable daemon tests without HA installed"
metrics:
  duration: "5 minutes"
  completed: "2026-04-03"
  tasks_completed: 1
  files_created: 5
  files_modified: 1
---

# Phase 2 Plan 1: extract_energy — Single-Channel UIIDs Summary

**One-liner:** Pure `extract_energy()` function + `EnergyReading` dataclass covering 8 single-channel UIIDs with per-UIID ×1/×0.01 scaling and string→float coercion — 18 TDD tests, all green.

## What Was Built

A pure Python extraction layer (`src/extractor.py`) that converts raw Sonoff LAN `params` dicts into typed `EnergyReading` values ready for InfluxDB writes. No I/O, no logging, no HA or ewelink dependencies.

### Files Created

| File | Purpose |
|------|---------|
| `src/extractor.py` | `EnergyReading` dataclass + `extract_energy()` pure function |
| `tests/test_extractor.py` | 18 TDD test cases covering every UIID and edge case |
| `tests/conftest.py` | Stubs homeassistant for tests/__init__.py; adds src/ to path |
| `conftest.py` | Root conftest adding src/ to PYTHONPATH |
| `pytest.ini` | Root pytest config with importlib mode for daemon tests |

### Exports from `src/extractor.py`

- `EnergyReading` — `@dataclass` with fields: `device_id`, `uiid`, `power`, `voltage`, `current`, `energy_today`, `channel`
- `extract_energy(device_id, uiid, params)` — returns `EnergyReading | None`

### UIID Coverage

| UIID | Device | Scale | dayKwh |
|------|--------|-------|--------|
| 32   | POWR2       | ×1    | — |
| 182  | S40         | ×1    | — |
| 226  | CK-BL602    | ×1    | — (phase_0_p/c/v remapping) |
| 190  | POWR3/S60   | ×0.01 | ✓ energy_today |
| 262  | CK-BL602-SWP1 | ×0.01 | — |
| 276  | S61STPF     | ×0.01 | ✓ energy_today |
| 277  | XMiniDim    | ×0.01 | — |
| 7032 | S60ZBTPF    | ×0.01 | ✓ energy_today |

## Verification Results

1. ✅ `PYTHONPATH=src python3 -m pytest tests/test_extractor.py -v` → 18 passed
2. ✅ `grep -r "homeassistant\|ewelink" src/extractor.py` → zero matches  
3. ✅ Plan success criteria: `extract_energy("dev1", 190, {"power": "2300", ...})` → `EnergyReading(power=23.0, current=5.0, voltage=220.0, energy_today=None, channel=None)` ✓
4. ✅ `src/extractor.py` exports `EnergyReading`, `extract_energy`
5. ✅ `tests/test_extractor.py` contains 18 test cases (≥13 required), 249 lines (≥60 required)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed legacy `tests/__init__.py` HA import blocking test collection**
- **Found during:** TDD RED phase — `pytest tests/test_extractor.py` failed with `ModuleNotFoundError: No module named 'homeassistant'`
- **Issue:** `tests/__init__.py` (legacy HA integration test helper) imports `homeassistant` unconditionally. Python imports `tests/__init__.py` when importing any file from the `tests/` package.
- **Fix:** Wrapped HA imports in `try/except ImportError` and guarded `DummyRegistry` class definition and `init()` function inside `if _HA_AVAILABLE:`. Added `tests/conftest.py` + root `conftest.py` for `src/` PYTHONPATH. Added root `pytest.ini` with `--import-mode=importlib`.
- **Files modified:** `tests/__init__.py`, `tests/conftest.py` (new), `conftest.py` (new), `pytest.ini` (new)
- **Commit:** `477e896`

## Commits

| Hash | Message |
|------|---------|
| `477e896` | test(02-energy-extraction-01): add failing tests for extract_energy single-channel UIIDs |
| `3dee4e1` | feat(02-energy-extraction-01): implement EnergyReading dataclass and extract_energy() function |

## Self-Check: PASSED

- `src/extractor.py` ✅ exists
- `tests/test_extractor.py` ✅ exists (249 lines, 18 tests)
- `tests/conftest.py` ✅ exists
- `conftest.py` ✅ exists
- `pytest.ini` ✅ exists
- Commit `477e896` ✅ verified
- Commit `3dee4e1` ✅ verified
