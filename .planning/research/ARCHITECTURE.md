# Architecture Patterns

**Domain:** Standalone Python asyncio daemon — LAN IoT telemetry → InfluxDB 3
**Researched:** 2026-04-03
**Overall confidence:** HIGH (based on direct source inspection + official docs)

---

## Recommended Architecture

### Overview

A flat, three-layer pipeline with no HA imports:

```
┌─────────────────────────────────────────────────────────────────┐
│  Config Layer  (pydantic-settings / env vars at startup)        │
└────────────────────────────┬────────────────────────────────────┘
                             │ Settings object (read-once)
┌────────────────────────────▼────────────────────────────────────┐
│  Daemon Core  (sonoff_influx/daemon.py)                         │
│  • Owns aiohttp.ClientSession                                   │
│  • Owns InfluxDBWriter                                          │
│  • Owns LanTransport (XRegistryLocal)                           │
│  • Owns Zeroconf instance                                       │
│  • Wires dispatcher: SIGNAL_UPDATE → on_lan_update()            │
│  • Handles SIGTERM/SIGINT → graceful shutdown                   │
└──────────┬─────────────────────────────────────────────────────┘
           │ dispatcher_send(SIGNAL_UPDATE, msg)
┌──────────▼──────────────────────┐   ┌───────────────────────────┐
│  LAN Transport                  │   │  InfluxDB Writer           │
│  (ewelink/local.py — kept)      │   │  (sonoff_influx/writer.py) │
│  XRegistryBase + XRegistryLocal │   │  InfluxDBClient3           │
│  mDNS browser, AES decrypt,     │   │  write(Point) per event    │
│  HTTP send (for getState polls) │   │  log-and-continue on error │
└─────────────────────────────────┘   └───────────────────────────┘
```

### Component Boundaries

| Component | File(s) | Responsibility | Communicates With |
|-----------|---------|---------------|-------------------|
| **Config** | `sonoff_influx/config.py` | Load + validate all env vars at startup; immutable after init | Daemon (passed in) |
| **Daemon** | `sonoff_influx/daemon.py` | Event loop owner; lifecycle (start/stop); wires transport to writer | Config, LanTransport, InfluxDBWriter |
| **LAN Transport** | `ewelink/local.py`, `ewelink/base.py` | mDNS discovery, AES decrypt, HTTP POST | Daemon (via dispatcher) |
| **Params Extractor** | `sonoff_influx/extractor.py` | Extract energy fields from raw params dict; returns `EnergyReading` or `None` | Daemon (called inline) |
| **InfluxDB Writer** | `sonoff_influx/writer.py` | Construct `Point`, write to InfluxDB 3 synchronously; log on error | Daemon (called inline) |
| **Entrypoint** | `sonoff_influx/__main__.py` | `asyncio.run(main())` — parse config, build daemon, run | Daemon |

---

## Suggested New File Structure

```
sonoff-influx/
├── sonoff_influx/
│   ├── __init__.py              # package marker (empty)
│   ├── __main__.py              # entrypoint: asyncio.run(main())
│   ├── config.py                # Settings(BaseSettings) — env var schema
│   ├── daemon.py                # SonoffDaemon — owns loop, wires all components
│   ├── extractor.py             # extract_energy(params: dict) → EnergyReading | None
│   └── writer.py                # InfluxWriter — wraps InfluxDBClient3
├── ewelink/                     # STRIPPED copy of core/ewelink/ (3 files only)
│   ├── __init__.py              # empty or re-exports XDevice
│   ├── base.py                  # XRegistryBase, XDevice TypedDict, dispatcher  ← KEEP (no changes)
│   └── local.py                 # XRegistryLocal — mDNS + HTTP + AES decrypt    ← KEEP (strip HA import only)
├── tests/
│   ├── test_extractor.py        # unit tests for energy param extraction
│   └── test_writer.py           # unit tests for InfluxWriter (mock client)
├── Dockerfile
├── pyproject.toml               # or requirements.txt
└── .env.example                 # documentation of all env vars
```

**Key structural decision:** `ewelink/` lives at the project root level, not nested under `custom_components/sonoff/core/`. This severs the HA import chain entirely. Only `base.py` and `local.py` are carried over — no `cloud.py`, no `camera.py`.

---

## Data Flow: mDNS Event → InfluxDB Write

