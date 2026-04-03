# Domain Pitfalls

**Domain:** Standalone async Python daemon — Sonoff LAN → InfluxDB 3 writer  
**Researched:** 2026-04-03  
**Confidence:** HIGH (official docs + codebase analysis)

---

## Critical Pitfalls

Mistakes that cause silent data loss, daemon crashes, or require rewrites.

---

### Pitfall 1: Using the Wrong InfluxDB Python Client

**What goes wrong:** Installing `influxdb-client` (the v2 client, package name
`influxdb-client`) instead of `influxdb3-python` (the v3 client, package name
`influxdb3-python`, module `influxdb_client_3`). Both exist on PyPI with
similar names. The v2 client (`influxdb_client.InfluxDBClient`) requires an
`org` argument and uses `/api/v2/write`; InfluxDB 3 Core does not use
organizations and its native endpoint is `/api/v3/write_lp`. Sending v2
payloads to a v3 server returns HTTP 404 or 400 with a misleading error.

**Why it happens:** The packages have almost identical names and the v2 client
is far more widely documented. Search results, StackOverflow answers, and AI
code suggestions default to the v2 client.

**Consequences:** Silent write failures or confusing HTTP errors. If someone
accidentally pins `influxdb-client` instead of `influxdb3-python`, the daemon
appears to start but never writes data.

**Prevention:**
- Pin `influxdb3-python` (not `influxdb-client`) in `requirements.txt` /
  `pyproject.toml`.
- Import from `influxdb_client_3` — if the import resolves from
  `influxdb_client`, the wrong package is installed.
- In the Dockerfile, verify the installed package with
  `pip show influxdb3-python`.

**Detection:**
- `ModuleNotFoundError: No module named 'influxdb_client_3'` means the v2
  package was installed instead.
- HTTP 404 on `/api/v2/write` from an InfluxDB 3 server.

**Phase:** Implement InfluxDB writer (any phase introducing the write client).

**Sources:** https://github.com/InfluxCommunity/influxdb3-python (official v3 Python client — `influxdb3-python`)  
https://influxdb-client.readthedocs.io/en/latest/ (v2 client — `influxdb-client` — wrong for this project)

---

### Pitfall 2: InfluxDB 3 Terminology Mismatch (bucket → database, org gone)

**What goes wrong:** InfluxDB v2 uses `bucket` and `org`; InfluxDB 3 uses
`database`. The v3 Python client (`InfluxDBClient3`) takes a `database`
parameter, not a `bucket`. If code is copied from v2 examples and `bucket=` is
passed, the client silently ignores it or raises a `TypeError`. Likewise, v2
requires `org=` for every write call; v3 has no org concept.

**Why it happens:** Almost all community examples, blog posts, and
StackOverflow answers were written for v2. The v3 docs are newer and less
indexed.

**Consequences:** `TypeError` at runtime, or writes go to the wrong database if
the parameter name mismatch is silent.

**Prevention:**
- Use the v3 client constructor: `InfluxDBClient3(host=..., database=...,
  token=...)` — no `org`, no `bucket`.
- Pass `write_precision` to `client.write()` if not nanosecond; the v3 API
  defaults to `"ns"` (nanosecond). v3 also supports `"auto"` precision
  detection on the `/api/v3/write_lp` endpoint.
- Do not use `from influxdb_client import InfluxDBClient` (v2 import) anywhere
  in new code.

**Detection:**
- `TypeError: __init__() got unexpected keyword argument 'org'` when
  constructing v3 client.
- Data missing in InfluxDB after writes that returned no error.

**Phase:** Implement InfluxDB writer.

**Sources:** https://docs.influxdata.com/influxdb3/core/write-data/ (official InfluxDB 3 Core write docs)

---

### Pitfall 3: InfluxDB 3 Write Client is Synchronous by Default; `await` Does Nothing

**What goes wrong:** `InfluxDBClient3.write()` is synchronous (blocking). In an
asyncio event loop, calling `client.write(point)` without `await` blocks the
entire event loop for the duration of the HTTP request. This manifests as mDNS
callbacks and LAN responses being delayed or dropped while a write is in
progress.

