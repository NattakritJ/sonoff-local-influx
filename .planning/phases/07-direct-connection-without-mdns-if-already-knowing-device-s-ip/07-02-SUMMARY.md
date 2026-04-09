---
phase: 07-direct-connection-without-mdns-if-already-knowing-device-s-ip
plan: 02
subsystem: infra
tags: [polling, asyncio, mdns, zeroconf, sonoff-lan, static-ip]

# Dependency graph
requires:
  - phase: 07-01
    provides: ip field in DeviceConfig and parse_poll_interval() config contract

provides:
  - SonoffDaemon._poll_device() coroutine for per-device HTTP polling
  - Conditional AsyncZeroconf — only created when at least one device has no ip
  - Polling task list with clean cancellation on SIGTERM
  - .env.example documenting SONOFF_POLL_INTERVAL and ip field
  - Unit tests covering polling lifecycle, failure handling, and routing logic

affects:
  - Future phases that modify SonoffDaemon.run() or add new device transport modes

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-device asyncio.Task for polling (mirroring heartbeat lifecycle pattern)
    - ip/mdns device routing split at daemon startup
    - Guard: AsyncZeroconf never instantiated when all devices use static IP

key-files:
  created:
    - tests/test_polling.py
  modified:
    - src/__main__.py
    - .env.example

key-decisions:
  - "devicekey passed to XDevice as empty string when absent — post-checkpoint bug revealed empty string triggered AES encryption attempt; fixed to omit devicekey entirely when non-empty check fails"
  - "Polling task name set to 'poll-{device_id}' via asyncio.create_task(name=...) for easier debugging in task introspection"
  - "POLL FAILED vs POLL ERROR distinction: non-online result = WARNING('POLL FAILED'), exception from send() = WARNING('POLL ERROR') — both continue loop"
  - "azc.async_close() only called if azc was created — prevents AttributeError when all devices are static-IP"
  - "registry.stop() called unconditionally — XRegistryLocal.stop() is no-op if never started"

patterns-established:
  - "Polling task lifecycle: create_task → store in list → cancel all on shutdown → await with CancelledError suppressed — matches heartbeat lifecycle exactly"
  - "Device routing split: ip_devices / mdns_devices filter at run() start; conditional mDNS block; conditional polling block"

requirements-completed: [LAN-07, LAN-09]

# Metrics
duration: ~30min (including live device testing and post-checkpoint bug fix)
completed: 2026-04-09
---

# Phase 7 Plan 02: Wire Polling + Conditional mDNS Summary

**SonoffDaemon now routes static-IP devices to HTTP polling (XRegistryLocal.send getState) and mDNS-only devices to Zeroconf push — both modes coexist, AsyncZeroconf skipped entirely when all devices have a static IP**

## Performance

- **Duration:** ~30 min (including live device testing + post-checkpoint bug fix)
- **Started:** 2026-04-09T04:00:00Z
- **Completed:** 2026-04-09T05:00:00Z
- **Tasks:** 3 (2 auto + 1 checkpoint:human-verify) + 1 post-checkpoint fix
- **Files modified:** 3

## Accomplishments

- `_poll_device()` coroutine added to `SonoffDaemon`: constructs XDevice inline, calls `registry.send(device, command="getState")` in a `while True` loop, logs POLL FAILED/POLL ERROR on non-success results, propagates `CancelledError` cleanly
- `SonoffDaemon.run()` refactored to split devices into `ip_devices` / `mdns_devices`; `AsyncZeroconf` only instantiated for `mdns_devices`; polling tasks created per `ip_device` and all cancelled on shutdown
- `.env.example` documents the `ip` field with description + two new usage examples (static-IP only, mixed mode), plus `SONOFF_POLL_INTERVAL` section
- Live device test confirmed: startup log shows `polling=1 mdns=1`, energy writes succeed, daemon exits cleanly on Ctrl+C
- Post-checkpoint bug fix: empty `devicekey` was being passed to `XDevice` causing AES encryption failure (HTTP 400 from device); fixed to omit `devicekey` from XDevice when the value is empty

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Write failing tests** - `689c788` (test)
2. **Task 1 (GREEN): Implement _poll_device() + refactor SonoffDaemon.run()** - `e588bf0` (feat)
3. **Task 2: Update .env.example** - `72c20b9` (docs)
4. **Task 3: Checkpoint human-verify** — approved after live device test
5. **Post-checkpoint fix: omit empty devicekey from XDevice** - `0be4211` (fix)

## Files Created/Modified

- `tests/test_polling.py` — 7 unit tests across `TestPollDevice` (4 tests) and `TestRunRouting` (3 tests)
- `src/__main__.py` — Added `_poll_device()` method; refactored `run()` with ip/mdns routing, conditional AsyncZeroconf, polling task lifecycle
- `.env.example` — Added `ip` field docs + two new device examples + `SONOFF_POLL_INTERVAL` optional section

## Decisions Made

- **Empty devicekey omitted from XDevice**: post-checkpoint live test revealed HTTP 400 error from device when `devicekey=""` was passed; `XRegistryLocal.send()` attempts AES encryption whenever `devicekey` is present (even empty string). Fix: only include `devicekey` in the XDevice dict when `cfg.get("devicekey", "")` is non-empty. This matches how DIY devices work (no devicekey).
- **Polling task naming**: `asyncio.create_task(name=f"poll-{device_id}")` makes tasks identifiable in `asyncio.all_tasks()` output for debugging.
- **POLL FAILED vs POLL ERROR**: two distinct warning prefixes — `POLL FAILED` for non-"online" return values (expected failure path), `POLL ERROR` for exceptions from `send()` (unexpected failure path).
- **registry.stop() unconditional**: `XRegistryLocal.stop()` is already a no-op if `self.online is False`, so calling it unconditionally is safe regardless of whether mDNS was ever started.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Empty devicekey caused HTTP 400 from Sonoff device**
- **Found during:** Task 3 (human-verify checkpoint) — live device test
- **Issue:** `_poll_device()` constructed `XDevice` with `"devicekey": cfg.get("devicekey", "")`. When `devicekey` is absent from config, this passes an empty string. `XRegistryLocal.send()` interprets any non-None `devicekey` as a signal to apply AES encryption, producing a malformed encrypted payload. Device returned HTTP 400.
- **Fix:** Changed XDevice construction to conditionally include `devicekey` only when non-empty:
  ```python
  device: XDevice = {"deviceid": device_id, "host": cfg["ip"]}
  if key := cfg.get("devicekey", ""):
      device["devicekey"] = key
  ```
- **Files modified:** `src/__main__.py`
- **Verification:** Live device confirmed successful polling after fix; unit tests updated and passing
- **Committed in:** `0be4211`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Critical correctness fix — without it, all DIY/unencrypted devices with static IP would fail polling with HTTP 400. No scope creep.

## Issues Encountered

- **Live device returned HTTP 400 on first test run.** Root cause: empty `devicekey=""` in XDevice triggered unnecessary AES encryption in `XRegistryLocal.send()`. Fixed in `0be4211` after checkpoint approval. Daemon worked correctly on retest.

## User Setup Required

None — no new external service configuration required. `.env.example` already updated with `SONOFF_POLL_INTERVAL` and `ip` field documentation.

## Next Phase Readiness

- Phase 7 (both plans) is now complete. The daemon fully supports static-IP polling mode.
- All requirements LAN-07 and LAN-09 satisfied.
- The daemon is ready for production use on macOS and Docker environments where mDNS multicast is unavailable.
- No blockers or known issues.

---
*Phase: 07-direct-connection-without-mdns-if-already-knowing-device-s-ip*
*Completed: 2026-04-09*
