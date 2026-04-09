---
phase: 07-direct-connection-without-mdns-if-already-knowing-device-s-ip
plan: 01
subsystem: config

tags: [python, typeddict, config, polling, env-vars, tdd]

# Dependency graph
requires:
  - phase: 04-integration-and-docker
    provides: "parse_config(), parse_log_level(), DeviceConfig TypedDict, parse_influx_config()"
provides:
  - "DeviceConfig.ip optional field — enables static-IP direct-connect path in Plan 07-02"
  - "parse_poll_interval() — returns SONOFF_POLL_INTERVAL as int, default 10, sys.exit(1) on invalid"
affects:
  - phase 07-02 — polling daemon reads both ip field and parse_poll_interval()

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD: write failing tests first (RED), implement minimally (GREEN), no refactor needed"
    - "Conditional TypedDict field population: check key presence before assignment"
    - "parse_* function pattern: env var + default + int() coercion + sys.exit(1) with clear message"

key-files:
  created: []
  modified:
    - src/config.py
    - tests/test_config.py

key-decisions:
  - "ip field stored conditionally via cfg['ip'] = dev['ip'] pattern (not in constructor) — keeps total=False semantics and avoids ip=None in DeviceConfig when absent"
  - "No IP format validation at parse time per plan D-02 — invalid IPs cause connection failure, caught at runtime"
  - "parse_poll_interval() default of 10 seconds — matches plan requirement D-03"

patterns-established:
  - "conditional TypedDict field: append then mutate pattern (validated.append(cfg); if 'ip' in dev: validated[-1]['ip'] = dev['ip'])"

requirements-completed: [CFG-05, LAN-08]

# Metrics
duration: 8min
completed: 2026-04-09
---

# Phase 07 Plan 01: Config — ip Field + parse_poll_interval() Summary

**Optional `ip` field added to `DeviceConfig` TypedDict and `parse_poll_interval()` function added to config.py — both TDD-verified with 13 new unit tests (23 total, zero regressions)**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-09T04:25:00Z
- **Completed:** 2026-04-09T04:33:00Z
- **Tasks:** 1 (TDD: RED + GREEN phases)
- **Files modified:** 2

## Accomplishments

- Added optional `ip: str` field to `DeviceConfig` TypedDict (backward-compatible, `total=False`)
- Updated `parse_config()` to conditionally store `ip` from device JSON only when present (no null pollution)
- Added `parse_poll_interval()` function following existing `parse_log_level()` pattern: default 10s, sys.exit(1) on non-integer/zero/negative
- 13 new unit tests: 5 for `TestParseConfigIp`, 8 for `TestParsePollInterval` — all passing with zero regressions

## Task Commits

TDD task — two commits per TDD protocol:

1. **RED phase: failing tests** - `64c9cbd` (test)
2. **GREEN phase: implementation** - `7b2c1a6` (feat)

## Files Created/Modified

- `src/config.py` — Added `ip: str` to `DeviceConfig`, updated `parse_config()` with conditional ip storage, added `parse_poll_interval()` after `parse_log_level()`
- `tests/test_config.py` — Added `TestParseConfigIp` (5 tests) and `TestParsePollInterval` (8 tests) classes

## Decisions Made

- `ip` field stored via post-append mutation (`validated[-1]["ip"] = dev["ip"]`) rather than in the constructor, to avoid setting `ip=None` when absent — preserves `total=False` semantics so `"ip" not in result[0]` is True for devices without ip
- No IP address format validation at parse time — invalid IPs silently fail at connection time (per plan D-02 spec)
- `parse_poll_interval()` default of 10 seconds matches plan requirement; `int(raw)` used so "10.5" fails via `ValueError`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `DeviceConfig.ip` field ready for Plan 07-02 polling daemon to use for direct HTTP connection
- `parse_poll_interval()` exportable from `config` module; Plan 07-02 can call it at startup
- All 23 `test_config.py` tests pass — solid foundation before adding polling logic

---
*Phase: 07-direct-connection-without-mdns-if-already-knowing-device-s-ip*
*Completed: 2026-04-09*