**Why it happens:** The `influxdb3-python` client wraps an HTTP request
synchronously. The "async write" mode in the older v2 client (`influxdb-client`)
used RxPY observables and does not exist in the v3 client. Developers assume
`async` because the surrounding application uses `asyncio`.

**Consequences:** LAN device responses time out under write pressure. mDNS
browser callbacks pile up. Device state updates are missed.

**Prevention:**
- Wrap every `client.write()` call in `asyncio.get_event_loop().run_in_executor(None, client.write, point)` or `asyncio.to_thread(client.write, point)` (Python 3.9+).
- Alternatively, construct the InfluxDB write as a raw `aiohttp` `POST` to
  `/api/v3/write_lp` since `aiohttp` is already a project dependency.
- **Preferred:** Use `asyncio.to_thread(client.write, point)` — cleanest and
  available in Python 3.9+ (project targets 3.11+).

**Detection:**
- Event loop latency spikes visible in logs during write operations.
- LAN device responses intermittently timing out.

**Phase:** Implement InfluxDB writer; must be addressed before integration test.

**Sources:** https://github.com/InfluxCommunity/influxdb3-python (README — no async write method listed)  
https://docs.influxdata.com/influxdb3/core/reference/client-libraries/v3/python/ (synchronous write mode is the default and only supported mode for simple writes)

---

### Pitfall 4: mDNS Multicast Blocked in Docker Bridge Network Mode

**What goes wrong:** By default Docker containers run in bridge network mode
(`docker0`). mDNS (Multicast DNS) uses UDP multicast to `224.0.0.251:5353`.
Multicast packets do NOT cross the bridge boundary — they are silently dropped
at the bridge interface. The `zeroconf` library will start without error, join
the multicast group, and then receive zero packets. The daemon logs no errors
but discovers no devices.

**Why it happens:** Docker bridge networking deliberately does not forward
multicast at Layer 2. The `--publish` flag cannot help because multicast is not
a unicast port mapping problem. This is a common trap: the daemon appears to
work (InfluxDB writes succeed for manually configured IPs) but mDNS discovery is
silently dead.

**Consequences:** No automatic device discovery. If the project evolves to use
mDNS-based discovery, bridge mode will be a complete blocker.

**Prevention:**
- **Use `--network host`** (Linux Docker Engine only). With host network mode,
  the container shares the host's network stack, multicast works, and mDNS
  behaves identically to a bare-metal process.
- Document `network_mode: host` in `docker-compose.yml` and the README as a
  **required** setting, not optional.
- Note: `host` network mode is Linux-only. Docker Desktop on macOS/Windows has
  limited support (layer-4 only as of Docker Desktop 4.34). For local
  development on macOS, run the daemon directly with `python` rather than in a
  container, or use a Linux VM.

**Detection:**
- `zeroconf` starts, no `ServiceBrowser` callbacks fire, no devices discovered.
- Container running in bridge mode: `docker inspect <id> | grep NetworkMode`
  shows `"bridge"`.

**Phase:** Docker packaging / deployment phase. Must be validated before any
mDNS reliance.

**Sources:** https://docs.docker.com/network/host/ (host network driver — required for multicast/mDNS)

---

### Pitfall 5: HA Import Chain Residue Breaks Standalone Startup

**What goes wrong:** `local.py` (the LAN transport layer) imports from
`custom_components.sonoff.core.ewelink` and indirectly from HA internals
(`homeassistant.core`, `homeassistant.helpers`). Any import that is not
explicitly cleaned will raise `ModuleNotFoundError` at startup because the
`homeassistant` package is not installed in the standalone environment.

The import chain in the original codebase:

```
local.py → __init__.py (XRegistry) → base.py → (possibly) HA helpers
devices.py → entity.py → homeassistant.helpers.entity
```

Even one surviving `from homeassistant.xxx import ...` anywhere in the imported
module tree will crash the process at `import` time, before any main code runs.

