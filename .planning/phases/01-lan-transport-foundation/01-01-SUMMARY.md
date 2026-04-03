---
phase: 01-lan-transport-foundation
plan: 01
subsystem: ewelink-transport
tags: [migration, ewelink, lan, python-package]
dependency_graph:
  requires: []
  provides: [src/ewelink package, XRegistryLocal, XRegistryBase, XDevice, SIGNAL_UPDATE, SIGNAL_CONNECTED]
  affects: [01-02, Phase 2, Phase 3]
tech_stack:
  added: [aiohttp>=3.9, cryptography>=41, zeroconf>=0.131]
  patterns: [async-dispatcher, mdns-browser, aes-cbc-decrypt]
key_files:
  created:
    - src/ewelink/__init__.py
    - src/ewelink/base.py
    - src/ewelink/local.py
    - requirements.txt
  modified: []
decisions:
  - "Copy base.py and local.py verbatim — both files were already free of homeassistant imports"
  - "No src/__init__.py created — ewelink importable by adding src/ to PYTHONPATH"
  - "requirements.txt uses major-version bounds (not exact pins) — exact pins deferred to Phase 4"
metrics:
  duration: "8 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  files_created: 4
---

# Phase 1 Plan 1: Extract Clean ewelink LAN Package Summary

**One-liner:** Extracted HA-free `src/ewelink` package from custom_components with AES-CBC decrypt, mDNS browser, and async dispatcher — importable in a clean Python env with only requirements.txt deps.

## What Was Built

The LAN transport foundation: a standalone Python package at `src/ewelink/` containing the mDNS discovery and AES-CBC decryption logic extracted from the Home Assistant custom component. Zero HA references remain.

### Files Created

| File | Purpose |
|------|---------|
| `src/ewelink/base.py` | `XRegistryBase` dispatcher + `XDevice` TypedDict — no HA imports |
| `src/ewelink/local.py` | `XRegistryLocal` — mDNS browser, AES decrypt, HTTP send |
| `src/ewelink/__init__.py` | Slim package init — re-exports 5 LAN-only symbols |
| `requirements.txt` | aiohttp, cryptography, zeroconf version bounds |

### Exports

`src/ewelink` exposes exactly:
- `XRegistryLocal` — mDNS discovery + AES-CBC decrypt + HTTP send
- `XRegistryBase` — async dispatcher, sequence counter
- `XDevice` — TypedDict for device state
- `SIGNAL_UPDATE` — signal constant for mDNS updates
- `SIGNAL_CONNECTED` — signal constant for connection events

## Verification Results

1. ✅ `grep -r "homeassistant" src/ewelink/` → zero matches
2. ✅ Clean venv + requirements.txt → `import ewelink.local` succeeds
3. ✅ All 5 symbols exportable: `from ewelink import XRegistryLocal, XRegistryBase, XDevice, SIGNAL_UPDATE, SIGNAL_CONNECTED`

## Deviations from Plan

None — plan executed exactly as written.

Both source files (`base.py`, `local.py`) confirmed to have zero HA imports prior to migration, so copy-verbatim was correct as planned.

## Commits

| Hash | Message |
|------|---------|
| `c2f0ea5` | feat(01-lan-transport-foundation-01): extract clean ewelink LAN package from HA component |

## Self-Check: PASSED

- `src/ewelink/__init__.py` ✅ exists
- `src/ewelink/base.py` ✅ exists
- `src/ewelink/local.py` ✅ exists
- `requirements.txt` ✅ exists
- Commit `c2f0ea5` ✅ verified
