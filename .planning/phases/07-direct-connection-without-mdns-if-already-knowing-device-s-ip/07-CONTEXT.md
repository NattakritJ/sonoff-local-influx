# Phase 7: Direct Connection without mDNS - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable devices configured with a static `ip` field in `SONOFF_DEVICES` to bypass mDNS discovery entirely and be polled via HTTP POST to `getState` at a fixed interval. Devices without an `ip` continue using mDNS push as before — both modes coexist in the same daemon instance. This makes the daemon usable on macOS and in Docker environments where mDNS multicast is unavailable.

Scope is limited to:
1. `src/config.py` — add optional `ip` field to `DeviceConfig` TypedDict; parse and validate it in `parse_config()`
2. `src/__main__.py` — start per-device asyncio polling tasks in `SonoffDaemon.run()` for devices with `ip`; conditionally start mDNS browser only for devices without `ip`
3. `src/config.py` — add `parse_poll_interval()` for `SONOFF_POLL_INTERVAL` env var (default 10s)
4. `.env.example` — document `SONOFF_POLL_INTERVAL` and the `ip` field in `SONOFF_DEVICES`
5. Tests — new tests for polling task lifecycle and failure handling

No changes to `ewelink/local.py`, `extractor.py`, or `writer.py`.

</domain>

<decisions>
## Implementation Decisions

### Config Structure

- **D-01:** `DeviceConfig` TypedDict gains an optional `ip: str` field (not required — `total=False` already applies)
- **D-02:** `parse_config()` accepts and stores `ip` from each device object if present; no format validation at parse time (IP validity checked implicitly when connection fails)
- **D-03:** `SONOFF_POLL_INTERVAL` is a new optional env var (integer seconds, default 10); parsed by a new `parse_poll_interval()` function in `config.py` using the same fail-fast pattern as other config parsers
- **D-04:** Startup log line confirms the polling interval in use when any static-IP devices are configured (per LAN-08 success criterion)

### Polling Architecture

- **D-05:** One `asyncio.create_task()` per static-IP device — each task runs its own `while True: poll → sleep(interval)` loop inside `SonoffDaemon.run()`
- **D-06:** Polling tasks are stored in a list and cancelled on shutdown (same pattern as the heartbeat task: `task.cancel()` + `await task` catching `asyncio.CancelledError`)
- **D-07:** mDNS browser starts **only if** at least one configured device lacks an `ip`; if all devices have `ip`, `AsyncZeroconf` is never created and no mDNS overhead occurs
- **D-08:** Both modes coexist — mDNS devices and static-IP devices can be in the same `SONOFF_DEVICES` list; the daemon handles each appropriately

### Data Flow (reuse existing pipeline)

- **D-09:** Polling tasks call **`XRegistryLocal.send()`** with `command="getState"` — this existing method handles HTTP POST, response parsing, AES decryption (if encrypted), and dispatching `SIGNAL_UPDATE`. No new HTTP or parsing code needed.
- **D-10:** Each polling call constructs a minimal `XDevice` dict inline from the `DeviceConfig` + static ip:
  ```python
  device: XDevice = {
      "deviceid": cfg["device_id"],
      "host": cfg["ip"],  # no port — send() appends :8081 if missing
      "devicekey": cfg.get("devicekey", ""),
  }
  ```
  This keeps `XDevice` construction in the daemon, not in `XRegistryLocal`.
- **D-11:** `_on_update()` receives polled events via `SIGNAL_UPDATE` dispatch — **unchanged**. Energy extraction and InfluxDB write path are identical for polled and mDNS-pushed events.

### Startup Behavior

- **D-12:** Static-IP devices are **NOT checked at startup** — no pre-flight connectivity test for individual devices. Polling tasks start immediately; the first poll attempt logs a warning if the device is unreachable. This is consistent with mDNS devices, which also have no startup reachability check.
- **D-13:** `SONOFF_POLL_INTERVAL` env var validation (if set to non-integer or ≤0) uses the same fail-fast pattern as other config parsers (`sys.exit(1)` with clear message)

### Runtime Failure Handling

- **D-14:** When a poll call returns a non-`"online"` result (timeout, connection error, etc.), log at **WARNING** level — transient device reboots are expected, this should not be noisy as ERROR
- **D-15:** Polling tasks **keep running** after failures — retry on the next interval, no backoff, no exponential delay
- **D-16:** Daemon never crashes from polling failures (log-and-continue, consistent with `PROJECT.md` constraint)