```
Step 1: STARTUP
  __main__.py
    └─▶ config = Settings()                  # reads env vars, validates
    └─▶ daemon = SonoffDaemon(config)
    └─▶ asyncio.run(daemon.run())

Step 2: DAEMON INIT (inside daemon.run())
  SonoffDaemon.run()
    ├─▶ session = aiohttp.ClientSession()
    ├─▶ writer = InfluxWriter(config)        # creates InfluxDBClient3
    ├─▶ transport = XRegistryLocal(session)
    ├─▶ transport.dispatcher_connect(SIGNAL_UPDATE, self.on_lan_update)
    ├─▶ zeroconf = Zeroconf()
    ├─▶ transport.start(zeroconf)            # starts AsyncServiceBrowser
    └─▶ await asyncio.Event().wait()         # sleep until SIGTERM

Step 3: DEVICE DISCOVERED / UPDATED (push from mDNS)
  XRegistryLocal._handler1()               # zeroconf callback (sync)
    └─▶ asyncio.create_task(_handler2())
  XRegistryLocal._handler2()               # async: fetch ServiceInfo
    └─▶ _handler3(deviceid, host, data)
  XRegistryLocal._handler3()               # parse TXT record
    └─▶ dispatcher_send(SIGNAL_UPDATE, msg) # msg = {deviceid, host, params?/data+iv}

Step 4: DAEMON RECEIVES UPDATE
  SonoffDaemon.on_lan_update(msg: dict)
    ├─▶ device = self.devices.get(msg["deviceid"])
    │   └─▶ if not in config.devices: log and return  # unknown device, ignore
    ├─▶ if msg has "data" (encrypted):
    │   └─▶ params = XRegistryLocal.decrypt_msg(msg, device["devicekey"])
    └─▶ else: params = msg["params"]
    └─▶ reading = extract_energy(params, device)
    └─▶ if reading: await writer.write(reading)

Step 5: INFLUXDB WRITE
  InfluxWriter.write(reading: EnergyReading)
    ├─▶ point = Point(reading.measurement)
    │       .tag("device_id", reading.device_id)
    │       .field("power", reading.power)      # if present
    │       .field("voltage", reading.voltage)  # if present
    │       .field("current", reading.current)  # if present
    │       .field("energy", reading.energy)    # if present
    │       .time(reading.timestamp, "s")
    ├─▶ try: client.write(record=point, write_precision="s")
    └─▶ except Exception as e: logger.error("write failed: %s", e)
                                # daemon continues — no crash

Step 6: SHUTDOWN (SIGTERM or SIGINT)
  signal handler sets shutdown_event
  daemon.run() exits Event().wait()
    └─▶ transport.stop()         # cancels AsyncServiceBrowser
    └─▶ session.close()
    └─▶ writer.close()           # closes InfluxDBClient3
    └─▶ zeroconf.close()
```

---

## Existing Files: Keep / Strip / Replace

### KEEP (copy verbatim or near-verbatim)

| File | What to Keep | Notes |
|------|-------------|-------|
| `core/ewelink/base.py` | Entire file | `XRegistryBase`, `XDevice` TypedDict, dispatcher — zero HA imports |
| `core/ewelink/local.py` | Entire file | Only import to remove: `from .base import ...` path changes when relocated; no HA imports in the file itself |

### STRIP (delete entirely — no code reuse)

| File | Why |
|------|-----|
| `custom_components/sonoff/__init__.py` | HA component lifecycle — `async_setup`, `async_setup_entry` |
| `custom_components/sonoff/config_flow.py` | HA GUI config wizard |
| `custom_components/sonoff/core/entity.py` | `XEntity(Entity)` — HA entity base |
| `custom_components/sonoff/core/ewelink/cloud.py` | eWeLink cloud — out of scope |
| `custom_components/sonoff/core/ewelink/camera.py` | UDP camera PTZ — out of scope |
| `custom_components/sonoff/core/ewelink/__init__.py` | `XRegistry` orchestrator — cloud+LAN+entity wiring; replaced by `SonoffDaemon` |
| All platform files (`switch.py`, `sensor.py`, `light.py`, …) | HA entity domains |
| `core/devices.py` | UIID→entity-class mapping (imports all HA platform files) |
| `manifest.json`, `services.yaml`, `translations/`, `hacs.json` | HA metadata |
| `diagnostics.py`, `system_health.py` | HA diagnostic endpoints |
| `core/const.py` | HA-specific constants (`DOMAIN`, `CONF_*`) |
| `core/xutils.py` | aiohttp session factory with HA source_hash — replace with plain `aiohttp.ClientSession()` |

