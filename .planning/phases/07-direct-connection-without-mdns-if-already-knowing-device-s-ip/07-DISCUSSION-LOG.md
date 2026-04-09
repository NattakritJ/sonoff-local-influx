# Phase 7: Direct Connection without mDNS - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 07-direct-connection-without-mdns-if-already-knowing-device-s-ip
**Areas discussed:** Polling architecture, getState response format, Startup + failure handling

---

## Polling Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Per-device asyncio task | One `asyncio.create_task()` per static-IP device, each running its own `while True` loop | ✓ |
| Single shared polling loop | One loop iterates all static-IP devices sequentially on each interval | |
| Separate PollingDaemon class | New class alongside SonoffDaemon for clean separation | |

**User's choice:** Per-device asyncio task

---

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse XRegistryLocal.send() + SIGNAL_UPDATE | Polling tasks call existing send(), which dispatches SIGNAL_UPDATE; `_on_update()` unchanged | ✓ |
| Direct aiohttp in SonoffDaemon | Poll via raw aiohttp HTTP POST directly; parse response inline | |

**User's choice:** Reuse XRegistryLocal.send() + SIGNAL_UPDATE

---

| Option | Description | Selected |
|--------|-------------|----------|
| Both modes in SonoffDaemon | mDNS and polling coexist; mDNS starts only if at least one device lacks ip | ✓ |
| ip device disables mDNS | Any device with ip disables mDNS for the whole daemon | |

**User's choice:** Both modes in SonoffDaemon

---

## getState Response Format

| Option | Description | Selected |
|--------|-------------|----------|
| Let local.py send() handle it | send() already parses getState responses and dispatches SIGNAL_UPDATE | ✓ |
| Parse response manually | Parse HTTP response body in polling loop; construct msg dict manually | |

**User's choice:** Let local.py send() handle it

---

| Option | Description | Selected |
|--------|-------------|----------|
| Construct XDevice from DeviceConfig + ip | Polling task builds a minimal XDevice inline from config fields | ✓ |
| New poll_device() helper in XRegistryLocal | XRegistryLocal gets a new method that builds XDevice internally | |

**User's choice:** Construct XDevice from DeviceConfig + ip

---

## Startup + Failure Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Warn on first failure, no startup check | Polling tasks start immediately; log WARNING on first failure | ✓ |
| Fail-fast at startup if unreachable | Attempt getState on each static-IP device at startup; exit on failure | |

**User's choice:** Warn on first failure, no startup check (consistent with mDNS pattern)

---

| Option | Description | Selected |
|--------|-------------|----------|
| LOG WARNING, keep polling | Transient offline expected; WARNING per cycle, retry every interval | ✓ |
| LOG ERROR, keep polling | Higher visibility but noisy for intermittent reboots | |
| Escalate to ERROR after N failures | More nuanced but more complex | |

**User's choice:** LOG WARNING, keep polling

---

| Option | Description | Selected |
|--------|-------------|----------|
| Cancel polling tasks on SIGTERM | Tasks cancelled via asyncio.CancelledError; same as heartbeat pattern | ✓ |
| Drain in-flight requests before cancel | Wait for active HTTP requests to complete before cancelling | |

**User's choice:** Cancel polling tasks on SIGTERM

---

## Agent's Discretion

- Whether to add `localtype` to the inline XDevice dict (optional field)
- Exact startup log line wording for poll interval confirmation
- Whether polling task's `while True` loop adds broad `except Exception` or relies on send() return codes
- Exact placement of ip_devices / mdns_devices split in SonoffDaemon.run()

## Deferred Ideas

None — discussion stayed within phase scope.
