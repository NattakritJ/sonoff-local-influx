---
status: complete
phase: 01-lan-transport-foundation
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md]
started: 2026-04-03T00:00:00Z
updated: 2026-04-03T17:25:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running daemon. Start from scratch with a valid SONOFF_DEVICES config. The daemon boots without errors, mDNS browser starts, and a startup log line appears.
result: pass

### 8. Live Device Discovery (optional — requires Sonoff POWCT at 10.20.30.63)
expected: With the POWCT device_id and device_key configured, the daemon discovers the device via mDNS and logs a structured update with the device payload (may show encrypted or decrypted params depending on whether the device key is correct).
result: pass

### 2. Import ewelink Package
expected: In a clean venv with requirements.txt installed, `from ewelink import XRegistryLocal, XRegistryBase, XDevice, SIGNAL_UPDATE, SIGNAL_CONNECTED` succeeds with no errors.
result: pass

### 3. No HA Dependencies
expected: Running `grep -r "homeassistant" src/ewelink/` returns zero matches. The ewelink package is fully HA-free.
result: pass

### 4. Missing SONOFF_DEVICES Exits Cleanly
expected: Running the daemon with `SONOFF_DEVICES=''` or without the env var set exits immediately with a human-readable error message like "ERROR: SONOFF_DEVICES environment variable is required."
result: pass

### 5. Invalid JSON Config Exits Cleanly
expected: Running with `SONOFF_DEVICES='not-json'` exits immediately with a clear parse/validation error — no Python traceback, just a readable message.
result: pass

### 6. Valid Config with Device Filtering
expected: Running with a valid JSON device list (e.g., `[{"device_id":"abc123","device_key":"secret"}]`), the daemon starts, logs the configured device IDs, and silently ignores mDNS updates from unknown device IDs.
result: pass

### 7. Graceful Shutdown on SIGTERM
expected: Sending SIGTERM to the running daemon causes it to shut down cleanly — mDNS browser stops, resources are released, no Python exception traceback shown.
result: pass

### 8. Live Device Discovery (optional — requires Sonoff POWCT at 10.20.30.63)
expected: With the POWCT device_id and device_key configured, the daemon discovers the device via mDNS and logs a structured update with the device payload (may show encrypted or decrypted params depending on whether the device key is correct).
result: [pending]

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