### REPLACE (new equivalent, same purpose)

| Old | New | Difference |
|-----|-----|------------|
| `XRegistry` (orchestrator) | `SonoffDaemon` in `sonoff_influx/daemon.py` | No cloud, no entity system, no HA; owns lifecycle and wires transport → writer |
| `XEntity.set_state(params)` | `extract_energy(params)` + `InfluxWriter.write()` | No HA state machine; pure extraction + write |
| `async_setup_entry` / HA config entry | `Settings(BaseSettings)` in `config.py` | Env vars, not HA config entries |
| `homeassistant.core.callback` dispatcher | Existing `XRegistryBase.dispatcher_send/connect` | Already plain Python — no change needed |

---

## Patterns to Follow

### Pattern 1: Graceful Shutdown via asyncio.Event + signal handler

**What:** Install `SIGTERM`/`SIGINT` handlers that set an `asyncio.Event`; the main coroutine `await`s the event instead of `run_forever()`. On signal, cleanup runs in the `finally` block.

**Why:** `asyncio.run()` on Python 3.11+ handles `SIGINT` via `CancelledError` automatically, but `SIGTERM` (the Docker stop signal) requires explicit installation. Using an `asyncio.Event` keeps cleanup deterministic.

```python
# sonoff_influx/daemon.py
import asyncio, signal, logging

_LOGGER = logging.getLogger(__name__)

class SonoffDaemon:
    def __init__(self, config):
        self._config = config
        self._shutdown = asyncio.Event()

    async def run(self):
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown.set)

        async with aiohttp.ClientSession() as session:
            writer = InfluxWriter(self._config)
            transport = XRegistryLocal(session)
            transport.dispatcher_connect(SIGNAL_UPDATE, self._on_update)
            zc = Zeroconf()
            try:
                transport.start(zc)
                _LOGGER.info("Daemon started — waiting for LAN events")
                await self._shutdown.wait()
            finally:
                _LOGGER.info("Shutting down")
                await transport.stop()
                zc.close()
                writer.close()
```

**Confidence:** HIGH — verified against Python 3.11+ docs (`loop.add_signal_handler`).

---

### Pattern 2: Config via pydantic-settings BaseSettings

**What:** A single `Settings(BaseSettings)` class defines all env vars. Validated at startup; if required fields are missing the process exits with a clear error before any I/O starts.

**Why:** pydantic-settings reads `os.environ` automatically, produces typed fields, and prints human-readable validation errors. It handles the `DEVICES` list as JSON (`list[DeviceConfig]`) via the default JSON env parsing.

```python
# sonoff_influx/config.py
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class DeviceConfig(BaseModel):
    device_id: str
    devicekey: str | None = None   # None = DIY/plain device
    name: str | None = None        # overrides measurement name

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SONOFF_")

    influxdb_url: str              # e.g. http://influxdb:8086
    influxdb_token: str
    influxdb_database: str
    devices: list[DeviceConfig]    # JSON array: [{"device_id":"...","devicekey":"..."}]
    log_level: str = "INFO"
```

Env vars:
```
SONOFF_INFLUXDB_URL=http://influxdb:8086
SONOFF_INFLUXDB_TOKEN=my-token
SONOFF_INFLUXDB_DATABASE=sonoff
SONOFF_DEVICES='[{"device_id":"1000xxxxxx","devicekey":"abc123"},{"device_id":"1001yyyyyy"}]'
```

**Confidence:** HIGH — pydantic-settings docs confirm list-of-models is parsed from JSON env var by default.

---

### Pattern 3: InfluxDB 3 Write — Synchronous Point per Event

**What:** Use `influxdb3-python` with default synchronous write mode (no `write_client_options`). Build a `Point` per energy reading and call `client.write()` immediately. Catch all exceptions, log, and continue.

**Why:** The project requirement is "immediate write per event, no buffering". Synchronous mode in `influxdb3-python` writes immediately without retry — that's the correct semantic for this use case. Retry logic would cause duplicate writes; we prefer log-and-lose.

