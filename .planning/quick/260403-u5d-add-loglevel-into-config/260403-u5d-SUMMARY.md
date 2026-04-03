---
phase: quick
plan: 260403-u5d
subsystem: config
tags: [logging, config, env-var, tdd]
dependency_graph:
  requires: []
  provides: [parse_log_level in src/config.py]
  affects: [src/__main__.py, .env.example]
tech_stack:
  added: []
  patterns: [env-var validation with sys.exit on invalid, TDD red-green]
key_files:
  created: [tests/test_config.py]
  modified: [src/config.py, src/__main__.py, .env.example]
decisions:
  - "Created tests/test_config.py instead of adding to test_diagnostics.py — test_diagnostics.py has a pre-existing broken import (influxdb_client_3 not installed in dev env)"
  - "Moved logging.basicConfig() inside main() after _load_dotenv() so LOG_LEVEL is honoured from .env files in local dev"
metrics:
  duration: "~8 min"
  completed: "2026-04-03"
---

# Quick Task 260403-u5d: Add LOG_LEVEL Environment Variable Support — Summary

**One-liner:** Added `parse_log_level()` to config.py with whitelist validation, wired into `__main__.py` after dotenv load, and documented in `.env.example`.

---

## Objective

Enable operators to control log verbosity via the `LOG_LEVEL` Docker env var without rebuilding the image. INFO is the unchanged default.

---

## Tasks Completed

| # | Task | Type | Commit | Files |
|---|------|------|--------|-------|
| RED | Add failing tests for parse_log_level() | test | 85317dd | tests/test_config.py (+103 lines) |
| 1 | Add parse_log_level() + wire into __main__.py | feat | 89779e0 | src/config.py, src/__main__.py |
| 2 | Document LOG_LEVEL in .env.example | chore | 7f4d959 | .env.example |

---

## Implementation Details

### `src/config.py` — `parse_log_level()`

```python
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

def parse_log_level() -> int:
    raw = os.environ.get("LOG_LEVEL", "INFO").upper()
    if raw not in _VALID_LOG_LEVELS:
        print(f"ERROR: LOG_LEVEL={raw!r} is not valid.\n  Allowed values: ...", file=sys.stderr)
        sys.exit(1)
    return getattr(logging, raw)
```

- Whitelists only 5 named levels (NOTSET excluded — too permissive)
- Case-insensitive via `.upper()` normalization
- Numeric strings (e.g. "10") are rejected
- Defaults to INFO when unset

### `src/__main__.py` — Call order

The module-level `logging.basicConfig()` was moved inside `main()`:

1. `_load_dotenv()` — loads `.env` file so `LOG_LEVEL` is available
2. `log_level = parse_log_level()` — reads and validates `LOG_LEVEL`
3. `logging.basicConfig(level=log_level, ...)` — configures logging

This ensures `LOG_LEVEL` set in `.env` (for local dev) is respected; Docker env vars override `.env` as before.

---

## Verification

- `python3 -m pytest tests/test_extractor.py tests/test_config.py -x -q` → **41 passed**
- `LOG_LEVEL=DEBUG` → `logging.DEBUG (10)` ✓
- Default (unset) → `logging.INFO (20)` ✓
- `LOG_LEVEL=BOGUS` → `sys.exit(1)` ✓
- `grep "LOG_LEVEL" .env.example` → `# LOG_LEVEL=INFO` ✓
- `grep "parse_log_level" src/__main__.py` → wired ✓

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created `tests/test_config.py` instead of adding to `test_diagnostics.py`**
- **Found during:** TDD RED phase
- **Issue:** `test_diagnostics.py` has a pre-existing broken import chain (`from writer import InfluxWriter` → `from influxdb_client_3 import ...` → `ModuleNotFoundError`). Adding to this file would make the new tests uncollectable.
- **Fix:** Created a dedicated `tests/test_config.py` that imports only from `config` — no third-party library dependency.
- **Files modified:** `tests/test_config.py` (new file)
- **Commit:** 85317dd

---

## Known Stubs

None — all behavior is fully implemented and tested.

---

## Self-Check: PASSED

- `src/config.py` ✓ exists with `parse_log_level()`
- `src/__main__.py` ✓ imports and calls `parse_log_level()`
- `.env.example` ✓ contains `LOG_LEVEL` documentation
- `tests/test_config.py` ✓ 10 tests passing
- Commits: 85317dd ✓, 89779e0 ✓, 7f4d959 ✓