### Agent's Discretion

- Whether to add a `localtype` field to the inline `XDevice` dict (it's optional in `XDevice`)
- Exact wording of the startup log line confirming poll interval
- Whether to add a `_POLL_UIIDS` frozenset or reuse `_MULTI_CHANNEL_UIIDS` logic — implementation detail for `_on_update()` routing (already works by device_id, not by transport)
- Whether the polling task's `while True` loop catches and logs `Exception` broadly or relies on the existing error strings from `send()`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements (this phase)
- `.planning/REQUIREMENTS.md` §Static IP + HTTP Polling Mode — CFG-05, LAN-07, LAN-08, LAN-09 (full spec for this feature)

### Project Constraints
- `.planning/PROJECT.md` §Constraints — env vars only, log-and-continue, no cloud dependency
- `.planning/PROJECT.md` §Key Decisions — established patterns for all prior phases

### Existing Source (integration points)
- `src/config.py` — `DeviceConfig` TypedDict and `parse_config()` to extend with `ip` field; `parse_influx_config()` as a reference pattern for `parse_poll_interval()`
- `src/__main__.py` — `SonoffDaemon`: `run()` method (add polling tasks + conditional mDNS start), `_on_update()` (unchanged), heartbeat task pattern (reference for polling task lifecycle)
- `src/ewelink/local.py` — `XRegistryLocal.send()` (the method polling calls); `start()` / `stop()` for conditional mDNS control
- `src/ewelink/base.py` — `XDevice` TypedDict fields required by `send()`; `SIGNAL_UPDATE` signal name

### State / Prior Decisions
- `.planning/STATE.md` §Accumulated Context — all architecture decisions from Phases 1–6 (asyncio patterns, logging format, shutdown handling)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ewelink/local.py:148-265` — `XRegistryLocal.send(device, command="getState")`: already handles HTTP POST, response parsing, AES decryption, and `SIGNAL_UPDATE` dispatch. Polling tasks call this directly — zero new HTTP logic needed.
- `src/__main__.py:50-61` — Heartbeat task pattern: `asyncio.ensure_future()` + cancel on shutdown + `CancelledError` catch. Polling tasks follow the same lifecycle.
- `src/config.py:10-17` — `DeviceConfig` TypedDict with `total=False` — new `ip: str` field can be added without breaking existing configs.
- `src/config.py:65-95` — `parse_influx_config()` pattern — fail-fast, per-variable error messages, `sys.exit(1)`. Mirror this for `parse_poll_interval()`.

### Established Patterns
- Per-task error handling: `send()` returns string codes (`"online"`, `"timeout"`, `"E#CON"`, etc.) — polling task checks the return value and logs warning on non-`"online"`
- Logger naming: `_LOGGER = logging.getLogger("sonoff_daemon")` in `__main__.py` — polling log lines follow the existing `"UPDATE | device_id | ..."` format
- SIGNAL_UPDATE dispatch: `registry.dispatcher_connect(SIGNAL_UPDATE, self._on_update)` — polled events reach `_on_update()` through the same channel as mDNS events

### Integration Points
- `src/__main__.py:36-68` — `SonoffDaemon.run()`: split device list into `ip_devices` and `mdns_devices`; start polling tasks for `ip_devices`; conditionally start `AsyncZeroconf` + `registry.start()` only for `mdns_devices`
- `src/__main__.py:37` — `XRegistryLocal(session)` is instantiated regardless of transport — polling tasks need it for `send()`; mDNS browser is optional
- `src/__main__.py:64-65` — `registry.stop()` and `azc.async_close()` — must be conditional if mDNS was never started

</code_context>

<specifics>
## Specific Ideas

- User confirmed: per-device asyncio tasks (not a shared loop) — isolated failure handling per device
- User confirmed: reuse `XRegistryLocal.send()` + `SIGNAL_UPDATE` — no duplicate HTTP logic
- User confirmed: both modes coexist in same `SonoffDaemon` — not separate classes
- User confirmed: no startup reachability check for static-IP devices — consistent with mDNS pattern
- User confirmed: LOG WARNING (not ERROR) for runtime polling failures — transient offline is expected
- User confirmed: cancel polling tasks on SIGTERM with `CancelledError` — same as heartbeat task

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-direct-connection-without-mdns-if-already-knowing-device-s-ip*
*Context gathered: 2026-04-09*