```python
# sonoff_influx/writer.py
import logging
from dataclasses import dataclass
from influxdb_client_3 import InfluxDBClient3, Point

_LOGGER = logging.getLogger(__name__)

@dataclass
class EnergyReading:
    measurement: str       # device_id or device name
    device_id: str
    timestamp_ns: int      # nanoseconds since epoch
    power: float | None = None
    voltage: float | None = None
    current: float | None = None
    energy: float | None = None

class InfluxWriter:
    def __init__(self, config):
        self._client = InfluxDBClient3(
            host=config.influxdb_url,
            database=config.influxdb_database,
            token=config.influxdb_token,
        )

    def write(self, reading: EnergyReading) -> None:
        point = Point(reading.measurement).tag("device_id", reading.device_id)
        if reading.power is not None:
            point = point.field("power", reading.power)
        if reading.voltage is not None:
            point = point.field("voltage", reading.voltage)
        if reading.current is not None:
            point = point.field("current", reading.current)
        if reading.energy is not None:
            point = point.field("energy", reading.energy)
        try:
            self._client.write(record=point)
            _LOGGER.debug("Wrote %s: %s", reading.measurement, reading)
        except Exception as e:
            _LOGGER.error("InfluxDB write failed for %s: %s", reading.device_id, e)

    def close(self) -> None:
        self._client.close()
```

**Important caveat:** `InfluxDBClient3.write()` is synchronous (blocking). Since the daemon runs a single asyncio event loop, blocking calls will stall mDNS event processing. Mitigation: wrap the write in `asyncio.get_event_loop().run_in_executor(None, self._client.write, point)` to push it to the thread pool executor. This is the correct pattern for any synchronous I/O called from an async context.

**Confidence:** HIGH — verified `InfluxDBClient3` synchronous mode in official InfluxDB 3 Python client docs.

---

### Pattern 4: Energy Params Extraction (Replaces devices.py / XSensor)

**What:** A pure function `extract_energy(params: dict, device_cfg: DeviceConfig) -> EnergyReading | None` handles all known energy param shapes. Returns `None` if no energy fields are present — caller skips the write.

**Why:** Decoupling extraction from the write step enables unit testing without InfluxDB. It also avoids reproducing the entire `devices.py` UIID→class system — we only need to recognise energy keys, not device types.

Known energy param keys from `core/devices.py` analysis:
- `power` (float, multiply 0.01 for some UIIDs)
- `voltage` (float, multiply 0.01 for some UIIDs)  
- `current` (float, multiply 0.001 for some UIIDs)
- `energyUsage` (dict with `monthKwh`, `weekKwh`, `todayKwh`)
- `hundredDayData` (encoded daily energy, complex)
- `actPow_00`, `actPow_01` (per-channel power for dual-relay devices)

The extractor needs to handle at minimum `power`, `voltage`, `current`, `energyUsage.todayKwh`.

---

### Pattern 5: Device Registry (Replaces XRegistry.devices)

**What:** A plain `dict[str, DeviceConfig]` built from config at startup. `on_lan_update` checks `msg["deviceid"]` against this dict to decide whether to process or skip. Devices not in config are silently ignored (no auto-discovery).

**Why:** Matches the project requirement "explicit config list only". Simpler than the original `XRegistry.devices` which was dynamically populated via cloud API or DIY detection.