**Why it happens:** HA custom integrations deeply interleave HA types into the
module-level import graph. Removing HA imports requires tracing the full import
graph of every module you keep, not just the top-level module.

**Consequences:** `ModuleNotFoundError: No module named 'homeassistant'` at
startup. Nothing runs.

**Prevention:**
- Build the import graph before any code changes: `python -c "import
  custom_components.sonoff.core.ewelink.local"` in the HA environment and note
  every transitive import.
- After each module you copy/adapt, verify with
  `python -c "import <new_module>"` in a clean venv that has **no**
  `homeassistant` package installed.
- Particular risk areas from codebase analysis:
  - `base.py` — uses `XRegistry` which has HA dispatcher references
  - `__init__.py` — `dispatcher_connect`/`dispatcher_send` are HA helpers
  - `devices.py` — all entity classes derive from `XEntity` which imports
    `homeassistant.helpers.entity`
  - `xutils.py` — `unwrap_cached_properties()` works around HA's
    `CachedProperties` metaclass; safe to remove in standalone context
- Replace the HA dispatcher with a simple Python `asyncio.Queue` or
  `collections.defaultdict(list)` callbacks dict.

**Detection:**
- `ModuleNotFoundError: No module named 'homeassistant'` in startup logs.
- `ImportError: cannot import name 'dispatcher_connect' from ...`

**Phase:** Strip HA code / create standalone entrypoint — first implementation phase.

**Sources:** `.planning/codebase/INTEGRATIONS.md` (import chain analysis)  
`.planning/codebase/CONCERNS.md` (HA metaclass dependency: `unwrap_cached_properties`)

---

### Pitfall 6: `zeroconf` Acquired from HA's Shared Instance — Must Be Self-Owned

**What goes wrong:** The original `local.py` acquires the `Zeroconf` instance
via `zeroconf.async_get_instance(hass)` — a shared HA singleton. In standalone
mode, there is no `hass` object and no HA zeroconf singleton. If the extracted
code calls `async_get_instance(hass)`, it crashes with `AttributeError` or
`NameError`. Even if the call is replaced naively with `Zeroconf()`, using
multiple `Zeroconf()` instances (one per run or per restart of a component) can
cause "Already registered" errors if `close()` is not called on the old
instance.

**Why it happens:** HA manages zeroconf as a shared resource because multiple
integrations share the same mDNS interface. In standalone mode, the daemon owns
it exclusively, but the lifecycle (open once, close on SIGTERM) must be
explicitly managed.

**Prevention:**
- Instantiate a single `Zeroconf()` at daemon startup (not per-device).
- Store the instance at the application level; pass it into
  `XRegistryLocal` (or its replacement).
- On SIGTERM/SIGINT, call `zeroconf_instance.close()` before stopping the
  event loop.
- Do not create more than one `Zeroconf()` instance in the process.

**Detection:**
- `Error: [Errno 98] Address already in use` on `5353/udp` when restarting
  without `close()`.
- Device discovery works once and then stops after a restart within the same
  process run.

**Phase:** Strip HA code / create standalone entrypoint.

---

## Moderate Pitfalls

Mistakes that cause correctness issues, data gaps, or maintenance headaches.

---

### Pitfall 7: `asyncio.get_event_loop()` Deprecation Breaks on Python 3.10+

**What goes wrong:** `cloud.py` (and possibly other carry-over code) calls
`asyncio.get_event_loop()` at module level or inside coroutines. On Python
3.10+, this emits `DeprecationWarning`. On Python 3.12+, calling
`get_event_loop()` when there is no running loop raises `RuntimeError`.

The standalone daemon targets Python 3.11+. If any carry-over code calls
`asyncio.get_event_loop()` outside a running loop (e.g., at module import
time), it will raise `RuntimeError` and crash startup.

**Prevention:**
- Replace all `asyncio.get_event_loop()` with `asyncio.get_running_loop()`
  inside coroutines.
- For code that runs before an event loop exists, use
  `asyncio.new_event_loop()` explicitly and then `asyncio.set_event_loop()`.
- Grep the extracted files: `grep -r "get_event_loop" .` — every hit is a
  risk.

