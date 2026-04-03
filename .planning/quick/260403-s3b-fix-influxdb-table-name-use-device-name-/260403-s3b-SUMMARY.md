---
id: 260403-s3b
type: quick
completed: "2026-04-03"
duration: "3 min"
tasks_completed: 2
files_modified:
  - src/writer.py
  - tests/test_writer.py
tags: [influxdb, writer, measurement, schema]
key-decisions:
  - "measurement name = device_name (fallback to device_id) — device identity carried by table name, not tags"
  - "no .tag() calls in write path — removes redundant device_id and device_name columns from InfluxDB schema"
---

# Quick Task 260403-s3b: Fix InfluxDB Table Name — Use Device Name

**One-liner:** InfluxDB measurement name changed from `device_id` to `device_name` with `device_id`/`device_name` tags removed entirely.

---

## What Was Done

### Task 1 — `src/writer.py`

Changed `InfluxWriter.write()` to use the human-readable device name as the InfluxDB measurement (table) name, and removed the two `.tag()` calls that previously wrote `device_id` and `device_name` as tag columns.

**Before:**
```python
point = (
    Point(reading.device_id)          # measurement = device_id
    .tag("device_id", reading.device_id)
    .tag("device_name", name)
)
```

**After:**
```python
name = device_name if device_name is not None else reading.device_id
point = Point(name)   # measurement = device_name (fallback: device_id)
```

Also updated the docstring to reflect the new schema (removed tag references, updated measurement description).

### Task 2 — `tests/test_writer.py`

Updated four tests that were asserting old behaviour:

| Old test name | New test name | Change |
|---|---|---|
| `test_write_builds_point_with_measurement_device_id` | `test_write_builds_point_with_measurement_device_name` | Asserts `Point("My Device")` not `Point("sonoff_abc123")` |
| `test_write_adds_tag_device_id` | `test_write_adds_no_tags` | Asserts `tag.call_count == 0` |
| `test_write_adds_tag_device_name_from_arg` | `test_write_measurement_uses_device_name_arg` | Asserts `Point("Kitchen Plug")` called |
| `test_write_tag_device_name_falls_back_to_device_id_when_none` | `test_write_measurement_falls_back_to_device_id_when_name_is_none` | Asserts `Point("dev99")` on `None` arg |

Tests 5–17 were unaffected. All 17 writer tests pass; 46 total tests pass (including extractor).

---

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | `7444dbb` | `fix(260403-s3b): use device_name as measurement, remove device_id/device_name tags` |
| Task 2 | `5ef9eaa` | `test(260403-s3b): update writer tests to assert measurement name, no tags` |

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Self-Check: PASSED

- `src/writer.py` — exists and updated ✅
- `tests/test_writer.py` — exists and updated ✅
- Commit `7444dbb` — exists ✅
- Commit `5ef9eaa` — exists ✅
- 46 tests pass, 0 failures ✅
