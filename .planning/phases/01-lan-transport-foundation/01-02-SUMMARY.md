---
phase: 01-lan-transport-foundation
plan: 02
subsystem: daemon-entrypoint
tags: [daemon, config, mdns, signal-handling, graceful-shutdown]
dependency_graph:
  requires: [01-01]
  provides: [src/config.py, src/__main__.py, runnable daemon]
  affects: [Phase 2, Phase 3, Phase 4]
tech_stack:
  added: []
  patterns: [asyncio-event-loop, signal-handler, mdns-filter, aes-decrypt-on-update]
key_files:
  created:
    - src/config.py
    - src/__main__.py
  modified: []
decisions:
  - "AsyncZeroconf owns zeroconf instance — passed as azc.zeroconf to registry.start() (no HA hass reference)"
  - "on_update is a synchronous callback — keeps event loop unblocked, no await inside"
  - "loop.add_signal_handler used (asyncio-native) rather than signal.signal — correct for async context"
  - "LOG_LEVEL env var support deferred to Phase 4 — keeps Phase 1 scope clean"
metrics:
  duration: "5 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  files_created: 2
---

# Phase 1 Plan 2: Daemon Entrypoint and Config Layer Summary

**One-liner:** Async daemon entrypoint wiring XRegistryLocal to mDNS discovery with per-device update filtering, AES-CBC decrypt, structured INFO logging, and SIGTERM/SIGINT graceful shutdown.

## What Was Built

The complete daemon entrypoint and configuration validation layer. The process is now runnable with `python src/__main__.py` and handles the full lifecycle: startup validation → mDNS registration → event-driven update handling → graceful shutdown.

### Files Created

| File | Purpose |
|------|---------|
| `src/config.py` | `parse_config()` — reads `SONOFF_DEVICES` env var, validates, returns typed list; `sys.exit(1)` on bad input |
| `src/__main__.py` | Async daemon: `XRegistryLocal` + `AsyncZeroconf` + `on_update` handler + SIGTERM/SIGINT hooks |

### Key Behaviors

- **CFG-01/02/03:** `parse_config()` exits immediately with a human-readable error if `SONOFF_DEVICES` is missing, not valid JSON, not a list, or any entry missing `device_id`
- **LAN-01:** mDNS browser started via `AsyncZeroconf` + `registry.start(azc.zeroconf)`
- **LAN-06:** `on_update` silently discards updates for device IDs not in the configured list
- **LAN-03/05:** Encrypted payloads (containing `data` + `iv` keys) decrypted via `XRegistryLocal.decrypt_msg(msg, devicekey)`
- **LAN-04:** Plain JSON payloads (`params` key) passed through directly
- **OPS-01:** Structured INFO log on startup and per-device update
- **OPS-02:** SIGTERM and SIGINT set `asyncio.Event` → graceful `registry.stop()` + `azc.async_close()`

## Verification Results

1. ✅ `from config import parse_config, DeviceConfig` → imports cleanly
2. ✅ `ast.parse` finds `async def main` in `__main__.py`
3. ✅ `grep -r "homeassistant|custom_components" src/` → zero matches
4. ✅ `grep AsyncZeroconf src/__main__.py` → shows `AsyncZeroconf` only (no hass variant)
5. ✅ `SONOFF_DEVICES='' python src/__main__.py` → exits with "ERROR: SONOFF_DEVICES environment variable is required."

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| `884a895` | feat(01-lan-transport-foundation-02): add daemon entrypoint and config layer |

## Self-Check: PASSED

- `src/config.py` ✅ exists
- `src/__main__.py` ✅ exists
- Commit `884a895` ✅ verified