**Detection:**
- `DeprecationWarning: There is no current event loop` in Python 3.10–3.11 logs.
- `RuntimeError: no running event loop` on Python 3.12+ at startup.

**Phase:** Strip HA code / create standalone entrypoint.

**Sources:** `.planning/codebase/CONCERNS.md` (Known Bugs — `asyncio.get_event_loop()` deprecated)

---

### Pitfall 8: LAN Send Uses Recursive Retry — Stack Overflow on Flaky Network

**What goes wrong:** `local.py`'s `send()` method retries `ECONNRESET` errors
recursively up to 10 times. On a flaky network with consecutive failures, this
creates 10-deep recursive call stacks. In an asyncio daemon that may handle
multiple devices simultaneously, deep recursion + asyncio task scheduling can
cause `RecursionError`.

**Prevention:**
- Convert to an iterative loop: `for attempt in range(MAX_RETRIES):` with
  `await asyncio.sleep(backoff)` between attempts.
- Add a `try/except RecursionError` as a safety net until refactored.

**Detection:**
- `RecursionError: maximum recursion depth exceeded` in logs when multiple
  devices are unreachable simultaneously.

**Phase:** Any phase that exercises the LAN send path under load.

**Sources:** `.planning/codebase/CONCERNS.md` (Fragile Areas — LAN send recursion)

---

### Pitfall 9: `UNIQUE_DEVICES` and Class-Level State Survive Process Restarts in Tests

**What goes wrong:** The original codebase stores device state in module-level
globals (`UNIQUE_DEVICES`) and class-level attributes (`XRegistry.config`,
`XRegistryBase._sequence`). In unit tests that import and re-use these modules
across test cases, stale state from a prior test leaks into the next. Device
sequence numbers collide, config overwrites happen silently.

**Prevention:**
- Move all global/class-level state to instance attributes in the new standalone
  code. The simplified `XRegistry` (or equivalent) should have no class-level
  mutable state.
- In tests, construct fresh instances per test case; do not rely on module-level
  reset.

**Detection:**
- Tests pass individually but fail when run as a suite.
- Sequence numbers start at unexpected values in test assertions.

**Phase:** Test authoring / any phase that introduces unit tests.

**Sources:** `.planning/codebase/CONCERNS.md` (Fragile Areas — `UNIQUE_DEVICES`, class attributes)

---

### Pitfall 10: Field Type Consistency — InfluxDB 3 Rejects Type Changes After First Write

**What goes wrong:** InfluxDB 3 infers field types from the first write to a
table. If the Sonoff device sends `power` as an integer (`"power": 0`) on the
first event and then as a float (`"power": 23.5`) later, the second write fails
with a schema conflict error. InfluxDB 3 does not auto-promote types.

Additionally, the Sonoff device may report energy fields as strings in some
firmware versions (e.g., `"power": "23.5"`). Passing a string to an
integer/float field creates a type mismatch.

**Prevention:**
- Always coerce metric values to `float` before writing:
  `float(params.get("power", 0.0))`. Never pass raw values from device payloads
  directly to `Point.field()`.
- Write a smoke test on first startup that verifies the schema of the target
  measurement is compatible, or simply accept that the table will be created
  correctly if all writes coerce types consistently.
- Log a warning (do not crash) when a value cannot be coerced to float.

**Detection:**
- HTTP 400 on write with message like `"field type conflict"` or
  `"schema mismatch"`.
- One device writes successfully; a second device with different firmware causes
  write failures for the same measurement.

**Phase:** Implement energy metrics extraction + InfluxDB writer.

---

### Pitfall 11: InfluxDB 3 Write Errors are Swallowed by Default Batch Mode

**What goes wrong:** If `InfluxDBClient3` is initialized without
`write_client_options` (synchronous mode, which is the default), write errors
raise `InfluxDBError`. If it is initialized in batch mode without `error_callback`
and `retry_callback`, write failures are silently dropped — the daemon appears
healthy but data is lost.

