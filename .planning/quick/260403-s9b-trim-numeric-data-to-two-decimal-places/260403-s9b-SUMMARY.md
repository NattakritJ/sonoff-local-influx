---
phase: quick
plan: 260403-s9b
subsystem: extractor
tags: [precision, rounding, floating-point, tdd]
dependency_graph:
  requires: []
  provides: [clean-2dp-floats-in-EnergyReading]
  affects: [src/extractor.py, tests/test_extractor.py]
tech_stack:
  added: []
  patterns: [round(..., 2) at extraction time, TDD red-green]
key_files:
  modified:
    - src/extractor.py
    - tests/test_extractor.py
decisions:
  - "round(..., 2) applied to power/current/voltage in both extract_energy() and extract_energy_multi()"
  - "energy_today stays at round(..., 4) — kWh precision at 4dp is meaningful and intentional"
  - "rounding belongs in extraction layer so EnergyReading is always clean before reaching InfluxDB"
metrics:
  duration: "~3 min"
  completed: "2026-04-03"
  tasks: 1
  files: 2
---

# Quick Task 260403-s9b: Round Power/Voltage/Current to 2dp in Extractor Summary

**One-liner:** Eliminated IEEE 754 floating-point artifacts (e.g. `1315.6100000000001`) by applying `round(..., 2)` to power/voltage/current at extraction time in both `extract_energy()` and `extract_energy_multi()`.

---

## What Was Done

Applied `round(..., 2)` to the three energy fields — `power`, `voltage`, `current` — in both extraction functions:

**`extract_energy()` (lines 121–123 of `src/extractor.py`):**
```python
# Before
power = (_to_float(raw_power) * scale) if raw_power is not None else None
current = (_to_float(raw_current) * scale) if raw_current is not None else None
voltage = (_to_float(raw_voltage) * scale) if raw_voltage is not None else None

# After
power = round(_to_float(raw_power) * scale, 2) if raw_power is not None else None
current = round(_to_float(raw_current) * scale, 2) if raw_current is not None else None
voltage = round(_to_float(raw_voltage) * scale, 2) if raw_voltage is not None else None
```

**`extract_energy_multi()` (lines 185–187 of `src/extractor.py`):**
```python
# Before (was round(..., 4))
power = round(_to_float(raw_power) * 0.01, 4) if raw_power is not None else None
current = round(_to_float(raw_current) * 0.01, 4) if raw_current is not None else None
voltage = round(_to_float(raw_voltage) * 0.01, 4) if raw_voltage is not None else None

# After
power = round(_to_float(raw_power) * 0.01, 2) if raw_power is not None else None
current = round(_to_float(raw_current) * 0.01, 2) if raw_current is not None else None
voltage = round(_to_float(raw_voltage) * 0.01, 2) if raw_voltage is not None else None
```

`energy_today` remains `round(..., 4)` — intentional, kWh precision at 4dp is meaningful.

---

## Tests Added (`tests/test_extractor.py`)

Two new precision tests added at the end of the file:

- **`test_single_channel_no_float_artifact`** — verifies `extract_energy()` with raw `power=131561` (UIID 190, ×0.01) produces exactly `1315.61` and `str(result.power) == "1315.61"`.
- **`test_multi_channel_no_float_artifact`** — verifies `extract_energy_multi()` with raw `actPow_00=131561` (UIID 126) produces exactly `1315.61`.

Both use exact `==` equality (not `pytest.approx`) to confirm no artifact digits remain.

---

## Test Results

```
30 passed in 0.01s  (tests/test_extractor.py — 28 existing + 2 new)
48 passed in 0.15s  (tests/test_extractor.py + tests/test_writer.py — full suite)
```

Zero regressions. All success criteria met.

---

## Decisions Made

1. **`round(..., 2)` at extraction time** — `EnergyReading` is the canonical representation; rounding there ensures all consumers (InfluxDB writer, future code) always receive clean values.
2. **`energy_today` unchanged** — kWh precision at 4dp is meaningful (0.0001 kWh = 0.36 J); changing it would degrade data quality.
3. **`extract_energy_multi` changed from `round(..., 4)` to `round(..., 2)`** — consistency with single-channel behaviour; the prior `round(..., 4)` was already preventing the artifact for the specific test case but was inconsistent with the stated 2dp policy.

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Commits

| Hash | Message |
|------|---------|
| `1ab8025` | `feat(quick-260403-s9b): round power/voltage/current to 2dp in extractor` |

---

## Self-Check: PASSED

- [x] `src/extractor.py` modified — `round(..., 2)` applied to power/current/voltage in both functions
- [x] `tests/test_extractor.py` — 2 new precision tests added
- [x] Commit `1ab8025` exists
- [x] All 30 extractor tests pass; 48 total tests pass
- [x] `131561 * 0.01` → `1315.61` (not `1315.6100000000001`)
- [x] `energy_today` still rounds to 4dp
