---
phase: 07-direct-connection-without-mdns-if-already-knowing-device-s-ip
verified: 2026-04-09T05:30:00Z
status: passed
score: 12/12 must-haves verified
gaps: []
human_verification:
  - test: "Live device static-IP polling with real Sonoff hardware"
    expected: "Startup log shows 'polling=N mdns=M', energy writes appear, daemon exits cleanly on Ctrl+C within 3 seconds"
    why_human: "Requires a live Sonoff device with known static IP and real InfluxDB instance — already completed per 07-02-SUMMARY.md Task 3 checkpoint approval"
---

# Phase 7: Direct Connection Without mDNS (Static-IP Polling) — Verification Report

**Phase Goal:** Enable static-IP devices to bypass mDNS entirely using HTTP polling, while preserving mDNS push for devices without an ip. Both modes must coexist in the same daemon instance.
**Verified:** 2026-04-09T05:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | DeviceConfig accepts an optional 'ip' field without breaking existing configs | ✓ VERIFIED | `ip: str` in `DeviceConfig` TypedDict (config.py:15); `total=False` preserves backward compat; 5 tests in `TestParseConfigIp` all pass |
| 2  | parse_config() stores 'ip' from each device object when present | ✓ VERIFIED | config.py:71-72 — conditional `if "ip" in dev: validated[-1]["ip"] = dev["ip"]`; `test_device_with_ip_includes_ip_field` passes |
| 3  | parse_poll_interval() returns 10 when SONOFF_POLL_INTERVAL is unset | ✓ VERIFIED | config.py:134-135 — `if raw is None: return 10`; `test_unset_returns_default_10` passes |
| 4  | parse_poll_interval() parses valid integer strings (1, 60, 3600) | ✓ VERIFIED | config.py:137-138 — `int(raw)` coercion; `test_valid_30`, `test_valid_1_minimum`, `test_valid_3600` all pass |
| 5  | parse_poll_interval() calls sys.exit(1) on non-integer or zero or negative values | ✓ VERIFIED | config.py:139-150 — ValueError/≤0 branches; `test_zero_exits`, `test_negative_exits`, `test_non_integer_string_exits`, `test_float_string_exits` all pass |
| 6  | A device with 'ip' in SONOFF_DEVICES is polled via XRegistryLocal.send() at the configured interval | ✓ VERIFIED | `__main__.py:122` — `await registry.send(device, command="getState")` in `_poll_device()` while-True loop; `test_failure_result_logs_warning` confirms send is called |
| 7  | A device without 'ip' continues to use mDNS push — both modes coexist | ✓ VERIFIED | `__main__.py:39/47-49` — `mdns_devices` filter + conditional `AsyncZeroconf`; `test_mixed_both_modes_active` verifies both azc AND poll task created together |
| 8  | AsyncZeroconf is never created when ALL devices have a static ip configured | ✓ VERIFIED | `__main__.py:47` — `if mdns_devices:` guard; `test_all_ip_devices_no_azc` confirms `AsyncZeroconf` not called |
| 9  | Polling tasks are cancelled cleanly on SIGTERM — daemon exits within 10 seconds | ✓ VERIFIED | `__main__.py:84-90` — tasks cancelled then awaited with `CancelledError` suppressed; `test_cancelled_propagates` verifies `CancelledError` propagates from `_poll_device` |
| 10 | Polling failures (non-online result) log at WARNING and retry on next interval — daemon never crashes | ✓ VERIFIED | `__main__.py:123-129` — POLL FAILED warning; `__main__.py:132-138` — POLL ERROR catches exceptions, continues loop; both test cases pass |
| 11 | Startup log confirms poll interval when any static-IP device is configured | ✓ VERIFIED | `__main__.py:51-60` — `if ip_devices:` branch logs `poll_interval=%ds` in startup message |
| 12 | .env.example documents SONOFF_POLL_INTERVAL and the ip field | ✓ VERIFIED | `.env.example:17,27,30,51,53` — ip field description + two device examples + `SONOFF_POLL_INTERVAL` commented section present |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/config.py` | `ip` field in `DeviceConfig` TypedDict + `parse_poll_interval()` function | ✓ VERIFIED | `ip: str` at line 15; `parse_poll_interval()` at lines 128-151; both exported; 151 lines total |
| `tests/test_config.py` | Unit tests for ip parsing and `parse_poll_interval()` | ✓ VERIFIED | `TestParseConfigIp` (5 tests, lines 109-167) + `TestParsePollInterval` (8 tests, lines 170-236); all 23 config tests pass |
| `src/__main__.py` | `SonoffDaemon` with `_poll_device` method and conditional mDNS routing | ✓ VERIFIED | `_poll_device()` at lines 106-139; `ip_devices`/`mdns_devices` split at lines 38-39; conditional `azc` at lines 46-49; polling task list at lines 69-75 |
| `tests/test_polling.py` | Unit tests for polling task lifecycle and failure handling | ✓ VERIFIED | `TestPollDevice` (4 tests, lines 65-168) + `TestRunRouting` (3 tests, lines 175-316); all 7 tests pass |
| `.env.example` | Documentation for `SONOFF_POLL_INTERVAL` and `ip` field | ✓ VERIFIED | `ip` docs at line 17; static-IP device examples at lines 27, 30; `SONOFF_POLL_INTERVAL` section at lines 50-53 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/__main__.py` polling task | `XRegistryLocal.send()` | `await registry.send(device, command="getState")` | ✓ WIRED | `__main__.py:122` — explicit call with `command="getState"`; response checked at line 123 |
| `SonoffDaemon.run()` | `parse_poll_interval()` | `from config import parse_poll_interval` + call at line 40 | ✓ WIRED | `__main__.py:10` imports; `__main__.py:40` calls at startup |
| `SIGNAL_UPDATE` dispatch | `_on_update()` handler | `dispatcher_connect(SIGNAL_UPDATE, self._on_update)` | ✓ WIRED | `__main__.py:44` — unchanged from prior phases; polled device updates flow through same handler |
| `tests/test_config.py` | `src/config.py` | `sys.path.insert(0, src/) + from config import ...` | ✓ WIRED | `test_config.py:25` + per-test `from config import parse_poll_interval` / `parse_config` |
| `tests/test_polling.py` | `src/__main__.py` | `importlib.util.spec_from_file_location("sonoff_main", ...)` | ✓ WIRED | `test_polling.py:25-30` — loads `__main__.py` as `sonoff_main`; `SonoffDaemon = _sonoff_main.SonoffDaemon` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `src/__main__.py` `_poll_device()` | `result` from `registry.send()` | `XRegistryLocal.send()` → HTTP POST to device | Yes — HTTP response from real device; dispatches `SIGNAL_UPDATE` internally which flows to `_on_update()` | ✓ FLOWING |
| `src/__main__.py` `run()` | `ip_devices` / `mdns_devices` | `parse_config()` → `DeviceConfig` list with/without `ip` key | Yes — from `SONOFF_DEVICES` env var JSON parse | ✓ FLOWING |
| `src/__main__.py` `run()` | `poll_interval` | `parse_poll_interval()` → `SONOFF_POLL_INTERVAL` env var | Yes — env var read at startup; default 10 if unset | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `parse_poll_interval()` default returns 10 | `python3 -c "from config import parse_poll_interval; import os; os.environ.pop('SONOFF_POLL_INTERVAL',None); print(parse_poll_interval())"` | `10` | ✓ PASS |
| `DeviceConfig` has `ip` field | `python3 -c "from config import DeviceConfig; print(list(DeviceConfig.__annotations__.keys()))"` | `['device_id', 'uiid', 'devicekey', 'device_name', 'ip']` | ✓ PASS |
| `SonoffDaemon._poll_device` exists | `python3 -c "... print(hasattr(SonoffDaemon, '_poll_device'))"` | `True` | ✓ PASS |
| All unit tests pass (no regression) | `python3 -m pytest tests/ -x -q --ignore=integration tests` | `87 passed in 0.73s` | ✓ PASS |
| Commits documented match git log | `git log --oneline -8` | 8 commits matching SUMMARY hashes: `64c9cbd`, `7b2c1a6`, `341b3cd`, `689c788`, `e588bf0`, `72c20b9`, `0be4211`, `4fe18c2` | ✓ PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CFG-05 | 07-01-PLAN.md | Each device entry in `SONOFF_DEVICES` accepts an optional `ip` field; when present, mDNS discovery is skipped for that device and the daemon connects directly to the configured IP | ✓ SATISFIED | `DeviceConfig.ip: str` in config.py:15; parse_config() stores it conditionally at lines 71-72; `__main__.py` routes by `"ip" in d` at lines 38-39 |
| LAN-07 | 07-02-PLAN.md | When a device has a configured `ip`, daemon polls it via HTTP POST to `http://{ip}:8081/zeroconf/getState` at fixed interval configurable via `SONOFF_POLL_INTERVAL` | ✓ SATISFIED | `_poll_device()` at `__main__.py:122` calls `registry.send(device, command="getState")`; `XRegistryLocal.send()` appends `:8081` when no colon; interval from `parse_poll_interval()` at line 40 |
| LAN-08 | 07-01-PLAN.md | Polling interval configurable per-daemon via `SONOFF_POLL_INTERVAL` env var (integer seconds, default 10) | ✓ SATISFIED | `parse_poll_interval()` in config.py:128-151; default 10, int coercion, sys.exit(1) on invalid; 8 unit tests all passing |
| LAN-09 | 07-02-PLAN.md | Static IP polling and mDNS push modes can coexist in the same daemon — devices with `ip` use polling; devices without use mDNS | ✓ SATISFIED | `__main__.py:38-49` — split + conditional `AsyncZeroconf` + polling tasks; `test_mixed_both_modes_active` explicitly verifies coexistence |

