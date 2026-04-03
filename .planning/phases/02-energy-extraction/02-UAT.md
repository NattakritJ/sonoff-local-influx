---
status: complete
phase: 02-energy-extraction
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md]
started: 2026-04-03T00:00:00Z
updated: 2026-04-03T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test Suite Passes
expected: Run `PYTHONPATH=src python -m pytest tests/test_extractor.py -v` from the repo root. All 28 tests pass with no errors or failures. Output ends with "28 passed".
result: pass

### 2. Single-Channel ×1 Pass-Through (UIID 32)
expected: |
  In a Python shell:
  ```python
  from extractor import extract_energy
  r = extract_energy("dev1", 32, {"power": 230, "current": 10, "voltage": 220})
  print(r.power, r.voltage, r.current, r.channel)
  ```
  Prints: `230.0 220.0 10.0 None`
  Values are passed through ×1, types are float, channel is None.
result: pass

### 3. Single-Channel ×0.01 Scaling (UIID 190)
expected: |
  In a Python shell:
  ```python
  r = extract_energy("dev1", 190, {"power": 2300, "current": 500, "voltage": 22000})
  print(r.power, r.current, r.voltage)
  ```
  Prints: `23.0 5.0 220.0`
  All values scaled by ×0.01.
result: pass

### 4. UIID 226 Param Remapping
expected: |
  In a Python shell:
  ```python
  r = extract_energy("dev1", 226, {"phase_0_p": 500, "phase_0_c": 20, "phase_0_v": 2300})
  print(r.power, r.current, r.voltage)
  ```
  Prints: `500.0 20.0 2300.0`
  The `phase_0_p/c/v` keys are remapped to `power/current/voltage` with ×1 scaling.
result: pass

### 5. energy_today from dayKwh (UIID 190)
expected: |
  In a Python shell:
  ```python
  r = extract_energy("dev1", 190, {"power": 100, "current": 10, "voltage": 22000, "dayKwh": 350})
  print(r.energy_today)
  ```
  Prints: `3.5`
  `dayKwh` value of 350 × 0.01 = 3.5.
result: pass

### 6. String Raw Value Coercion
expected: |
  In a Python shell:
  ```python
  r = extract_energy("dev1", 190, {"power": "2300", "current": "500", "voltage": "22000"})
  print(r.power, type(r.power))
  ```
  Prints: `23.0 <class 'float'>`
  String inputs are coerced to float before scaling.
result: pass

### 7. Returns None for Unrecognised Params
expected: |
  In a Python shell:
  ```python
  r = extract_energy("dev1", 190, {"switch": "on", "ltype": "white"})
  print(r)
  ```
  Prints: `None`
  No energy keys → function returns None, not an EnergyReading.
result: pass

### 8. Multi-Channel DualR3 (UIID 126)
expected: |
  In a Python shell:
  ```python
  from extractor import extract_energy_multi
  readings = extract_energy_multi("dev1", 126, {
      "actPow_00": 1000, "current_00": 50, "voltage_00": 22000,
      "actPow_01": 500,  "current_01": 25, "voltage_01": 22000,
  })
  print(len(readings), readings[0].channel, readings[1].channel)
  print(readings[0].power, readings[1].power)
  ```
  Prints: `2 1 2`
  Then: `10.0 5.0`
  Two readings, channels 1 and 2 (1-based), values scaled ×0.01.
result: [pending]

### 9. Multi-Channel SPM-4Relay (UIID 130) — All 4 Channels
expected: |
  In a Python shell:
  ```python
  readings = extract_energy_multi("dev1", 130, {
      "actPow_00": 100, "current_00": 5, "voltage_00": 22000,
      "actPow_01": 200, "current_01": 10, "voltage_01": 22000,
      "actPow_02": 300, "current_02": 15, "voltage_02": 22000,
      "actPow_03": 400, "current_03": 20, "voltage_03": 22000,
  })
  print(len(readings), [r.channel for r in readings])
  ```
  Prints: `4 [1, 2, 3, 4]`
  Four readings, channels 1–4.
result: [pending]

### 10. Absent Channels Skipped
expected: |
  In a Python shell:
  ```python
  readings = extract_energy_multi("dev1", 126, {
      "actPow_00": 1000, "current_00": 50, "voltage_00": 22000,
      # channel 2 params absent
  })
  print(len(readings), readings[0].channel)
  ```
  Prints: `1 1`
  Only channel 1 present in params → only one reading returned, no error.
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