The project specification requires "log-and-continue on InfluxDB write failure."
This is easy to implement in synchronous mode (`try/except InfluxDBError`) but
requires explicit callbacks in batch mode.

**Prevention:**
- Use synchronous write mode for this daemon (one event → one immediate write,
  as required by the spec). Synchronous mode raises exceptions that are
  catchable with `try/except InfluxDBError`.
- Wrap every `client.write()` call (via `asyncio.to_thread`) in a
  `try/except influxdb_client_3.InfluxDBError` block.
- Log the error with `logger.error("InfluxDB write failed: %s", e)` and
  continue — do not re-raise.

**Detection:**
- Write errors not appearing in logs.
- `InfluxDB write failed` log messages absent when InfluxDB is intentionally
  stopped.

**Phase:** Implement InfluxDB writer.

**Sources:** https://docs.influxdata.com/influxdb3/core/reference/client-libraries/v3/python/ (synchronous vs. batch mode — error handling differences)

---

### Pitfall 12: AES Decryption Silently Produces Garbage on Incorrect `devicekey`

**What goes wrong:** If a device's `devicekey` is wrong (e.g., fat-fingered in
the config env var), `decrypt()` in `local.py` does not raise an exception —
AES-CBC decryption with a wrong key simply returns random bytes. The subsequent
`json.loads()` call will raise `json.JSONDecodeError`, which if not caught,
kills the task handling that device's updates.

**Prevention:**
- Wrap `json.loads(decrypt(...))` in `try/except json.JSONDecodeError`.
- Log `"Decryption failed for device {device_id} — check devicekey"` at
  `ERROR` level and skip the event; do not crash the task.
- During startup config validation, log a `WARNING` if any device has an
  explicitly configured `devicekey` that looks invalid (too short, wrong
  format).

**Detection:**
- `json.JSONDecodeError` in logs for a specific device while others work.
- Device events silently disappearing from InfluxDB while the daemon continues
  running.

**Phase:** Implement LAN protocol handler / device config loading.

**Sources:** `.planning/codebase/INTEGRATIONS.md` (LAN encryption — MD5 key derivation, AES-CBC)

---

## Minor Pitfalls

---

### Pitfall 13: asyncio Task Leak from Unawaited Coroutines

**What goes wrong:** If `asyncio.create_task()` is used to fire-and-forget a
coroutine (e.g., write to InfluxDB from an mDNS callback), the task must be
kept alive or it will be garbage-collected mid-execution. In Python 3.11+,
tasks that are garbage-collected while running emit `RuntimeWarning: coroutine
... was never awaited` or the task silently disappears.

**Prevention:**
- Store strong references to tasks created with `asyncio.create_task()`:
  use a `set` at the application level and remove tasks on completion via
  `task.add_done_callback(task_set.discard)`.
- Prefer `asyncio.to_thread()` directly in the callback path and `await` it
  where possible.

**Detection:**
- `RuntimeWarning: Enable tracemalloc to get the object allocation traceback`
  in logs.
- Writes sporadically missing from InfluxDB with no error logs.

**Phase:** Implement async daemon main loop.

---

### Pitfall 14: Docker `--network host` Not Supported on macOS/Windows Docker Desktop (Layer 4 Limitation)

**What goes wrong:** Docker Desktop on macOS/Windows supports host networking
only at layer 4 (TCP/UDP) starting from version 4.34. mDNS multicast operates
at layer 3/2. Even with host networking enabled on Docker Desktop, multicast
may not work correctly on macOS/Windows hosts. This is a platform limitation, not
a Docker bug.

**Prevention:**
- Document that the Docker image **must run on a Linux host** (e.g., a
  Raspberry Pi, Linux server, or Linux VM).
- For development on macOS, run the daemon directly (not in Docker) or use a
  Linux VM with bridged networking.
- CI environments should test on Linux only.

**Detection:**
- No device discovery on macOS Docker Desktop even with `--network host`.
- Works on a Linux host with the identical `docker run` command.

**Phase:** Docker packaging / deployment.

**Sources:** https://docs.docker.com/network/host/ (Docker Desktop host networking limitations)