**No orphaned requirements.** All 4 requirements (CFG-05, LAN-07, LAN-08, LAN-09) are claimed and verified across the two plans.

---

### Anti-Patterns Found

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| None | — | — | No TODOs, FIXMEs, placeholder returns, or empty handlers found in phase files. Post-checkpoint bug fix (`0be4211`) was identified and corrected before phase completion — empty `devicekey` no longer passed to `XDevice`. |

---

### Human Verification Required

#### 1. Live Device End-to-End Test

**Test:** Add `"ip":"<DEVICE_IP>"` to one `SONOFF_DEVICES` entry; `python src/__main__.py`
**Expected:** Startup log shows `polling=1 mdns=N`; energy readings appear as `WRITE |` log lines; press Ctrl+C → `Daemon stopped cleanly.` within 3 seconds
**Why human:** Requires live Sonoff hardware + InfluxDB — cannot mock network stack

> **Note:** Per `07-02-SUMMARY.md`, Task 3 (human-verify checkpoint) was executed and approved by the developer after live device testing confirmed the polling path worked end-to-end, including the post-checkpoint bug fix for empty `devicekey`.

---

### Gaps Summary

No gaps. All 12 must-have truths are verified against the actual codebase:

- **Config layer (07-01):** `DeviceConfig.ip` field is present and optional, stored conditionally. `parse_poll_interval()` implements correct default/validation behaviour. 23 config tests all pass.
- **Daemon layer (07-02):** `_poll_device()` is implemented with correct POLL FAILED / POLL ERROR warning distinction and clean `CancelledError` propagation. `SonoffDaemon.run()` correctly splits `ip_devices` / `mdns_devices`, guards `AsyncZeroconf` creation behind `if mdns_devices:`, and cancels all polling tasks on shutdown. 7 polling tests all pass.
- **Documentation:** `.env.example` documents both `ip` field (with two concrete examples) and `SONOFF_POLL_INTERVAL` optional section.
- **Zero regressions:** 87 unit tests pass (prior phases unaffected).

---

*Verified: 2026-04-09T05:30:00Z*
*Verifier: gsd-verifier (claude-sonnet-4.6)*