```python
# in SonoffDaemon.__init__
self._devices: dict[str, DeviceConfig] = {
    d.device_id: d for d in config.devices
}
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Importing anything from `custom_components/sonoff/`

**What:** Importing `core/devices.py`, `core/entity.py`, or any platform file.

**Why bad:** `devices.py` imports all 12 platform files which import `homeassistant.*`. A single transitive import pulls in the entire HA dependency tree (~15 packages). The daemon would fail to start without a functioning HA environment.

**Instead:** Copy only `ewelink/base.py` and `ewelink/local.py` to a new `ewelink/` package at the project root. No other files from the original codebase are needed.

---

### Anti-Pattern 2: Using XRegistry as-is

**What:** Instantiating the original `XRegistry` (from `core/ewelink/__init__.py`) and connecting a custom "entity".

**Why bad:** `XRegistry.__init__` creates `XRegistryCloud(session)` and immediately wires up cloud signals. Even if cloud is never started, the import of `cloud.py` will succeed but adds dead weight. More importantly, `XRegistry.setup_devices()` imports `core/devices.py` which imports all HA platform files — same anti-pattern 1 problem.

**Instead:** `SonoffDaemon` replaces `XRegistry`. It directly creates `XRegistryLocal`, wires `SIGNAL_UPDATE`, and handles decryption via `XRegistryLocal.decrypt_msg`.

---

### Anti-Pattern 3: Blocking InfluxDB write on the event loop

**What:** Calling `client.write(point)` directly in an `async` method without executor offload.

**Why bad:** `influxdb3-python` `write()` in synchronous mode is blocking. The asyncio event loop is single-threaded; a blocking call during `on_lan_update` will delay all pending mDNS callbacks and potentially cause `asyncio.TimeoutError` in `_handler2` (which has a 3000 ms zeroconf request timeout).

**Instead:** Use `loop.run_in_executor(None, writer.write, reading)` or wrap the write in `asyncio.to_thread(writer.write, reading)` (Python 3.9+).

---

### Anti-Pattern 4: Re-implementing the XRegistryBase dispatcher

**What:** Writing a new pub/sub or callback system to replace `dispatcher_connect`/`dispatcher_send`.

**Why bad:** `XRegistryBase.dispatcher` is a plain `dict[str, list[Callable]]` — 30 lines total. It works correctly and is already tested in the upstream project. Replacing it adds risk with no benefit.

**Instead:** Keep `base.py` as-is. The dispatcher is the clean interface between LAN transport and the daemon callback.

---

### Anti-Pattern 5: Zeroconf running in a daemon thread with asyncio

**What:** Using the synchronous `Zeroconf` + `ServiceBrowser` (not the async variants).

**Why bad:** The existing code already uses `AsyncServiceBrowser` and `AsyncServiceInfo` from `zeroconf.asyncio`. Using the synchronous variants would require a daemon thread, creating thread-safety issues with the asyncio event loop (particularly the `asyncio.create_task()` calls inside `_handler1`).

**Instead:** Keep the existing `AsyncServiceBrowser` usage. `Zeroconf()` (sync instance) can still be used as the underlying zeroconf instance — only the browser and info lookups need to be async.

---

## Build Order Implications

The component structure implies this build sequence for the roadmap:

1. **Config layer first** — `config.py` with `Settings(BaseSettings)`. Nothing else can start without a valid config. Enables early validation failure with clear error messages.

2. **Transport layer second** — Copy `ewelink/base.py` and `ewelink/local.py`, remove the one relative import path (`from .base import ...` → `from ewelink.base import ...`). Write a smoke-test that starts the mDNS browser and receives one event.

3. **Extractor third** — `extractor.py` is pure logic (no I/O), fully unit-testable in isolation. Build and test before wiring to writer.

4. **Writer fourth** — `writer.py` wraps `InfluxDBClient3`. Can be tested against a real InfluxDB 3 instance or mocked. Confirm synchronous write works, then add executor offload.

5. **Daemon last** — `daemon.py` wires all components together. Integration test: start daemon, trigger a fake mDNS event, assert InfluxDB receives the point.

6. **Docker** — `Dockerfile` is the final deliverable layer; depends on all of the above being stable.

---

## Scalability Considerations

This project is single-host, single-network — scalability is not a primary concern. However:

| Concern | At current scale (1–20 devices) | Notes |
|---------|--------------------------------|-------|
| Event throughput | mDNS push is ~1 Hz per device max | Synchronous write per event is fine |
| InfluxDB write latency | <100 ms typical on LAN | Executor offload prevents stalling mDNS loop |
| Memory | O(n_devices) for device dict | Trivial |
| Config size | `SONOFF_DEVICES` JSON env var | Works up to ~100 devices; beyond that, a config file would be cleaner |

---

## Sources

| Source | Confidence | Used For |
|--------|------------|----------|
| `custom_components/sonoff/core/ewelink/local.py` (direct read) | HIGH | Transport layer design, handler pipeline, dispatcher |
| `custom_components/sonoff/core/ewelink/base.py` (direct read) | HIGH | Dispatcher API, XDevice TypedDict |
| `custom_components/sonoff/core/ewelink/__init__.py` (direct read) | HIGH | XRegistry teardown, local_update decryption logic |
| Python 3.11 asyncio docs (asyncio-runner.html) | HIGH | SIGTERM handling, `loop.add_signal_handler` |
| InfluxDB 3 Python client docs (influxdata.com) | HIGH | `InfluxDBClient3` write API, synchronous mode, `Point` construction |
| pydantic-settings docs (pydantic.dev) | HIGH | `BaseSettings`, env var loading, list-of-models from JSON env |

---

*Architecture research: 2026-04-03*