---

### Pitfall 15: `zeroconf` `ServiceBrowser` Callbacks Run in a Separate Thread

**What goes wrong:** `zeroconf`'s `ServiceBrowser` calls its `add_service` and
`remove_service` callbacks from a background thread (not from the asyncio event
loop thread). If the callback directly mutates asyncio data structures or calls
`asyncio.create_task()` without `call_soon_threadsafe`, this causes race
conditions and `RuntimeError: non-thread-safe operation invoked on an event
loop`.

**Prevention:**
- Use `loop.call_soon_threadsafe(asyncio.ensure_future, coro)` or
  `asyncio.run_coroutine_threadsafe(coro, loop)` from within the
  `ServiceBrowser` callback.
- Or, use `AsyncServiceBrowser` (available in python-zeroconf) which provides
  coroutine-based callbacks that run natively on the asyncio event loop —
  eliminating the thread boundary entirely.

**Detection:**
- `RuntimeError: non-thread-safe operation` in logs when a device is discovered.
- Intermittent crashes only when a new device comes online, not during steady
  state.

**Phase:** Strip HA code / create standalone entrypoint (zeroconf lifecycle).

---

### Pitfall 16: Missing SIGTERM Handling Causes Dirty Container Shutdown

**What goes wrong:** Docker sends `SIGTERM` to PID 1 when stopping a container.
If the Python process does not handle `SIGTERM`, Docker waits for the default
timeout (10 seconds) then sends `SIGKILL`. A `SIGKILL` shutdown:
- Does not flush any in-flight InfluxDB writes.
- Does not call `zeroconf.close()`, leaving the multicast socket open briefly.
- Causes Docker to log `Killed` rather than `Exited (0)`.

**Prevention:**
- Register `signal.signal(signal.SIGTERM, handler)` early in `main()`.
- The handler should call `loop.stop()` or set a `stop_event` that the main
  loop monitors.
- Ensure `zeroconf.close()` and `influxdb_client.close()` are called in
  shutdown cleanup (e.g., via `try/finally` in `main()`).

**Detection:**
- `docker stop` takes 10+ seconds (timeout before SIGKILL).
- Container logs end abruptly without a clean shutdown message.

**Phase:** Daemon entrypoint / Docker packaging.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Strip HA imports / create entrypoint | Import chain residue (#5), HA zeroconf singleton (#6), `get_event_loop` deprecation (#7) | Run `python -c "import <module>"` in clean venv after each file edit |
| Implement LAN transport (local.py adaptation) | Recursive retry (#8), AES decryption silent failure (#12), zeroconf thread safety (#15) | Wrap retry in loop; wrap decrypt in try/except |
| Implement InfluxDB writer | Wrong client package (#1), v2/v3 terminology mismatch (#2), blocking write in event loop (#3), type consistency (#10), silent batch errors (#11) | Use `influxdb3-python`; coerce all values to float; wrap write in `asyncio.to_thread` |
| Docker packaging | mDNS multicast in bridge mode (#4), macOS host networking limits (#14), missing SIGTERM (#16) | Require `--network host`; document Linux-only requirement |
| Test authoring | Class-level state leakage (#9), task leak (#13) | Fresh instances per test; store task references |

---

## Sources

- https://github.com/InfluxCommunity/influxdb3-python — Official InfluxDB 3 Python client (v3)
- https://influxdb-client.readthedocs.io/en/latest/ — InfluxDB v2 Python client (NOT for this project)
- https://docs.influxdata.com/influxdb3/core/write-data/ — InfluxDB 3 Core write API docs
- https://docs.influxdata.com/influxdb3/core/reference/client-libraries/v3/python/ — v3 Python client reference
- https://docs.docker.com/network/host/ — Docker host network driver (required for mDNS)
- https://python-zeroconf.readthedocs.io/en/latest/ — python-zeroconf library docs
- `.planning/codebase/CONCERNS.md` — Codebase audit (fragile areas, known bugs)
- `.planning/codebase/INTEGRATIONS.md` — Import chain and external integration audit
